# ui/download_item_widget.py
# 다운로드 목록에서 항목 하나를 표시하는 위젯

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QProgressBar, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from models.download_item import DownloadItem, DownloadStatus
from utils.file_utils import format_duration, open_folder


class DownloadItemWidget(QWidget):
    """
    다운로드 항목 하나를 표시하는 위젯

    시그널:
        cancel_requested  : 취소 버튼 클릭 시
        open_requested    : 폴더 열기 버튼 클릭 시
        remove_requested  : 항목 삭제 버튼 클릭 시
    """

    cancel_requested = Signal(str)  # item_id 전달
    open_requested   = Signal(str)  # item_id 전달
    remove_requested = Signal(str)  # item_id 전달

    def __init__(self, item: DownloadItem, parent=None):
        super().__init__(parent)
        self.item = item
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        """UI 구성"""

        # 전체 가로 레이아웃
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(12)

        # ── 썸네일 영역 ──
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(120, 68)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setStyleSheet(
            "background:#1e1e1e; border-radius:4px;"
        )
        self.lbl_thumb.setText("🎬")
        root.addWidget(self.lbl_thumb)

        # ── 정보 + 진행률 영역 ──
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 제목
        self.lbl_title = QLabel(self.item.title)
        self.lbl_title.setObjectName("itemTitle")
        self.lbl_title.setWordWrap(False)
        info_layout.addWidget(self.lbl_title)

        # 업로더 + 재생시간
        meta = f"{self.item.uploader}  •  " \
               f"{format_duration(self.item.duration)}"
        self.lbl_meta = QLabel(meta)
        self.lbl_meta.setObjectName("itemMeta")
        info_layout.addWidget(self.lbl_meta)

        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        info_layout.addWidget(self.progress_bar)

        # 상태 + 속도 + 남은시간
        status_row = QHBoxLayout()
        self.lbl_status = QLabel(self.item.status.value)
        self.lbl_status.setObjectName("itemStatus")
        self.lbl_speed  = QLabel("")
        self.lbl_speed.setObjectName("itemMeta")
        self.lbl_eta    = QLabel("")
        self.lbl_eta.setObjectName("itemMeta")
        status_row.addWidget(self.lbl_status)
        status_row.addStretch()
        status_row.addWidget(self.lbl_speed)
        status_row.addSpacing(12)
        status_row.addWidget(self.lbl_eta)
        info_layout.addLayout(status_row)

        root.addLayout(info_layout, stretch=1)

        # ── 버튼 영역 ──
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        # 취소 버튼
        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setFixedWidth(60)
        self.btn_cancel.clicked.connect(
            lambda: self.cancel_requested.emit(self.item.item_id)
        )
        btn_layout.addWidget(self.btn_cancel)

        # 폴더 열기 버튼 (완료 후 표시)
        self.btn_open = QPushButton("📂 열기")
        self.btn_open.setObjectName("btnOpen")
        self.btn_open.setFixedWidth(60)
        self.btn_open.setVisible(False)
        self.btn_open.clicked.connect(
            lambda: self.open_requested.emit(self.item.item_id)
        )
        btn_layout.addWidget(self.btn_open)

        # 삭제 버튼
        self.btn_remove = QPushButton("✕")
        self.btn_remove.setObjectName("btnRemove")
        self.btn_remove.setFixedWidth(60)
        self.btn_remove.clicked.connect(
            lambda: self.remove_requested.emit(self.item.item_id)
        )
        btn_layout.addWidget(self.btn_remove)

        btn_layout.addStretch()
        root.addLayout(btn_layout)

    def _apply_style(self):
        """위젯 스타일 적용"""
        self.setStyleSheet("""
            DownloadItemWidget {
                background: #2b2b2b;
                border-radius: 8px;
                border: 1px solid #3a3a3a;
            }
            QLabel#itemTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#itemMeta {
                color: #888888;
                font-size: 11px;
            }
            QLabel#itemStatus {
                color: #4a90d9;
                font-size: 11px;
            }
            QProgressBar {
                background: #3c3c3c;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: #4a90d9;
                border-radius: 3px;
            }
            QPushButton#btnCancel {
                background: #555;
                color: #fff;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton#btnCancel:hover { background: #e05555; }
            QPushButton#btnOpen {
                background: #4a90d9;
                color: #fff;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton#btnOpen:hover { background: #5aa0e9; }
            QPushButton#btnRemove {
                background: #444;
                color: #aaa;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton#btnRemove:hover { background: #e05555; color: #fff; }
        """)

    # ── 외부에서 호출하는 업데이트 메서드 ──

    def update_progress(self, pct: float):
        """진행률 바 업데이트"""
        self.progress_bar.setValue(int(pct))

    def update_speed(self, speed: str):
        """속도 레이블 업데이트"""
        self.lbl_speed.setText(speed)

    def update_eta(self, eta: str):
        """남은 시간 레이블 업데이트"""
        self.lbl_eta.setText(f"남은시간 {eta}")

    def update_status(self, status: DownloadStatus):
        """상태 레이블 업데이트"""
        self.lbl_status.setText(status.value)

        if status == DownloadStatus.DONE:
            # 완료 시 버튼 전환
            self.btn_cancel.setVisible(False)
            self.btn_open.setVisible(True)
            self.progress_bar.setValue(100)
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")

        elif status == DownloadStatus.ERROR:
            self.btn_cancel.setVisible(False)
            self.lbl_status.setStyleSheet("color: #e05555;")

        elif status == DownloadStatus.MERGING:
            self.lbl_speed.setText("")
            self.lbl_eta.setText("병합 중...")

    def update_title(self, title: str):
        """제목 레이블 업데이트"""
        self.lbl_title.setText(title)
        self.item.title = title

    def update_thumbnail(self, data: bytes):
        """
        썸네일 이미지 업데이트.

        v7 변경: QPixmap 인자 → bytes 인자.
        QPixmap 생성·디코드를 이 메서드(GUI 스레드) 안에서 수행한다.
        워커 스레드에서 만든 QPixmap 은 paint engine 에서 빈 텍스처로
        그려지는 버그가 있어 GUI 스레드 단독 생성이 필수.
        """
        if not data:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            # 디코드 실패 — 라벨은 기본 이모지 유지
            return

        # 라벨의 실제 크기 사용. 초기 0x0 회피용으로 fixed size fallback.
        target_w = self.lbl_thumb.width()  or 120
        target_h = self.lbl_thumb.height() or 68

        scaled = pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        try:
            self.lbl_thumb.setPixmap(scaled)
            self.lbl_thumb.setText("")
            # paint 강제 트리거 — modal 다이얼로그 직후의 paint 누락 방어
            self.lbl_thumb.update()
        except RuntimeError:
            # 위젯이 이미 삭제된 경우 (사용자가 항목을 빠르게 지웠을 때)
            pass
