# workers/update_check_worker.py
# yt-dlp 새 버전이 있는지 백그라운드 스레드에서 확인하는 워커 (D062)
#
# 버전 확인은 네트워크를 쓰므로 GUI 스레드에서 돌리면 응답을 기다리는 동안 창이 멈춘다.

from PySide6.QtCore import QThread, Signal

from utils.updater import YtdlpUpdater


class UpdateCheckWorker(QThread):
    """
    시그널:
        checked(bool, str, str) : (업데이트 필요 여부, 현재 버전, 최신 버전)
    """

    checked = Signal(bool, str, str)

    def run(self):
        self.checked.emit(*YtdlpUpdater().is_update_available())
