# 오류는 항목에 사유와 함께 남고 자동 창을 띄우지 않는다 (D061). 버전 확인은 워커에서 (D062).
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from ui.main_window import MainWindow
from utils.updater import YtdlpUpdater
from workers.update_check_worker import UpdateCheckWorker

PRIVATE = "ERROR: Private video. Sign in if you've been granted access"


@pytest.fixture
def no_modal(monkeypatch):
    def fail(self):
        raise AssertionError("자동으로 뜨면 안 되는 창")
    monkeypatch.setattr(QMessageBox, "exec", fail)
    monkeypatch.setattr(QApplication, "alert", lambda *a: None)


def _fake(item):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    fake = SimpleNamespace(
        items={item.item_id: item},
        widgets={item.item_id: DownloadItemWidget(item)},
        status_bar=SimpleNamespace(showMessage=lambda _: None),
        _predetermined={},
        _failed_specs={},
        _release_info_slot=lambda _: None,
        _enqueue_info=lambda _: None,
    )
    fake._mark_error = lambda item_id, err: MainWindow._mark_error(fake, item_id, err)
    return fake


def test_download_error_keeps_reason_without_modal(no_modal):
    item = DownloadItem(url="u", title="t")
    fake = _fake(item)
    MainWindow._on_download_error(fake, item.item_id, PRIVATE)
    w = fake.widgets[item.item_id]
    assert item.status == DownloadStatus.ERROR
    assert item.error_msg == PRIVATE
    assert w.lbl_status.text() == "오류 · 비공개 영상입니다"


def test_error_detail_shows_original_message(monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append((self.text(), self.detailedText())))
    item = DownloadItem(url="u", title="t", error_msg=PRIVATE)
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    parent = QWidget()  # QMessageBox 의 부모는 진짜 위젯이어야 한다
    parent.items = {item.item_id: item}
    MainWindow._on_error_detail(parent, item.item_id)
    assert shown == [("비공개 영상입니다", PRIVATE)]


def test_detail_button_only_on_error():
    item = DownloadItem(url="u", title="t")
    fake = _fake(item)
    w = fake.widgets[item.item_id]
    for status in DownloadStatus:
        w.update_status(status)
        assert w.btn_detail.isVisibleTo(w) == (status == DownloadStatus.ERROR), status


def test_detail_button_emits_item_id():
    item = DownloadItem(url="u", title="t")
    fake = _fake(item)
    w = fake.widgets[item.item_id]
    got = []
    w.detail_requested.connect(got.append)
    w.btn_detail.click()
    assert got == [item.item_id]


def test_single_info_error_stays_in_list_with_url(no_modal):
    item = DownloadItem(url="https://example.invalid/a")
    fake = _fake(item)
    MainWindow._on_info_error(fake, item.item_id, PRIVATE)
    assert item.item_id in fake.items
    assert item.status == DownloadStatus.ERROR
    assert item.title == item.url
    assert item.error_msg == PRIVATE
    assert item.item_id not in fake._failed_specs


def test_single_info_retry_opens_quality_dialog_path(no_modal):
    item = DownloadItem(url="https://example.invalid/a")
    fake = _fake(item)
    queued = []
    fake._enqueue_info = queued.append
    MainWindow._on_info_error(fake, item.item_id, PRIVATE)
    MainWindow._on_retry(fake, item.item_id)
    assert queued == [item.item_id]
    assert item.item_id not in fake._predetermined


def test_playlist_info_retry_keeps_chosen_form(no_modal):
    item = DownloadItem(url="https://example.invalid/a")
    fake = _fake(item)
    queued = []
    fake._enqueue_info = queued.append
    spec = ("bestaudio/best", "mp3")
    fake._predetermined[item.item_id] = spec
    MainWindow._on_info_error(fake, item.item_id, PRIVATE)
    MainWindow._on_retry(fake, item.item_id)
    assert queued == [item.item_id]
    assert fake._predetermined[item.item_id] == spec


def test_update_check_worker_reports_result(monkeypatch):
    monkeypatch.setattr(YtdlpUpdater, "is_update_available", lambda self: (True, "1", "2"))
    worker = UpdateCheckWorker()
    got = []
    worker.checked.connect(lambda *a: got.append(a))
    worker.run()
    assert got == [(True, "1", "2")]


def test_update_prompt_only_when_needed(monkeypatch):
    asked = []
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *a: asked.append(a) or QMessageBox.StandardButton.No,
    )
    MainWindow._on_update_checked(SimpleNamespace(), False, "1", "1")
    assert not asked
    MainWindow._on_update_checked(SimpleNamespace(), True, "1", "2")
    assert len(asked) == 1


def test_close_waits_for_update_check():
    waited = []
    fake = SimpleNamespace(
        download_manager=SimpleNamespace(unfinished_count=lambda: 0, shutdown=lambda: None),
        _update_check_worker=SimpleNamespace(wait=lambda ms: waited.append(ms)),
        hide=lambda: None,
    )
    MainWindow.closeEvent(fake, SimpleNamespace(accept=lambda: None))
    assert waited
