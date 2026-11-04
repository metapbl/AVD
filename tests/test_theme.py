# 다크·라이트 테마 — 색표, Windows 따라가기, 전환 (D059, D065).
import re
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from models.download_item import DownloadItem, DownloadStatus
from ui import theme
from ui.download_item_widget import DownloadItemWidget
from ui.preferences_dialog import PreferencesDialog

_REPO = Path(__file__).resolve().parent.parent
_ICONS = [theme.icon_path(k, n) for k in ("check", "radio") for n in ("dark", "light")]


@pytest.fixture
def app():
    app = QApplication.instance() or QApplication([])
    yield app
    theme.apply_theme(app, "dark")
    app.setStyleSheet("")


def test_palettes_have_same_names():
    assert theme.DARK.keys() == theme.LIGHT.keys()


@pytest.mark.parametrize("icon", _ICONS, ids=lambda p: p.name)
def test_indicator_icons_load_and_are_bundled(icon):
    assert not QImage(str(icon)).isNull()
    spec = (_REPO / "AVD.spec").read_text(encoding="utf-8")
    assert f'("assets/icons/{icon.name}", "assets/icons")' in spec


@pytest.mark.parametrize("mode, scheme, name", [
    ("system", Qt.ColorScheme.Dark, "dark"),
    ("system", Qt.ColorScheme.Light, "light"),
    ("system", Qt.ColorScheme.Unknown, "dark"),
    ("dark", Qt.ColorScheme.Light, "dark"),
    ("light", Qt.ColorScheme.Dark, "light"),
    ("이상한 값", Qt.ColorScheme.Light, "light"),
])
def test_resolve(mode, scheme, name):
    assert theme.resolve(mode, scheme) == name


def test_config_default_follows_windows():
    from utils.config_manager import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["theme_mode"] == "system"


def test_ui_files_use_palette_names_only():
    # 창 코드에 색을 직접 쓰면 라이트 테마에서 안 보이는 글자가 생긴다.
    allowed = {"#c9a227", "#b03030", "#e6b800"}  # 동시 다운로드 위험 구간 색 — 테마와 무관
    for path in (_REPO / "ui").glob("*.py"):
        if path.name == "theme.py":
            continue
        code = "\n".join(
            line.split(" #")[0] if line.lstrip().startswith("#") is False else ""
            for line in path.read_text(encoding="utf-8").splitlines()
        )
        found = set(re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", code)) - allowed
        assert not found, (path.name, found)


def test_switch_changes_palette_and_notifies(app):
    theme.apply_theme(app, "dark")
    got = []
    theme.notifier.changed.connect(lambda: got.append(True))
    theme.apply_theme(app, "light")
    assert theme.color("accent") == theme.LIGHT["accent"]
    assert app.palette().color(app.palette().ColorRole.Window).name() == theme.LIGHT["surface"]
    assert "check_light.svg" in app.styleSheet()
    assert got == [True]
    theme.apply_theme(app, "light")  # 같은 테마면 다시 칠하지 않는다
    assert got == [True]


def test_item_recolors_status_on_switch(app):
    theme.apply_theme(app, "dark")
    w = DownloadItemWidget(DownloadItem(url="u", title="t"))
    w.update_status(DownloadStatus.DONE)
    assert theme.DARK["success2"] in w.lbl_status.styleSheet()
    theme.apply_theme(app, "light")
    w.refresh_theme()
    assert theme.LIGHT["success2"] in w.lbl_status.styleSheet()
    assert theme.LIGHT["surface"] in w.styleSheet()


class _Config:
    def __init__(self, mode="system"):
        self.values = {"theme_mode": mode}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


@pytest.mark.parametrize("mode", ["system", "dark", "light"])
def test_preferences_shows_and_saves_mode(app, mode):
    config = _Config(mode)
    dlg = PreferencesDialog(config)
    assert dlg._theme_radios[mode].isChecked()
    other = "light" if mode != "light" else "dark"
    dlg._theme_radios[other].setChecked(True)
    dlg._on_save()
    assert config.values["theme_mode"] == other
