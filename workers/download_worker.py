# workers/download_worker.py
# 다운로드를 백그라운드 스레드에서 실행하는 파일
# UI가 멈추지 않도록 QThread로 분리

from PySide6.QtCore import QThread, Signal
from core.downloader import Downloader


class DownloadWorker(QThread):
    """
    다운로드를 백그라운드로 실행하는 워커 스레드

    시그널:
        progress    : 진행률 (0.0 ~ 100.0)
        speed       : 다운로드 속도 문자열 (예: "2.3 MiB/s")
        eta         : 남은 시간 문자열 (예: "00:42")
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

    def run(self):
        """
        스레드 실행 진입점
        Downloader.download() 호출 후 시그널로 결과 전달
        """
        try:
            self._downloader.download(
                url              = self.url,
                format_id        = self.format_id,
                ext              = self.ext,
                save_dir         = self.save_dir,
                progress_hook    = self._on_progress,
                postprocess_hook = self._on_postprocess,
            )

            # 취소되지 않았으면 완료 시그널 전송
            self.finished.emit(self._output_path)

        except Exception as e:
            err = str(e)
            if "취소" in err or "Cancelled" in err:
                self.cancelled.emit()
            else:
                self.error.emit(err)

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
            # 진행률
            pct_str = d.get("_percent_str", "0%").strip()
            try:
                pct = float(pct_str.replace("%", ""))
                self.progress.emit(pct)
            except ValueError:
                pass

            # 속도
            speed = d.get("_speed_str", "").strip()
            if speed:
                self.speed.emit(speed)

            # 남은 시간
            eta = d.get("_eta_str", "").strip()
            if eta:
                self.eta.emit(eta)

            # 파일 크기
            size = d.get("_total_bytes_str", "") or \
                   d.get("_total_bytes_estimate_str", "")
            if size:
                self.file_size.emit(size.strip())

        elif status == "finished":
            # 단일 스트림 완료 (병합 전)
            self._output_path = d.get("filename", "")
            self.progress.emit(100.0)

    def _on_postprocess(self, d: dict):
        """
        yt-dlp 후처리 콜백
        영상+음성 병합 시작/완료 시점에 호출됨
        """
        status = d.get("status")

        if status == "started":
            # 병합 시작 알림
            self.merging.emit()

        elif status == "finished":
            # 병합 완료 - 최종 파일 경로 저장
            self._output_path = d.get("info_dict", {}).get(
                "filepath",
                self._output_path
            )