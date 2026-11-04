# ui/error_detail_dialog.py
# 항목의 "자세히" 버튼이 여는 오류 내용 창 (D061)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ui import theme


class ErrorDetailDialog(QDialog):
    """오류 요약·대처법·원문을 보여 준다. 원문은 그대로 복사할 수 있다."""

    def __init__(self, title: str, description: str, original: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("오류 내용")
        self.setFixedWidth(520)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("errorTitle")
        self.lbl_title.setWordWrap(True)
        root.addWidget(self.lbl_title)

        self.lbl_description = QLabel(description)
        self.lbl_description.setObjectName("errorDescription")
        self.lbl_description.setWordWrap(True)
        root.addWidget(self.lbl_description)

        lbl_original = QLabel("오류 원문")
        lbl_original.setObjectName("errorSection")
        root.addWidget(lbl_original)

        # 사이트가 준 문자열이므로 서식으로 해석하지 않는다 (SECURITY_POLICY §4)
        self.txt_original = QPlainTextEdit(original)
        self.txt_original.setReadOnly(True)
        self.txt_original.setFixedHeight(110)
        self.txt_original.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        root.addWidget(self.txt_original)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("닫기")
        btn_close.setObjectName("btnClose")
        btn_close.setFixedSize(80, 32)
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

        self.setStyleSheet(theme.qss("""
            QDialog {
                background: @surface;
            }
            QLabel#errorTitle {
                color: @text;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#errorDescription {
                color: @text2;
                font-size: 13px;
            }
            QLabel#errorSection {
                color: @muted;
                font-size: 12px;
            }
            QPlainTextEdit {
                background: @base;
                color: @text2;
                border: 1px solid @line2;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
            QPushButton#btnClose {
                background: @accent;
                color: @on_accent;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnClose:hover {
                background: @accent2;
            }
        """))
