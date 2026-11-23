"""환경설정 창 — 왼쪽 목록 + 오른쪽 페이지 (D090)."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from ui.preferences_dialog import PreferencesDialog
from utils.config_manager import DEFAULT_CONFIG
from utils.i18n import LANGUAGES, apply_language

MAX_HEIGHT = 500


class _Config(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def set(self, key, value):
        self[key] = value


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _shown(app, **overrides):
    dlg = PreferencesDialog(_Config({**DEFAULT_CONFIG, **overrides}))
    dlg.show()
    app.processEvents()
    return dlg


def test_nav_lists_four_pages_starting_at_general(app):
    dlg = _shown(app)
    assert [dlg.nav.item(i).text() for i in range(dlg.nav.count())] == ["일반", "다운로드", "MP3 음량", "로그인 쿠키"]
    assert dlg.nav.currentRow() == 0
    assert dlg.input_path.isVisible() and dlg.combo_language.isVisible() and dlg.chk_auto_update.isVisible()


@pytest.mark.parametrize("row, shown, hidden", [
    (1, "slider_concurrent", "input_path"),
    (2, "chk_gain", "slider_concurrent"),
    (3, "input_cookie_file", "chk_gain"),
])
def test_choosing_a_page_shows_only_its_settings(app, row, shown, hidden):
    dlg = _shown(app, cookie_source="file")
    dlg.nav.setCurrentRow(row)
    app.processEvents()
    assert getattr(dlg, shown).isVisible()
    assert not getattr(dlg, hidden).isVisible()


def test_window_is_short_and_does_not_jump(app):
    dlg = _shown(app)
    size = dlg.size()
    assert size.height() <= MAX_HEIGHT
    for row in range(dlg.nav.count()):
        dlg.nav.setCurrentRow(row)
        dlg.chk_gain.setChecked(not dlg.chk_gain.isChecked())
        dlg._cookie_radios["file"].setChecked(True)
        app.processEvents()
        assert dlg.size() == size
        dlg._cookie_radios["none"].setChecked(True)
        app.processEvents()
        assert dlg.size() == size


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_every_language_fits(app, lang):
    apply_language(app, lang)
    dlg = _shown(app, mp3_gain_enabled=True, cookie_source="file")
    assert dlg.height() <= MAX_HEIGHT
    room = dlg.nav.viewport().width()
    for i in range(dlg.nav.count()):
        text = dlg.nav.item(i).text()
        assert dlg.nav.fontMetrics().horizontalAdvance(text) + 16 <= room, text  # 16: 항목 좌우 여백


# ── 세 버튼 "확인 · 취소 · 적용" (D091) ──

def _buttons_left_to_right(dlg):
    from PySide6.QtWidgets import QPushButton

    buttons = [b for b in dlg.findChildren(QPushButton) if b.objectName() in ("btnConfirm", "btnCancel", "btnApply")]
    return [b.text() for b in sorted(buttons, key=lambda b: b.mapTo(dlg, b.rect().topLeft()).x())]


def test_buttons_are_ok_cancel_apply_and_enter_is_ok(app):
    dlg = _shown(app)
    assert _buttons_left_to_right(dlg) == ["확인", "취소", "적용"]
    assert dlg.btn_ok.isDefault()


def test_apply_is_enabled_only_while_something_changed(app):
    dlg = _shown(app)
    assert not dlg.btn_apply.isEnabled()
    dlg.chk_auto_update.toggle()
    assert dlg.btn_apply.isEnabled()
    dlg.chk_auto_update.toggle()  # 원래대로 되돌리면 다시 꺼진다
    assert not dlg.btn_apply.isEnabled()


def test_apply_saves_and_keeps_the_window_open(app):
    config = _Config(DEFAULT_CONFIG)
    dlg = PreferencesDialog(config)
    dlg.show()
    saved = []
    dlg.settings_saved.connect(saved.append)
    before = config["auto_update_ytdlp"]
    dlg.chk_auto_update.toggle()
    dlg.btn_apply.click()
    assert config["auto_update_ytdlp"] is (not before)
    assert saved and dlg.isVisible() and not dlg.btn_apply.isEnabled()


def test_cancel_after_apply_keeps_what_was_applied(app):
    config = _Config(DEFAULT_CONFIG)
    dlg = PreferencesDialog(config)
    dlg.show()
    dlg.slider_concurrent.setValue(3)
    dlg.btn_apply.click()
    dlg.btn_cancel.click()
    assert config["max_concurrent"] == 3 and not dlg.isVisible()


def test_theme_change_redraws_open_window_on_same_page(app):
    from ui import theme

    theme.apply_theme(app, "light")  # 다른 테스트가 남긴 테마와 상관없이 실제로 바뀌게
    dlg = _shown(app)
    dlg.nav.setCurrentRow(3)
    old_nav = dlg.nav
    size = dlg.size()
    try:
        theme.apply_theme(app, "dark")
        for _ in range(3):
            app.processEvents()
        assert dlg.nav is not old_nav and dlg.nav.currentRow() == 3 and dlg.isVisible()
        assert dlg.size() == size  # 다시 그린 뒤에도 창이 납작해지지 않는다 (실기에서 발견)
    finally:
        theme.apply_theme(app, "light")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DWM 제목 표시줄")
def test_title_bar_follows_theme_applied_while_open(app):
    # 라이트로 적용했다가 다크로 적용하면 열린 환경설정 창의 제목 표시줄이 흰색으로 남았다 (실기, T37)
    import ctypes

    from ui import theme

    def dark_title_bar(widget):
        value = ctypes.c_int(-1)
        ctypes.windll.dwmapi.DwmGetWindowAttribute(int(widget.winId()), 20, ctypes.byref(value), 4)
        return value.value

    theme.apply_theme(app, "dark")
    dlg = _shown(app)
    try:
        for mode, expected in (("light", 0), ("dark", 1)):
            theme.apply_theme(app, mode)
            for _ in range(5):
                app.processEvents()
            assert dark_title_bar(dlg) == expected, mode
    finally:
        theme.apply_theme(app, "light")
