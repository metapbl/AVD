# ui/preferences_dialog.py
# 환경설정 팝업 다이얼로그

import sys

from PySide6.QtCore import QCoreApplication, QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDoubleValidator, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.about_dialog import REPO_URL
from utils.config_manager import ConfigManager
from utils.i18n import LANGUAGES

translate = QCoreApplication.translate


def cookie_help_url() -> str:
    """지금 언어 README 의 로그인 쿠키 절. 확장 안내는 앱을 다시 배포하지 않고 README 만 고쳐 갱신한다.
    번역문은 그 언어 README 파일과 절 앵커다 (D085)."""
    return REPO_URL + "/blob/main/" + translate("PreferencesDialog", "README.ko.md#로그인-쿠키")

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

    DOT_DIAMETER = 3

    def paintEvent(self, event):
        # 1) 기본 슬라이더(트랙·핸들) 먼저 그린다
        super().paintEvent(event)

        # 2) 점 8 개를 트랙 위에 덮어 그린다 — 값 2~9
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.color("muted")))

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
        self.setModal(True)
        self._rebuild_pending = False
        self._build()
        # 적용으로 테마가 바뀌면 열린 창도 새 색으로 다시 그린다 (D091)
        theme.notifier.changed.connect(self._schedule_rebuild)

    def _build(self, values: dict | None = None):
        self.setWindowTitle(translate("PreferencesDialog", "환경설정"))
        self._build_ui()
        # 이미 떠 있는 창에 새로 붙인 위젯은 직접 보이게 하기 전까지 숨은 상태라 크기 계산에서 빠진다
        # — 다시 그린 뒤 창이 제목 표시줄만큼 납작해지던 원인 (실기에서 발견, R§4 T36)
        for child in self.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            child.show()
        self._load_values(values)
        self._apply_style()
        # 창 크기는 가장 긴 페이지(접히는 칸까지 펼친 상태)에 맞춰 고정한다 — 페이지를 바꾸거나
        # 칸을 접고 펴도 창이 흔들리지 않게 (D090)
        self.gain_detail.setVisible(True)
        self.cookie_file_row.setVisible(True)
        self.setFixedSize(680, self.sizeHint().height())
        self._on_gain_toggled(self.chk_gain.isChecked())
        self._on_cookie_source_changed()
        self._watch_changes()

    def _schedule_rebuild(self):
        # 신호가 버튼을 누르는 도중에 오므로 그 버튼을 지우지 않게 다음 차례로 미룬다
        if not self._rebuild_pending:
            self._rebuild_pending = True
            QTimer.singleShot(0, self, self._rebuild)  # 그 사이 창이 지워지면 취소된다

    def _rebuild(self):
        """언어·테마가 바뀌면 창을 다시 그린다. 보던 페이지와 입력 중인 값은 그대로 (D091)."""
        self._rebuild_pending = False
        row = self.nav.currentRow()
        values = self._collect()  # 시스템 밝기 모드가 바뀌어 다시 그릴 때 저장 안 한 입력을 잃지 않게
        QWidget().setLayout(self.layout())  # 옛 배치와 위젯을 임시 위젯으로 넘겨 함께 지운다
        self._build(values)
        self.nav.setCurrentRow(row)
        self._sync_title_bar()

    def _sync_title_bar(self):
        """Qt 는 색 모드가 바뀔 때 열린 모달 창의 제목 표시줄을 다크로 되돌리지 못한다 — 직접 맞춘다 (Windows, T37)."""
        if sys.platform != "win32" or not self.isVisible():
            return
        import ctypes

        dark = ctypes.c_int(1 if theme.current() == "dark" else 0)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE
        ctypes.windll.dwmapi.DwmSetWindowAttribute(int(self.winId()), 20, ctypes.byref(dark), ctypes.sizeof(dark))

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange and self.layout() is not None:
            self._schedule_rebuild()
        super().changeEvent(event)

    def _watch_changes(self):
        """값이 저장된 것과 달라질 때만 "적용" 을 누를 수 있게 한다 (D091)."""
        for w in self.findChildren(QLineEdit):
            w.textChanged.connect(self._update_apply)
        for w in self.findChildren(QCheckBox) + self.findChildren(QRadioButton):
            w.toggled.connect(self._update_apply)
        for w in self.findChildren(QSlider):
            w.valueChanged.connect(self._update_apply)
        self.combo_language.currentIndexChanged.connect(self._update_apply)
        self._update_apply()

    def _update_apply(self):
        self.btn_apply.setEnabled(any(self.config.get(k) != v for k, v in self._collect().items()))

    def _build_ui(self):
        """UI 구성"""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)
        # 페이지 위젯은 목록에 넣을 때까지 붙잡아 둔다 — 부모 없는 임시 위젯은 바로 지워진다
        self._page_widgets = [QWidget() for _ in range(4)]
        general, downloads, gain, cookies = (QVBoxLayout(w) for w in self._page_widgets)
        for page in (general, downloads, gain, cookies):
            page.setContentsMargins(0, 0, 0, 0)
            page.setSpacing(16)

        # ── 저장 경로 그룹 ──
        grp_path = QGroupBox(translate("PreferencesDialog", "저장 경로"))
        grp_path.setObjectName("settingsGroup")
        path_layout = QHBoxLayout(grp_path)
        path_layout.setSpacing(8)

        self.input_path = QLineEdit()
        self.input_path.setFixedHeight(32)
        self.input_path.setReadOnly(True)
        path_layout.addWidget(self.input_path)

        btn_browse = QPushButton(translate("PreferencesDialog", "찾아보기"))
        btn_browse.setObjectName("btnBrowse")
        btn_browse.setMinimumWidth(80)  # 긴 번역문이면 늘어난다 (F17)
        btn_browse.setFixedHeight(32)
        btn_browse.clicked.connect(self._browse_path)
        path_layout.addWidget(btn_browse)

        general.addWidget(grp_path)

        # ── 다운로드 설정 그룹 ──
        grp_dl = QGroupBox(translate("PreferencesDialog", "다운로드 설정"))
        grp_dl.setObjectName("settingsGroup")
        dl_layout = QVBoxLayout(grp_dl)
        dl_layout.setSpacing(8)

        # 동시 다운로드 수 — 슬라이더 + 큰 숫자 + 그라데이션 컬러 바 + 라벨
        # 본 단계의 슬라이더는 placebo: 값은 config 에 저장되지만 실제 동시성
        # 제어는 후속 항목 "동시성 제어 구현 (큐 매니저)" 에서 처리한다.

        # 상단 행: 라벨 + 현재 값 큰 숫자 (우측)
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(translate("PreferencesDialog", "동시 다운로드 수")))
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

        lbl_green = QLabel(translate("PreferencesDialog", "권장"))
        lbl_green.setObjectName("zoneLabelGreen")
        lbl_green.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_label_row.addWidget(lbl_green, stretch=2)   # 좌측 약 22%

        lbl_yellow = QLabel(translate("PreferencesDialog", "주의"))
        lbl_yellow.setObjectName("zoneLabelYellow")
        lbl_yellow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_label_row.addWidget(lbl_yellow, stretch=4)  # 중앙 약 44%

        lbl_red = QLabel(translate("PreferencesDialog", "비권장"))
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
            translate("PreferencesDialog", "yt-dlp 는 단일 인스턴스 병렬 다운로드를 공식 지원하지 않습니다.\n"
            "1~3 권장. 높은 값은 IP 차단 위험.")
        )
        self.slider_concurrent.valueChanged.connect(self._on_concurrent_changed)
        dl_layout.addWidget(self.slider_concurrent)

        downloads.addWidget(grp_dl)

        # ── 로그인 쿠키 그룹 (F15, D079·D080) — 출처만 저장, 쿠키 값은 다루지 않는다 ──
        grp_cookie = QGroupBox(translate("PreferencesDialog", "로그인 쿠키"))
        grp_cookie.setObjectName("settingsGroup")
        cookie_layout = QVBoxLayout(grp_cookie)
        cookie_layout.setSpacing(8)

        radio_row = QHBoxLayout()
        radio_row.setSpacing(16)
        self._cookie_radios = {
            "none": QRadioButton(translate("PreferencesDialog", "사용 안 함")),
            "firefox": QRadioButton(translate("PreferencesDialog", "Firefox 에서 읽기")),
            "file": QRadioButton(translate("PreferencesDialog", "cookies.txt 파일")),
        }
        for radio in self._cookie_radios.values():
            radio_row.addWidget(radio)
            radio.toggled.connect(self._on_cookie_source_changed)
        radio_row.addStretch()
        cookie_layout.addLayout(radio_row)

        self.cookie_file_row = QWidget()
        file_row = QHBoxLayout(self.cookie_file_row)
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.setSpacing(8)
        self.input_cookie_file = QLineEdit()
        self.input_cookie_file.setFixedHeight(32)
        self.input_cookie_file.setReadOnly(True)
        file_row.addWidget(self.input_cookie_file)
        self.btn_cookie_file = QPushButton(translate("PreferencesDialog", "찾아보기"))
        self.btn_cookie_file.setObjectName("btnBrowse")
        self.btn_cookie_file.setMinimumWidth(80)  # 긴 번역문이면 늘어난다 (F17)
        self.btn_cookie_file.setFixedHeight(32)
        self.btn_cookie_file.clicked.connect(self._browse_cookie_file)
        file_row.addWidget(self.btn_cookie_file)
        cookie_layout.addWidget(self.cookie_file_row)

        # 고른 선택마다 문구가 바뀐다 (_on_cookie_source_changed)
        self.lbl_cookie_note = QLabel()
        self.lbl_cookie_note.setObjectName("gainHint")
        self.lbl_cookie_note.setWordWrap(True)
        self.lbl_cookie_note.setOpenExternalLinks(True)
        cookie_layout.addWidget(self.lbl_cookie_note)

        cookies.addWidget(grp_cookie)

        # ── MP3 음량 정규화 그룹 ──
        # 체크박스를 켜면 접혀 있던 게인 컨트롤(슬라이더+입력창)이 펼쳐진다.
        # 목표 dB 는 0.5dB 단위(슬라이더 정수 스텝 = 0.5dB, GAIN_SCALE=2).
        grp_gain = QGroupBox(translate("PreferencesDialog", "MP3 음량 정규화"))
        grp_gain.setObjectName("settingsGroup")
        gain_layout = QVBoxLayout(grp_gain)
        gain_layout.setSpacing(8)

        self.chk_gain = QCheckBox(translate("PreferencesDialog", "MP3 다운로드 시 음량 정규화"))
        self.chk_gain.setToolTip(
            translate("PreferencesDialog", "MP3 로 저장할 때 곡별 음량을 목표 dB 로 맞춥니다(무손실 ReplayGain).\n"
            "여러 곡의 음량 편차를 줄여 재생 시 볼륨을 다시 만질 필요를 덜어줍니다.")
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
        gain_top.addWidget(QLabel(translate("PreferencesDialog", "목표 음량")))
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

        # 범위 안내 — 최소/기본/최대 텍스트(값 텍스트 표기).
        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        lbl_min = QLabel(translate("PreferencesDialog", "{0} 조용").format(f"{_GAIN_DB_MIN:.0f}"))
        lbl_min.setObjectName("gainHint")
        lbl_mid = QLabel(translate("PreferencesDialog", "{0} 표준").format(f"{_GAIN_DB_DEFAULT:.0f}"))
        lbl_mid.setObjectName("gainHint")
        lbl_mid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_max = QLabel(translate("PreferencesDialog", "{0} 크게").format(f"{_GAIN_DB_MAX:.0f}"))
        lbl_max.setObjectName("gainHint")
        lbl_max.setAlignment(Qt.AlignmentFlag.AlignRight)
        hint_row.addWidget(lbl_min, stretch=1)
        hint_row.addWidget(lbl_mid, stretch=1)
        hint_row.addWidget(lbl_max, stretch=1)
        detail_layout.addLayout(hint_row)

        # 클리핑 주의 안내 — 높은 값일수록 음이 깨질(클리핑) 수 있음.
        lbl_clip = QLabel(translate("PreferencesDialog", "값이 높을수록 음량이 커지지만 클리핑(왜곡) 위험이 있습니다."))
        lbl_clip.setObjectName("gainClipNote")
        lbl_clip.setWordWrap(True)
        detail_layout.addWidget(lbl_clip)

        gain_layout.addWidget(self.gain_detail)
        gain.addWidget(grp_gain)

        # ── 업데이트 설정 그룹 ──
        grp_update = QGroupBox(translate("PreferencesDialog", "업데이트 설정"))
        grp_update.setObjectName("settingsGroup")
        update_layout = QVBoxLayout(grp_update)

        self.chk_auto_update = QCheckBox(
            translate("PreferencesDialog", "앱 시작 시 yt-dlp 자동 업데이트 확인")
        )
        update_layout.addWidget(self.chk_auto_update)


        # ── 언어 그룹 (F17, D084) — 언어 이름은 그 언어로 쓰고 번역하지 않는다 ──
        grp_lang = QGroupBox(translate("PreferencesDialog", "언어"))
        grp_lang.setObjectName("settingsGroup")
        lang_layout = QHBoxLayout(grp_lang)
        self.combo_language = QComboBox()
        self.combo_language.addItem(translate("PreferencesDialog", "시스템 설정 따르기"), "system")
        for code, name in LANGUAGES.items():
            self.combo_language.addItem(name, code)
        lang_layout.addWidget(self.combo_language)
        lang_layout.addStretch()
        general.addWidget(grp_lang)

        # ── 화면 테마 그룹 (D065) ──
        grp_theme = QGroupBox(translate("PreferencesDialog", "화면 테마"))
        grp_theme.setObjectName("settingsGroup")
        theme_layout = QHBoxLayout(grp_theme)
        theme_layout.setSpacing(16)
        self._theme_radios = {
            "system": QRadioButton(translate("PreferencesDialog", "Windows 설정 따르기")),
            "dark": QRadioButton(translate("PreferencesDialog", "다크")),
            "light": QRadioButton(translate("PreferencesDialog", "라이트")),
        }
        for radio in self._theme_radios.values():
            theme_layout.addWidget(radio)
        theme_layout.addStretch()
        general.addWidget(grp_theme)
        general.addWidget(grp_update)

        # ── 왼쪽 목록 + 오른쪽 페이지 (D090) ──
        self.nav = QListWidget()
        self.nav.setObjectName("prefsNav")
        self.pages = QStackedWidget()
        for name, page in (
            (translate("PreferencesDialog", "일반"), general),
            (translate("PreferencesDialog", "다운로드"), downloads),
            (translate("PreferencesDialog", "MP3 음량"), gain),
            (translate("PreferencesDialog", "로그인 쿠키"), cookies),
        ):
            page.addStretch()
            self.nav.addItem(name)
            self.pages.addWidget(page.parentWidget())
        # 목록 폭은 가장 긴 이름에 맞춘다 (언어마다 길이가 다르다, 최소 150)
        self.nav.setFixedWidth(max(150, self.nav.sizeHintForColumn(0) + 2 * self.nav.frameWidth() + 24))
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self.nav)
        body.addWidget(self.pages, 1)
        root.addLayout(body, 1)

        # ── 버튼 행 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        # Windows 관례 "확인 · 취소 · 적용" (D091)
        self.btn_ok = QPushButton(translate("PreferencesDialog", "확인"))
        self.btn_ok.setObjectName("btnConfirm")
        self.btn_ok.setProperty("role", "primary")
        self.btn_ok.clicked.connect(self._on_save)
        # 정하지 않으면 Qt 가 첫 버튼을 기본으로 삼아 Enter 가 엉뚱한 버튼을 누른다 (D060).
        self.btn_ok.setDefault(True)

        self.btn_cancel = QPushButton(translate("PreferencesDialog", "취소"))
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_apply = QPushButton(translate("PreferencesDialog", "적용"))
        self.btn_apply.setObjectName("btnApply")
        self.btn_apply.clicked.connect(self._on_apply)

        for button in (self.btn_ok, self.btn_cancel, self.btn_apply):
            button.setMinimumWidth(80)  # 긴 번역문이면 늘어난다 (F17)
            button.setFixedHeight(32)
            btn_row.addWidget(button)

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

    # ── 로그인 쿠키 컨트롤 ──────────────────────────

    def _on_cookie_source_changed(self):
        """cookies.txt 를 골랐을 때만 경로 칸이 보이고, 안내 문구도 선택을 따른다."""
        is_file = self._cookie_radios["file"].isChecked()
        self.cookie_file_row.setVisible(is_file)
        if is_file:
            note = translate(
                "PreferencesDialog",
                "Chrome, Edge 등에서 확장으로 내보낸 cookies.txt 를 지정하세요. "
                '<a href="{0}" style="color:{1};">만드는 법 ↗</a>',
            ).format(cookie_help_url(), theme.color("accent"))
        elif self._cookie_radios["firefox"].isChecked():
            note = translate("PreferencesDialog", "Firefox 에 로그인한 계정으로 받습니다. Firefox 에서 사이트에 로그인해 두세요.")
        else:
            note = translate("PreferencesDialog", "연령 제한처럼 로그인해야 볼 수 있는 영상을 받을 때 켜세요.")
        self.lbl_cookie_note.setText(note)

    def _browse_cookie_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, translate("PreferencesDialog", "cookies.txt 선택"), self.input_cookie_file.text(), translate("PreferencesDialog", "쿠키 파일 (*.txt);;모든 파일 (*)")
        )
        if path:
            self.input_cookie_file.setText(path)

    # ── MP3 음량 정규화 컨트롤 ──────────────────────

    def _on_gain_toggled(self, checked: bool):
        """
        체크 상태에 따라 게인 상세(슬라이더+입력창)를 펼치거나 접는다.
        창 크기는 고정이라 페이지 안에서만 접히고 펴진다 (D090).
        """
        self.gain_detail.setVisible(checked)

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

    def _load_values(self, values: dict | None = None):
        """설정값을 UI 에 반영. values 가 있으면 그 값이 저장된 값보다 먼저다."""
        def get(key, default=None):
            return values[key] if values and key in values else self.config.get(key, default)

        self.input_path.setText(
            get("save_path", "")
        )

        # max_concurrent — 슬라이더에 반영, 변경 핸들러로 라벨·색까지 동기화
        current = int(get("max_concurrent", 2) or 2)
        current = max(1, min(10, current))   # 클램프 (구버전 설정 방어)
        self.slider_concurrent.setValue(current)
        # setValue 가 valueChanged 를 쏘지 않는 경계(동일 값) 케이스 방어
        self._on_concurrent_changed(current)

        self.chk_auto_update.setChecked(
            get("auto_update_ytdlp", True)
        )

        index = self.combo_language.findData(get("ui_language", "system"))
        self.combo_language.setCurrentIndex(max(index, 0))  # 모르는 값은 시스템 설정 따르기

        mode = get("theme_mode", "system")
        self._theme_radios.get(mode, self._theme_radios["system"]).setChecked(True)

        source = get("cookie_source", "none")
        self._cookie_radios.get(source, self._cookie_radios["none"]).setChecked(True)
        self.input_cookie_file.setText(get("cookie_file", ""))
        self._on_cookie_source_changed()   # 같은 값이라 toggled 가 안 올 때도 맞춘다

        # MP3 음량 정규화 — 목표 dB 를 슬라이더(정수 스텝)로 환산해 반영,
        # 슬라이더 핸들러가 입력창까지 동기화한다. 체크 상태로 상세 펼침 결정.
        gain_db = float(get("mp3_gain_db", _GAIN_DB_DEFAULT) or _GAIN_DB_DEFAULT)
        gain_db = max(_GAIN_DB_MIN, min(_GAIN_DB_MAX, gain_db))   # 구설정 방어
        raw = round(gain_db * _GAIN_SCALE)
        self.slider_gain.setValue(raw)
        self._on_gain_slider_changed(raw)   # 동일 값 경계에서도 입력창 채움

        gain_on = bool(get("mp3_gain_enabled", False))
        self.chk_gain.setChecked(gain_on)
        self.gain_detail.setVisible(gain_on)   # 초기 접힘/펼침

    def _browse_path(self):
        """저장 경로 탐색기 열기"""
        folder = QFileDialog.getExistingDirectory(
            self,
            translate("PreferencesDialog", "저장 폴더 선택"),
            self.input_path.text()
        )
        if folder:
            self.input_path.setText(folder)

    def _collect(self) -> dict:
        """화면의 값을 설정 키로 모은다."""
        return {
            "save_path"         : self.input_path.text(),
            "max_concurrent"    : self.slider_concurrent.value(),
            "auto_update_ytdlp" : self.chk_auto_update.isChecked(),
            "theme_mode"        : next(m for m, r in self._theme_radios.items() if r.isChecked()),
            "ui_language"       : self.combo_language.currentData(),
            "mp3_gain_enabled"  : self.chk_gain.isChecked(),
            # 슬라이더는 GAIN_SCALE 배 정수 → 실제 dB(float, 0.5 단위)로 환산.
            "mp3_gain_db"       : self.slider_gain.value() / _GAIN_SCALE,
            "cookie_source"     : next(s for s, r in self._cookie_radios.items() if r.isChecked()),
            "cookie_file"       : self.input_cookie_file.text(),
        }

    def _on_apply(self):
        """적용 — 저장하고 바로 반영한다. 창은 그대로 (D091). 반영은 settings_saved 를 받은 메인 창이 한다."""
        new_settings = self._collect()
        for key, value in new_settings.items():
            self.config.set(key, value)
        self.btn_apply.setEnabled(False)
        self.settings_saved.emit(new_settings)

    def _on_save(self):
        """확인 — 적용하고 닫는다."""
        self._on_apply()
        self.accept()

    def _apply_style(self):
        """스타일 적용"""
        self.setStyleSheet(theme.qss("""
            QDialog {
                background: @surface;
            }
            QGroupBox#settingsGroup {
                color: @text2;
                font-size: 12px;
                border: 1px solid @line;
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
                color: @text2;
                font-size: 12px;
            }
            QLineEdit {
                background: @base;
                color: @text;
                border: 1px solid @line2;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 12px;
            }

            /* 현재 값 큰 숫자 — 동적 색 (zone property) */
            QLabel#concurrentValue {
                color: @success2;
                font-size: 22px;
                font-weight: bold;
                padding: 0;
            }
            QLabel#concurrentValue[zone="green"]  { color: @success2; }
            QLabel#concurrentValue[zone="yellow"] { color: @warn; }
            QLabel#concurrentValue[zone="red"]    { color: @danger; }

            /* 컬러 바 — 그라데이션 단일 띠 */
            QLabel#zoneGradientBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0.000 @success,
                    stop:0.222 @success,
                    stop:0.333 @warn,
                    stop:0.556 @warn,
                    stop:0.667 @danger,
                    stop:1.000 @danger
                );
                border-radius: 3px;
            }

            /* 띠 아래 구간 라벨 — 다이얼로그 배경 위에서 가독성 확보 */
            QLabel#zoneLabelGreen,
            QLabel#zoneLabelYellow,
            QLabel#zoneLabelRed {
                color: @text2;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 0 0 0;
            }

            /* 슬라이더 — 핸들 색은 zone property 로 동적 변경 */
            QSlider#concurrentSlider::groove:horizontal {
                background: @base;
                border: 1px solid @line2;
                height: 6px;
                border-radius: 3px;
            }
            /* 공통 스타일의 강조색 채움을 끈다 — 위험 구간은 핸들 색과 위 띠가 알려 준다 */
            QSlider#concurrentSlider::sub-page:horizontal { background: transparent; }
            QSlider#concurrentSlider::handle:horizontal {
                background: @success2;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
                border: 2px solid @base;
            }
            QSlider#concurrentSlider[zone="green"]::handle:horizontal  { background: @success2; }
            QSlider#concurrentSlider[zone="yellow"]::handle:horizontal { background: @warn; }
            QSlider#concurrentSlider[zone="red"]::handle:horizontal    { background: @danger; }

            QCheckBox, QRadioButton {
                color: @text2;
                font-size: 12px;
            }

            /* 게인 목표 dB 입력창 */
            QLineEdit#gainInput {
                background: @base;
                color: @text;
                border: 1px solid @line2;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit#gainInput:focus { border: 1px solid @accent; }

            /* 게인 슬라이더 — 파란 핸들(동시성 슬라이더의 위험색과 구분) */
            QSlider#gainSlider::groove:horizontal {
                background: @base;
                border: 1px solid @line2;
                height: 6px;
                border-radius: 3px;
            }
            QSlider#gainSlider::handle:horizontal {
                background: @accent;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
                border: 2px solid @base;
            }
            QSlider#gainSlider::handle:horizontal:hover { background: @accent2; }

            /* 게인 범위 안내 라벨 */
            QLabel#gainHint {
                color: @muted;
                font-size: 10px;
            }
            QLabel#gainClipNote {
                color: @warn;
                font-size: 10px;
            }

            QPushButton#btnBrowse {
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#btnCancel {
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#btnConfirm {
                border-radius: 4px;
                font-size: 12px;
            }
        """))
