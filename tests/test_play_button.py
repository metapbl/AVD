# 완료 항목 "▶ 재생" 버튼 — 받은 파일을 OS 기본 앱으로 연다 (D049).
import pytest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QVBoxLayout

from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from utils.file_utils import open_file


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls.append(url) or True)
    return urls


def test_open_file_opens_existing_file(tmp_path, opened):
    f = tmp_path / "영상.mp4"
    f.write_bytes(b"")
    open_file(str(f))
    assert opened == [QUrl.fromLocalFile(str(f))]


def test_open_file_ignores_missing_file(tmp_path, opened):
    open_file(str(tmp_path / "없음.mp4"))
    assert opened == []


def _widget():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    return DownloadItemWidget(DownloadItem(url="u", title="t"))


def test_play_button_only_on_done():
    w = _widget()
    for status in DownloadStatus:
        w.update_status(status)
        assert w.btn_play.isVisibleTo(w) == (status == DownloadStatus.DONE), status


def test_play_button_between_open_and_remove():
    w = _widget()
    (col,) = [lay for lay in w.findChildren(QVBoxLayout) if lay.indexOf(w.btn_open) >= 0]  # 버튼 줄
    assert col.indexOf(w.btn_open) + 1 == col.indexOf(w.btn_play) == col.indexOf(w.btn_remove) - 1


def test_play_button_emits_item_id():
    w = _widget()
    got = []
    w.play_requested.connect(got.append)
    w.update_status(DownloadStatus.DONE)
    w.btn_play.click()
    assert got == [w.item.item_id]


def test_done_buttons_fit_without_overlap():
    w = _widget()
    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    w.update_status(DownloadStatus.DONE)
    w.show()
    QApplication.processEvents()
    a, b, c = (x.geometry() for x in (w.btn_open, w.btn_play, w.btn_remove))
    assert a.bottom() < b.top() and b.bottom() < c.top()
    assert c.bottom() < w.height()
    w.close()
