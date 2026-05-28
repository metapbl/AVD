# ui/preferences_dialog.py
# 환경설정 팝업 다이얼로그

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit,
    QSlider, QCheckBox,
    QFileDialog, QGroupBox
)
from PySide6.QtCore import Qt, Signal
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
        dl_layout.setSpacing(8)

        # 동시 다운로드 수 — 슬라이더 + 큰 숫자 + 컬러 바
        # 본 단계의 슬라이더는 placebo: 값은 config 에 저장되지만 실제 동시성
        # 제어는 후속 항목 "동시성 제어 구현 (큐 매니저)" 에서 처리한다.
        # WORKLOG 단기 섹션 참조.

        # 상단 행: 라벨 + 현재 값 큰 숫자 (우측)
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("동시 다운로드 수"))
        top_row.addStretch()
        self.lbl_concurrent_value = QLabel("2")
        self.lbl_concurrent_value.setObjectName("concurrentValue")
        self.lbl_concurrent_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_concurrent_value.setFixedWidth(40)
        top_row.addWidget(self.lbl_concurrent_value)
        dl_layout.addLayout(top_row)

        # 컬러 바 (3:3:4 — 녹 1~3 / 노 4~6 / 빨 7~10)
        color_bar = QHBoxLayout()
        color_bar.setSpacing(0)
        color_bar.setContentsMargins(0, 0, 0, 0)

        lbl_green = QLabel("권장")
        lbl_green.setObjectName("zoneGreen")
        lbl_green.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color_bar.addWidget(lbl_green, stretch=3)

        lbl_yellow = QLabel("주의")
        lbl_yellow.setObjectName("zoneYellow")
        lbl_yellow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color_bar.addWidget(lbl_yellow, stretch=3)

        lbl_red = QLabel("비권장")
        lbl_red.setObjectName("zoneRed")
        lbl_red.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color_bar.addWidget(lbl_red, stretch=4)

        dl_layout.addLayout(color_bar)

        # 슬라이더
        self.slider_concurrent = QSlider(Qt.Orientation.Horizontal)
        self.slider_concurrent.setObjectName("concurrentSlider")
        self.slider_concurrent.setMinimum(1)
        self.slider_concurrent.setMaximum(10)
        self.slider_concurrent.setSingleStep(1)
        self.slider_concurrent.setPageStep(1)
        self.slider_concurrent.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider_concurrent.setToolTip(
            "yt-dlp 는 단일 인스턴스 병렬 다운로드를 공식 지원하지 않습니다.\n"
            "1~3 권장. 높은 값은 IP 차단 위험."
        )
        self.slider_concurrent.valueChanged.connect(self._on_concurrent_changed)
        dl_layout.addWidget(self.slider_concurrent)

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

    def _on_concurrent_changed(self, value: int):
        """
        슬라이더 값 변경 — 우측 큰 숫자 갱신 + 위험 구간 색상 동기화.

        구간 정책 (컬러 바와 일치):
            1~3 → green  (권장)
            4~6 → yellow (주의)
            7~10 → red   (비권장)
        """
        self.lbl_concurrent_value.setText(str(value))

        if value <= 3:
            zone = "green"
        elif value <= 6:
            zone = "yellow"
        else:
            zone = "red"

        # dynamic property 로 색 전환 — 매 틱마다 setStyleSheet 재파싱 회피.
        # _apply_style 의 [zone=...] 셀렉터가 받는다.
        self.lbl_concurrent_value.setProperty("zone", zone)
        self.slider_concurrent.setProperty("zone", zone)

        for w in (self.lbl_concurrent_value, self.slider_concurrent):
            w.style().unpolish(w)
            w.style().polish(w)

    def _load_values(self):
        """현재 설정값을 UI에 반영"""
        self.input_path.setText(
            self.config.get("save_path", "")
        )

        # max_concurrent — 슬라이더에 반영, 변경 핸들러로 라벨·색까지 동기화
        current = int(self.config.get("max_concurrent", 2) or 2)
        current = max(1, min(10, current))   # 클램프 (구버전 설정 방어)
        self.slider_concurrent.setValue(current)
        # setValue 가 valueChanged 를 쏘지 않는 경계(동일 값) 케이스 방어
        self._on_concurrent_changed(current)

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
        """
        저장 버튼 처리.

        주의: max_concurrent 는 본 단계에선 placebo — 값은 저장되지만
        실제 동시 다운로드 제어는 후속 "동시성 제어 구현 (큐 매니저)"
        항목에서 도입된다. WORKLOG 단기 섹션 참조.
        """
        new_settings = {
            "save_path"         : self.input_path.text(),
            "max_concurrent"    : self.slider_concurrent.value(),
            "auto_update_ytdlp" : self.chk_auto_update.isChecked(),
        }

        # ConfigManager 에 저장
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

            /* 현재 값 큰 숫자 — 동적 색 (zone property) */
            QLabel#concurrentValue {
                color: #4caf50;
                font-size: 22px;
                font-weight: bold;
                padding: 0;
            }
            QLabel#concurrentValue[zone="green"]  { color: #4caf50; }
            QLabel#concurrentValue[zone="yellow"] { color: #e6b800; }
            QLabel#concurrentValue[zone="red"]    { color: #e05555; }

            /* 컬러 바 띠 */
            QLabel#zoneGreen {
                background: #2e7d32;
                color: #ffffff;
                font-size: 10px;
                font-weight: bold;
                padding: 3px 0;
                border-top-left-radius: 3px;
                border-bottom-left-radius: 3px;
            }
            QLabel#zoneYellow {
                background: #c9a227;
                color: #1e1e1e;
                font-size: 10px;
                font-weight: bold;
                padding: 3px 0;
            }
            QLabel#zoneRed {
                background: #b03030;
                color: #ffffff;
                font-size: 10px;
                font-weight: bold;
                padding: 3px 0;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }

            /* 슬라이더 — 핸들 색은 zone property 로 동적 변경 */
            QSlider#concurrentSlider::groove:horizontal {
                background: #1e1e1e;
                border: 1px solid #555;
                height: 6px;
                border-radius: 3px;
            }
            QSlider#concurrentSlider::handle:horizontal {
                background: #4caf50;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
                border: 2px solid #1e1e1e;
            }
            QSlider#concurrentSlider[zone="green"]::handle:horizontal  { background: #4caf50; }
            QSlider#concurrentSlider[zone="yellow"]::handle:horizontal { background: #e6b800; }
            QSlider#concurrentSlider[zone="red"]::handle:horizontal    { background: #e05555; }

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
