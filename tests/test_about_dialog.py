# 프로그램 정보 (F14, D077) — 창 제목의 버전과 정보 창.
import yt_dlp.version
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

import gaindb
from ui import about_dialog
from ui.about_dialog import REPO_URL, AboutDialog
from ui.main_window import MainWindow
from utils.updater import APP_VERSION


def _texts(dlg):
    return " | ".join(lbl.text() for lbl in dlg.findChildren(QLabel))


def test_window_title_shows_version():
    QApplication.instance() or QApplication([])
    assert MainWindow().windowTitle() == f"AV Downloader {APP_VERSION}"


def test_about_dialog_shows_running_versions_and_link():
    QApplication.instance() or QApplication([])
    dlg = AboutDialog()
    text = _texts(dlg)
    assert f"버전 {APP_VERSION}" in text
    assert yt_dlp.version.__version__ in text  # 자동 업데이트 뒤 지금 실제로 도는 버전
    assert gaindb.__version__ in text
    assert "MIT" in text and "THIRD_PARTY_LICENSES" in text
    link = next(lbl for lbl in dlg.findChildren(QLabel) if REPO_URL in lbl.text())
    assert link.openExternalLinks()


def test_about_dialog_enter_closes():
    QApplication.instance() or QApplication([])
    dlg = AboutDialog()
    (default,) = [b for b in dlg.findChildren(QPushButton) if b.isDefault()]
    assert default.text() == "닫기"  # D060


def test_version_text_can_be_copied():
    QApplication.instance() or QApplication([])
    dlg = AboutDialog()
    lbl = next(x for x in dlg.findChildren(QLabel) if yt_dlp.version.__version__ in x.text())
    assert lbl.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse


def test_toolbar_button_opens_about_dialog(monkeypatch):
    QApplication.instance() or QApplication([])
    opened = []
    monkeypatch.setattr(about_dialog.AboutDialog, "exec", lambda self: opened.append(self))
    w = MainWindow()
    w.btn_about.click()
    assert len(opened) == 1
