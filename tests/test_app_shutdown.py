"""앱 종료 때 다운로드 정리 (열 번째 계획 작업 5-1, D057)."""
import functools
import http.server
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QMessageBox

from controllers.download_manager import DownloadManager
from models.download_item import DownloadItem, DownloadStatus
from ui.main_window import MainWindow

_REPO = Path(__file__).resolve().parent.parent

_CHILD = r"""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from controllers.download_manager import DownloadManager
from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget

url, save = sys.argv[1:3]
app = QApplication([])
item = DownloadItem(url=url, title="T", format_id="best", ext="mp4")
item.status = DownloadStatus.WAITING
widget = DownloadItemWidget(item)
manager = DownloadManager({"save_path": save, "max_concurrent": 1}, {item.item_id: item}, {item.item_id: widget})
manager.enqueue(item.item_id)

def on_progress(pct):
    if pct > 2:
        manager.shutdown()
        app.quit()

manager.dl_workers[item.item_id].progress.connect(on_progress, Qt.ConnectionType.QueuedConnection)
sys.exit(app.exec())
"""


class _Manager:
    def __init__(self, count):
        self.count = count
        self.shutdowns = 0

    def unfinished_count(self):
        return self.count

    def shutdown(self):
        self.shutdowns += 1


class _Event:
    def __init__(self):
        self.result = None

    def accept(self):
        self.result = "accept"

    def ignore(self):
        self.result = "ignore"


def _close(monkeypatch, count, reply=None):
    asked = []

    def question(*a):
        asked.append(a)
        return reply

    monkeypatch.setattr(QMessageBox, "question", question)
    hidden = []
    window = SimpleNamespace(
        download_manager=_Manager(count), hide=lambda: hidden.append(True), _update_check_worker=None
    )
    event = _Event()
    MainWindow.closeEvent(window, event)
    return window.download_manager, event, asked, hidden


def test_close_declined_keeps_running(monkeypatch):
    manager, event, asked, hidden = _close(monkeypatch, 2, QMessageBox.StandardButton.No)
    assert asked
    assert event.result == "ignore"
    assert manager.shutdowns == 0
    assert hidden == []


def test_close_confirmed_cancels_and_waits(monkeypatch):
    manager, event, asked, hidden = _close(monkeypatch, 2, QMessageBox.StandardButton.Yes)
    assert asked
    assert event.result == "accept"
    assert manager.shutdowns == 1
    assert hidden == [True]


def test_close_without_downloads_does_not_ask(monkeypatch):
    manager, event, asked, _ = _close(monkeypatch, 0)
    assert asked == []
    assert event.result == "accept"
    assert manager.shutdowns == 1


def test_unfinished_count_includes_waiting():
    waiting = DownloadItem(url="u", status=DownloadStatus.WAITING)
    done = DownloadItem(url="u", status=DownloadStatus.DONE)
    manager = DownloadManager({"save_path": ""}, {"a": waiting, "b": done}, {})
    assert manager.unfinished_count() == 1


def test_shutdown_stops_queue(monkeypatch):
    waiting = DownloadItem(url="u", status=DownloadStatus.WAITING)
    manager = DownloadManager({"save_path": ""}, {"a": waiting}, {})
    started = []
    monkeypatch.setattr(manager, "_start_worker", started.append)
    manager.shutdown()
    manager._dispatch_next()
    assert started == []


@pytest.fixture
def slow_server(tmp_path):
    srv = tmp_path / "srv"
    srv.mkdir()
    (srv / "big.mp4").write_bytes(b"\0" * (100 << 20))

    class Slow(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def copyfile(self, source, outputfile):
            try:
                while block := source.read(1 << 18):
                    outputfile.write(block)
                    time.sleep(0.01)
            except OSError:
                pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Slow, directory=str(srv)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/big.mp4"
    server.shutdown()


def test_quit_while_downloading_exits_clean(slow_server, tmp_path):
    # 워커가 도는 중 앱이 끝나면 0xC0000409 로 죽고 임시 폴더가 남던 문제
    save = tmp_path / "save"
    save.mkdir()
    result = subprocess.run(
        [sys.executable, "-c", _CHILD, slow_server, str(save)],
        check=False,
        cwd=_REPO,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")[-500:]
    assert list(save.glob(".avd_*")) == []
