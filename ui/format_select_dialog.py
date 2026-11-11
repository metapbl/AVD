# ui/format_select_dialog.py
# 화질/형식 선택 팝업 다이얼로그

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from core.info_fetcher import (
    AUTO_FORMAT_ID,
    COMPAT_FORMAT_ID,
    M4A_FORMAT_ID,
    MP3_FORMAT_ID,
    FormatInfo,
    VideoInfo,
)
from ui import theme
from ui.download_item_widget import format_bitrate, humanize_codec
from utils.config_manager import ConfigManager
from utils.file_utils import format_duration, format_file_size

# 모든 영상에 같은 포맷 문자열로 나오는 행 — 고른 행을 포맷으로 기억할 수 있다.
_FIXED_FORMAT_IDS = (AUTO_FORMAT_ID, COMPAT_FORMAT_ID, MP3_FORMAT_ID, M4A_FORMAT_ID)


class FormatSelectDialog(QDialog):
    """
    화질/형식 선택 팝업 다이얼로그

    시그널:
        format_selected : 확인 버튼 클릭 시 FormatInfo 전달

    config 의존:
        - 읽기·쓰기: last_chosen_format_id (고정 행을 골랐을 때만 그 포맷, 아니면 "")
        - 읽기·쓰기: last_chosen_ext (해상도 행은 영상마다 포맷이 달라 ext 로 찾는다)
    """

    format_selected = Signal(object)  # FormatInfo 전달

    def __init__(self, video_info: VideoInfo, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.video_info = video_info
        self.config = config
        self.selected_format: FormatInfo | None = None

        self.setWindowTitle("화질 선택")
        self.setFixedSize(600, 520)
        self.setModal(True)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        """UI 구성"""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # ── 영상 정보 요약 ──
        info_row = QHBoxLayout()

        # 제목
        title_col = QVBoxLayout()
        lbl_title = QLabel(self.video_info.title)
        lbl_title.setObjectName("videoTitle")
        lbl_title.setTextFormat(Qt.TextFormat.PlainText)  # 사이트가 준 문자열 (SECURITY_POLICY §4)
        lbl_title.setWordWrap(True)
        title_col.addWidget(lbl_title)

        # 업로더 + 재생시간
        meta = (
            f"{self.video_info.uploader}  •  "
            f"{format_duration(self.video_info.duration)}"
        )
        lbl_meta = QLabel(meta)
        lbl_meta.setObjectName("videoMeta")
        lbl_meta.setTextFormat(Qt.TextFormat.PlainText)
        title_col.addWidget(lbl_meta)
        info_row.addLayout(title_col, stretch=1)
        root.addLayout(info_row)

        # 구분선
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet(theme.qss("background: @raised;"))
        root.addWidget(line)

        # ── 포맷 목록 ──
        lbl_fmt = QLabel("다운로드 형식을 선택하세요")
        lbl_fmt.setObjectName("sectionLabel")
        root.addWidget(lbl_fmt)

        self.list_formats = QTreeWidget()
        self.list_formats.setHeaderLabels(["형식", "해상도", "코덱", "크기"])
        self.list_formats.setRootIsDecorated(False)
        self.list_formats.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        header = self.list_formats.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.list_formats.itemDoubleClicked.connect(self._on_confirm)
        root.addWidget(self.list_formats)

        # 포맷 목록 채우기 — 형식 | 해상도 | 코덱/비트레이트 | 크기
        # - 라벨이 해상도와 같으면 해상도 칸은 비운다.
        # - 코덱 칸: 통합 포맷(AUTO_FORMAT_ID) 은 "자동". 그 외에는
        #   사람 친화 이름으로 정규화. 비트레이트는 abr→tbr.
        for fmt in self.video_info.formats:
            # 크기 칸
            size_str = (
                format_file_size(fmt.filesize)
                if fmt.filesize > 0
                else "크기 미확인"
            )

            # 코덱 칸 — 정규화 후 조립.
            if fmt.format_id == AUTO_FORMAT_ID:
                # 통합 포맷 — 선택 시점에 코덱 미확정.
                codec_str = "자동"
            else:
                v_name = humanize_codec(fmt.vcodec, "video")
                a_name = humanize_codec(fmt.acodec, "audio")
                bitrate = format_bitrate(fmt.abr, fmt.tbr)

                if fmt.is_audio:
                    # 오디오 전용: "MP3 320kbps" 또는 "MP3"
                    base_name = a_name or (fmt.ext or "").upper()
                    if base_name and bitrate:
                        codec_str = f"{base_name} {bitrate}"
                    elif base_name:
                        codec_str = base_name
                    else:
                        codec_str = "자동"
                else:
                    # 영상: "H.264 / AAC 192kbps"
                    parts = []
                    if v_name:
                        parts.append(v_name)
                    if a_name:
                        parts.append(
                            f"{a_name} {bitrate}" if bitrate else a_name
                        )
                    codec_str = " / ".join(parts) if parts else "자동"

            res_col = fmt.resolution if fmt.resolution != fmt.label else ""
            item = QTreeWidgetItem([fmt.label, res_col, codec_str, size_str])
            item.setData(0, Qt.ItemDataRole.UserRole, fmt)
            self.list_formats.addTopLevelItem(item)

        # 기본 선택 행 결정 — last_chosen_ext 가 있으면 같은 ext 의 첫 행,
        # 없거나 매칭 실패 시 첫 행.
        default_row = self._find_default_row()
        if self.list_formats.topLevelItemCount() > 0:
            self.list_formats.setCurrentItem(self.list_formats.topLevelItem(default_row))

        # ── 버튼 행 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setFixedSize(80, 32)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("다운로드")
        btn_confirm.setObjectName("btnConfirm")
        btn_confirm.setProperty("role", "primary")
        btn_confirm.setFixedSize(100, 32)
        btn_confirm.clicked.connect(self._on_confirm)
        # 정하지 않으면 Qt 가 첫 버튼을 기본으로 삼아 Enter 가 엉뚱한 버튼을 누른다 (D060).
        btn_confirm.setDefault(True)
        btn_row.addWidget(btn_confirm)

        root.addLayout(btn_row)

    def _find_default_row(self) -> int:
        """
        직전에 고른 고정 행(last_chosen_format_id), 없으면 last_chosen_ext 와
        일치하는 첫 포맷의 행 번호를 반환. 둘 다 못 찾으면 0 (첫 행).
        """
        last_id = self.config.get("last_chosen_format_id", "") or ""
        for row in range(self.list_formats.topLevelItemCount()):
            fmt = self.list_formats.topLevelItem(row).data(0, Qt.ItemDataRole.UserRole)
            if last_id and fmt is not None and fmt.format_id == last_id:
                return row

        last_ext = (self.config.get("last_chosen_ext", "") or "").strip().lower()
        if not last_ext:
            return 0

        for row in range(self.list_formats.topLevelItemCount()):
            item = self.list_formats.topLevelItem(row)
            fmt: FormatInfo = item.data(0, Qt.ItemDataRole.UserRole)
            if fmt is not None and (fmt.ext or "").lower() == last_ext:
                return row
        return 0

    def _on_confirm(self):
        """다운로드 버튼 처리"""
        current = self.list_formats.currentItem()
        if not current:
            return

        fmt: FormatInfo = current.data(0, Qt.ItemDataRole.UserRole)

        # 다음 호출 시 기본 선택을 위해 ext 를 기억
        if fmt is not None and fmt.ext:
            try:
                self.config.set("last_chosen_ext", fmt.ext)
                self.config.set(
                    "last_chosen_format_id",
                    fmt.format_id if fmt.format_id in _FIXED_FORMAT_IDS else "",
                )
            except Exception:
                # config 저장 실패는 본 흐름을 막지 않는다 (UX 우선)
                pass

        self.format_selected.emit(fmt)
        self.accept()

    def _apply_style(self):
        """스타일 적용"""
        self.setStyleSheet(theme.qss("""
            QDialog {
                background: @surface;
            }
            QLabel#videoTitle {
                color: @text;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#videoMeta {
                color: @muted;
                font-size: 11px;
            }
            QLabel#sectionLabel {
                color: @text2;
                font-size: 12px;
            }
            QTreeWidget {
                background: @base;
                color: @text;
                border: 1px solid @line;
                border-radius: 6px;
                font-size: 12px;
                outline: none;
            }
            QTreeWidget::item {
                height: 36px;
                padding-left: 6px;
            }
            QTreeWidget::item:hover {
                background: @raised;
            }
            QTreeWidget::item:selected {
                background: @accent;
                color: @on_accent;
            }
            QHeaderView::section {
                background: @raised;
                color: @text2;
                border: none;
                padding: 6px;
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
