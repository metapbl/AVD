# "자세히" 창 — 원문을 펼쳐 보여 주고, 버튼은 한국어다.
from PySide6.QtWidgets import QApplication, QMessageBox, QTextEdit, QWidget

import main
from models.download_item import DownloadItem
from ui.main_window import MainWindow, _friendly_error

TRUNCATED = "ERROR: [youtube:truncated_id] 1: Incomplete YouTube ID 1. URL looks truncated."


def _open_detail(monkeypatch, err):
    seen = {}

    def capture(self):
        seen["informative"] = self.informativeText()
        (edit,) = self.findChildren(QTextEdit)
        seen["expanded"] = not edit.parentWidget().isHidden()  # 펼침은 부모 틀이 맡는다

    monkeypatch.setattr(QMessageBox, "exec", capture)
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    item = DownloadItem(url="u", error_msg=err)
    parent = QWidget()
    parent.items = {item.item_id: item}
    MainWindow._on_error_detail(parent, item.item_id)
    return seen


def test_detail_opens_expanded(monkeypatch):
    assert _open_detail(monkeypatch, TRUNCATED)["expanded"]


def test_guidance_does_not_tell_user_to_press_detail_again(monkeypatch):
    assert "눌러" not in _open_detail(monkeypatch, "ERROR: 알 수 없음")["informative"]


def test_truncated_url_has_own_title():
    assert _friendly_error(TRUNCATED)[0] == "주소가 올바르지 않습니다"


def test_standard_buttons_are_korean():
    app = QApplication.instance() or QApplication([])
    translator = main.install_korean_translator(app)
    try:
        box = QMessageBox()
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        assert box.button(QMessageBox.StandardButton.Ok).text() == "확인"
    finally:
        app.removeTranslator(translator)
