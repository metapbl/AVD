# workers/download_worker.py
# 다운로드를 백그라운드 스레드에서 실행하는 파일
# UI가 멈추지 않도록 QThread로 분리

import time

from PySide6.QtCore import QThread, Signal
from core.downloader import Downloader
from utils.file_utils import strip_ansi


# yt-dlp 가 _eta_str 자리에 ETA 산정 불가의 의미로 박는 placeholder 들.
# 빈 문자열은 별도 처리(아예 안 옴) 되므로 여기서 제외.
_ETA_UNKNOWN_TOKENS = frozenset({
    "unknown", "unknown eta",
    "--:--", "--:--:--",
    "00:00", "00:00:00",
    "n/a",
})


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

        try:
            self._downloader.download(
                url              = self.url,
                format_id        = self.format_id,
                ext              = self.ext,
                save_dir         = self.save_dir,
                progress_hook    = self._on_progress,
                postprocess_hook = self._on_postprocess,
            )

            # 정상 완료
            self.finished.emit(self._output_path)

        except Exception as e:
            # 취소 예외는 타입으로 판별 (문자열 매칭은 언어/버전에 취약)
            if DownloadCancelled is not None and isinstance(e, DownloadCancelled):
                self.cancelled.emit()
            else:
                self.error.emit(str(e))

    def cancel(self):
        """외부에서 취소 요청"""
        self._downloader.cancel()

    def _on_progress(self, d: dict):
        """
        yt-dlp 진행률 콜백
        다운로드 진행 중 주기적으로 호출됨
        """
        status = d.get("status")

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

            # 파일 크기
            size = strip_ansi(
                d.get("_total_bytes_str", "")
                or d.get("_total_bytes_estimate_str", "")
            ).strip()
            if size:
                self.file_size.emit(size)

        elif status == "finished":
            # 단일 스트림 완료 (병합 전)
            self._output_path = d.get("filename", "")
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
