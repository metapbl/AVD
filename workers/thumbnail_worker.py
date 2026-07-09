# workers/thumbnail_worker.py
# 썸네일 이미지를 백그라운드로 다운로드하는 워커
#
# v7 변경 (썸네일 표시 실패 근본 수정):
#   • QPixmap/QImage 생성을 워커 스레드에서 제거 — bytes 만 emit
#   • item_id 동봉 — 늦은 시그널이 엉뚱한 위젯에 꽂히는 사고 방지
#   • cancel() 추가 — 위젯 삭제 시 진행 중 워커 무효화
# v8 변경 (미리보기 누락 근본 수정):
#   • 단일 URL → 후보 URL 리스트를 순회. 첫 후보(예: YouTube
#     maxresdefault.jpg)가 404 여도 다음 후보(sddefault/hqdefault)로
#     폴백해 성공할 때까지 시도. hqdefault 는 모든 YouTube 영상에
#     존재하므로 사실상 100% 표시.
#   • 실패 시 마지막 사유를 reason 에 담아 emit + 콘솔 진단 로그.

import requests
from PySide6.QtCore import QThread, Signal


class ThumbnailWorker(QThread):
    """
    썸네일 URL 후보 리스트에서 이미지를 다운로드하는 워커 스레드.

    핵심 원칙: QPixmap 은 GUI 스레드에서만 만든다.
    이 워커는 raw bytes 까지만 책임진다.

    시그널:
        thumb_ready(item_id: str, data: bytes) : 후보 중 하나 다운로드 성공.
            ⚠ QThread 내장 finished 와 겹치지 않도록 thumb_ready 로 둔다.
            내장 finished 는 MainWindow 가 스레드 수명 관리에 쓴다.
            (LESSONS: QThread 상속 워커는 started/finished 이름을 자체
            시그널로 쓰지 말 것.)
        failed(item_id: str, reason: str)      : 모든 후보 실패
    """

    thumb_ready = Signal(str, bytes)
    failed      = Signal(str, str)

    TIMEOUT_SEC = 10
    MAX_BYTES   = 8 * 1024 * 1024  # 8MB 방어

    def __init__(self, item_id: str, urls):
        """
        urls: 후보 URL 문자열 하나 또는 리스트. 하위호환을 위해 문자열도 허용.
        """
        super().__init__()
        self.item_id  = item_id
        if isinstance(urls, str):
            self.urls = [urls] if urls else []
        else:
            self.urls = [u for u in (urls or []) if isinstance(u, str) and u]
        self._cancel  = False

    def cancel(self):
        """진행 중인 워커 무효화."""
        self._cancel = True

    def run(self):
        if self._cancel or not self.urls:
            self.failed.emit(self.item_id, "empty url or cancelled")
            return

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "image/webp,image/jpeg,image/png,image/*,*/*;q=0.8",
        }

        last_reason = "no candidates"
        for idx, url in enumerate(self.urls):
            if self._cancel:
                self.failed.emit(self.item_id, "cancelled")
                return
            try:
                res = requests.get(url, timeout=self.TIMEOUT_SEC, headers=headers)
                res.raise_for_status()

                if self._cancel:
                    self.failed.emit(self.item_id, "cancelled")
                    return

                data = res.content
                if not data:
                    last_reason = "empty response"
                    continue
                if len(data) > self.MAX_BYTES:
                    last_reason = "response too large"
                    continue

                # 성공 — 후보 하나라도 받으면 즉시 emit 하고 종료.
                self.thumb_ready.emit(self.item_id, data)
                return

            except Exception as e:
                # 다음 후보로 폴백. 마지막 사유만 보관.
                last_reason = f"{type(e).__name__}: {e}"
                continue

        # 모든 후보 실패 — 진단 로그 + 실패 emit.
        print(
            f"[thumb] all {len(self.urls)} candidate(s) failed "
            f"(item={self.item_id}) last={last_reason} "
            f"first_url={self.urls[0][:80] if self.urls else ''}"
        )
        self.failed.emit(self.item_id, last_reason)
