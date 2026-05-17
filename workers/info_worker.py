# workers/info_worker.py
# 영상 정보 추출을 백그라운드 스레드에서 실행하는 파일
# UI가 멈추지 않도록 QThread로 분리

from PySide6.QtCore import QThread, Signal
from core.info_fetcher import InfoFetcher, VideoInfo


class InfoWorker(QThread):
    """
    URL에서 영상 정보를 백그라운드로 추출하는 워커 스레드

    시그널:
        finished  : 정보 추출 성공 시 VideoInfo 전달
        error     : 실패 시 에러 메시지 문자열 전달
    """

    # 성공 시그널 - VideoInfo 객체 전달
    finished = Signal(object)

    # 실패 시그널 - 에러 메시지 전달
    error    = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url     = url
        self._fetcher = InfoFetcher()

    def run(self):
        """
        스레드 실행 진입점
        InfoFetcher로 영상 정보 추출 후 시그널로 결과 전달
        """
        try:
            info = self._fetcher.fetch(self.url)
            self.finished.emit(info)

        except Exception as e:
            self.error.emit(str(e))