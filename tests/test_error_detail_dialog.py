# "자세히" 창 — 읽기 좋은 폭, 원문 표시, 잘린 주소 안내. 기본 버튼은 한국어다.
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget

import main
from models.download_item import DownloadItem
from ui import main_window as mw
from ui.error_detail_dialog import ErrorDetailDialog
from ui.main_window import MainWindow, _friendly_error

TRUNCATED = "ERROR: [youtube:truncated_id] 1: Incomplete YouTube ID 1. URL looks truncated."


def _app():
    return QApplication.instance() or QApplication([])


def test_detail_shows_summary_and_original(monkeypatch):
    app = _app()  # noqa: F841 — 위젯에 필요
    seen = []

    class Dialog(ErrorDetailDialog):
        def exec(self):
            seen.append((self.lbl_title.text(), self.lbl_description.text(), self.txt_original.toPlainText()))

    monkeypatch.setattr(mw, "ErrorDetailDialog", Dialog)
    item = DownloadItem(url="u", error_msg=TRUNCATED)
    parent = QWidget()
    parent.items = {item.item_id: item}
    MainWindow._on_error_detail(parent, item.item_id)
    title, desc = _friendly_error(TRUNCATED)
    assert seen == [(title, desc, TRUNCATED)]


def test_dialog_is_wide_enough_to_read():
    app = _app()  # noqa: F841 — 위젯에 필요
    assert ErrorDetailDialog("제목", "설명", "원문").width() >= 500


def test_original_is_plain_and_read_only():
    app = _app()  # noqa: F841 — 위젯에 필요
    html = "<b>굵게</b>"
    dlg = ErrorDetailDialog("제목", "설명", html)
    assert dlg.txt_original.isReadOnly()
    assert dlg.txt_original.toPlainText() == html


def test_site_text_is_not_used_for_summary_labels():
    # 요약·설명은 앱이 정한 문구만 쓴다. 사이트 문자열은 원문 칸에만 들어간다.
    assert "<b>" not in _friendly_error("<b>Incomplete YouTube ID</b> looks truncated")[1]


def test_enter_closes_dialog():
    app = _app()  # noqa: F841 — 위젯에 필요
    dlg = ErrorDetailDialog("제목", "설명", "원문")
    dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    dlg.show()
    QTest.keyClick(dlg, Qt.Key.Key_Return)
    assert dlg.result() == QDialog.DialogCode.Accepted
    assert not dlg.isVisible()


def test_truncated_url_guidance_reads_naturally():
    title, desc = _friendly_error(TRUNCATED)
    assert title == "주소를 확인해 주세요"
    assert "전체 주소" in desc


def test_guidance_does_not_tell_user_to_press_detail_again():
    assert "눌러" not in _friendly_error("ERROR: 알 수 없음")[1]


def test_standard_buttons_are_korean():
    app = _app()
    translator = main.install_korean_translator(app)
    try:
        box = QMessageBox()
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        assert box.button(QMessageBox.StandardButton.Ok).text() == "확인"
    finally:
        app.removeTranslator(translator)
