# Graphite 테마 — 체크·라디오 아이콘이 읽히고 exe 에도 들어간다 (D059).
from pathlib import Path

from PySide6.QtGui import QImage

from ui import theme

_REPO = Path(__file__).resolve().parent.parent


def test_indicator_icons_load():
    for icon in (theme.CHECK_ICON, theme.RADIO_ICON):
        assert not QImage(str(icon)).isNull(), icon
        assert icon.as_posix() in theme.APP_QSS


def test_indicator_icons_are_bundled():
    spec = (_REPO / "AVD.spec").read_text(encoding="utf-8")
    for icon in (theme.CHECK_ICON, theme.RADIO_ICON):
        assert f'("assets/icons/{icon.name}", "assets/icons")' in spec
