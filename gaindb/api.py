# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""gaindb/api.py — CLI·GUI·AVD 공유 순수 함수 API 계층.

비파괴·무출력. 분석 결과를 dict 로만 반환한다(파일 수정·stdout 출력 없음).
실제 게인 적용은 apply_gain.apply_track_gain(파괴적, 별개 단계)이 담당하되,
GUI 편의를 위해 apply_file_track_gain 래퍼로 감싼다(목표 dB→offset 변환을
이 계층에 가둔다).

파괴적 파일 액션(undo·태그 제거)도 GUI 편의를 위해 얇게 감싼다:
  undo_file_gain    : mp3gain -u 와 동일한 undo(GUI Undo File Gain 배선용).
  remove_file_tags  : mp3gain -s d 와 동일한 태그 제거(GUI Delete File Tags 배선용).

Album 계층(GUI Album Analysis/Album Gain 배선용):
  group_by_album         : 경로들을 폴더(또는 전체) 단위 앨범으로 묶는다.
  analyze_album_file     : 곡 하나를 스트리밍 분석해 그룹 누적용 원재료를 반환.
  album_gain_from_files  : 곡별 원재료를 모아 앨범 dB·peak·min/max 를 산출.
  compute_album_display  : 곡별 result 에 album_* 표시 키를 추가.
  apply_file_album_gain  : 한 곡에 그룹 공통 스텝을 적용하며 track+album 태그
                           를 둘 다 기록(앨범 게인 곡별 적용).

표시 조정(근거 CLAUDE.md 10):
  1) Track Gain 표시 제수는 정밀값 5*log10(2).
  2) 스텝 반올림은 db_to_steps(round-half-away-from-zero) — 표시=적용 일치.

GUI 무계산 원칙: 89·offset·db_to_steps·clip 판정식은 _compute_display 에만
존재. 표시 진입점(analyze_file/read_file_tags/recompute_target/
shift_after_apply/compute_album_display)이 모두 이를 공유한다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from gaindb.decode import decode_pcm_streaming, _probe_stream_info
from gaindb.analysis import (
    TrackAnalyzer,
    analyze_track,
    track_peak,
    db_to_steps,
    DB_PER_STEP,
    NOT_ENOUGH_SAMPLES,
    gain_from_histograms,
)
from gaindb.writer import scan_gain
from gaindb.tag import (
    read_mp3gain_tags,
    change_gain_and_tag,
    remove_mp3gain_ape_tag,
)
from gaindb.apply_gain import apply_track_gain, _apply_one_album_file


# 목표 음량 기준: 89 dB ReplayGain 레퍼런스.
DEFAULT_TARGET_DB = 89.0


def _compute_display(track_db: float, curr_max_amp,
                     target_db: float) -> dict:
    """표시값 계산의 유일한 출처(Volume/Gain/clip 표시값 산출)."""
    modify_db = target_db - DEFAULT_TARGET_DB

    volume = DEFAULT_TARGET_DB - track_db
    target_volume = DEFAULT_TARGET_DB + modify_db - track_db

    steps = db_to_steps(track_db + modify_db)
    track_gain_db = steps * DB_PER_STEP

    if curr_max_amp is None:
        clip_state = "none"
    elif curr_max_amp * (2.0 ** (steps / 4.0)) > 32767.0:
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
    """파일의 기존 mp3gain 태그만 읽어 GUI 표시용 결과를 반환(비파괴)."""
    info, _file_tags = read_mp3gain_tags(path)

    if not info.have_track_gain:
        return {
            "status": "no_tag", "target_db": target_db,
            "track_db": None, "volume": None, "steps": None,
            "track_gain_db": None, "peak": None, "curr_max_amp": None,
            "min_gain": None, "max_gain": None, "clip_state": "none",
        }

    track_db = info.track_gain

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
    """한 MP3 를 스트리밍 분석해 GUI 표시용 결과를 반환한다(비파괴)."""
    sample_rate, _channels, _duration = _probe_stream_info(Path(path))
    analyzer = TrackAnalyzer(sample_rate)

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
    """목표 음량만 바뀌었을 때 표시값을 다시 계산한다(재분석 없음)."""
    updated = dict(result)
    updated["target_db"] = target_db

    if result.get("status") != "ok" or result.get("track_db") is None:
        return updated

    cma = result.get("curr_max_amp")
    disp = _compute_display(result["track_db"],
                            None if cma is None else float(cma),
                            target_db)
    updated["volume"] = disp["volume"]
    updated["steps"] = disp["steps"]
    updated["track_gain_db"] = disp["track_gain_db"]
    updated["clip_state"] = disp["clip_state"]

    if result.get("album_db") is not None:
        adisp = _compute_display(result["album_db"],
                                 None if cma is None else float(cma),
                                 target_db)
        updated["album_volume"] = adisp["volume"]
        updated["album_steps"] = adisp["steps"]
        updated["album_gain_db"] = adisp["track_gain_db"]
        updated["album_clip_state"] = adisp["clip_state"]
    return updated


def shift_after_apply(result: dict, applied_steps: int) -> dict:
    """게인 적용/undo 후 표시값을 갱신한다(재분석 없음)."""
    updated = dict(result)

    if result.get("status") != "ok" or result.get("track_db") is None:
        return updated

    new_track_db = result["track_db"] - applied_steps * DB_PER_STEP
    updated["track_db"] = new_track_db

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

    if result.get("album_db") is not None:
        new_album_db = result["album_db"] - applied_steps * DB_PER_STEP
        updated["album_db"] = new_album_db
        adisp = _compute_display(new_album_db, new_cma, target_db)
        updated["album_volume"] = adisp["volume"]
        updated["album_steps"] = adisp["steps"]
        updated["album_gain_db"] = adisp["track_gain_db"]
        updated["album_clip_state"] = adisp["clip_state"]
    return updated


def apply_file_track_gain(path: str, target_db: float = DEFAULT_TARGET_DB,
                          skip_tag: bool = False, use_id3: bool = False,
                          seed: dict | None = None,
                          should_cancel: Callable[[], bool] | None = None,
                          on_progress: Callable[[float], None] | None = None
                          ) -> dict:
    """목표 dB 를 반영해 Track ReplayGain 을 실제 적용한다(파괴적)."""
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
    """저장된 undo 태그로 이전 게인 변경을 되돌린다(파괴적, 디코딩 없음)."""
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
    """파일의 mp3gain 태그를 제거한다(파괴적, 디코딩 없음)."""
    remove_mp3gain_ape_tag(path, save_timestamp)
    if use_id3:
        from gaindb.id3 import remove_mp3gain_id3_tag
        remove_mp3gain_id3_tag(path, save_timestamp)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Album 계층 (GUI Album Analysis / Album Gain 배선용)
# ---------------------------------------------------------------------------

# 그룹 전체를 한 앨범으로 묶을 때 쓰는 그룹 키(폴더=앨범이 아닐 때).
_ALL_ALBUM_KEY = "<all>"


def group_by_album(paths, each_folder_is_album: bool = True) -> dict:
    """경로들을 앨범 그룹으로 묶어 {album_key: [paths]} 를 반환한다(순수 함수).

    "Each folder is album" 토글 동작:
      each_folder_is_album=True  : 폴더(os.path.dirname)별로 묶는다.
      each_folder_is_album=False : 전체를 단일 그룹(_ALL_ALBUM_KEY)으로 묶는다.
    입력 순서를 그룹 안에서 보존한다.
    """
    groups: dict[str, list[str]] = {}
    for p in paths:
        if each_folder_is_album:
            key = os.path.dirname(os.path.abspath(p))
        else:
            key = _ALL_ALBUM_KEY
        groups.setdefault(key, []).append(p)
    return groups


def analyze_album_file(
    path: str,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    """곡 하나를 스트리밍 분석해 앨범 그룹 누적용 원재료를 반환한다(비파괴).

    analyze_file 과 같은 스트리밍 경로를 쓰되 히스토그램을 보존한다(앨범 dB
    산출용). 곡별 peak·min/max 도 함께 모은다. track_db 가 not_enough 여도
    히스토그램은 그대로 반환한다(앨범 판정은 그룹 누적으로 하기 때문).
    """
    sample_rate, _channels, _duration = _probe_stream_info(Path(path))
    analyzer = TrackAnalyzer(sample_rate)

    decode_pcm_streaming(
        path, on_chunk=analyzer.feed,
        should_cancel=should_cancel, on_progress=on_progress)

    track_db = analyzer.result()
    peak = analyzer.peak_normalized()
    histogram = analyzer.histogram()
    min_gain, max_gain = scan_gain(path)

    return {
        "status": "ok",
        "path": path,
        "track_db": track_db,  # NOT_ENOUGH_SAMPLES 일 수 있음(그대로 보존)
        "peak": peak,
        "min_gain": min_gain,
        "max_gain": max_gain,
        "histogram": histogram,
        "sample_rate": sample_rate,
    }


def album_gain_from_files(per_file_results: list) -> dict:
    """곡별 원재료(analyze_album_file 결과)를 모아 앨범 집계를 산출한다.

    앨범 게인 누적과 동일: album_db=gain_from_histograms(합),
    album_peak=곡별 peak 의 max, album_min/max=곡별 min/max 의 min/max.
    """
    histograms = [r["histogram"] for r in per_file_results]
    album_db = gain_from_histograms(histograms)

    if album_db is NOT_ENOUGH_SAMPLES:
        return {
            "status": "not_enough_samples",
            "album_db": None, "album_peak": None,
            "album_min": None, "album_max": None,
        }

    album_peak = 0.0
    album_max = 0
    album_min = 255
    for r in per_file_results:
        if r["peak"] > album_peak:
            album_peak = r["peak"]
        if r["max_gain"] is not None and r["max_gain"] > album_max:
            album_max = r["max_gain"]
        if r["min_gain"] is not None and r["min_gain"] < album_min:
            album_min = r["min_gain"]

    return {
        "status": "ok",
        "album_db": album_db,
        "album_peak": album_peak,
        "album_min": album_min,
        "album_max": album_max,
    }


def compute_album_display(result: dict, album_db: float,
                          target_db: float = DEFAULT_TARGET_DB) -> dict:
    """곡별 표시 result 에 앨범 표시값(album_* 키)을 추가한다(재분석 없음).

    Album dB Gain 이 있을 때 Album Volume/Gain/clip 을 Track 과 같은 수식(입력만
    앨범 dB)으로 계산한다. Track 키는 보존하고 album 키만 보탠다. clip 판정
    curr_max_amp 는 곡별 값을 쓴다(mp3gain 과 동일).
    """
    updated = dict(result)
    updated["album_db"] = album_db

    cma = result.get("curr_max_amp")
    disp = _compute_display(album_db,
                            None if cma is None else float(cma),
                            target_db)
    updated["album_volume"] = disp["volume"]
    updated["album_steps"] = disp["steps"]
    updated["album_gain_db"] = disp["track_gain_db"]
    updated["album_clip_state"] = disp["clip_state"]
    return updated


def apply_file_album_gain(
    path: str,
    album_db: float,
    album_peak: float,
    album_min: int,
    album_max: int,
    track_seed: dict,
    target_db: float = DEFAULT_TARGET_DB,
    skip_tag: bool = False,
    use_id3: bool = False,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    """한 곡에 앨범 게인을 적용한다(파괴적). track+album 태그를 둘 다 기록.

    앨범 게인 곡별 적용: 그룹 공통 스텝(db_to_steps(album_db + mod))을 적용하며
    track 값(씨앗)과 album 값(그룹 집계)을 둘 다 채운다. 실제 적용 본체는
    apply_gain._apply_one_album_file 을 호출해 CLI album 경로와 태그 결과가
    정확히 일치한다. track_seed 로 재디코딩을 생략한다(이중 디코딩 제거).
    """
    db_gain_mod = target_db - DEFAULT_TARGET_DB
    steps = db_to_steps(album_db + db_gain_mod)

    track_db = track_seed.get("track_db")
    peak = track_seed.get("peak")
    min_gain = track_seed.get("min_gain")
    max_gain = track_seed.get("max_gain")

    res = _apply_one_album_file(
        path, steps, album_db, album_db, track_db, peak, min_gain, max_gain,
        album_peak, album_min, album_max,
        wrap=False, skip_tag=skip_tag, use_id3=use_id3,
        should_cancel=should_cancel, on_progress=on_progress,
    )

    return {
        "status": "no_change" if steps == 0 else "ok",
        "steps": steps,
        "album_db": album_db,
        "frames_changed": res.get("frames_changed"),
        "tag_written": res.get("tag_written", False),
    }


def result_from_album_raw(raw: dict, target_db: float = DEFAULT_TARGET_DB) -> dict:
    """analyze_album_file 원재료(dict)를 track 표시 result 로 변환한다(재분석 없음).

    analyze_album_file 은 그룹 누적용 원재료(track_db·peak·min/max·histogram)를
    준다. 앨범 워커는 그룹 dB 를 얻은 뒤, 각 곡의 이 원재료로 track 표시
    result(analyze_file 과 같은 키 구조)를 만들고 compute_album_display 로 album
    키를 얹는다. 이 함수는 그 앞 단계 — 원재료 → track 표시 result 변환이다.
    재분석·재디코딩 없이 _compute_display 만 부르므로 가볍다.

    raw 의 track_db 가 NOT_ENOUGH_SAMPLES 면(단곡 판정 실패) track 표시값을
    만들 수 없으므로 status="not_enough_samples" 로 돌려준다. 이 경우에도 앨범
    표시는 그룹 dB 로 별도로 얹을 수 있으나(track 실패해도 album 은 진행),
    MVP 에서는 track 표시가 없는 곡은 그대로 둔다(합의된 단순화).

    반환: analyze_file 과 동일 키 구조의 track 표시 result dict.
    """
    track_db = raw.get("track_db")
    if track_db is None or track_db is NOT_ENOUGH_SAMPLES:
        return {
            "status": "not_enough_samples", "target_db": target_db,
            "track_db": None, "volume": None, "steps": None,
            "track_gain_db": None, "peak": None, "curr_max_amp": None,
            "min_gain": None, "max_gain": None, "clip_state": "none",
        }

    peak = raw.get("peak")
    curr_max_amp = None if peak is None else peak * 32768.0
    disp = _compute_display(track_db, curr_max_amp, target_db)

    return {
        "status": "ok",
        "target_db": target_db,
        "track_db": track_db,
        "volume": disp["volume"],
        "steps": disp["steps"],
        "track_gain_db": disp["track_gain_db"],
        "peak": peak,
        "curr_max_amp": None if curr_max_amp is None else round(curr_max_amp),
        "min_gain": raw.get("min_gain"),
        "max_gain": raw.get("max_gain"),
        "clip_state": disp["clip_state"],
    }
