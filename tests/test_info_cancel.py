# 정보 가져오는 중에도 "취소" 가 듣는다. 늦게 온 결과는 버리고, 재시도는 정보 추출부터.
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from ui.main_window import MainWindow


@pytest.fixture
def yes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes)


def _fake(item, worker):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    fake = SimpleNamespace(
        items={item.item_id: item},
        widgets={item.item_id: DownloadItemWidget(item)},
        status_bar=SimpleNamespace(showMessage=lambda _: None),
        download_manager=SimpleNamespace(is_active=lambda _: False),
        info_workers={item.item_id: worker},
        _info_pending=[],
        _info_running={item.item_id},
        _info_cancelled=set(),
        _predetermined={item.item_id: ("bestaudio/best", "mp3")},
        _failed_specs={},
        _dispatch_info=lambda: None,
    )
    fake._release_info_slot = lambda iid: MainWindow._release_info_slot(fake, iid)
    fake._cancel_info = lambda iid: MainWindow._cancel_info(fake, iid)
    fake.widgets[item.item_id].update_status(DownloadStatus.FETCHING)
    return fake


def test_cancel_while_fetching(yes):
    item = DownloadItem(url="https://example.invalid/a")
    worker = object()
    fake = _fake(item, worker)
    MainWindow._on_cancel(fake, item.item_id)
    assert item.status == DownloadStatus.CANCELLED
    assert item.item_id not in fake._info_running
    # 늦게 온 결과는 info_workers 의 현재 워커가 아니므로 버려진다. 객체는 끝날 때까지 붙잡는다.
    assert fake.info_workers.get(item.item_id) is not worker
    assert worker in fake._info_cancelled


def test_retry_after_fetch_cancel_refetches_with_spec(yes):
    item = DownloadItem(url="https://example.invalid/a")
    fake = _fake(item, object())
    queued = []
    fake._enqueue_info = queued.append
    MainWindow._on_cancel(fake, item.item_id)
    MainWindow._on_retry(fake, item.item_id)
    assert queued == [item.item_id]
    assert fake._predetermined[item.item_id] == ("bestaudio/best", "mp3")
