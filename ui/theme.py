# ui/theme.py
# 화면 테마 — 다크(Graphite)·라이트(Paper) 색표, 앱 전체 팔레트, 공통 위젯 스타일 (D059, D065)
# 창별 QSS 는 각 창의 _apply_style 이 갖고, 색은 @이름 으로 적어 qss() 로 바꾼다.

import re
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# 동결 빌드에서도 ui\ 는 _internal\ 아래에 있다고 보므로 datas 경로와 맞는다 (AVD.spec)
ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"

DARK = {
    "base": "#1c1c1c", "surface": "#272727", "raised": "#323232", "line": "#383838", "line2": "#4a4a4a",
    "btn": "#363636", "btn2": "#454545", "accent": "#4cc2ff", "accent2": "#7dd3ff", "on_accent": "#06222f",
    "text": "#f3f3f3", "text2": "#cfcfcf", "muted": "#9a9a9a", "faint": "#6e6e6e", "danger": "#e5636b",
    "success": "#3f9c6a", "success2": "#57b884", "warn": "#e0b050", "ext": "#7dd3ff", "track": "#3a3a3a",
    "sel": "#23465a", "on_strong": "#ffffff",
}
LIGHT = {
    "base": "#f3f4f6", "surface": "#ffffff", "raised": "#eef0f2", "line": "#e1e4e8", "line2": "#c9ced4",
    "btn": "#eceef1", "btn2": "#dfe2e6", "accent": "#0f6cbd", "accent2": "#2a84d2", "on_accent": "#ffffff",
    "text": "#1b1f24", "text2": "#3f4650", "muted": "#6a737d", "faint": "#7f8892", "danger": "#c8323c",
    "success": "#1f8a4c", "success2": "#2aa35c", "warn": "#a86e00", "ext": "#0f6cbd", "track": "#e4e7eb",
    "sel": "#d3e6f7", "on_strong": "#ffffff",
}
_THEMES = {"dark": DARK, "light": LIGHT}

_current = DARK
_name: str | None = None  # 지금 칠해진 테마. 처음 적용 전에는 None
_mode = "system"
_listening = False


class _Notifier(QObject):
    changed = Signal()  # 테마가 실제로 바뀜 — 열려 있는 창이 다시 칠한다


notifier = _Notifier()


def qss(css: str) -> str:
    """QSS 의 @이름 을 현재 테마 색으로 바꾼다."""
    return re.sub(r"@(\w+)", lambda m: _current[m.group(1)], css)


def color(name: str) -> str:
    """현재 테마의 색 하나."""
    return _current[name]


def resolve(mode: str, scheme: Qt.ColorScheme) -> str:
    """설정값과 Windows 색 모드로 쓸 테마를 정한다. 알 수 없으면 다크."""
    if mode in _THEMES:
        return mode
    return "light" if scheme == Qt.ColorScheme.Light else "dark"


def icon_path(kind: str, name: str | None = None) -> Path:
    """테마별 체크·라디오 아이콘 경로. 강조색 위에 그리므로 테마마다 색이 다르다."""
    suffix = "_light" if (name or _name) == "light" else ""
    return ICON_DIR / f"{kind}{suffix}.svg"


def app_qss() -> str:
    """창에 묶이지 않는 공통 위젯 스타일."""
    check = icon_path("check").as_posix()
    radio = icon_path("radio").as_posix()
    return qss(f"""
    QCheckBox, QRadioButton {{ spacing: 8px; }}
    QCheckBox::indicator, QTableWidget::indicator {{
        width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid @muted; background: @base;
    }}
    QTableWidget::indicator {{ width: 14px; height: 14px; }}
    QCheckBox::indicator:hover, QTableWidget::indicator:hover {{ border: 1px solid @accent; }}
    QCheckBox::indicator:checked, QTableWidget::indicator:checked {{
        background: @accent; border: 1px solid @accent; image: url({check});
    }}
    QCheckBox::indicator:checked:hover, QTableWidget::indicator:checked:hover {{
        background: @accent2; border: 1px solid @accent2;
    }}
    QRadioButton::indicator {{
        width: 16px; height: 16px; border-radius: 9px;
        border: 1px solid @muted; background: @base;
    }}
    QRadioButton::indicator:hover {{ border: 1px solid @accent; }}
    QRadioButton::indicator:checked {{
        width: 18px; height: 18px; border: none; background: transparent;
        image: url({radio});
    }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: @btn2; border-radius: 3px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: @muted; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QToolTip {{ background: @raised; color: @text; border: 1px solid @line2; padding: 2px 4px; }}
""")


def _paint(app: QApplication) -> None:
    palette = app.palette()
    role = QPalette.ColorRole
    for r, name in (
        (role.Window, "surface"),
        (role.Base, "base"),
        (role.AlternateBase, "surface"),
        (role.Text, "text"),
        (role.WindowText, "text"),
        (role.Button, "btn"),
        (role.ButtonText, "text"),
        (role.Highlight, "accent"),
        (role.HighlightedText, "on_accent"),
        (role.ToolTipBase, "raised"),
        (role.ToolTipText, "text"),
        (role.PlaceholderText, "muted"),
    ):
        palette.setColor(r, QColor(_current[name]))
    app.setPalette(palette)
    app.setStyleSheet(app_qss())


def _sync() -> None:
    """설정과 Windows 색 모드에 맞춰 칠한다. 이미 그 테마면 아무것도 하지 않는다."""
    global _current, _name
    app = QApplication.instance()
    name = resolve(_mode, app.styleHints().colorScheme())
    if name == _name:
        return
    first = _name is None
    _name = name
    _current = _THEMES[name]
    _paint(app)
    if not first:
        notifier.changed.emit()


def apply_theme(app: QApplication, mode: str = "system") -> None:
    """테마를 적용한다. mode: system(Windows 따라가기) / dark / light."""
    global _mode, _listening
    _mode = mode
    hints = app.styleHints()
    # 제목 표시줄도 같은 색 모드를 쓰게 한다. Unknown 은 Windows 설정을 따른다.
    hints.setColorScheme(
        {"dark": Qt.ColorScheme.Dark, "light": Qt.ColorScheme.Light}.get(mode, Qt.ColorScheme.Unknown)
    )
    if not _listening:
        hints.colorSchemeChanged.connect(lambda _scheme: _sync())
        _listening = True
    _sync()
