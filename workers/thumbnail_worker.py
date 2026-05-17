# workers/thumbnail_worker.py
# 썸네일 이미지를 백그라운드로 다운로드하는 워커

import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap


class ThumbnailWorker(QThread):
    """
    썸네일 URL에서 이미지를 다운로드하는 워커 스레드

    시그널:
        finished : 다운로드 완료 시 QPixmap 전달
    """

    finished = Signal(QPixmap)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            res = requests.get(self.url, timeout=5)
            res.raise_for_status()

            pixmap = QPixmap()
            pixmap.loadFromData(res.content)

            if not pixmap.isNull():
                self.finished.emit(pixmap)

        except Exception as e:
            print(f"[ThumbnailWorker] 썸네일 로드 실패: {e}")