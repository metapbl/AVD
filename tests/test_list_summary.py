# 목록 요약, 완료 항목 지우기, 저장 폴더 표시 (열네 번째 계획 작업 1).
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QLabel

from models.download_item import DownloadItem
from models.download_item import DownloadStatus as S
from ui.download_item_widget import DownloadItemWidget
from ui.main_window import MainWindow, _summary_text


def _items(*statuses):
    return {str(i): DownloadItem(url="u", status=s, item_id=str(i)) for i, s in enumerate(statuses)}


def test_summary_counts_each_group():
    items = _items(S.FETCHING, S.DOWNLOADING, S.MERGING, S.NORMALIZING, S.WAITING, S.DONE, S.DONE, S.ERROR, S.CANCELLED)
    assert _summary_text(items) == "진행 4 · 대기 1 · 완료 2 · 오류 1 · 취소 1"


def test_summary_hides_zero_groups_and_empty_list():
    assert _summary_text(_items(S.DONE)) == "완료 1"
    assert _summary_text({}) == ""


def test_widget_reports_status_change():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    w = DownloadItemWidget(DownloadItem(url="u"))
    got = []
    w.status_changed.connect(lambda: got.append(True))
    w.update_status(S.DONE)
    assert got == [True]


def _fake_for_clear(items):
    removed, messages = [], []

    def remove(item_id):
        removed.append(item_id)
        items.pop(item_id)

    return SimpleNamespace(
        items=items,
        widgets=items,
        _remove_item_quiet=remove,
        lbl_empty=SimpleNamespace(setVisible=lambda v: messages.append(("empty", v))),
        status_bar=SimpleNamespace(showMessage=messages.append),
    ), removed, messages


def test_clear_done_removes_only_done_items():
    items = _items(S.DONE, S.DOWNLOADING, S.DONE, S.ERROR)
    fake, removed, messages = _fake_for_clear(items)
    MainWindow._on_clear_done(fake)
    assert removed == ["0", "2"]
    assert ("empty", True) not in messages
    assert "2개" in messages[-1]


def test_clear_done_shows_empty_label_when_list_empties():
    fake, _, messages = _fake_for_clear(_items(S.DONE))
    MainWindow._on_clear_done(fake)
    assert ("empty", True) in messages


def test_clear_done_with_nothing_to_clear():
    fake, removed, messages = _fake_for_clear(_items(S.ERROR))
    MainWindow._on_clear_done(fake)
    assert not removed
    assert messages == ["완료된 항목이 없습니다."]


def test_save_path_label_elides_but_tooltip_keeps_full_path():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    path = "C:\\" + "\\".join(["아주긴폴더이름"] * 20)
    label = QLabel()
    fake = SimpleNamespace(config=SimpleNamespace(get=lambda key, default=None: path), lbl_save_path=label)
    MainWindow._refresh_save_path(fake)
    assert label.toolTip() == path
    assert label.text().startswith("저장: ")
    assert len(label.text()) < len(path)
