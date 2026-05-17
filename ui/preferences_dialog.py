# ui/preferences_dialog.py
# 환경설정 팝업 다이얼로그

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit,
    QSpinBox, QComboBox, QCheckBox,
    QFileDialog, QGroupBox
)
from PySide6.QtCore import Signal
from utils.config_manager import ConfigManager


class PreferencesDialog(QDialog):
    """
    환경설정 팝업 다이얼로그

    시그널:
        settings_saved : 저장 버튼 클릭 시 변경된 설정 dict 전달
    """

    settings_saved = Signal(dict)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("환경설정")
        self.setFixedSize(480, 400)
        self.setModal(True)
        self._build_ui()
        self._load_values()
        self._apply_style()

    def _build_ui(self):
        """UI 구성"""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── 저장 경로 그룹 ──
        grp_path = QGroupBox("저장 경로")
        grp_path.setObjectName("settingsGroup")
        path_layout = QHBoxLayout(grp_path)
        path_layout.setSpacing(8)

        self.input_path = QLineEdit()
        self.input_path.setFixedHeight(32)
        self.input_path.setReadOnly(True)
        path_layout.addWidget(self.input_path)

        btn_browse = QPushButton("찾아보기")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.setFixedSize(80, 32)
        btn_browse.clicked.connect(self._browse_path)
        path_layout.addWidget(btn_browse)

        root.addWidget(grp_path)

        # ── 다운로드 설정 그룹 ──
        grp_dl = QGroupBox("다운로드 설정")
        grp_dl.setObjectName("settingsGroup")
        dl_layout = QVBoxLayout(grp_dl)
        dl_layout.setSpacing(10)

        # 동시 다운로드 수
        concurrent_row = QHBoxLayout()
        concurrent_row.addWidget(QLabel("동시 다운로드 수"))
        self.spin_concurrent = QSpinBox()
        self.spin_concurrent.setRange(1, 5)
        self.spin_concurrent.setFixedSize(60, 28)
        concurrent_row.addStretch()
        concurrent_row.addWidget(self.spin_concurrent)
        dl_layout.addLayout(concurrent_row)

        # 기본 확장자
        ext_row = QHBoxLayout()
        ext_row.addWidget(QLabel("기본 저장 형식"))
        self.combo_ext = QComboBox()
        self.combo_ext.addItems(["mp4", "mkv", "webm", "mp3", "m4a"])
        self.combo_ext.setFixedSize(100, 28)
        ext_row.addStretch()
        ext_row.addWidget(self.combo_ext)
        dl_layout.addLayout(ext_row)

        root.addWidget(grp_dl)

        # ── 업데이트 설정 그룹 ──
        grp_update = QGroupBox("업데이트 설정")
        grp_update.setObjectName("settingsGroup")
        update_layout = QVBoxLayout(grp_update)

        self.chk_auto_update = QCheckBox(
            "앱 시작 시 yt-dlp 자동 업데이트 확인"
        )
        update_layout.addWidget(self.chk_auto_update)

        root.addWidget(grp_update)

        root.addStretch()

        # ── 버튼 행 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setFixedSize(80, 32)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("저장")
        btn_save.setObjectName("btnConfirm")
        btn_save.setFixedSize(80, 32)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        root.addLayout(btn_row)

    def _load_values(self):
        """현재 설정값을 UI에 반영"""
        self.input_path.setText(
            self.config.get("save_path", "")
        )
        self.spin_concurrent.setValue(
            self.config.get("max_concurrent", 2)
        )
        ext = self.config.get("default_ext", "mp4")
        idx = self.combo_ext.findText(ext)
        if idx >= 0:
            self.combo_ext.setCurrentIndex(idx)

        self.chk_auto_update.setChecked(
            self.config.get("auto_update_ytdlp", True)
        )

    def _browse_path(self):
        """저장 경로 탐색기 열기"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "저장 폴더 선택",
            self.input_path.text()
        )
        if folder:
            self.input_path.setText(folder)

    def _on_save(self):
        """저장 버튼 처리"""
        new_settings = {
            "save_path"         : self.input_path.text(),
            "max_concurrent"    : self.spin_concurrent.value(),
            "default_ext"       : self.combo_ext.currentText(),
            "auto_update_ytdlp" : self.chk_auto_update.isChecked(),
        }

        # ConfigManager에 저장
        for key, value in new_settings.items():
            self.config.set(key, value)

        self.settings_saved.emit(new_settings)
        self.accept()

    def _apply_style(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QDialog {
                background: #2b2b2b;
            }
            QGroupBox#settingsGroup {
                color: #aaaaaa;
                font-size: 12px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 8px;
                padding: 12px 8px 8px 8px;
            }
            QGroupBox#settingsGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLabel {
                color: #cccccc;
                font-size: 12px;
            }
            QLineEdit {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 12px;
            }
            QSpinBox, QComboBox {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 12px;
            }
            QCheckBox {
                color: #cccccc;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555;
                border-radius: 3px;
                background: #1e1e1e;
            }
            QCheckBox::indicator:checked {
                background: #4a90d9;
                border: 1px solid #4a90d9;
            }
            QPushButton#btnBrowse {
                background: #444;
                color: #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#btnBrowse:hover { background: #555; }
            QPushButton#btnCancel {
                background: #444;
                color: #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#btnCancel:hover { background: #555; }
            QPushButton#btnConfirm {
                background: #4a90d9;
                color: #fff;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnConfirm:hover { background: #5aa0e9; }
        """)