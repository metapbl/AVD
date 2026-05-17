# workers/thumbnail_worker.py
# 썸네일 이미지를 백그라운드로 다운로드하는 워커
#
# v7 변경 (썸네일 표시 실패 근본 수정):
#   • QPixmap/QImage 생성을 워커 스레드에서 제거 — bytes 만 emit
#   • item_id 동봉 — 늦은 시그널이 엉뚱한 위젯에 꽂히는 사고 방지
#   • cancel() 추가 — 위젯 삭제 시 진행 중 워커 무효화

import requests
from PySide6.QtCore import QThread, Signal


class ThumbnailWorker(QThread):
    """
    썸네일 URL에서 이미지를 다운로드하는 워커 스레드.

    핵심 원칙: QPixmap 은 GUI 스레드에서만 만든다.
    이 워커는 raw bytes 까지만 책임진다.

    시그널:
        finished(item_id: str, data: bytes) : 다운로드 완료
        failed(item_id: str, reason: str)   : 실패
    """

    finished = Signal(str, bytes)
    failed   = Signal(str, str)

    TIMEOUT_SEC = 10
    MAX_BYTES   = 8 * 1024 * 1024  # 8MB 방어

    def __init__(self, item_id: str, url: str):
        super().__init__()
        self.item_id  = item_id
        self.url      = url
        self._cancel  = False

    def cancel(self):
        """진행 중인 워커 무효화."""
        self._cancel = True

    def run(self):
        if self._cancel or not self.url:
            self.failed.emit(self.item_id, "empty url or cancelled")
            return
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "image/webp,image/jpeg,image/png,image/*,*/*;q=0.8",
            }
            res = requests.get(self.url, timeout=self.TIMEOUT_SEC, headers=headers)
            res.raise_for_status()

            if self._cancel:
                self.failed.emit(self.item_id, "cancelled")
                return

            data = res.content
            if not data:
                self.failed.emit(self.item_id, "empty response")
                return
            if len(data) > self.MAX_BYTES:
                self.failed.emit(self.item_id, "response too large")
                return

            self.finished.emit(self.item_id, data)

        except Exception as e:
            self.failed.emit(self.item_id, str(e))
