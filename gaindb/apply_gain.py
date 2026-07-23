"""
apply_gain.py - MP3 파일의 global_gain 을 무손실 조정하는 스크립트.

사용법:
    수동:  python apply_gain.py <게인스텝> "<파일.mp3>"
    자동:  python apply_gain.py auto "<파일.mp3>"
    앨범:  python apply_gain.py album "<파일1.mp3>" "<파일2.mp3>" ...

수동 모드: 게인스텝은 정수. 1스텝 = 약 1.5dB. 양수=키우기, 음수=줄이기.
자동 모드: ReplayGain 분석으로 89dB 기준 적정 스텝을 계산해 곡별로 적용한다.
앨범 모드: 여러 곡의 히스토그램을 누적해 앨범 단일 스텝을 산출, 전 곡에 동일 적용.

auto/album 은 원본 mp3gain 의 main 순서를 따른다: 분석으로 89dB 기준 dB·peak·
min/max 를 얻어 태그(info)에 먼저 채우고(원본 허용오차 비교로 dirty 판정),
그 위에서 change_gain_and_tag 가 적용분만큼 재차감하며 태그를 갱신한다.
skip_tag 면 태그를 건드리지 않고 게인만 적용한다(원본 changeGain 분기).

use_id3 면 APE 대신 ID3v2 로 태그를 읽고/쓴다(원본 -s i 동등).

주의: 파일을 직접 수정한다. 되돌리려면 undo(태그 기반) 또는 반대 부호 수동 적용.
클리핑 경고·자동 클립(-k)·클립 질의는 5단계(CLI) 에서 다룬다(합의된 단계 분할).
"""

import sys

from gaindb.decode import decode_pcm
from gaindb.analysis import (
    analyze_track,
    track_histogram,
    track_peak,
    gain_from_histograms,
    db_to_steps,
    NOT_ENOUGH_SAMPLES,
)
from gaindb.writer import apply_gain, scan_gain
from gaindb.tag import (
    read_mp3gain_tags,
    _write_mp3gain_tag,
    change_gain_and_tag,
)

# 원본 허용오차 (main 루프).
_GAIN_EPS = 0.01        # track/album gain: dB
_PEAK_EPS = 3.3         # track peak: ±32768 스케일에서의 차이
_ALBUM_PEAK_EPS = 0.0001  # album peak: 정규화 스케일에서의 차이


def _fill_track_info(info, db_gain, peak, min_gain, max_gain):
    """원본 main 의 track 값 채우기(허용오차 비교 → dirty/세팅).

    db_gain: 89dB 기준 raw dB. peak: 정규화 peak. min/max: scan_gain 결과.
    값을 info 에 채우고, 무언가 바뀌면 info.dirty 를 켠다.
    """
    # track gain: 미보유거나 0.01dB 이상 차이면 갱신.
    if (not info.have_track_gain) or (abs(db_gain - info.track_gain) >= _GAIN_EPS):
        info.dirty = True
        info.have_track_gain = True
        info.track_gain = db_gain

    # min/max global_gain: 미보유거나 불일치면 갱신.
    if min_gain is not None and max_gain is not None:
        if (not info.have_min_max_gain) or (
            info.min_gain != min_gain or info.max_gain != max_gain
        ):
            info.dirty = True
            info.have_min_max_gain = True
            info.min_gain = min_gain
            info.max_gain = max_gain

    # track peak: 미보유거나 ±32768 스케일 3.3 이상 차이면 갱신.
    maxsample = peak * 32768.0
    if (not info.have_track_peak) or (
        abs(maxsample - info.track_peak * 32768.0) >= _PEAK_EPS
    ):
        info.dirty = True
        info.have_track_peak = True
        info.track_peak = maxsample / 32768.0


def _fill_album_info(info, db_gain, album_peak, album_min, album_max):
    """원본 main 의 album 값 채우기(허용오차 비교 → dirty/세팅).

    album_peak 은 곡별 track_peak 의 max(정규화). album_min/max 는 곡별 min/max 의
    min/max. db_gain 은 89dB 기준 album raw dB.
    """
    if (not info.have_album_gain) or (abs(db_gain - info.album_gain) >= _GAIN_EPS):
        info.dirty = True
        info.have_album_gain = True
        info.album_gain = db_gain

    if album_min is not None and album_max is not None:
        if (not info.have_album_min_max_gain) or (
            info.album_min_gain != album_min or info.album_max_gain != album_max
        ):
            info.dirty = True
            info.have_album_min_max_gain = True
            info.album_min_gain = album_min
            info.album_max_gain = album_max

    if (not info.have_album_peak) or (
        abs(album_peak - info.album_peak) >= _ALBUM_PEAK_EPS
    ):
        info.dirty = True
        info.have_album_peak = True
        info.album_peak = album_peak


def apply_track_gain(
    path: str,
    db_gain_mod: float = 0.0,
    mp3_gain_mod: int = 0,
    wrap: bool = False,
    skip_tag: bool = False,
    use_id3: bool = False,
    seed_db_gain: float = None,
    seed_peak: float = None,
    seed_min_gain: int = None,
    seed_max_gain: int = None,
    should_cancel=None,
    on_progress=None,
) -> dict:
    """
    한 MP3 파일에 Track ReplayGain 을 무손실 적용한다(원본 applyTrack 순서).

    흐름: decode → analyze_track(89dB raw dB) + track_peak + scan_gain(min/max)
    → (태그 기록 시) read 로 info 채우기 → dB+mod → 스텝 양자화 + mp3_gain_mod
    → change_gain_and_tag(적용분 재차감) 또는 skip_tag 시 apply_gain.

    use_id3 면 APE 대신 ID3v2 경로로 태그를 읽고/쓴다(원본 -s i).

    씨앗 주입(GUI 이중 디코딩 제거): seed_db_gain·seed_peak·seed_min_gain·
    seed_max_gain 을 모두 주면 decode/analyze/track_peak/scan_gain 을 건너뛰고
    그 값을 그대로 쓴다. GUI 는 Track Analysis(또는 태그 읽기)에서 이미 이
    값들을 확보하므로, 적용 시 같은 곡을 다시 디코딩하지 않는다. 결과 수치는
    재계산과 동일하다(같은 값 재사용). 씨앗을 안 주면(기본 None) 종전대로
    디코딩·분석·scan 을 수행한다 → CLI 경로 동작 불변.
    (seed_min_gain/seed_max_gain 은 None 이 유효 값일 수 있어 '주어졌는지'는
     db_gain·peak 유무로 판단하고, min/max 는 그때만 씨앗을 신뢰한다.)

    should_cancel/on_progress: 적용 단계(scan_gain·apply_gain·change_gain_and_tag)
    로 통과한다. 초장시간 곡의 프레임 순회 중 취소·진행률을 위해서다. 취소 시
    writer.GainCancelled 가 전파되며, 그 시점에 파일은 원본 그대로다.

    반환 dict:
      - status: "ok" | "no_change" | "not_enough_samples"
      - db_gain: 분석 dB(89dB 기준). not_enough_samples 면 None.
      - steps: 적용한 정수 스텝. not_enough_samples 면 None.
      - frames_changed: 실제 수정한 프레임 수.
      - tag_written: 태그를 기록했으면 True.
    """
    have_seed = (seed_db_gain is not None) and (seed_peak is not None)

    if have_seed:
        # 이미 분석된 값 재사용: 디코딩·분석·track_peak 을 건너뛴다.
        db_gain = seed_db_gain
        peak = seed_peak
        # min/max 도 씨앗이 있으면 scan_gain 을 생략. 없으면 여기서만 스캔.
        if seed_min_gain is not None and seed_max_gain is not None:
            min_gain, max_gain = seed_min_gain, seed_max_gain
        else:
            min_gain, max_gain = scan_gain(
                path, should_cancel=should_cancel, on_progress=on_progress)
    else:
        left, right, sample_rate = decode_pcm(path)

        db_gain = analyze_track(left, right, sample_rate)
        if db_gain is NOT_ENOUGH_SAMPLES:
            return {
                "status": "not_enough_samples",
                "db_gain": None,
                "steps": None,
                "frames_changed": 0,
                "tag_written": False,
            }

        peak = track_peak(left, right)
        del left, right
        min_gain, max_gain = scan_gain(path)

    # 태그 기록 모드면 기존 태그를 읽어 track 값으로 채운다(원본 순서).
    info = None
    file_tags = None
    if not skip_tag:
        info, file_tags = read_mp3gain_tags(path, use_id3)
        _fill_track_info(info, db_gain, peak, min_gain, max_gain)

    # 89dB raw dB 에 dB 보정을 더한 뒤 정수 스텝으로 양자화(원본 순서).
    steps = db_to_steps(db_gain + db_gain_mod) + mp3_gain_mod

    if steps == 0:
        # 게인 변화 없음. 태그가 dirty 면 태그만 기록(원본 동작).
        tag_written = False
        if (not skip_tag) and info.dirty:
            _write_mp3gain_tag(path, info, file_tags, use_id3=use_id3)
            tag_written = True
        return {
            "status": "no_change",
            "db_gain": db_gain,
            "steps": 0,
            "frames_changed": 0,
            "tag_written": tag_written,
        }

    if skip_tag:
        changed = apply_gain(path, steps, wrap=wrap,
                             should_cancel=should_cancel, on_progress=on_progress)
        return {
            "status": "ok",
            "db_gain": db_gain,
            "steps": steps,
            "frames_changed": changed,
            "tag_written": False,
        }

    # change_gain_and_tag 가 게인 적용 + undo 누적 + 적용분 재차감 + 태그 기록.
    change_gain_and_tag(path, steps, steps, info, file_tags, wrap=wrap,
                        use_id3=use_id3,
                        should_cancel=should_cancel, on_progress=on_progress)
    return {
        "status": "ok",
        "db_gain": db_gain,
        "steps": steps,
        "frames_changed": None,  # change_gain_and_tag 는 프레임 수를 따로 안 돌려줌
        "tag_written": True,
    }


def _apply_one_album_file(
    path: str,
    steps: int,
    db_gain,
    album_db,
    track_db,
    peak,
    min_gain,
    max_gain,
    album_peak,
    album_min,
    album_max,
    wrap: bool = False,
    skip_tag: bool = False,
    use_id3: bool = False,
    should_cancel=None,
    on_progress=None,
) -> dict:
    """앨범 게인 적용의 곡별 본체(CLI apply_album_gain 과 GUI api 가 공유).

    원본 album 곡별 루프와 동일: 태그 기록 모드면 기존 태그를 읽어 track 값과
    album 값을 둘 다 채운 뒤(track 먼저, album 다음), 정해진 그룹 공통 steps 를
    적용한다. steps==0 이면 dirty 태그만 기록하고 오디오는 안 건드린다.

    steps 는 그룹 공통값(호출자가 db_to_steps(album_db + mod)로 미리 계산해
    넘긴다) — 전 곡 동일 스텝이 원본 앨범 게인의 핵심(상대 음량 보존).

    track_db 가 NOT_ENOUGH_SAMPLES 면 그 곡의 track 값은 채우지 않고 album 값만
    채운다(원본 동일: track 분석 실패해도 album 은 진행).

    should_cancel/on_progress: 적용 프레임 순회로 통과(초장시간 곡 취소·진행률).

    반환 dict: {"path", "frames_changed", "tag_written"}.
    """
    info = None
    file_tags = None
    if not skip_tag:
        info, file_tags = read_mp3gain_tags(path, use_id3)
        if track_db is not NOT_ENOUGH_SAMPLES:
            _fill_track_info(info, track_db, peak, min_gain, max_gain)
        _fill_album_info(info, album_db, album_peak, album_min, album_max)

    if steps == 0:
        tag_written = False
        if (not skip_tag) and info.dirty:
            _write_mp3gain_tag(path, info, file_tags, use_id3=use_id3)
            tag_written = True
        return {"path": path, "frames_changed": 0, "tag_written": tag_written}

    if skip_tag:
        changed = apply_gain(path, steps, wrap=wrap,
                             should_cancel=should_cancel, on_progress=on_progress)
        return {"path": path, "frames_changed": changed, "tag_written": False}

    change_gain_and_tag(path, steps, steps, info, file_tags, wrap=wrap,
                        use_id3=use_id3,
                        should_cancel=should_cancel, on_progress=on_progress)
    return {"path": path, "frames_changed": None, "tag_written": True}


def apply_album_gain(
    paths,
    db_gain_mod: float = 0.0,
    mp3_gain_mod: int = 0,
    wrap: bool = False,
    skip_tag: bool = False,
    use_id3: bool = False,
) -> dict:
    """
    여러 MP3 파일에 Album ReplayGain 을 무손실 적용한다(원본 album 순서).

    흐름: 각 곡 decode → 히스토그램 누적 + 곡별 track_peak/min/max 수집 →
    album dB(누적) + album_peak(곡별 peak 의 max) + album_min/max(곡별 min/max
    의 min/max) → 각 곡 read 로 track+album 값 채우기 → 스텝 양자화 →
    전 곡에 동일 스텝을 change_gain_and_tag(또는 skip_tag 시 apply_gain) 적용.

    곡별 적용 본체는 _apply_one_album_file 로 추출해 GUI api 경로와 공유한다
    (태그 결과가 정확히 일치하도록). 이 CLI 경로는 종전대로 통짜 decode_pcm 을
    쓴다(결과 불변). 스트리밍·씨앗·취소가 필요한 GUI 는 api 계층이 담당한다.

    use_id3 면 APE 대신 ID3v2 경로로 태그를 읽고/쓴다(원본 -s i).

    반환 dict:
      - status: "ok" | "no_change" | "not_enough_samples"
      - db_gain: 앨범 분석 dB(89dB 기준). not_enough_samples 면 None.
      - steps: 적용한 정수 스텝. not_enough_samples 면 None.
      - per_file: [{"path": str, ...}] 순서는 입력 순.
    """
    histograms = []
    # 곡별 분석 결과 보관(track 값 채우기·album 누적용).
    per = []  # [{"path", "track_db", "peak", "min", "max"}]
    for path in paths:
        left, right, sample_rate = decode_pcm(path)
        histograms.append(track_histogram(left, right, sample_rate))
        track_db = analyze_track(left, right, sample_rate)
        peak = track_peak(left, right)
        del left, right
        min_gain, max_gain = scan_gain(path)
        per.append({
            "path": path,
            "track_db": track_db,
            "peak": peak,
            "min": min_gain,
            "max": max_gain,
        })

    db_gain = gain_from_histograms(histograms)
    if db_gain is NOT_ENOUGH_SAMPLES:
        return {
            "status": "not_enough_samples",
            "db_gain": None,
            "steps": None,
            "per_file": [{"path": p, "frames_changed": 0} for p in paths],
        }

    # album peak = 곡별 track_peak 의 max, album min/max = 곡별 min/max 의 min/max.
    album_peak, album_min, album_max = _album_aggregate(per)

    steps = db_to_steps(db_gain + db_gain_mod) + mp3_gain_mod

    per_file = []
    for item in per:
        per_file.append(_apply_one_album_file(
            item["path"], steps, db_gain, db_gain, item["track_db"],
            item["peak"], item["min"], item["max"],
            album_peak, album_min, album_max,
            wrap=wrap, skip_tag=skip_tag, use_id3=use_id3,
        ))

    status = "no_change" if steps == 0 else "ok"
    return {
        "status": status,
        "db_gain": db_gain,
        "steps": steps,
        "per_file": per_file,
    }


def _album_aggregate(per):
    """곡별 결과 리스트에서 앨범 peak/min/max 를 집계한다.

    album_peak = 곡별 track_peak 의 max(정규화).
    album_min/max = 곡별 min/max 의 min/max(global_gain 0~255).
    per 각 항목은 "peak"/"min"/"max" 키를 가진 dict. min/max 가 None 인 곡은
    집계에서 제외한다. 반환: (album_peak, album_min, album_max).
    """
    album_peak = 0.0
    album_max = 0
    album_min = 255
    for item in per:
        if item["peak"] > album_peak:
            album_peak = item["peak"]
        if item["max"] is not None and item["max"] > album_max:
            album_max = item["max"]
        if item["min"] is not None and item["min"] < album_min:
            album_min = item["min"]
    return album_peak, album_min, album_max


def _run_manual(change: int, path: str) -> int:
    count = apply_gain(path, change)
    print(f"{path}")
    print(f"Applied gain {change:+d} steps (about {change * 1.5:+.1f} dB): "
          f"{count} frames modified")
    return 0


def _run_auto(path: str) -> int:
    result = apply_track_gain(path)
    print(f"{path}")
    if result["status"] == "not_enough_samples":
        print("Not enough samples to analyze. No changes applied.")
        return 1
    if result["status"] == "no_change":
        msg = (
            f"Analysis gain {result['db_gain']:+.2f} dB -> 0 steps. "
            "Already at target loudness; no change."
        )
        if result["tag_written"]:
            msg += " (tag updated only)"
        print(msg)
        return 0
    steps = result["steps"]
    print(
        f"Analysis gain {result['db_gain']:+.2f} dB -> {steps:+d} steps "
        f"(about {steps * 1.5:+.1f} dB) applied, tag updated."
    )
    return 0


def _run_album(paths) -> int:
    result = apply_album_gain(paths)
    if result["status"] == "not_enough_samples":
        print("Not enough samples across the album. No changes applied.")
        return 1

    steps = result["steps"]
    if result["status"] == "no_change":
        print(
            f"Album gain {result['db_gain']:+.2f} dB -> 0 steps. "
            "No gain change (tag updated if needed). Per-file results:"
        )
    else:
        print(
            f"Album gain {result['db_gain']:+.2f} dB -> {steps:+d} steps "
            f"(about {steps * 1.5:+.1f} dB) applied. Per-file results:"
        )
    for item in result["per_file"]:
        fc = item.get("frames_changed")
        fc_str = f"{fc} frames modified" if fc is not None else "tag updated"
        print(f"  {item['path']}: {fc_str}")
    return 0


def main(argv):
    if len(argv) < 2:
        print('Usage (manual): python apply_gain.py <gain_steps> "<file.mp3>"')
        print('Usage (auto):   python apply_gain.py auto "<file.mp3>"')
        print('Usage (album):  python apply_gain.py album "<file1.mp3>" "<file2.mp3>" ...')
        return 1

    mode_arg = argv[1]

    if mode_arg.lower() == "album":
        paths = argv[2:]
        if not paths:
            print('Usage (album): python apply_gain.py album "<file1.mp3>" "<file2.mp3>" ...')
            return 1
        return _run_album(paths)

    if mode_arg.lower() == "auto":
        if len(argv) != 3:
            print('Usage (auto): python apply_gain.py auto "<file.mp3>"')
            return 1
        return _run_auto(argv[2])

    # 수동 모드: 첫 인자가 정수 게인스텝.
    if len(argv) != 3:
        print('Usage (manual): python apply_gain.py <gain_steps> "<file.mp3>"')
        return 1

    try:
        change = int(mode_arg)
    except ValueError:
        print("The first argument must be an integer gain step, or 'auto'/'album'.")
        return 1

    return _run_manual(change, argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
