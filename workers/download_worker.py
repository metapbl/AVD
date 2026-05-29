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
    초 단위 ETA 를 표시 문자열로. 폴백 추정이면 선두에 "~" 를 붙인다.
    """
    if secs < 0:
        return ""
    if secs >= 3600:
        body = f"{secs // 3600}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
    else:
        body = f"{secs // 60}:{secs % 60:02d}"
    return f"~{body}" if is_estimate else body


class DownloadWorker(QThread):
    """
    다운로드를 백그라운드로 실행하는 워커 스레드

    시그널:
        progress    : 진행률 (0.0 ~ 100.0)
        speed       : 다운로드 속도 문자열 (예: "2.3 MiB/s")
        eta         : 남은 시간 문자열 (예: "0:42", HLS 폴백 시 "~0:42")
        file_size   : 파일 크기 문자열 (예: "128.5 MiB")
        merging     : 영상+음성 병합 시작 알림
        finished    : 다운로드 완료 - 저장된 파일 경로 전달
        error       : 오류 발생 - 에러 메시지 전달
        cancelled   : 사용자 취소 알림
    """

    progress    = Signal(float)  # 진행률
    speed       = Signal(str)    # 속도
    eta         = Signal(str)    # 남은 시간
    file_size   = Signal(str)    # 파일 크기
    merging     = Signal()       # 병합 시작
    finished    = Signal(str)    # 완료 (파일 경로)
    error       = Signal(str)    # 오류
    cancelled   = Signal()       # 취소

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
            self.finished.emit(self._output_path)

    def cancel(self):
        """외부에서 취소 요청"""
        self._downloader.cancel()

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
            pct: float | None
            try:
                pct = float(pct_str.replace("%", ""))
                self.progress.emit(pct)
            except ValueError:
                pct = None

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
            # 다음 스트림(예: 오디오) 을 위해 ETA 상태 모두 리셋
            self._dl_start_ts       = 0.0
            self._eta_source        = None
            self._eta_smoothed      = -1.0
            self._eta_last_input_ts = 0.0
            self._last_eta_emit_ts  = 0.0
            self._last_eta_secs     = -1
            self._last_eta_text     = ""

    def _decide_eta_source(self, d: dict) -> str:
        """
        다운로드의 ETA 출처를 결정. 첫 호출 시점의 후크 dict 를 보고 판정.

        결정 규칙:
        - fragment_index 가 정수 (frag 다운로더) → "yt-dlp" 신뢰.
          fragment 다운로더는 각 frag 평균 속도로 ETA 를 계산해 안정적.
        - 그 외 (단일 progressive 또는 식별 불가) → "fallback".
          native HTTP 다운로더는 매 5초 ETA 를 Unknown 으로 리셋하는 패턴이라
          우리 elapsed/pct 폴백이 훨씬 안정적.

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
        - "yt-dlp": yt-dlp 의 _eta_str 을 평활화해 emit. unknown 시 emit 생략.
        - "fallback": elapsed/pct 로 계산한 추정치를 평활화해 "~" 접두사로 emit.
        """
        if self._eta_source is None:
            self._eta_source = self._decide_eta_source(d)

        if self._eta_source == "yt-dlp":
            raw = strip_ansi(d.get("_eta_str", "")).strip()
            if not raw or _normalize_token(raw) in _UNKNOWN_TOKENS:
                return  # unknown 은 emit 생략 (직전 표시값 유지)
            secs = _parse_eta_secs(raw)
            if secs < 0:
                return
            self._maybe_emit_eta(
                secs=secs, is_estimate=False, tau=_ETA_EMA_TAU_YTDLP
            )
            return

        # fallback 출처 — 우리 elapsed/pct 추정
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

        EMA: alpha_eff = 1 - exp(-dt / tau). tau 가 클수록 더 부드럽다.
        호출 빈도에 무관한 시간 기준 평활. 단일 progressive(초당 수십~수백 회)
        와 fragment(초당 몇 회) 모두 일관된 시정수로 평탄화.

        스로틀:
        - 첫 emit 은 항상 통과.
        - 큰 변동 (직전 emit 대비 30% 또는 15초) 은 즉시 통과.
        - 그 외는 비례 스로틀: max(2, min(secs * 0.05, 30)).
        - 같은 표시 문자열은 emit 생략.
        """
        now = time.monotonic()

        # ── 시간 정규화 EMA ──
        if self._eta_smoothed < 0:
            self._eta_smoothed      = float(secs)
            self._eta_last_input_ts = now
        else:
            dt = max(0.0, now - self._eta_last_input_ts)
            alpha_eff = 1.0 - math.exp(-dt / tau)
            self._eta_smoothed = (
                alpha_eff * float(secs)
                + (1.0 - alpha_eff) * self._eta_smoothed
            )
            self._eta_last_input_ts = now

        display_secs = int(self._eta_smoothed)
        text = _format_eta_secs(display_secs, is_estimate)
        if not text:
            return

        # ── 스로틀 ──
        if self._last_eta_emit_ts == 0.0:
            self._do_emit_eta(text, display_secs, now)
            return

        if self._last_eta_secs >= 0:
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
        yt-dlp 의 `_downloaded_bytes_str` 와 `_total_bytes_str` 두 문자열을
        UI 표시용 한 문자열로 합친다.

        규칙:
            - 둘 다 의미 있는 값이고 단위 같음   → "48.20 / 128.50 MiB"
            - 둘 다 의미 있는 값이고 단위 다름   → "48.20MiB / 1.25GiB"
            - 전체가 unknown(N/A 등) 이면         → "48.20 MiB" (현재만)
            - 현재가 unknown 이면                 → "" (의미 없음)
            - 둘 다 비거나 unknown 이면           → ""

        _is_unknown_size 로 정규화 비교 후 분기. "98.15 MiB / N / A" 같은
        라벨이 새어 나가는 것을 차단.
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

        # 둘 다 의미 있는 값 — 단위 비교
        d_num, d_unit = _split_size_str(d)
        t_num, t_unit = _split_size_str(t)

        if d_unit and t_unit and d_unit == t_unit:
            return f"{d_num} / {t_num} {t_unit}"
        return f"{_normalize_size_str(d)} / {_normalize_size_str(t)}"

    def _on_postprocess(self, d: dict):
        """
        yt-dlp 후처리 콜백.

        ADR-001 이후 후처리 체인이 길어져, 한 다운로드에 다음 후처리기들이
        순차적으로 발사된다:
            ThumbnailsConvertor → Merger → Metadata → EmbedThumbnail → MoveFiles

        이 중 사용자에게 "병합 중"으로 보여야 하는 단계는 영상+오디오를
        실제로 머지하는 'Merger' 한 단계뿐이다.
        """
        status        = d.get("status")
        postprocessor = d.get("postprocessor", "")

        self._collect_paths_from_hook(d)

        if postprocessor == "Merger" and status == "started":
            self.merging.emit()

        if status == "finished":
            self._output_path = d.get("info_dict", {}).get(
                "filepath",
                self._output_path
            )

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
