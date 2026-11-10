# 플레이리스트 확인 중 취소하면 늦게 온 결과로 선택 창이 뜨지 않는다.
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

import controllers.playlist_flow as pf


class _FakeWorker(QObject):
    probe_ready = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url):
        super().__init__()

    def start(self):
        pass

    def requestInterruption(self):
        pass

    def quit(self):
        pass


def test_late_probe_result_after_cancel_is_ignored(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(pf, "PlaylistProbeWorker", _FakeWorker)
    parent = QObject()
    flow = pf.PlaylistFlow(parent)
    shown = []
    monkeypatch.setattr(flow, "_show_dialog", shown.append)

    flow.start("https://example.invalid/list")
    worker = flow._worker
    flow.cancel()
    assert not flow.is_busy

    worker.probe_ready.emit("result")
    worker.error.emit("late")
    app.processEvents()
    app.processEvents()
    assert shown == []
    assert not flow.is_busy
