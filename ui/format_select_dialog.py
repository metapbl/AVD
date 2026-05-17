# ui/format_select_dialog.py
# 화질/형식 선택 팝업 다이얼로그

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget,
    QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from core.info_fetcher import VideoInfo, FormatInfo
from utils.file_utils import format_duration, format_file_size


class FormatSelectDialog(QDialog):
    """
    화질/형식 선택 팝업 다이얼로그

    시그널:
        format_selected : 확인 버튼 클릭 시 FormatInfo 전달
    """

    format_selected = Signal(object)  # FormatInfo 전달

    def __init__(self, video_info: VideoInfo, parent=None):
        super().__init__(parent)
        self.video_info = video_info
        self.selected_format: FormatInfo | None = None

        self.setWindowTitle("화질 선택")
        self.setFixedSize(480, 520)
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
        lbl_title.setWordWrap(True)
        title_col.addWidget(lbl_title)

        # 업로더 + 재생시간
        meta = (
            f"{self.video_info.uploader}  •  "
            f"{format_duration(self.video_info.duration)}"
        )
        lbl_meta = QLabel(meta)
        lbl_meta.setObjectName("videoMeta")
        title_col.addWidget(lbl_meta)
        info_row.addLayout(title_col, stretch=1)
        root.addLayout(info_row)

        # 구분선
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #3a3a3a;")
        root.addWidget(line)

        # ── 포맷 목록 ──
        lbl_fmt = QLabel("다운로드 형식을 선택하세요")
        lbl_fmt.setObjectName("sectionLabel")
        root.addWidget(lbl_fmt)

        self.list_formats = QListWidget()
        self.list_formats.setSpacing(2)
        self.list_formats.itemDoubleClicked.connect(self._on_confirm)
        root.addWidget(self.list_formats)

        # 포맷 목록 채우기
        for fmt in self.video_info.formats:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, fmt)

            # 표시 텍스트 구성
            size_str = (
                format_file_size(fmt.filesize)
                if fmt.filesize > 0
                else "크기 미확인"
            )
            item.setText(
                f"  {fmt.label}"
                f"{'  |  ' + fmt.resolution if fmt.resolution != fmt.label else ''}"
                f"  |  {size_str}"
            )
            self.list_formats.addItem(item)

        # 첫 번째 항목 기본 선택
        if self.list_formats.count() > 0:
            self.list_formats.setCurrentRow(0)

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
        btn_confirm.setFixedSize(100, 32)
        btn_confirm.clicked.connect(self._on_confirm)
        btn_row.addWidget(btn_confirm)

        root.addLayout(btn_row)

    def _on_confirm(self):
        """다운로드 버튼 처리"""
        current = self.list_formats.currentItem()
        if not current:
            return

        fmt: FormatInfo = current.data(Qt.ItemDataRole.UserRole)
        self.format_selected.emit(fmt)
        self.accept()

    def _apply_style(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QDialog {
                background: #2b2b2b;
            }
            QLabel#videoTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#videoMeta {
                color: #888888;
                font-size: 11px;
            }
            QLabel#sectionLabel {
                color: #aaaaaa;
                font-size: 12px;
            }
            QListWidget {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                height: 36px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #4a90d9;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background: #3a3a3a;
            }
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