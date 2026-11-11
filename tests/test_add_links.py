# 링크 추가 — 여러 줄, Ctrl+V, 끌어다 놓기, 화질 창 차례대로 (열네 번째 계획 작업 2).
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QApplication, QMessageBox

from ui import main_window as mw
from ui.add_link_dialog import AddLinkDialog, extract_urls
from ui.main_window import MainWindow, _urls_from_mime

A, B = "https://example.invalid/a", "http://example.invalid/b"
V = "https://player.vimeo.com/video/76979871"


@pytest.mark.parametrize("text, urls", [
    (A, [A]),
    (f"{A}\n{B}", [A, B]),
    (f"{A} {B}\r\n{A}", [A, B]),
    (f"{A}\u2028{B}", [A, B]),  # QLineEdit 이 줄바꿈을 바꾸는 문자
    ("메모 " + A, [A]),
    ("httpfoo ftp://x 글자", []),
    ("", []),
    # Vimeo `vimeo.com/숫자` 는 임베드 주소로 (F12, D068)
    ("https://vimeo.com/76979871", [V]),
    ("http://www.vimeo.com/76979871/", [V]),
    ("https://vimeo.com/76979871?share=copy", [V]),
    ("https://vimeo.com/76979871/abcdef1234", ["https://vimeo.com/76979871/abcdef1234"]),
    ("https://vimeo.com/showcase/123", ["https://vimeo.com/showcase/123"]),
    ("https://vimeo.com/channels/staffpicks/1", ["https://vimeo.com/channels/staffpicks/1"]),
    (V, [V]),
    ("https://www.youtube.com/watch?v=x", ["https://www.youtube.com/watch?v=x"]),
    (f"https://vimeo.com/76979871 {V}", [V]),
])
def test_extract_urls(text, urls):
    assert extract_urls(text) == urls


def _dialog(text):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    QApplication.clipboard().clear()
    dlg = AddLinkDialog()
    got = []
    dlg.link_submitted.connect(got.append)
    dlg.input_url.setText(text)
    return dlg, got


def test_dialog_submits_every_pasted_line():
    dlg, got = _dialog(f"{A}\n{B}")
    dlg._on_confirm()
    assert got == [A, B]


def test_dialog_rejects_text_without_url(monkeypatch):
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warned.append(a))
    dlg, got = _dialog("글자")
    dlg._on_confirm()
    assert warned
    assert not got


def _mime(text=None, urls=None):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — QMimeData 에 필요
    m = QMimeData()
    if text:
        m.setText(text)
    if urls:
        m.setUrls([QUrl(u) for u in urls])
    return m


def test_mime_prefers_urls_over_duplicate_text():
    assert _urls_from_mime(_mime(text=A, urls=[A])) == [A]


def test_mime_uses_text_when_no_urls():
    assert _urls_from_mime(_mime(text=f"{A}\n{B}")) == [A, B]


def test_mime_ignores_local_files():
    assert _urls_from_mime(_mime(urls=["file:///C:/a.mp4"])) == []


def test_drag_enter_accepts_only_links():
    accepted = []
    event = SimpleNamespace(mimeData=lambda: _mime(text=A), acceptProposedAction=lambda: accepted.append(True))
    MainWindow.dragEnterEvent(None, event)
    assert accepted
    accepted.clear()
    event = SimpleNamespace(mimeData=lambda: _mime(text="글자"), acceptProposedAction=lambda: accepted.append(True))
    MainWindow.dragEnterEvent(None, event)
    assert not accepted


def test_drop_adds_links():
    added = []
    fake = SimpleNamespace(_on_link_submitted=added.append)
    MainWindow.dropEvent(fake, SimpleNamespace(mimeData=lambda: _mime(urls=[A, B]), acceptProposedAction=lambda: None))
    assert added == [A, B]


def test_paste_adds_links_from_clipboard():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 클립보드에 필요
    QApplication.clipboard().setText(f"{A}\n{B}")
    added = []
    fake = SimpleNamespace(_on_link_submitted=added.append)
    MainWindow._on_paste_links(fake)
    assert added == [A, B]


def test_paste_without_links_tells_user():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 클립보드에 필요
    QApplication.clipboard().setText("글자")
    messages = []
    fake = SimpleNamespace(status_bar=SimpleNamespace(showMessage=messages.append))
    MainWindow._on_paste_links(fake)
    assert messages == ["클립보드에 링크가 없습니다."]


def _fake_for_dialogs(monkeypatch, ids):
    opened = []

    class Dialog:
        def __init__(self, info, config, parent):
            self.format_selected = SimpleNamespace(connect=lambda f: None)
            self.rejected = SimpleNamespace(connect=lambda f: None)
            self.info = info

        def exec(self):
            # 창이 열린 동안 다음 항목이 도착해도 겹쳐 뜨지 않아야 한다.
            opened.append(self.info)
            if self.info == "첫째":
                fake._format_pending.append(("둘", "둘째"))
                MainWindow._show_format_dialogs(fake)
                assert opened == ["첫째"]

    monkeypatch.setattr(mw, "FormatSelectDialog", Dialog)
    fake = SimpleNamespace(
        items=dict.fromkeys(ids),
        config=None,
        _format_pending=[],
        _format_dialog_open=False,
    )
    fake._show_format_dialogs = lambda: MainWindow._show_format_dialogs(fake)
    return fake, opened


def test_format_dialogs_open_one_at_a_time(monkeypatch):
    fake, opened = _fake_for_dialogs(monkeypatch, ["하나", "둘"])
    fake._format_pending.append(("하나", "첫째"))
    MainWindow._show_format_dialogs(fake)
    assert opened == ["첫째", "둘째"]
    assert not fake._format_dialog_open


def test_format_dialog_skips_removed_item(monkeypatch):
    fake, opened = _fake_for_dialogs(monkeypatch, ["둘"])
    fake._format_pending.append(("없어진 항목", "셋째"))
    MainWindow._show_format_dialogs(fake)
    assert not opened
