"""환경설정 창 — 왼쪽 목록 + 오른쪽 페이지 (D090)."""
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
