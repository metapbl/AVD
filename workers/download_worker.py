# workers/download_worker.py
# 다운로드를 백그라운드 스레드에서 실행하는 파일
# UI가 멈추지 않도록 QThread로 분리

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


# yt-dlp 가 _eta_str 자리에 ETA 산정 불가의 의미로 박는 placeholder 들.
# 빈 문자열은 별도 처리(아예 안 옴) 되므로 여기서 제외.
_ETA_UNKNOWN_TOKENS = frozenset({
    "unknown", "unknown eta",
    "--:--", "--:--:--",
    "00:00", "00:00:00",
    "n/a",
})


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

class DownloadWorker(QThread):
    """
    다운로드를 백그라운드로 실행하는 워커 스레드

    시그널:
        progress    : 진행률 (0.0 ~ 100.0)
        speed       : 다운로드 속도 문자열 (예: "2.3 MiB/s")
        eta         : 남은 시간 문자열 (예: "00:42", HLS 폴백 시 "~0:42")
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
        # HLS 같이 total_bytes 가 없는 케이스에서 yt-dlp 가 _eta_str 에
        # "Unknown" 류 placeholder 를 박는데, 우리가 _percent_str 의 진행률과
        # 경과 시간으로 직접 ETA 를 추정해 emit 한다. 추정값은 표기에 "~" 를
        # 붙여 사용자에게 추정임을 알린다.
        self._dl_start_ts: float = 0.0

        # 잔여물 추적 — 두 후크가 알려주는 모든 경로를 누적.
        # 취소/에러 시 이 집합 + 각 경로의 .part / .ytdl 형제를 삭제한다.
        # 정상 완료 시에는 손대지 않는다 (산출물이므로).
        self._touched_files: set[str] = set()

        # 자식 PID 차분용 스냅샷.
        # run() 진입 직후 — Downloader.download() 가 yt-dlp 를 부르기 직전 —
        # 우리 프로세스의 자식 PID 집합을 박아두고, 취소 시 다시 찍어
        # 새로 늘어난 자식(=내가 띄운 ffmpeg/node) 만 종료한다.
        self._pre_pids: set[int] = set()

    def run(self):
        """
        스레드 실행 진입점
        Downloader.download() 호출 후 시그널로 결과 전달
        """
        # 취소 예외 타입을 import (yt-dlp 버전에 따라 위치가 다를 수 있어 안전 처리)
        try:
            from yt_dlp.utils import DownloadCancelled
        except ImportError:
            DownloadCancelled = None

        # 자식 PID 스냅샷 — Downloader.download() 가 자식을 띄우기 직전.
        # 이 시점 이후에 새로 늘어난 자식만 "내 워커가 띄운 자식" 으로 본다.
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

        # ── 자식 / 잔여물 정리 ─────────────────────────────
        # 취소 · 에러로 끝났을 때는 yt-dlp 자식(ffmpeg/node)이 살아 있을 수
        # 있고, .part / .ytdl 잔여 파일도 남는다. 자식을 먼저 끊어야 (Windows
        # 파일 잠금 해제) 잔여물 삭제가 성공한다.
        if cancelled or errored:
            new_pids = snapshot_child_pids() - self._pre_pids
            terminate_pids(new_pids)
            self._cleanup_residue()

        # ── 결과 시그널 발사 ────────────────────────────────
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
        다운로드 진행 중 주기적으로 호출됨
        """
        status = d.get("status")

        # 모든 진행률 후크에서 알려주는 경로를 누적 (취소 시 정리용)
        self._collect_paths_from_hook(d)

        if status == "downloading":
            # 시작 시각 기록 (ETA 폴백 산정용)
            if self._dl_start_ts == 0.0:
                self._dl_start_ts = time.monotonic()

            # 진행률
            pct_str = strip_ansi(d.get("_percent_str", "0%")).strip()
            pct: float | None
            try:
                pct = float(pct_str.replace("%", ""))
                self.progress.emit(pct)
            except ValueError:
                pct = None

            # 속도
            speed = strip_ansi(d.get("_speed_str", "")).strip()
            if speed:
                self.speed.emit(speed)

            # 남은 시간 — yt-dlp 값 우선, unknown 류면 폴백 계산
            self._emit_eta(d, pct)

            # 파일 크기 — "현재 / 전체" 형태로 합쳐서 emit.
            # yt-dlp 가 두 문자열을 각각 사람 친화 단위로 포맷해서 준다
            # (예: "48.20MiB", "128.50MiB"). 둘 다 같은 단위면 뒤쪽 단위만 남기고
            # 다르면(드묾) 양쪽 단위 모두 표기. 전체가 없으면 현재만, 현재도 없으면
            # emit 생략.
            downloaded = strip_ansi(d.get("_downloaded_bytes_str", "")).strip()
            total      = strip_ansi(
                d.get("_total_bytes_str", "")
                or d.get("_total_bytes_estimate_str", "")
            ).strip()
            size_text = self._compose_size_text(downloaded, total)
            if size_text:
                self.file_size.emit(size_text)

        elif status == "finished":
            # 단일 스트림 완료 (병합 전)
            self._output_path = d.get("filename", "") or self._output_path
            self.progress.emit(100.0)
            # 다음 스트림(예: 오디오) 다운로드를 위해 시작 시각 리셋
            self._dl_start_ts = 0.0

    def _emit_eta(self, d: dict, pct: float | None):
        """
        ETA 시그널 발사.

        1) yt-dlp 의 _eta_str 이 의미 있는 값이면 그대로 emit.
        2) _eta_str 이 비었거나 unknown placeholder("Unknown", "--:--", "00:00" 등)
           이면 — HLS 처럼 total_bytes 가 없는 케이스 — 우리가 측정한 elapsed 와
           _percent_str 기반 pct 로 ETA 를 추정해 "~M:SS" 형태로 emit.

        추정 가능 조건은 pct >= 0.5 (초반 출렁임 회피) + elapsed > 0.
        조건 미충족이면 emit 하지 않는다 (위젯 라벨은 직전 값 또는 빈 값 유지).
        """
        raw = strip_ansi(d.get("_eta_str", "")).strip()
        if raw and raw.lower() not in _ETA_UNKNOWN_TOKENS:
            self.eta.emit(raw)
            return

        # 폴백 계산
        if pct is None or pct < 0.5:
            return
        elapsed = time.monotonic() - self._dl_start_ts
        if elapsed <= 0:
            return

        remaining = elapsed * (100.0 - pct) / pct
        if remaining < 0:
            return

        secs = int(remaining)
        if secs >= 3600:
            text = f"~{secs // 3600}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
        else:
            text = f"~{secs // 60}:{secs % 60:02d}"
        self.eta.emit(text)

    @staticmethod
    def _compose_size_text(downloaded: str, total: str) -> str:
        """
        yt-dlp 의 `_downloaded_bytes_str` 와 `_total_bytes_str` 두 문자열을
        UI 표시용 한 문자열로 합친다.

        규칙:
            - 둘 다 있고 단위가 같으면      → "48.20 / 128.50 MiB"  (앞 단위 생략)
            - 둘 다 있고 단위가 다르면      → "48.20MiB / 1.25GiB"   (각자 단위)
            - 전체만 있으면                  → "128.50 MiB"
            - 현재만 있으면                  → "48.20 MiB"
            - 둘 다 비면                     → ""  (emit 생략 의미)

        yt-dlp 의 사람 친화 단위는 "숫자+공백없음+단위" 패턴(예: "48.20MiB").
        간단한 분리 로직으로 단위 부분만 추출해 비교한다.
        """
        d = (downloaded or "").strip()
        t = (total      or "").strip()

        if not d and not t:
            return ""
        if d and not t:
            return _normalize_size_str(d)
        if t and not d:
            return _normalize_size_str(t)

        # 둘 다 있음 — 단위 비교
        d_num, d_unit = _split_size_str(d)
        t_num, t_unit = _split_size_str(t)

        if d_unit and t_unit and d_unit == t_unit:
            # 단위 같음 — 앞 단위 생략, 사이에 공백·슬래시
            return f"{d_num} / {t_num} {t_unit}"
        # 단위 다르거나 분리 실패 — 원형 그대로 슬래시로 묶음
        return f"{_normalize_size_str(d)} / {_normalize_size_str(t)}"

    def _on_postprocess(self, d: dict):
        """
        yt-dlp 후처리 콜백.

        ADR-001 이후 후처리 체인이 길어져, 한 다운로드에 다음 후처리기들이
        순차적으로 발사된다 (yt-dlp 2026.3.17 기준 진단 확인):
            ThumbnailsConvertor → Merger → Metadata → EmbedThumbnail → MoveFiles

        이 중 사용자에게 "병합 중"으로 보여야 하는 단계는 영상+오디오를
        실제로 머지하는 'Merger' 한 단계뿐이다. 다른 후처리기에서 merging
        시그널을 발사하면, 영상 스트림 종료 직후 ThumbnailsConvertor 시점에
        라벨이 "병합 중"으로 잠겨 이후 오디오 스트림 다운로드 동안에도
        그대로 고정되는 UX 버그가 발생한다.
        """
        status        = d.get("status")
        postprocessor = d.get("postprocessor", "")

        # 후처리 단계에서도 경로 후보를 누적 (취소 시 정리용)
        self._collect_paths_from_hook(d)

        if postprocessor == "Merger" and status == "started":
            # 진짜 머지 단계 — 사용자에게 "병합 중" 표시
            self.merging.emit()

        if status == "finished":
            # 모든 후처리기의 완료 이벤트에서 최종 파일 경로 갱신.
            # 체인의 마지막 단계(MoveFiles 등)가 최종 경로를 갖는다.
            self._output_path = d.get("info_dict", {}).get(
                "filepath",
                self._output_path
            )

    # ── 잔여물 추적·정리 ──────────────────────────────────────

    def _collect_paths_from_hook(self, d: dict):
        """
        yt-dlp 후크 dict 에서 파일 경로 후보를 모두 추출해 _touched_files 에 누적.

        경로 후보가 등장하는 키 (yt-dlp 2026.3.17 기준):
        - progress_hook: d["filename"]
        - postprocess_hook: d["info_dict"]["filepath"], d["info_dict"]["__files_to_move"]
        - 양쪽 공통: d["info_dict"]["filename"], d["info_dict"]["_filename"]

        prefix 매칭 같은 추측 경로는 쓰지 않는다 — yt-dlp 가 명시적으로 알려준
        경로만 신뢰. 빈 문자열·None 은 자연스럽게 걸러진다.
        """
        # progress_hook 의 평탄한 키
        fn = d.get("filename")
        if fn:
            self._touched_files.add(fn)

        info = d.get("info_dict") or {}
        if not isinstance(info, dict):
            return

        # postprocess_hook 의 info_dict 경로 키들
        for key in ("filepath", "filename", "_filename"):
            v = info.get(key)
            if isinstance(v, str) and v:
                self._touched_files.add(v)

        # __files_to_move 는 {원본경로: 목적경로} 형태의 dict (yt-dlp 내부 키)
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

        자식 프로세스 종료가 선행되어야 Windows 의 파일 잠금이 풀려 삭제가
        성공한다. run() 의 정리 블록에서 terminate_pids 직후 호출된다.

        삭제 실패(권한 / 이미 없음 / 잠금) 는 조용히 무시 — 일부라도 지우는 게
        목적이고, 실패 자체를 사용자에게 보고하지 않는다 (취소 흐름의 무게를
        가볍게 유지).
        """
        for path_str in list(self._touched_files):
            base = Path(path_str)
            # 본체
            self._safe_unlink(base)
            # yt-dlp 잔여 형제 — base.part, base.ytdl, base.part.ytdl 등
            # base.with_suffix 가 아니라 문자열 결합. 멀티-suffix(.mp4.part)
            # 가 정상 패턴이라 with_suffix 는 망가뜨릴 수 있다.
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
