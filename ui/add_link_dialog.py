# ui/add_link_dialog.py
# URL 입력 팝업 다이얼로그

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent


class AddLinkDialog(QDialog):
    """
    URL 입력 팝업 다이얼로그

    시그널:
        link_submitted : 확인 버튼 클릭 시 URL 문자열 전달
    """

    link_submitted = Signal(str)  # URL 전달

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("링크 붙여넣기")
        self.setFixedSize(520, 160)
        self.setModal(True)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        """UI 구성"""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # 안내 레이블
        lbl = QLabel("다운로드할 영상의 URL을 붙여넣으세요.")
        lbl.setObjectName("dialogLabel")
        root.addWidget(lbl)

        # URL 입력창
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText(
            "https://www.youtube.com/watch?v=..."
        )
        self.input_url.setFixedHeight(36)
        self.input_url.returnPressed.connect(self._on_confirm)
        root.addWidget(self.input_url)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        # 취소 버튼
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setFixedSize(80, 32)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        # 확인 버튼
        btn_confirm = QPushButton("확인")
        btn_confirm.setObjectName("btnConfirm")
        btn_confirm.setFixedSize(80, 32)
        btn_confirm.clicked.connect(self._on_confirm)
        btn_row.addWidget(btn_confirm)

        root.addLayout(btn_row)

        # 다이얼로그 열릴 때 클립보드 자동 붙여넣기
        self._paste_from_clipboard()

    def _paste_from_clipboard(self):
        """
        클립보드에 URL이 있으면 자동으로 입력창에 붙여넣기
        4K Downloader 와 동일한 UX
        """
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard().text().strip()
        if clipboard.startswith("http"):
            self.input_url.setText(clipboard)
            self.input_url.selectAll()

    def _on_confirm(self):
        """확인 버튼 처리"""
        url = self.input_url.text().strip()

        if not url:
            QMessageBox.warning(self, "입력 오류", "URL을 입력해 주세요.")
            return

        if not url.startswith("http"):
            QMessageBox.warning(
                self, "입력 오류",
                "올바른 URL 형식이 아닙니다.\n"
                "http:// 또는 https:// 로 시작해야 합니다."
            )
            return

        self.link_submitted.emit(url)
        self.accept()

    def _apply_style(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QDialog {
                background: #2b2b2b;
            }
            QLabel#dialogLabel {
                color: #cccccc;
                font-size: 13px;
            }
            QLineEdit {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #4a90d9;
            }
            QPushButton#btnCancel {
                background: #444;
                color: #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#btnCancel:hover {
                background: #555;
            }
            QPushButton#btnConfirm {
                background: #4a90d9;
                color: #fff;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnConfirm:hover {
                background: #5aa0e9;
            }
        """)