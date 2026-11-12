# ui/about_dialog.py
# 도구 모음의 "정보" 버튼이 여는 프로그램 정보 창 (D077)

import PySide6
import yt_dlp.version
from PySide6.QtCore import Qt, qVersion
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

import gaindb
from ui import theme
from utils.updater import APP_VERSION

REPO_URL = "https://github.com/metapbl/AVD"


class AboutDialog(QDialog):
    """앱 버전, 지금 돌고 있는 구성요소 버전, 저장소 링크, 라이선스."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("프로그램 정보")
        self.setFixedWidth(420)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(14)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(QApplication.windowIcon().pixmap(48, 48))
        head.addWidget(lbl_icon)
        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        lbl_name = QLabel("AV Downloader")
        lbl_name.setObjectName("aboutName")
        name_col.addWidget(lbl_name)
        lbl_version = QLabel(f"버전 {APP_VERSION}")
        lbl_version.setObjectName("aboutVersion")
        name_col.addWidget(lbl_version)
        head.addLayout(name_col, stretch=1)
        root.addLayout(head)

        lbl_desc = QLabel("yt-dlp 기반 영상·오디오 다운로더")
        lbl_desc.setObjectName("aboutText")
        root.addWidget(lbl_desc)

        # 문제를 알릴 때 그대로 복사해 붙일 수 있게 선택 가능한 글자로 둔다.
        # yt-dlp 는 자동 업데이트되므로 지금 불러온 모듈의 버전을 적는다.
        lbl_parts = QLabel(
            f"yt-dlp {yt_dlp.version.__version__}\n"
            f"GaindB {gaindb.__version__}\n"
            f"PySide6 {PySide6.__version__} (Qt {qVersion()})"
        )
        lbl_parts.setObjectName("aboutParts")
        lbl_parts.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(lbl_parts)

        lbl_link = QLabel(f'<a href="{REPO_URL}">{REPO_URL}</a>')
        lbl_link.setObjectName("aboutText")
        lbl_link.setOpenExternalLinks(True)
        root.addWidget(lbl_link)

        lbl_license = QLabel(
            "MIT License · © 2026 META PUBLIC\n"
            "함께 배포하는 구성요소의 고지는 THIRD_PARTY_LICENSES 파일에 있습니다."
        )
        lbl_license.setObjectName("aboutSmall")
        lbl_license.setWordWrap(True)
        root.addWidget(lbl_license)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("닫기")
        btn_close.setObjectName("btnClose")
        btn_close.setProperty("role", "primary")
        btn_close.setFixedSize(80, 32)
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

        self.setStyleSheet(theme.qss("""
            QDialog {
                background: @surface;
            }
            QLabel#aboutName {
                color: @text;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#aboutVersion {
                color: @text2;
                font-size: 13px;
            }
            QLabel#aboutText {
                color: @text2;
                font-size: 12px;
            }
            QLabel#aboutParts {
                color: @text;
                font-size: 12px;
            }
            QLabel#aboutSmall {
                color: @muted;
                font-size: 11px;
            }
            QPushButton#btnClose {
                border-radius: 4px;
                font-size: 12px;
            }
        """))
