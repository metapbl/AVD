# 조용한 실패 안내와 상태 표시 (열두 번째 계획 작업 3·4).
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

import ui.main_window as mw
from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from ui.main_window import MainWindow


@pytest.fixture
def warnings(monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: shown.append(text))
    return shown


def _locked_unlink(monkeypatch):
    def fail(self, missing_ok=False):
        raise PermissionError("사용 중")
    monkeypatch.setattr(Path, "unlink", fail)


def test_delete_failure_is_reported(tmp_path, warnings, monkeypatch):
    f = tmp_path / "영상.mp4"
    f.write_bytes(b"")
    _locked_unlink(monkeypatch)
    MainWindow._delete_files(SimpleNamespace(), [str(f)])
    assert len(warnings) == 1
    assert str(f) in warnings[0]


def test_delete_success_is_quiet(tmp_path, warnings):
    f = tmp_path / "영상.mp4"
    f.write_bytes(b"")
    MainWindow._delete_files(SimpleNamespace(), [str(f)])
    assert not f.exists()
    assert not warnings


def test_remove_item_reports_delete_failure(tmp_path, warnings, monkeypatch):
    f = tmp_path / "영상.mp4"
    f.write_bytes(b"")
    item = DownloadItem(url="u", save_path=str(f), status=DownloadStatus.DONE)
    dialog = SimpleNamespace(exec=lambda: None, confirmed=True, delete_disk_files=True)
    monkeypatch.setattr(mw, "ConfirmRemoveDialog", lambda *a, **k: dialog)
    _locked_unlink(monkeypatch)
    fake = SimpleNamespace(
        items={item.item_id: item},
        widgets={"다른 항목": object()},
        download_manager=SimpleNamespace(is_active=lambda _: False, enqueue=lambda _: None),
        _remove_item_quiet=lambda _: None,
    )
    fake._delete_files = lambda paths: MainWindow._delete_files(fake, paths)
    MainWindow._on_remove(fake, item.item_id)
    assert len(warnings) == 1


@pytest.mark.parametrize("handler", [MainWindow._on_play_file, MainWindow._on_open_folder])
def test_moved_file_is_reported(tmp_path, warnings, monkeypatch, handler):
    opened = []
    monkeypatch.setattr(mw, "open_file", opened.append)
    monkeypatch.setattr(mw, "open_folder", opened.append)
    gone = str(tmp_path / "없음.mp4")
    item = DownloadItem(url="u", save_path=gone)
    handler(SimpleNamespace(items={item.item_id: item}), item.item_id)
    assert not opened
    assert gone in warnings[0]


@pytest.mark.parametrize("handler", [MainWindow._on_play_file, MainWindow._on_open_folder])
def test_existing_file_opens_without_warning(tmp_path, warnings, monkeypatch, handler):
    opened = []
    monkeypatch.setattr(mw, "open_file", opened.append)
    monkeypatch.setattr(mw, "open_folder", opened.append)
    f = tmp_path / "영상.mp4"
    f.write_bytes(b"")
    item = DownloadItem(url="u", save_path=str(f))
    handler(SimpleNamespace(items={item.item_id: item}), item.item_id)
    assert opened == [str(f)]
    assert not warnings


def _widget():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    return DownloadItemWidget(DownloadItem(url="u", title="t"))


@pytest.mark.parametrize("status, color", [
    (DownloadStatus.WAITING, "#9a9a9a"),
    (DownloadStatus.CANCELLED, "#9a9a9a"),
    (DownloadStatus.ERROR, "#e5636b"),
])
def test_status_color(status, color):
    w = _widget()
    w.update_status(status)
    assert color in w.lbl_status.styleSheet()


def test_active_status_returns_to_accent_color():
    w = _widget()
    w.update_status(DownloadStatus.ERROR)
    w.update_status(DownloadStatus.DOWNLOADING)
    assert w.lbl_status.styleSheet() == ""


def test_done_with_gain_failure_uses_warning_color():
    w = _widget()
    w.update_normalize_failed("실패")
    w.update_status(DownloadStatus.DONE)
    assert "#e0b050" in w.lbl_status_mark.styleSheet()
    assert w.lbl_status_mark.text() == "⚠"
    assert "#e0b050" not in w.lbl_status.styleSheet()


def test_done_color_only_on_mark():
    """success2 는 라이트 테마에서 글자 대비가 모자라 기호에만 칠한다."""
    w = _widget()
    w.update_status(DownloadStatus.DONE)
    assert w.lbl_status_mark.text() == "✓"
    assert "#57b884" in w.lbl_status_mark.styleSheet()
    assert "#57b884" not in w.lbl_status.styleSheet()
    w.update_status(DownloadStatus.ERROR)
    assert w.lbl_status_mark.isHidden()


def test_item_buttons_have_tooltips():
    w = _widget()
    for button in (w.btn_open, w.btn_play, w.btn_remove):
        assert button.toolTip()


def test_download_done_alerts_taskbar(monkeypatch):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    alerts = []
    monkeypatch.setattr(QApplication, "alert", lambda widget, *a: alerts.append(widget))
    item = DownloadItem(url="u", title="t")
    fake = SimpleNamespace(
        items={item.item_id: item},
        widgets={item.item_id: DownloadItemWidget(item)},
        status_bar=SimpleNamespace(showMessage=lambda _: None),
    )
    MainWindow._on_download_done(fake, item.item_id, "")
    assert alerts == [fake]


def test_meta_without_uploader_starts_with_duration():
    w = _widget()
    w.update_meta("", 245)
    assert w.lbl_meta.text() == "4:05"
    w.update_meta("Channel", 245)
    assert w.lbl_meta.text() == "Channel  •  4:05"


def test_window_geometry_restored(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from ui.main_window import MainWindow
    from utils import config_manager

    monkeypatch.setattr(config_manager, "CONFIG_PATH", tmp_path / "config.json")
    first = MainWindow()
    first.setGeometry(120, 140, 1000, 700)
    MainWindow.closeEvent(first, SimpleNamespace(accept=lambda: None))
    second = MainWindow()
    assert (second.width(), second.height()) == (1000, 700)
    for w in (first, second):
        w.download_manager.shutdown()
        w.deleteLater()
