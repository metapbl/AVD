# 플레이리스트 확인 중 표시 (열네 번째 계획 작업 4).
from types import SimpleNamespace

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from controllers.playlist_flow import PlaylistFlow
from ui.main_window import MainWindow

PLAYLIST = "https://example.invalid/playlist?list=1"


def test_playlist_link_shows_banner():
    shown = []
    fake = SimpleNamespace(
        playlist_flow=SimpleNamespace(is_busy=False, start=lambda url: None),
        playlist_banner=SimpleNamespace(setVisible=shown.append),
    )
    MainWindow._on_link_submitted(fake, PLAYLIST)
    assert shown == [True]


def test_probe_done_signals_before_dialog(monkeypatch):
    monkeypatch.setattr(PlaylistFlow, "_show_dialog", lambda self, result: None)
    app = QApplication.instance() or QApplication([])  # noqa: F841 — QObject 에 필요
    parent = QObject()
    flow = PlaylistFlow(parent)
    got = []
    flow.probe_finished.connect(lambda: got.append(True))
    flow._on_probe_done(SimpleNamespace(title="p", entries=[], total_found=0))
    assert got == [True]


def test_probe_error_signals_end():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — QObject 에 필요
    parent = QObject()
    flow = PlaylistFlow(parent)
    flow._busy = True
    got = []
    flow.probe_finished.connect(lambda: got.append(True))
    flow._on_probe_error("실패")
    assert got == [True]
