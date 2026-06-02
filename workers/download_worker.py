# workers/download_worker.py
# 다운로드를 백그라운드 스레드에서 실행하는 파일
# UI가 멈추지 않도록 QThread로 분리

import math
import os
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from core.downloader import Downloader
from utils.file_utils import (
    strip_ansi,
    snapshot_child_pids,
    terminate_pids,
)


# yt-dlp 가 ETA / 크기 자리에 "값 없음" 의미로 박는 placeholder 들.
# 비교는 _normalize_token 으로 공백 모두 제거 + 소문자화 후 수행한다.
_UNKNOWN_TOKENS = frozenset({
    "unknown", "unknowneta",
    "--:--", "--:--:--",
    "00:00", "00:00:00",
    "n/a", "na",
})


# ETA EMA 시정수 (초). yt-dlp ETA 출처일 때 사용.
# fragment 다운로더는 yt-dlp ETA 가 충분히 안정적이라 5초로 평탄화.
_ETA_EMA_TAU_YTDLP = 5.0

# 폴백 추정용 EMA 시정수 (초). 우리가 elapsed/pct 로 계산한 값에 적용.
# 폴백은 단조롭게 변하지만 pct 가 0.1% 단위로 흔들려 그대로 표시하면
# 1~2초 단위로 깜빡인다. 10초로 더 길게 잡아 사용자 체감 안정화.
_ETA_EMA_TAU_FALLBACK = 10.0


def _normalize_token(s: str) -> str:
    """
    yt-dlp 가 주는 placeholder 문자열을 비교용 정규화.
    공백 모두 제거 + 소문자화. " N / A " → "n/a", "Unknown ETA" → "unknowneta".
    """
    return "".join(s.split()).lower()


def _split_size_str(s: str) -> tuple[str, str]:
    """
    yt-dlp 사람 친화 크기 문자열을 (숫자부, 단위부) 로 분리.
    예: "48.20MiB" -> ("48.20", "MiB"),  "1.25GiB" -> ("1.25", "GiB")
    단위가 식별되지 않으면 (원문, "") 반환.
    """
    s = s.strip()
    if not s:
        return ("", "")
    # 뒤에서부터 알파벳을 모은다 — yt-dlp 단위는 항상 알파벳만(KiB/MiB/GiB/TiB/B)
    i = len(s)
    while i > 0 and s[i - 1].isalpha():
        i -= 1
    if i == len(s) or i == 0:
        return (s, "")
    return (s[:i].strip(), s[i:].strip())


def _normalize_size_str(s: str) -> str:
    """
    "48.20MiB" -> "48.20 MiB" 처럼 숫자와 단위 사이에 공백을 한 칸 끼운다.
    단위 분리 실패 시 원문 그대로 반환.
    """
    num, unit = _split_size_str(s)
    if not unit:
        return s.strip()
    return f"{num} {unit}"


def _is_unknown_size(s: str) -> bool:
    """
    yt-dlp 크기 문자열이 "값 없음" 의미인지 판정.
    빈 문자열도 unknown 으로 본다.
    """
    if not s:
        return True
    return _normalize_token(s) in _UNKNOWN_TOKENS


def _parse_eta_secs(s: str) -> int:
    """
    yt-dlp 의 ETA 표기("00:42", "1:23:45", "~0:42") 를 초 단위 정수로 환산.
    파싱 실패 시 -1.
    """
    s = s.strip().lstrip("~").strip()
    if not s:
        return -1
    parts = s.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return -1
    if len(nums) == 2:
        m, sec = nums
        return m * 60 + sec
    if len(nums) == 3:
        h, m, sec = nums
        return h * 3600 + m * 60 + sec
    return -1


def _format_eta_secs(secs: int, is_estimate: bool) -> str:
    """
    초 단위 ETA 를 표시 문자열로. 폴백 추정이면 선두에 "약 " 을 붙인다.
    "약" 은 한국어에서 어림 표지로 자연스럽고 "~" 의 의미 모호성(범위 구분자
    로 오인) 을 피한다. 사용자 측에서 표시 라벨이 "남은시간 약 0:42" 가 된다.
    """
    if secs < 0:
        return ""
    if secs >= 3600:
        body = f"{secs // 3600}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
    else:
        body = f"{secs // 60}:{secs % 60:02d}"
    return f"약 {body}" if is_estimate else body


def _extract_codec_info(info_dict: dict) -> tuple[str, str, str, float, float] | None:
    """
    yt-dlp 의 info_dict 에서 코덱·컨테이너·비트레이트 정보를 뽑아낸다.

    반환: (vcodec, acodec, ext, abr, tbr) 또는 None (의미 있는 정보 없음).

    "의미 있음" 의 기준은 vcodec 또는 acodec 중 하나라도 "none" / 빈값이
    아닌 것. info_dict 가 진행 중 fragment 정보일 수도 있고 후처리 직전의
    부분 정보일 수도 있어, 코덱이 전혀 없으면 emit 하지 않는다 (직전 emit 유지).
    """
    if not isinstance(info_dict, dict):
        return None

    vcodec = (info_dict.get("vcodec") or "").strip()
    acodec = (info_dict.get("acodec") or "").strip()

    # 둘 다 "none"/빈값이면 정보 없음
    has_video = vcodec and vcodec != "none"
    has_audio = acodec and acodec != "none"
    if not has_video and not has_audio:
        return None

    ext = (info_dict.get("ext") or "").strip()
    try:
        abr = float(info_dict.get("abr") or 0.0)
    except (TypeError, ValueError):
        abr = 0.0
    try:
        tbr = float(info_dict.get("tbr") or 0.0)
    except (TypeError, ValueError):
        tbr = 0.0

    return (vcodec, acodec, ext, abr, tbr)


class DownloadWorker(QThread):
    """
    다운로드를 백그라운드로 실행하는 워커 스레드

    시그널:
        progress             : 진행률 (0.0 ~ 100.0)
        speed                : 다운로드 속도 문자열 (예: "2.3 MiB/s")
        eta                  : 남은 시간 문자열 (예: "0:42", HLS 폴백 시 "~0:42")
        file_size            : 파일 크기 문자열 (예: "128.5 MiB")
        merging              : 영상+음성 병합 시작 알림
        codec_info_resolved  : 다운로드/후처리 진행 중 확정된 코덱·비트레이트
                               (vcodec, acodec, ext, abr, tbr) — 여러 번 발사
                               될 수 있으며 마지막 값이 최종 진실. 위젯은 매번
                               덮어쓰면 됨. is_audio 항목은 위젯 측에서 거부.
        download_finished    : 다운로드 완료 - 저장된 파일 경로 전달.
                               ⚠ QThread 내장 finished(인자 없음, 스레드 종료
                               신호) 와 이름이 겹치지 않도록 download_finished
                               로 둔다. 내장 finished 는 매니저가 스레드 수명
                               관리(객체 소멸·dict 정리) 에 쓰므로 가리면 안 된다.
                               (LESSONS: QThread 상속 워커는 started/finished
                               이름을 자체 시그널로 쓰지 말 것.)
        error                : 오류 발생 - 에러 메시지 전달
        cancelled            : 사용자 취소 알림
    """

    progress             = Signal(float)                        # 진행률
    speed                = Signal(str)                          # 속도
    eta                  = Signal(str)                          # 남은 시간
    file_size            = Signal(str)                          # 파일 크기
    merging              = Signal()                             # 병합 시작
    codec_info_resolved  = Signal(str, str, str, float, float)  # vcodec, acodec, ext, abr, tbr
    download_finished    = Signal(str)                          # 완료 (파일 경로)
    error                = Signal(str)                          # 오류
    cancelled            = Signal()                             # 취소

    def __init__(
        self,
        url         : str,
        format_id   : str,
        ext         : str,
        save_dir    : str,
    ):
        super().__init__()
        self.url        = url
        self.format_id  = format_id
        self.ext        = ext
        self.save_dir   = save_dir
        self._downloader = Downloader()
        self._output_path = ""  # 완료된 파일 경로 저장용

        # ETA 폴백용 — 다운로드 시작 시각.
        # native HTTP 단일 progressive 다운로더는 yt-dlp 가 매 5초마다 ETA 를
        # Unknown 으로 리셋한 뒤 새 추정치를 박는 패턴이라, 우리가 elapsed 와
        # pct 로 직접 계산한 폴백이 훨씬 안정적이다. fragment 케이스에서만
        # yt-dlp ETA 를 신뢰한다.
        self._dl_start_ts: float = 0.0

        # ETA 출처 — 한 다운로드(스트림) 안에서 출처를 한 번 정하면 끝까지
        # 그 출처만 쓴다. "yt-dlp" / "fallback" / None(미정).
        # 결정 기준: 첫 의미 있는 ETA 가 들어온 시점에 fragment_index 와
        # _total_bytes_str 을 보고 분기.
        self._eta_source: str | None = None

        # ETA EMA 평활값 (초 단위, 실수) + 마지막 평활 입력 시각.
        self._eta_smoothed       : float = -1.0
        self._eta_last_input_ts  : float = 0.0

        # ETA emit 스로틀 캐시.
        self._last_eta_emit_ts: float = 0.0
        self._last_eta_secs   : int   = -1
        self._last_eta_text   : str   = ""

        # 진행률 단조 증가 floor — fragment 경계에서 yt-dlp 가 total 추정을
        # 다시 계산하면서 pct 가 일시적으로 뒤로 후퇴하는 출렁임을 차단.
        # 한 다운로드(스트림) 안에서만 유효하며 finished 시점에 리셋.
        self._pct_floor: float = -1.0

        # codec_info_resolved 의 마지막 emit 값 — 같은 값을 중복 emit 하지
        # 않기 위한 가드. (vcodec, acodec, ext, abr, tbr) 튜플.
        self._last_codec_info: tuple[str, str, str, float, float] | None = None

        # 잔여물 추적
        self._touched_files: set[str] = set()

        # 자식 PID 차분용 스냅샷
        self._pre_pids: set[int] = set()

    def run(self):
        """
        스레드 실행 진입점
        Downloader.download() 호출 후 시그널로 결과 전달
        """
        try:
            from yt_dlp.utils import DownloadCancelled
        except ImportError:
            DownloadCancelled = None

        self._pre_pids = snapshot_child_pids()

        cancelled = False
        errored   = False
        error_msg = ""

        try:
            self._downloader.download(
                url              = self.url,
                format_id        = self.format_id,
                ext              = self.ext,
                save_dir         = self.save_dir,
                progress_hook    = self._on_progress,
                postprocess_hook = self._on_postprocess,
            )

        except Exception as e:
            if DownloadCancelled is not None and isinstance(e, DownloadCancelled):
                cancelled = True
            else:
                errored   = True
                error_msg = str(e)

        if cancelled or errored:
            new_pids = snapshot_child_pids() - self._pre_pids
            terminate_pids(new_pids)
            self._cleanup_residue()

        if cancelled:
            self.cancelled.emit()
        elif errored:
            self.error.emit(error_msg)
        else:
            self.download_finished.emit(self._output_path)

    def cancel(self):
        """외부에서 취소 요청"""
        self._downloader.cancel()

    def _maybe_emit_codec_info(self, info_dict: dict):
        """
        info_dict 에서 코덱 정보를 뽑아 의미 있으면 codec_info_resolved 시그널 발사.

        같은 값 연속 emit 은 가드한다 (라벨 깜빡임 방지). 후처리 체인의 각
        단계마다 호출될 수 있고 마지막 단계의 값이 최종 진실이 된다.
        """
        extracted = _extract_codec_info(info_dict)
        if extracted is None:
            return
        if extracted == self._last_codec_info:
            return
        self._last_codec_info = extracted
        vcodec, acodec, ext, abr, tbr = extracted
        self.codec_info_resolved.emit(vcodec, acodec, ext, abr, tbr)

    def _on_progress(self, d: dict):
        """
        yt-dlp 진행률 콜백
        """
        status = d.get("status")

        self._collect_paths_from_hook(d)

        if status == "downloading":
            if self._dl_start_ts == 0.0:
                self._dl_start_ts = time.monotonic()

            pct_str = strip_ansi(d.get("_percent_str", "0%")).strip()
            raw_pct: float | None
            try:
                raw_pct = float(pct_str.replace("%", ""))
            except ValueError:
                raw_pct = None

            # fragment 출렁임 보정 + 단조 ceiling 적용한 표시용 pct.
            # ETA 계산은 raw_pct 가 아니라 표시용 pct 를 쓰는 것이 자연스럽다
            # — 사용자에게 보이는 진행도와 남은시간이 같은 기준을 공유해야
            # "37.5% / 남은시간 8초" 가 일관된다.
            pct = self._compute_display_pct(d, raw_pct)
            if pct is not None:
                self.progress.emit(pct)

            speed = strip_ansi(d.get("_speed_str", "")).strip()
            if speed and _normalize_token(speed) not in _UNKNOWN_TOKENS:
                self.speed.emit(speed)

            self._emit_eta(d, pct)

            downloaded = strip_ansi(d.get("_downloaded_bytes_str", "")).strip()
            total      = strip_ansi(
                d.get("_total_bytes_str", "")
                or d.get("_total_bytes_estimate_str", "")
            ).strip()
            size_text = self._compose_size_text(downloaded, total)
            if size_text:
                self.file_size.emit(size_text)

        elif status == "finished":
            self._output_path = d.get("filename", "") or self._output_path
            self.progress.emit(100.0)
            # 코덱 정보 사후 갱신 — progress hook 의 finished 시점에
            # info_dict 가 들어 있으면 거기서 한 번 emit. 머지가 있는 경로는
            # _on_postprocess 의 finished 가 더 진실에 가까운 통합 정보를
            # 갖지만, 머지 없는 단일 progressive 경로는 여기가 끝일 수 있다.
            info_dict = d.get("info_dict")
            if isinstance(info_dict, dict):
                self._maybe_emit_codec_info(info_dict)
            # ETA 라벨을 명시적으로 비운다. 단조 하향으로 raw 가 0 까지
            # 따라간다 해도, 마지막 emit 이 1~2 초에서 멈춘 채 finished
            # 가 들어오는 경우의 잔재를 방어. update_status(DONE) 이
            # 어차피 라벨을 비우지만, 여기서 한 번 더 비워두면 단일
            # progressive 처럼 후속 전이가 늦는 경로에서도 안전.
            self.eta.emit("")
            # 다음 스트림(예: 오디오) 을 위해 ETA 상태 모두 리셋
            self._dl_start_ts       = 0.0
            self._eta_source        = None
            self._eta_smoothed      = -1.0
            self._eta_last_input_ts = 0.0
            self._last_eta_emit_ts  = 0.0
            self._last_eta_secs     = -1
            self._last_eta_text     = ""
            self._pct_floor         = -1.0

    def _compute_display_pct(self, d: dict, raw_pct: float | None) -> float | None:
        """
        UI 표시용 진행률 계산.

        두 단계로 보정:
        1) fragment 다운로더일 때는 yt-dlp 가 준 raw_pct (= 현재 fragment 내
           진행률) 대신 ((index - 1) + raw_pct/100) / count * 100 로 재계산.
           yt-dlp 는 fragment 경계마다 total 추정을 다시 잡아 raw_pct 가
           55% → 52% → 57% 처럼 출렁이는데, fragment 인덱스 기반 식은
           구조적으로 단조 증가한다.
        2) 그래도 일관성을 잃은 경계 케이스 (frag 정보 누락·재시도 등) 를
           위해 self._pct_floor 단조 ceiling 적용. 새 pct 가 floor 보다
           작으면 floor 를 그대로 반환.

        반환값: 표시할 pct (float) 또는 raw_pct 가 None 일 때 None.
        """
        if raw_pct is None:
            return None

        # ── 1) fragment 기반 재계산 ──
        frag_idx   = d.get("fragment_index")
        frag_count = d.get("fragment_count")
        if (
            isinstance(frag_idx, int) and isinstance(frag_count, int)
            and frag_count > 0 and 0 <= frag_idx <= frag_count
        ):
            completed = max(0, frag_idx - 1)
            base_pct  = completed / frag_count * 100.0
            slice_pct = (raw_pct / 100.0) / frag_count * 100.0
            pct       = base_pct + slice_pct
            if pct < 0.0:
                pct = 0.0
            if pct > 100.0:
                pct = 100.0
        else:
            pct = raw_pct

        # ── 2) 단조 ceiling ──
        if self._pct_floor < 0.0:
            self._pct_floor = pct
        elif pct < self._pct_floor:
            pct = self._pct_floor
        else:
            self._pct_floor = pct

        return pct

    def _decide_eta_source(self, d: dict) -> str:
        """
        다운로드의 ETA 출처를 결정. 첫 호출 시점의 후크 dict 를 보고 판정.

        결정 규칙:
        - fragment_index 가 정수 (frag 다운로더) → "yt-dlp" 신뢰.
        - 그 외 (단일 progressive 또는 식별 불가) → "fallback".
        한 번 결정되면 그 스트림 끝까지 유지 (finished 에서 리셋).
        """
        frag_idx = d.get("fragment_index")
        if isinstance(frag_idx, int):
            return "yt-dlp"
        return "fallback"

    def _emit_eta(self, d: dict, pct: float | None):
        """
        ETA 시그널 후보 산정.

        출처 잠금: 첫 진입에서 _decide_eta_source 로 출처를 결정하고, 이후 같은
        스트림 끝까지 그 출처만 쓴다.
        """
        if self._eta_source is None:
            self._eta_source = self._decide_eta_source(d)

        if self._eta_source == "yt-dlp":
            raw = strip_ansi(d.get("_eta_str", "")).strip()
            if not raw or _normalize_token(raw) in _UNKNOWN_TOKENS:
                return
            secs = _parse_eta_secs(raw)
            if secs < 0:
                return
            self._maybe_emit_eta(
                secs=secs, is_estimate=False, tau=_ETA_EMA_TAU_YTDLP
            )
            return

        if pct is None or pct < 0.5:
            return
        elapsed = time.monotonic() - self._dl_start_ts
        if elapsed <= 0:
            return

        remaining = elapsed * (100.0 - pct) / pct
        if remaining < 0:
            return

        self._maybe_emit_eta(
            secs=int(remaining), is_estimate=True, tau=_ETA_EMA_TAU_FALLBACK
        )

    def _maybe_emit_eta(self, secs: int, is_estimate: bool, tau: float):
        """
        시간 정규화 EMA 평활화 + 스로틀 규칙에 따라 ETA 를 emit.
        """
        now = time.monotonic()

        raw_secs = float(secs)
        if self._eta_smoothed < 0:
            self._eta_smoothed      = raw_secs
            self._eta_last_input_ts = now
        elif raw_secs <= self._eta_smoothed:
            self._eta_smoothed      = raw_secs
            self._eta_last_input_ts = now
        else:
            dt = max(0.0, now - self._eta_last_input_ts)
            alpha_eff = 1.0 - math.exp(-dt / tau)
            self._eta_smoothed = (
                alpha_eff * raw_secs
                + (1.0 - alpha_eff) * self._eta_smoothed
            )
            self._eta_last_input_ts = now

        display_secs = int(self._eta_smoothed)
        text = _format_eta_secs(display_secs, is_estimate)
        if not text:
            return

        if self._last_eta_emit_ts == 0.0:
            self._do_emit_eta(text, display_secs, now)
            return

        if self._last_eta_secs >= 0:
            if display_secs <= 10:
                threshold = 1
            else:
                threshold = max(15, int(self._last_eta_secs * 0.30))
            if abs(display_secs - self._last_eta_secs) >= threshold:
                self._do_emit_eta(text, display_secs, now)
                return

        min_gap = max(2.0, min(display_secs * 0.05, 30.0))
        if (now - self._last_eta_emit_ts) < min_gap:
            return

        if text == self._last_eta_text:
            self._last_eta_emit_ts = now
            return

        self._do_emit_eta(text, display_secs, now)

    def _do_emit_eta(self, text: str, secs: int, now: float):
        """emit + 스로틀 캐시 갱신을 한 곳에서."""
        self.eta.emit(text)
        self._last_eta_emit_ts = now
        self._last_eta_secs    = secs
        self._last_eta_text    = text

    @staticmethod
    def _compose_size_text(downloaded: str, total: str) -> str:
        """
        yt-dlp 의 두 크기 문자열을 UI 표시용 한 문자열로 합친다.
        """
        d = (downloaded or "").strip()
        t = (total      or "").strip()

        d_known = not _is_unknown_size(d)
        t_known = not _is_unknown_size(t)

        if not d_known and not t_known:
            return ""
        if d_known and not t_known:
            return _normalize_size_str(d)
        if t_known and not d_known:
            return _normalize_size_str(t)

        d_num, d_unit = _split_size_str(d)
        t_num, t_unit = _split_size_str(t)

        if d_unit and t_unit and d_unit == t_unit:
            return f"{d_num} / {t_num} {t_unit}"
        return f"{_normalize_size_str(d)} / {_normalize_size_str(t)}"

    def _on_postprocess(self, d: dict):
        """
        yt-dlp 후처리 콜백.
        """
        status        = d.get("status")
        postprocessor = d.get("postprocessor", "")

        self._collect_paths_from_hook(d)

        if postprocessor == "Merger" and status == "started":
            self.merging.emit()

        if status == "finished":
            info_dict = d.get("info_dict") or {}
            if isinstance(info_dict, dict):
                self._output_path = info_dict.get(
                    "filepath",
                    self._output_path
                )
                self._maybe_emit_codec_info(info_dict)

    # ── 잔여물 추적·정리 ──────────────────────────────────────

    def _collect_paths_from_hook(self, d: dict):
        """
        yt-dlp 후크 dict 에서 파일 경로 후보를 모두 추출해 _touched_files 에 누적.
        """
        fn = d.get("filename")
        if fn:
            self._touched_files.add(fn)

        info = d.get("info_dict") or {}
        if not isinstance(info, dict):
            return

        for key in ("filepath", "filename", "_filename"):
            v = info.get(key)
            if isinstance(v, str) and v:
                self._touched_files.add(v)

        files_to_move = info.get("__files_to_move")
        if isinstance(files_to_move, dict):
            for src, dst in files_to_move.items():
                if isinstance(src, str) and src:
                    self._touched_files.add(src)
                if isinstance(dst, str) and dst:
                    self._touched_files.add(dst)

    def _cleanup_residue(self):
        """
        취소·에러로 끝났을 때 누적된 파일들과 그 .part / .ytdl 형제를 삭제.
        """
        for path_str in list(self._touched_files):
            base = Path(path_str)
            self._safe_unlink(base)
            for ext in (".part", ".ytdl", ".part.ytdl"):
                self._safe_unlink(Path(str(base) + ext))

    @staticmethod
    def _safe_unlink(path: Path):
        """파일이 있으면 지우고, 없거나 권한 실패면 조용히 통과."""
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
