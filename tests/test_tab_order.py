# 목록의 Tab 순서는 화면 순서(위→아래)를 따른다. 새 항목은 맨 위에 끼워 넣지만 만든 순서는 마지막이다.
from PySide6.QtWidgets import QApplication, QPushButton

from models.download_item import DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from ui.main_window import MainWindow


def _item_order_by_tab(w):
    """btn_add 에서 Tab 체인을 한 바퀴 돌며 보이는 항목 버튼이 속한 항목 id 를 차례로 모은다."""
    order = []
    cur = w.btn_add.nextInFocusChain()
    while cur is not w.btn_add:
        if isinstance(cur, QPushButton) and cur.isVisibleTo(w):
            parent = cur.parentWidget()
            while parent is not None and not isinstance(parent, DownloadItemWidget):
                parent = parent.parentWidget()
            if parent is not None and (not order or order[-1] != parent.item.item_id):
                order.append(parent.item.item_id)
        cur = cur.nextInFocusChain()
    return order


def test_tab_order_follows_list_from_top():
    app = QApplication.instance() or QApplication([])  # noqa: F841
    w = MainWindow()
    w._enqueue_info = lambda _iid: None
    for i in range(3):
        w._spawn_item(f"https://example.invalid/{i}", predetermined=None, append=False)
    w._spawn_item("https://example.invalid/last", predetermined=None, append=True)
    for widget in w.widgets.values():
        widget.update_status(DownloadStatus.DONE)
    w.show()

    on_screen = [
        w.list_layout.itemAt(i).widget().item.item_id
        for i in range(w.list_layout.count())
        if isinstance(w.list_layout.itemAt(i).widget(), DownloadItemWidget)
    ]
    assert _item_order_by_tab(w) == on_screen
    w.close()
