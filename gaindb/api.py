"""gaindb/api.py — CLI·GUI·AVD 공유 순수 함수 API 계층.

비파괴·무출력. 분석 결과를 dict 로만 반환한다(파일 수정·stdout 출력 없음).
실제 게인 적용은 apply_gain.apply_track_gain(파괴적, 별개 단계)이 담당하되,
GUI 편의를 위해 apply_file_track_gain 래퍼로 감싼다(목표 dB→offset 변환을
이 계층에 가둔다).

파괴적 파일 액션(undo·태그 제거)도 GUI 편의를 위해 얇게 감싼다:
  undo_file_gain    : 원본 mp3gain -u / GUI UndoFileGain 대응. 태그의 undo
                      정보로 프레임 게인을 되돌린다(디코딩 없음). 되돌린 스텝
                      수를 반환해, 호출자가 shift_after_apply 로 표시를 갱신한다.
  remove_file_tags  : 원본 mp3gain -s d / GUI DeleteFileTags 대응. APE(+use_id3
                      면 ID3v2) mp3gain 태그를 제거한다(디코딩 없음).
이 둘은 change_gain_and_tag/remove_* 를 그대로 부르므로 CLI(-u/-s d)와 동일
결과를 낸다. 원본 DoFileAction 이 undo/deletetag 를 한 껍데기로 분기한 것과
같은 성격의 통합 진입점이다.

원본 MP3GainGUI 의 DispJunk / Mp3Info.cls 표시 로직을 재현하되 두 가지를
의도적으로 조정한다(근거는 CLAUDE.md 10 진척 로그 참조):
  1) Track Gain 표시 제수는 원본 화면용 근사 1.505 대신 정밀값 5*log10(2) 사용.
     (원본조차 실제 계산 RadioMp3Gain/AlterDb 에는 정밀값을 쓴다.)
  2) 스텝 반올림은 원본 GUI 의 banker's rounding 대신 적용 경로와 동일한
     db_to_steps(round-half-away-from-zero)를 사용한다. 이로써 "표시된 스텝·
     dB·클립 = 실제 apply_track_gain 이 적용할 결과"가 항상 일치한다(표시Only
     정책의 핵심). 0.5 경계의 극소수 곡에서 원본 GUI 표시와 1스텝 다를 수 있다.

GUI 무계산 원칙:
  GUI 는 계산하지 않는다. 목표 dB 와 경로만 넘기고, 돌려받은 dict 를 표시만
  한다. 89·offset·db_to_steps·clip 판정식은 전부 이 모듈 내부(특히
  _compute_display)에만 존재한다. 표시값을 만드는 진입점(analyze_file,
  read_file_tags, recompute_target, shift_after_apply)은 모두 _compute_display
  하나를 공유하며, apply_track_gain 의 steps 도 동일한 offset·db_to_steps 를
  쓰므로 표시와 적용이 구조적으로 일치한다.

  GUI 가 아는 함수는 일곱:
    read_file_tags(path, target_db)        # 추가 시 태그만 읽어 표시(가볍다)
    analyze_file(path, target_db, ...)     # 최초 분석(무겁다: decode+scan)
    recompute_target(result, target_db)    # 목표 변경 시 즉시 재표시(가볍다)
    apply_file_track_gain(path, target_db) # 실제 적용(무겁다)
    shift_after_apply(result, steps)        # 적용/undo 후 재표시(가볍다)
    undo_file_gain(path, ...)               # 태그 기반 원복(가볍다: 디코딩 없음)
    remove_file_tags(path, ...)             # mp3gain 태그 제거(가볍다)

취소·진행률(GUI 대응):
  analyze_file 은 무거운 decode 단계에서 should_cancel(취소 콜백)과
  on_progress(파일 내부 진행률 콜백, 0~1)를 그대로 decode_pcm 에 넘긴다.
  취소되면 decode 계층이 DecodeCancelled(=DecodeError 하위)를 던지므로,
  호출자(워커)는 이를 실패가 아닌 정상 취소로 구분해 처리한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from gaindb.decode import decode_pcm_streaming, _probe_stream_info
from gaindb.analysis import (
    TrackAnalyzer,
    db_to_steps,
    DB_PER_STEP,
    NOT_ENOUGH_SAMPLES,
)
from gaindb.writer import scan_gain
from gaindb.tag import (
    read_mp3gain_tags,
    change_gain_and_tag,
    remove_mp3gain_ape_tag,
)
# AVD 벤더링: 원본은 apply_gain.py 가 리포 루트 모듈이라 `from apply_gain ...`
# 였으나, AVD 에서는 apply_gain.py 를 gaindb/ 패키지 안으로 벤더링했으므로
# 패키지 내부 절대경로로 가져온다.
from gaindb.apply_gain import apply_track_gain


# 목표 음량 기준: mp3gain 내부 89 dB ReplayGain 레퍼런스.
# (상대값이며 절대 SPL/LUFS 가 아니다. GUI 라벨/툴팁에 명시할 것.)
DEFAULT_TARGET_DB = 89.0


def _compute_display(track_db: float, curr_max_amp,
                     target_db: float) -> dict:
    """표시값 계산의 유일한 출처(원본 DispJunk / RadioMp3Gain 재현).

    track_db     : 89dB 기준 raw dB (원본 mvarRadiodBGain, mod 미포함).
    curr_max_amp : peak * 32768 (원본 CurrMaxAmp). None 이면 clip "none".
    target_db    : 사용자 지정 목표 음량(89dB 기준 상대).

    Volume(원본 DispJunk): 89 + ModifydBGain - RadiodBGain = 89 - raw. 즉
    modify_db 가 상쇄되는 "곡의 현재 실제 음량". 적용 후 shift_after_apply 가
    raw 를 낮춰 목표로 수렴한다.
    steps / clip 판정: 원본 RadioMp3Gain·DispJunk 와 동일하게 modify_db 반영.
    원본 clip 의 possible 분기는 (83 - (target - raw)) 를 쓰므로, Volume(=89-raw)
    이 아니라 target 기준 값을 별도로 계산해 넣는다.
    """
    modify_db = target_db - DEFAULT_TARGET_DB

    # 원본 DispJunk: Volume = 89 - raw (ModifydBGain 상쇄).
    volume = DEFAULT_TARGET_DB - track_db
    # 원본 clip 판정에 쓰이는 target 기준 볼륨 = DEFAULTTARGET + ModifydBGain - raw.
    target_volume = DEFAULT_TARGET_DB + modify_db - track_db

    steps = db_to_steps(track_db + modify_db)
    track_gain_db = steps * DB_PER_STEP

    if curr_max_amp is None:
        clip_state = "none"
    elif curr_max_amp * (2.0 ** (steps / 4.0)) > 32767.0:
        # 원본: CurrMaxAmp * 2^((83 - target_volume)/6.0206) > 32767 → possible.
        if curr_max_amp * (2.0 ** ((83.0 - target_volume) / 6.0206)) > 32767.0:
            clip_state = "possible"
        else:
            clip_state = "definite"
    else:
        clip_state = "none"

    return {
        "volume": round(volume, 1),
        "steps": steps,
        "track_gain_db": round(track_gain_db, 1),
        "clip_state": clip_state,
    }


def read_file_tags(path: str, target_db: float = DEFAULT_TARGET_DB) -> dict:
    """파일의 기존 mp3gain 태그만 읽어 GUI 표시용 결과를 반환한다(비파괴, 무출력).

    원본 MP3GainGUI 의 AddSingleFile 이 파일 추가 시 `mp3gain /o /s c` 로
    태그만 조회(디코딩 없음)해 볼륨을 즉시 표시하던 동작에 대응한다.
    파일 끝부분의 태그만 읽으므로 매우 가볍다(디코딩 없음).

    태그에 track_gain 이 있으면 그 raw dB(원본 RadiodBGain 대응)로 표시값을
    만든다. peak(track_peak)이 있으면 curr_max_amp 로 clip 도 판정하고, 없으면
    clip 은 "none"(원본 DispJunk 가 CurrMaxAmp 없을 때 clip 비우는 동작).

    반환 dict(analyze_file 과 같은 키 구조, status 만 다름):
      status : "ok"     — 태그에서 track_gain 을 읽어 표시값을 만듦(분석 불필요).
               "no_tag" — 태그가 없거나 track_gain 미보유(분석 필요, 원본 NOREALNUM).
      나머지 키(target_db·track_db·volume·steps·track_gain_db·peak·
      curr_max_amp·min_gain·max_gain·clip_state)는 analyze_file 과 동일.
    """
    info, _file_tags = read_mp3gain_tags(path)

    if not info.have_track_gain:
        # 원본 RadiodBGain = NOREALNUM: 분석해야 값이 나온다.
        return {
            "status": "no_tag", "target_db": target_db,
            "track_db": None, "volume": None, "steps": None,
            "track_gain_db": None, "peak": None, "curr_max_amp": None,
            "min_gain": None, "max_gain": None, "clip_state": "none",
        }

    track_db = info.track_gain  # 89dB 기준 raw dB (원본 RadiodBGain)

    if info.have_track_peak:
        peak = info.track_peak
        curr_max_amp = peak * 32768.0
    else:
        peak = None
        curr_max_amp = None

    disp = _compute_display(track_db, curr_max_amp, target_db)

    min_gain = info.min_gain if info.have_min_max_gain else None
    max_gain = info.max_gain if info.have_min_max_gain else None

    return {
        "status": "ok",
        "target_db": target_db,
        "track_db": track_db,
        "volume": disp["volume"],
        "steps": disp["steps"],
        "track_gain_db": disp["track_gain_db"],
        "peak": peak,
        "curr_max_amp": None if curr_max_amp is None else round(curr_max_amp),
        "min_gain": min_gain,
        "max_gain": max_gain,
        "clip_state": disp["clip_state"],
    }


def analyze_file(
    path: str,
    target_db: float = DEFAULT_TARGET_DB,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    """한 MP3 를 분석해 GUI 표시용 결과를 반환한다(비파괴, 무출력).

    스트리밍 분석: 곡 전체 PCM 을 메모리에 올리지 않고, decode_pcm_streaming
    이 흘려보내는 청크를 TrackAnalyzer 에 먹여 히스토그램·peak 을 누적한다.
    초장시간 곡(수 시간)도 청크 하나 크기의 메모리로 처리한다. 결과는 일괄
    처리(analyze_track/track_peak)와 수학적으로 동일하다(검증됨).

    target_db: 사용자 지정 목표 음량(89 dB 기준 상대). 예: 96.
    should_cancel: 디코딩 청크마다 확인되는 취소 콜백. True 면 decode 계층이
      DecodeCancelled(=DecodeError 하위)를 던진다(기본 None = 취소 없음).
      취소는 실패가 아니므로 호출자(워커)가 예외로 구분해 처리해야 한다.
    on_progress: 디코딩 청크마다 호출되는 파일 내부 진행률 콜백(0.0~1.0,
      duration 기반 근사). 분석·스캔 단계는 디코딩 대비 짧아 진행률에 포함하지
      않는다(기본 None = 콜백 없음).

    반환 dict:
      status        : "ok" | "not_enough_samples"
      target_db     : 이 결과가 계산된 목표 음량(재계산·적용 후 이동에 사용).
      track_db      : 89 dB 기준 raw dB (원본 mvarRadiodBGain, mod 미포함).
      volume        : 예측 결과 음량 = target - track_db (원본 DispJunk Volume).
      steps         : 적용 정수 스텝 (db_to_steps, 적용 경로와 동일).
      track_gain_db : steps * DB_PER_STEP (실제 적용될 dB 변화량).
      peak          : 정규화 peak (0~1, 1.0 초과 가능).
      curr_max_amp  : peak * 32768 (원본 CurrMaxAmp, 클립 기준값).
      min_gain,max_gain : scan_gain 결과(프레임 global_gain min/max).
      clip_state    : "none"(검정) | "possible"(파랑 ???) | "definite"(빨강 Y).
    """
    # analyzer 생성에 필요한 sample_rate 를 먼저 확보(ffprobe, 매우 가벼움).
    sample_rate, _channels, _duration = _probe_stream_info(Path(path))
    analyzer = TrackAnalyzer(sample_rate)

    # 스트리밍 디코드: 청크를 analyzer 에 먹이고 버린다(곡 전체를 안 모음).
    decode_pcm_streaming(
        path, on_chunk=analyzer.feed,
        should_cancel=should_cancel, on_progress=on_progress)

    track_db = analyzer.result()
    if track_db is NOT_ENOUGH_SAMPLES:
        return {
            "status": "not_enough_samples", "target_db": target_db,
            "track_db": None, "volume": None, "steps": None,
            "track_gain_db": None, "peak": None, "curr_max_amp": None,
            "min_gain": None, "max_gain": None, "clip_state": "none",
        }

    peak = analyzer.peak_normalized()
    min_gain, max_gain = scan_gain(path)

    curr_max_amp = peak * 32768.0
    disp = _compute_display(track_db, curr_max_amp, target_db)

    return {
        "status": "ok",
        "target_db": target_db,
        "track_db": track_db,
        "volume": disp["volume"],
        "steps": disp["steps"],
        "track_gain_db": disp["track_gain_db"],
        "peak": peak,
        "curr_max_amp": round(curr_max_amp),
        "min_gain": min_gain,
        "max_gain": max_gain,
        "clip_state": disp["clip_state"],
    }


def recompute_target(result: dict, target_db: float) -> dict:
    """목표 음량만 바뀌었을 때 표시값을 다시 계산한다(재분석 없음, 가볍다).

    result 안의 raw track_db·curr_max_amp 를 씨앗으로 _compute_display 를
    호출해 volume·steps·track_gain_db·clip_state 만 갱신한다. raw 값은 그대로
    유지한다. 원본 DispJunk 가 target 변경 시 재분석 없이 다시 그리던 동작과
    정합적이다.

    result: analyze_file/read_file_tags(또는 이전 recompute/shift)가 돌려준 dict.
    target_db: 새 목표 음량.

    반환: 새 target 기준 표시값이 갱신된 새 dict(원본 dict 는 변경하지 않음).
    """
    updated = dict(result)
    updated["target_db"] = target_db

    if result.get("status") != "ok" or result.get("track_db") is None:
        # 분석 불가/미태그 상태는 표시값을 만들 수 없다. target 만 바꿔 돌려준다.
        return updated

    cma = result.get("curr_max_amp")
    disp = _compute_display(result["track_db"],
                            None if cma is None else float(cma),
                            target_db)
    updated["volume"] = disp["volume"]
    updated["steps"] = disp["steps"]
    updated["track_gain_db"] = disp["track_gain_db"]
    updated["clip_state"] = disp["clip_state"]
    return updated


def shift_after_apply(result: dict, applied_steps: int) -> dict:
    """게인 적용/undo 후 표시값을 갱신한다(재분석 없음, 가볍다).

    원본 RadioGain 이 적용 성공 후 `AlterDb(-steps * FIVELOG10TWO)` 로
    수행하는 두 갱신을 재현한다(undo 도 원본 UndoFileGain 이 되돌린 스텝으로
    같은 AlterDb 를 부른다 — applied_steps 에 undo 스텝을 넘기면 그대로 원복):
      1) mvarRadiodBGain += (-steps * FIVELOG10TWO) → raw track_db 를 낮춘다.
         raw 는 "89 로 맞추는 데 필요한 게인"이므로, 곡을 applied_steps 만큼
         키웠으면 그만큼 덜 필요하다(빼기). 낮춘 raw 로 재계산하면 steps 는 0,
         Volume(=89-raw)은 목표로 수렴한다. undo 로 음(-)의 스텝이 들어오면
         raw 가 다시 올라가 undo 전 상태로 되돌아간다.
      2) mvarCurrMaxAmp *= 2^(steps/4) → peak(클립 기준)을 실제 적용에 맞춰
         갱신한다. 이걸 빠뜨리면 목표를 올렸다 내렸다 할 때 curr_max_amp 가
         이전 목표의 값으로 남아 clip 표시가 실제 파일과 어긋난다(원본은 매
         적용마다 정확히 갱신함).

    result: 적용 직전의 dict(target_db·track_db·curr_max_amp 포함).
    applied_steps: 방금 적용된 정수 스텝(undo 면 되돌린 스텝, 부호 그대로).
    반환: "적용된 상태"를 반영한 새 dict(원본 dict 는 변경하지 않음).
    """
    updated = dict(result)

    if result.get("status") != "ok" or result.get("track_db") is None:
        return updated

    # (1) 원본 AlterDb: mvarRadiodBGain += (-steps * FIVELOG10TWO). raw 를 낮춘다.
    new_track_db = result["track_db"] - applied_steps * DB_PER_STEP
    updated["track_db"] = new_track_db

    # (2) 원본 AlterDb: mvarCurrMaxAmp *= 2^(steps/4). peak 를 적용에 맞춰 갱신.
    cma = result.get("curr_max_amp")
    if cma is not None:
        new_cma = float(cma) * (2.0 ** (applied_steps / 4.0))
        updated["curr_max_amp"] = round(new_cma)
    else:
        new_cma = None

    target_db = result.get("target_db", DEFAULT_TARGET_DB)
    disp = _compute_display(new_track_db, new_cma, target_db)
    updated["volume"] = disp["volume"]
    updated["steps"] = disp["steps"]
    updated["track_gain_db"] = disp["track_gain_db"]
    updated["clip_state"] = disp["clip_state"]
    return updated


def apply_file_track_gain(path: str, target_db: float = DEFAULT_TARGET_DB,
                          skip_tag: bool = False, use_id3: bool = False,
                          seed: dict | None = None,
                          should_cancel: Callable[[], bool] | None = None,
                          on_progress: Callable[[float], None] | None = None
                          ) -> dict:
    """목표 dB 를 반영해 Track ReplayGain 을 실제 적용한다(파괴적, 무겁다).

    GUI 는 apply_gain.apply_track_gain 을 직접 부르지 않고 이 래퍼를 쓴다.
    목표→offset 변환(target_db - 89)을 여기 안에 가둠으로써 GUI 는 89·offset 을
    모른 채 target_db 만 넘기면 되고, 표시(analyze_file/recompute_target 산출)와
    실제 적용 steps 가 동일한 offset·db_to_steps 를 쓰므로 반드시 일치한다.

    path: 대상 MP3. target_db: 목표 음량(89dB 기준 상대).
    skip_tag / use_id3: apply_track_gain 으로 그대로 전달(원본 -s s / -s i).
    seed: 이미 분석된 표시 result dict(analyze_file/read_file_tags 산출).
      track_db·peak·min_gain·max_gain 이 있으면 apply_track_gain 에 씨앗으로
      넘겨 디코딩·분석·scan 을 건너뛴다(이중 디코딩 제거). None 이면 종전대로
      apply_track_gain 이 직접 디코딩·분석한다.
    should_cancel / on_progress: 적용 단계(scan/apply/change_gain_and_tag)의
      프레임 순회로 통과한다. 초장시간 곡의 취소·진행률을 위해서다.

    반환: apply_track_gain 의 결과 dict(status·db_gain·steps·frames_changed·
          tag_written)를 그대로 돌려준다. GUI 는 status·steps 로 행 상태를
          갱신하고, steps 로 shift_after_apply 를 호출해 재표시한다.
    """
    db_gain_mod = target_db - DEFAULT_TARGET_DB

    seed_db_gain = seed_peak = seed_min_gain = seed_max_gain = None
    if seed and seed.get("status") == "ok" and seed.get("track_db") is not None:
        seed_db_gain = seed.get("track_db")
        seed_peak = seed.get("peak")
        seed_min_gain = seed.get("min_gain")
        seed_max_gain = seed.get("max_gain")

    return apply_track_gain(path, db_gain_mod=db_gain_mod,
                            skip_tag=skip_tag, use_id3=use_id3,
                            seed_db_gain=seed_db_gain, seed_peak=seed_peak,
                            seed_min_gain=seed_min_gain,
                            seed_max_gain=seed_max_gain,
                            should_cancel=should_cancel,
                            on_progress=on_progress)


def undo_file_gain(path: str, use_id3: bool = False,
                   save_timestamp: bool = False) -> dict:
    """저장된 undo 태그로 이전 게인 변경을 되돌린다(파괴적, 가볍다: 디코딩 없음).

    원본 mp3gain -u / MP3GainGUI UndoFileGain 대응. 태그를 읽어 undo 정보가
    있고 값이 0 이 아니면 change_gain_and_tag(undo_left, undo_right, ...)로
    프레임 게인을 되돌린다(CLI _run_undo 와 동일 경로). 디코딩이 없으므로
    가볍다(9번 함정: "적용엔 디코딩 불필요").

    되돌린 스텝(undo_left)을 반환해, 호출자가 shift_after_apply(result,
    undo_steps)로 표시를 갱신하게 한다(원본 UndoFileGain 이 되돌린 gain 으로
    AlterDb 를 부르는 것과 정합). 좌우가 다른(채널 분리) 경우에도 표시는
    left 기준으로 이동한다(원본도 단일 dB 이동만 하고 좌우 분리는 표시에
    반영하지 않음 — MVP 범위에선 좌우 동일 적용이 대부분).

    반환 dict:
      status     : "ok"            — 되돌림 완료(undo_steps 유효).
                   "nothing_to_undo" — undo 태그는 있으나 값이 0(되돌릴 것 없음).
                   "no_undo"       — undo 태그 자체가 없음.
      undo_steps : 되돌린 정수 스텝(undo_left). "ok" 가 아니면 0.
    """
    info, file_tags = read_mp3gain_tags(path, use_id3)

    if not info.have_undo:
        return {"status": "no_undo", "undo_steps": 0}
    if not (info.undo_left or info.undo_right):
        return {"status": "nothing_to_undo", "undo_steps": 0}

    undo_left = info.undo_left
    undo_right = info.undo_right
    change_gain_and_tag(path, undo_left, undo_right, info, file_tags,
                        wrap=info.undo_wrap, save_timestamp=save_timestamp,
                        use_id3=use_id3)
    return {"status": "ok", "undo_steps": undo_left}


def remove_file_tags(path: str, use_id3: bool = False,
                     save_timestamp: bool = False) -> dict:
    """파일의 mp3gain 태그를 제거한다(파괴적, 가볍다: 디코딩 없음).

    원본 mp3gain -s d / MP3GainGUI DeleteFileTags 대응. APE mp3gain/ReplayGain
    필드를 제거하고(다른 APE 필드·꼬리는 보존), use_id3 이면 ID3v2 mp3gain
    프레임도 제거한다(CLI _run_delete_tag 와 동일 경로). 원래 mp3gain 태그가
    없던 파일은 건드리지 않는다(remove_mp3gain_ape_tag 의 dirty 판정).

    반환 dict: {"status": "ok"}. GUI 는 이후 해당 행 result 를 비워(clear_result)
    미분석 상태로 되돌린다 — 태그를 지웠으므로 표시값도 사라지는 게 실제 파일
    상태와 일치한다.
    """
    remove_mp3gain_ape_tag(path, save_timestamp)
    if use_id3:
        from gaindb.id3 import remove_mp3gain_id3_tag
        remove_mp3gain_id3_tag(path, save_timestamp)
    return {"status": "ok"}
