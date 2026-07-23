# ui/preferences_dialog.py
# 환경설정 팝업 다이얼로그

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit,
    QSlider, QCheckBox, QWidget,
    QFileDialog, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QDoubleValidator
from utils.config_manager import ConfigManager


# ── MP3 음량 정규화 목표 dB 범위 ──────────────────────
# 슬라이더는 정수 스텝만 다루므로 dB 값을 2배 스케일한 정수로 저장한다
# (예: 89.0dB → 178). 0.5dB 단위를 슬라이더 1스텝으로 표현하기 위함.
# 표시·저장 시 GAIN_SCALE 로 나눠 실제 dB(float)로 환산한다.
_GAIN_DB_MIN     = 75.0
_GAIN_DB_MAX     = 105.0
_GAIN_DB_DEFAULT = 89.0
_GAIN_SCALE      = 2          # 1 슬라이더 스텝 = 0.5dB


class ConcurrentSlider(QSlider):
    """
    동시 다운로드 수 슬라이더.

    표준 QSlider 위에 위치 안내용 점 8 개(값 2~9)를 트랙 내부에 그린다.
    값 1·10 의 끝점에는 점을 두지 않는다 — 끝은 트랙 자체로 표현되며
    핸들 위치로 충분히 식별 가능하기 때문.

    핸들 색의 동적 변경은 상위 다이얼로그가 dynamic property + style.polish
    로 처리하므로 본 클래스는 점 그리기만 책임진다.
    """

    DOT_COLOR    = QColor("#cccccc")
    DOT_DIAMETER = 3

    def paintEvent(self, event):
        # 1) 기본 슬라이더(트랙·핸들) 먼저 그린다
        super().paintEvent(event)

        # 2) 점 8 개를 트랙 위에 덮어 그린다 — 값 2~9
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.DOT_COLOR)

            min_v = self.minimum()        # 1
            max_v = self.maximum()        # 10
            span  = max_v - min_v         # 9

            # 핸들 절반 폭만큼 좌우 여백이 있다 — 그 안에서 점 위치를 잡는다.
            # 스타일시트에서 핸들 width 16px 로 잡았으므로 여백 ≈ 8px.
            # QStyle 로 정확히 구할 수도 있지만 본 케이스에선 고정값으로 충분.
            margin = 8
            usable = self.width() - margin * 2
            if usable <= 0 or span <= 0:
                return

            cy = self.height() // 2
            r  = self.DOT_DIAMETER / 2

            for v in range(min_v + 1, max_v):     # 2 ~ 9
                ratio = (v - min_v) / span
                cx    = margin + ratio * usable
                painter.drawEllipse(
                    int(cx - r), int(cy - r),
                    self.DOT_DIAMETER, self.DOT_DIAMETER,
                )
        finally:
            painter.end()


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
        # 게인 그룹이 체크 상태에 따라 접혔다 펴지므로 고정 높이 대신 폭만
        # 고정하고 높이는 내용에 맞춰 자동 조정한다(adjustSize).
        self.setFixedWidth(480)
        self.setModal(True)
        self._build_ui()
        self._load_values()
        self._apply_style()
        self.adjustSize()

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

        # 동시 다운로드 수 — 슬라이더 + 큰 숫자 + 그라데이션 컬러 바 + 라벨
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

        # 컬러 바 — 그라데이션 단일 띠
        # stop 위치는 점(값 1~10) 과 정합:
        #   0.000 (1) ~ 0.222 (3)  : 녹 단색
        #   0.222 (3) ~ 0.333 (4)  : 녹 → 노 전환
        #   0.333 (4) ~ 0.556 (6)  : 노 단색
        #   0.556 (6) ~ 0.667 (7)  : 노 → 빨 전환
        #   0.667 (7) ~ 1.000 (10) : 빨 단색
        self.color_bar = QLabel()
        self.color_bar.setObjectName("zoneGradientBar")
        self.color_bar.setFixedHeight(14)
        dl_layout.addWidget(self.color_bar)

        # 띠 아래 라벨 행 — "권장 / 주의 / 비권장"
        # 각 라벨이 해당 단색 구간의 중앙 부근에 떠 있도록 stretch 배분.
        # 녹 단색 1~3 의 중앙 ≈ 2, 노 단색 4~6 의 중앙 = 5, 빨 단색 7~10 의
        # 중앙 ≈ 8.5. 트랙 너비 기준 % 로 환산: 11.1% / 44.4% / 83.3%.
        zone_label_row = QHBoxLayout()
        zone_label_row.setSpacing(0)
        zone_label_row.setContentsMargins(0, 0, 0, 0)

        lbl_green = QLabel("권장")
        lbl_green.setObjectName("zoneLabelGreen")
        lbl_green.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_label_row.addWidget(lbl_green, stretch=2)   # 좌측 약 22%

        lbl_yellow = QLabel("주의")
        lbl_yellow.setObjectName("zoneLabelYellow")
        lbl_yellow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_label_row.addWidget(lbl_yellow, stretch=4)  # 중앙 약 44%

        lbl_red = QLabel("비권장")
        lbl_red.setObjectName("zoneLabelRed")
        lbl_red.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_label_row.addWidget(lbl_red, stretch=3)     # 우측 약 33%

        dl_layout.addLayout(zone_label_row)

        # 슬라이더 — 점 8 개를 그리는 커스텀 서브클래스
        self.slider_concurrent = ConcurrentSlider(Qt.Orientation.Horizontal)
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

        # ── MP3 음량 정규화 그룹 ──
        # 체크박스를 켜면 접혀 있던 게인 컨트롤(슬라이더+입력창)이 펼쳐진다.
        # 목표 dB 는 0.5dB 단위(슬라이더 정수 스텝 = 0.5dB, GAIN_SCALE=2).
        grp_gain = QGroupBox("MP3 음량 정규화")
        grp_gain.setObjectName("settingsGroup")
        gain_layout = QVBoxLayout(grp_gain)
        gain_layout.setSpacing(8)

        self.chk_gain = QCheckBox("MP3 다운로드 시 음량 정규화")
        self.chk_gain.setToolTip(
            "MP3 로 저장할 때 곡별 음량을 목표 dB 로 맞춥니다(무손실 ReplayGain).\n"
            "여러 곡의 음량 편차를 줄여 재생 시 볼륨을 다시 만질 필요를 덜어줍니다."
        )
        self.chk_gain.toggled.connect(self._on_gain_toggled)
        gain_layout.addWidget(self.chk_gain)

        # 접히는 컨테이너 — 체크 시에만 보인다.
        self.gain_detail = QWidget()
        detail_layout = QVBoxLayout(self.gain_detail)
        detail_layout.setContentsMargins(0, 4, 0, 0)
        detail_layout.setSpacing(6)

        # 상단 행: "목표 음량" 라벨 + 입력창(dB)
        gain_top = QHBoxLayout()
        gain_top.addWidget(QLabel("목표 음량"))
        gain_top.addStretch()
        self.input_gain_db = QLineEdit()
        self.input_gain_db.setObjectName("gainInput")
        self.input_gain_db.setFixedSize(72, 28)
        self.input_gain_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 75.0~105.0, 소수 1자리. 슬라이더가 0.5 단위라 1자리면 충분.
        gain_validator = QDoubleValidator(_GAIN_DB_MIN, _GAIN_DB_MAX, 1, self)
        gain_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.input_gain_db.setValidator(gain_validator)
        self.input_gain_db.editingFinished.connect(self._on_gain_input_edited)
        gain_top.addWidget(self.input_gain_db)
        gain_top.addWidget(QLabel("dB"))
        detail_layout.addLayout(gain_top)

        # 슬라이더 — 정수 스텝(0.5dB). 값은 GAIN_SCALE 배 정수로 다룬다.
        self.slider_gain = QSlider(Qt.Orientation.Horizontal)
        self.slider_gain.setObjectName("gainSlider")
        self.slider_gain.setMinimum(int(_GAIN_DB_MIN * _GAIN_SCALE))   # 150
        self.slider_gain.setMaximum(int(_GAIN_DB_MAX * _GAIN_SCALE))   # 210
        self.slider_gain.setSingleStep(1)   # 0.5dB
        self.slider_gain.setPageStep(2)     # 1.0dB
        self.slider_gain.valueChanged.connect(self._on_gain_slider_changed)
        detail_layout.addWidget(self.slider_gain)

        # 범위 안내 — 최소/기본/최대 텍스트(WORKLOG 방침: 값 텍스트 표기).
        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        lbl_min = QLabel(f"{_GAIN_DB_MIN:.0f} 조용")
        lbl_min.setObjectName("gainHint")
        lbl_mid = QLabel(f"{_GAIN_DB_DEFAULT:.0f} 표준")
        lbl_mid.setObjectName("gainHint")
        lbl_mid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_max = QLabel(f"{_GAIN_DB_MAX:.0f} 크게")
        lbl_max.setObjectName("gainHint")
        lbl_max.setAlignment(Qt.AlignmentFlag.AlignRight)
        hint_row.addWidget(lbl_min, stretch=1)
        hint_row.addWidget(lbl_mid, stretch=1)
        hint_row.addWidget(lbl_max, stretch=1)
        detail_layout.addLayout(hint_row)

        # 클리핑 주의 안내 — 높은 값일수록 음이 깨질(클리핑) 수 있음.
        lbl_clip = QLabel("값이 높을수록 음량이 커지지만 클리핑(왜곡) 위험이 있습니다.")
        lbl_clip.setObjectName("gainClipNote")
        lbl_clip.setWordWrap(True)
        detail_layout.addWidget(lbl_clip)

        gain_layout.addWidget(self.gain_detail)
        root.addWidget(grp_gain)

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

        구간 정책 (그라데이션의 단색 구간과 일치):
            1~3 → green  (권장)
            4~6 → yellow (주의)
            7~10 → red   (비권장)

        전환 구간(3~4, 6~7)에서는 컬러 바가 그라데이션으로 매끄럽게
        넘어가지만, 핸들·큰 숫자의 색은 이산 구간 정책을 따른다 —
        값이 정수이므로 양가성이 발생하지 않는다.
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

    # ── MP3 음량 정규화 컨트롤 ──────────────────────

    def _on_gain_toggled(self, checked: bool):
        """
        체크 상태에 따라 게인 상세(슬라이더+입력창)를 펼치거나 접는다.
        접힘/펼침으로 다이얼로그 높이가 달라지므로 adjustSize 로 재조정한다.
        """
        self.gain_detail.setVisible(checked)
        # 레이아웃이 즉시 반영되도록 다음 이벤트 루프가 아니라 지금 재계산.
        self.adjustSize()

    def _on_gain_slider_changed(self, raw: int):
        """
        슬라이더(정수, GAIN_SCALE 배) 변경 → 입력창에 dB(소수1자리) 반영.
        입력창과의 순환 갱신을 막기 위해 editingFinished 만 역방향으로 쓴다
        (valueChanged→setText 는 시그널을 쏘지 않으므로 순환 없음).
        """
        db = raw / _GAIN_SCALE
        self.input_gain_db.setText(f"{db:.1f}")

    def _on_gain_input_edited(self):
        """
        입력창 편집 완료 → 값을 클램프·0.5 단위 양자화 후 슬라이더에 반영.
        슬라이더 setValue 가 valueChanged 를 쏘면 입력창이 정규화된 값으로
        다시 채워진다(예: 89.3 → 89.5). 빈 값이면 기본값으로 되돌린다.
        """
        text = self.input_gain_db.text().strip()
        try:
            db = float(text)
        except ValueError:
            db = _GAIN_DB_DEFAULT
        db = max(_GAIN_DB_MIN, min(_GAIN_DB_MAX, db))
        # 0.5 단위로 양자화(반올림) 후 슬라이더 정수 스텝으로 환산.
        raw = round(db * _GAIN_SCALE)
        self.slider_gain.setValue(raw)          # valueChanged → 입력창 정규화
        self._on_gain_slider_changed(raw)       # 동일 값일 때도 표시 갱신 보장

    def _load_values(self):
        """현재 설정값을 UI 에 반영"""
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

        # MP3 음량 정규화 — 목표 dB 를 슬라이더(정수 스텝)로 환산해 반영,
        # 슬라이더 핸들러가 입력창까지 동기화한다. 체크 상태로 상세 펼침 결정.
        gain_db = float(self.config.get("mp3_gain_db", _GAIN_DB_DEFAULT) or _GAIN_DB_DEFAULT)
        gain_db = max(_GAIN_DB_MIN, min(_GAIN_DB_MAX, gain_db))   # 구설정 방어
        raw = round(gain_db * _GAIN_SCALE)
        self.slider_gain.setValue(raw)
        self._on_gain_slider_changed(raw)   # 동일 값 경계에서도 입력창 채움

        gain_on = bool(self.config.get("mp3_gain_enabled", False))
        self.chk_gain.setChecked(gain_on)
        self.gain_detail.setVisible(gain_on)   # 초기 접힘/펼침

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
            "mp3_gain_enabled"  : self.chk_gain.isChecked(),
            # 슬라이더는 GAIN_SCALE 배 정수 → 실제 dB(float, 0.5 단위)로 환산.
            "mp3_gain_db"       : self.slider_gain.value() / _GAIN_SCALE,
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

            /* 컬러 바 — 그라데이션 단일 띠 */
            QLabel#zoneGradientBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0.000 #2e7d32,
                    stop:0.222 #2e7d32,
                    stop:0.333 #c9a227,
                    stop:0.556 #c9a227,
                    stop:0.667 #b03030,
                    stop:1.000 #b03030
                );
                border-radius: 3px;
            }

            /* 띠 아래 구간 라벨 — 다이얼로그 배경 위에서 가독성 확보 */
            QLabel#zoneLabelGreen,
            QLabel#zoneLabelYellow,
            QLabel#zoneLabelRed {
                color: #cccccc;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 0 0 0;
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

            /* 게인 목표 dB 입력창 */
            QLineEdit#gainInput {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit#gainInput:focus { border: 1px solid #4a90d9; }

            /* 게인 슬라이더 — 파란 핸들(동시성 슬라이더의 위험색과 구분) */
            QSlider#gainSlider::groove:horizontal {
                background: #1e1e1e;
                border: 1px solid #555;
                height: 6px;
                border-radius: 3px;
            }
            QSlider#gainSlider::handle:horizontal {
                background: #4a90d9;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
                border: 2px solid #1e1e1e;
            }
            QSlider#gainSlider::handle:horizontal:hover { background: #5aa0e9; }

            /* 게인 범위 안내 라벨 */
            QLabel#gainHint {
                color: #888888;
                font-size: 10px;
            }
            QLabel#gainClipNote {
                color: #b58900;
                font-size: 10px;
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
