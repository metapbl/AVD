# ui/theme.py
# Graphite 테마 — 앱 전체 팔레트와 공통 위젯(체크박스·라디오·스크롤바) 스타일 (D059)
# 창별 색은 각 창의 _apply_style 이 갖고, 여기는 창에 묶이지 않는 것만 둔다.

from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# 동결 빌드에서도 ui\ 는 _internal\ 아래에 있다고 보므로 datas 경로와 맞는다 (AVD.spec)
ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
CHECK_ICON = ICON_DIR / "check.svg"
RADIO_ICON = ICON_DIR / "radio.svg"

APP_QSS = f"""
    QCheckBox, QRadioButton {{ spacing: 8px; }}
    QCheckBox::indicator, QTableWidget::indicator {{
        width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid #9a9a9a; background: #1c1c1c;
    }}
    QTableWidget::indicator {{ width: 14px; height: 14px; }}
    QCheckBox::indicator:hover, QTableWidget::indicator:hover {{ border: 1px solid #4cc2ff; }}
    QCheckBox::indicator:checked, QTableWidget::indicator:checked {{
        background: #4cc2ff; border: 1px solid #4cc2ff; image: url({CHECK_ICON.as_posix()});
    }}
    QCheckBox::indicator:checked:hover, QTableWidget::indicator:checked:hover {{
        background: #7dd3ff; border: 1px solid #7dd3ff;
    }}
    QRadioButton::indicator {{
        width: 16px; height: 16px; border-radius: 9px;
        border: 1px solid #9a9a9a; background: #1c1c1c;
    }}
    QRadioButton::indicator:hover {{ border: 1px solid #4cc2ff; }}
    QRadioButton::indicator:checked {{
        width: 18px; height: 18px; border: none; background: transparent;
        image: url({RADIO_ICON.as_posix()});
    }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: #454545; border-radius: 3px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: #9a9a9a; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QToolTip {{ background: #323232; color: #f3f3f3; border: 1px solid #4a4a4a; padding: 2px 4px; }}
"""


def apply_theme(app: QApplication) -> None:
    """팔레트와 공통 스타일을 앱에 적용한다. Windows 라이트 모드에서도 같은 색을 쓴다."""
    palette = app.palette()
    role = QPalette.ColorRole
    for r, color in (
        (role.Window, "#272727"),
        (role.Base, "#1c1c1c"),
        (role.AlternateBase, "#272727"),
        (role.Text, "#f3f3f3"),
        (role.WindowText, "#f3f3f3"),
        (role.Button, "#363636"),
        (role.ButtonText, "#f3f3f3"),
        (role.Highlight, "#4cc2ff"),
        (role.HighlightedText, "#06222f"),
        (role.ToolTipBase, "#323232"),
        (role.ToolTipText, "#f3f3f3"),
        (role.PlaceholderText, "#9a9a9a"),
    ):
        palette.setColor(r, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(APP_QSS)
