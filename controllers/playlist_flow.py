# controllers/playlist_flow.py
# 플레이리스트 라이프사이클(probe → 선택 다이얼로그 → 항목 펼침)을
# 단일 객체가 소유하는 상태머신. ADR-003 의 매니저 분리 철학과 같은 결로,
# MainWindow 가 플레이리스트 흐름의 시그널 라우팅을 직접 떠안지 않게 한다.

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt
from PySide6.QtWidgets import QWidget

from workers.playlist_probe_worker import PlaylistProbeWorker
from ui.playlist_select_dialog import PlaylistSelectDialog


class PlaylistFlow(QObject):
    """
    플레이리스트 흐름 상태머신.

    공개 진입점:
        start(url) : 플레이리스트 처리를 시작. 이미 진행 중이면 무시.

    시그널:
        status(str)               : 진행 상태 메시지 (상태바용)
        entry_ready(str,str,str)  : 펼칠 항목 하나 — (url, format_id, ext).
                                     MainWindow 가 받아 항목·위젯·InfoWorker
                                     를 생성한다. mode 가 아니라 format_id/ext
                                     로 넘기는 이유는 아래 _mode_to_format 참조.
        finished()                : 어떤 결말이든(성공·실패·취소) 종료 알림.

    설계 원칙 (v4.7.5 PlaylistFlow 에서 채택):
        1. 한 시점에 활성 플로우는 최대 1개 (_busy 가드).
        2. 워커 시그널 핸들러 안에서 자기 스레드를 wait/종료하지 않는다.
           스레드 종료는 quit→finished→deleteLater 체인에 맡긴다.
        3. 선택 다이얼로그는 워커 정리가 끝난 뒤 QTimer.singleShot(0) 로
           한 박자 미뤄 modal exec — 시그널 재진입 데드락 방지.
        4. 종료·실패·취소를 모두 _finish() 단일 경로로 수렴 → MainWindow 는
           finished 시그널만 본다.

    음원 단일 출처 (ADR 합의):
        "음원만" 선택 시 별도 비트레이트·컨테이너를 만들지 않고, 단일 항목
        경로가 쓰는 것과 동일한 format_id="bestaudio/best" + ext="mp3" 만
        박는다. 실제 음질은 core/downloader.py 의 후처리(MP3_BITRATE_KBPS)
        단일 출처가 결정한다. ADR-005 가 음원 정책을 바꾸면 플레이리스트는
        코드 변경 없이 자동으로 따라온다.
    """

    status      = Signal(str)
    entry_ready = Signal(str, str, str)  # (url, format_id, ext)
    finished    = Signal()

    # 형태 → (format_id, ext) 매핑. core/info_fetcher.py 의 통합 포맷 /
    # MP3 행과 동일한 값을 쓴다 — 단일 출처. 여기 값이 바뀌면 info_fetcher
    # 의 해당 행과 ui/download_item_widget.py 의 AUTO_FORMAT_ID 도 함께.
    _VIDEO_FORMAT_ID = "bestvideo+bestaudio/best"
    _VIDEO_EXT       = "mp4"
    _AUDIO_FORMAT_ID = "bestaudio/best"
    _AUDIO_EXT       = "mp3"

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: PlaylistProbeWorker | None = None
        self._busy: bool = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    # ── 진입점 ────────────────────────────────────────

    def start(self, url: str):
        """플레이리스트 처리 시작. 이미 진행 중이면 조용히 무시."""
        if self._busy:
            return
        self._busy = True
        self.status.emit("플레이리스트 정보를 가져오는 중...")

        worker = PlaylistProbeWorker(url)
        worker.finished.connect(self._on_probe_done, Qt.ConnectionType.QueuedConnection)
        worker.error.connect(self._on_probe_error, Qt.ConnectionType.QueuedConnection)
        # 스레드 종료는 자기 핸들러가 아니라 시그널 체인에 맡긴다(원칙 2).
        worker.finished.connect(worker.quit)
        worker.error.connect(worker.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def cancel(self):
        """진행 중 probe 워커를 종료 시도하고 플로우를 닫는다."""
        w = self._worker
        if w is not None:
            try:
                w.requestInterruption()
                w.quit()
            except Exception:
                pass
        self._finish()

    # ── probe 워커 핸들러 ─────────────────────────────

    def _on_probe_done(self, result):
        """probe 성공 — 워커 정리가 끝난 뒤 다이얼로그를 한 박자 미뤄 띄운다."""
        self._worker = None
        # 원칙 3: 워커 스레드 정리가 이벤트 큐에서 끝난 뒤 모달을 띄운다.
        QTimer.singleShot(0, lambda r=result: self._show_dialog(r))

    def _on_probe_error(self, message: str):
        self._worker = None
        self.status.emit(f"플레이리스트를 가져오지 못했습니다: {message}")
        self._finish()

    # ── 다이얼로그 단계 ───────────────────────────────

    def _show_dialog(self, result):
        """선택 다이얼로그를 modal 로 띄우고 결과를 항목 펼침으로 연결."""
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = PlaylistSelectDialog(result, parent)
        dialog.confirmed.connect(self._on_confirmed)
        # confirmed 가 안 오고 닫히면(취소) finished 로 수렴.
        dialog.exec()
        # exec 반환 후에도 confirmed 가 발사됐으면 _on_confirmed 에서 이미
        # 펼침을 마쳤다. 여기서는 항상 _finish 로 닫는다(중복 호출 방어됨).
        self._finish()

    def _on_confirmed(self, entries: list, mode: str):
        """사용자가 항목·형태를 확정 — 각 항목을 entry_ready 로 펼친다."""
        format_id, ext = self._mode_to_format(mode)
        for entry in entries:
            # entry 는 PlaylistEntry. url 만 MainWindow 로 넘기면 거기서
            # InfoWorker 가 제목·메타·썸네일을 풀 추출로 채운다.
            self.entry_ready.emit(entry.url, format_id, ext)
        self.status.emit(f"{len(entries)}개 항목을 추가했습니다.")

    def _mode_to_format(self, mode: str) -> tuple[str, str]:
        """형태 문자열을 (format_id, ext) 로. 단일 출처 매핑."""
        if mode == "audio":
            return (self._AUDIO_FORMAT_ID, self._AUDIO_EXT)
        return (self._VIDEO_FORMAT_ID, self._VIDEO_EXT)

    # ── 종료 수렴 ─────────────────────────────────────

    def _finish(self):
        """
        모든 결말의 단일 수렴점. 중복 호출에 안전하다 — _busy 가 이미
        False 면 즉시 반환해 finished 가 두 번 발사되지 않는다.
        """
        if not self._busy:
            return
        self._busy = False
        self._thread = None
        self._worker = None
        self.finished.emit()
