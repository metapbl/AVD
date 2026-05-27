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
        cancel_requested  : 취소 버튼 클릭 시 (라벨이 "취소" 일 때)
        retry_requested   : 재시도 버튼 클릭 시 (라벨이 "재시도" 일 때 — ERROR/CANCELLED)
        open_requested    : 폴더 열기 버튼 클릭 시
        remove_requested  : 항목 삭제 버튼 클릭 시
    """

    cancel_requested = Signal(str)  # item_id 전달
    retry_requested  = Signal(str)  # item_id 전달 — ERROR / CANCELLED 상태에서 재시도
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

        # 업로더 + 재생시간 — 위젯 생성 시점엔 둘 다 비어 있을 수 있다.
        # InfoWorker 완료 후 update_meta 가 같은 헬퍼로 다시 그린다.
        self.lbl_meta = QLabel(
            self._format_meta(self.item.uploader, self.item.duration)
        )
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

        # 취소/재시도 버튼 — 같은 버튼을 상태에 따라 라벨·동작 전환.
        # 라우터 메서드(_on_cancel_or_retry) 가 item.status 를 보고
        # cancel_requested / retry_requested 중 하나를 발사한다.
        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setFixedWidth(60)
        self.btn_cancel.clicked.connect(self._on_cancel_or_retry)
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

    # ── 사적 포맷 헬퍼 ───────────────────────────────

    @staticmethod
    def _format_meta(uploader: str, duration: int) -> str:
        """
        lbl_meta 라벨에 들어갈 "업로더 • 재생시간" 문자열을 만든다.
        _build_ui 의 초기 표시와 update_meta 의 갱신이 동일 포맷을 쓰도록
        단일 출처화한 헬퍼. 한 곳만 고치면 양쪽이 함께 따라온다.
        """
        return f"{uploader}  •  {format_duration(duration)}"

    # ── 버튼 라우터 ───────────────────────────────────

    def _on_cancel_or_retry(self):
        """
        btn_cancel 의 라우터.

        같은 버튼을 라벨에 따라 두 가지 동작으로 쓴다 — "취소" / "재시도".
        판단 기준은 라벨 텍스트가 아니라 self.item.status (단일 출처).
        라벨은 표시일 뿐이며 update_status 에서 상태에 맞춰 갱신된다.
        """
        if self.item.status in (DownloadStatus.ERROR, DownloadStatus.CANCELLED):
            self.retry_requested.emit(self.item.item_id)
        else:
            self.cancel_requested.emit(self.item.item_id)

    # ── 외부에서 호출하는 업데이트 메서드 ──

    def update_progress(self, pct: float):
        """
        진행률 바 업데이트.
        다운로드 단계에서는 상태 라벨도 "38.5% 다운로드 중" 형식으로 함께 갱신.
        병합 등 다른 단계에서 들어오는 progress 시그널은 라벨을 덮지 않는다.
        """
        self.progress_bar.setValue(int(pct))

        if self.item.status == DownloadStatus.DOWNLOADING:
            self.lbl_status.setText(f"{pct:.1f}% 다운로드 중")

    def update_speed(self, speed: str):
        """속도 레이블 업데이트"""
        self.lbl_speed.setText(speed)

    def update_eta(self, eta: str):
        """남은 시간 레이블 업데이트"""
        self.lbl_eta.setText(f"남은시간 {eta}")

    def update_status(self, status: DownloadStatus):
        """
        상태 레이블 + 버튼 라벨 업데이트.

        버튼 전환 규약:
        - DONE      : 취소/재시도 숨김, "열기" 노출
        - ERROR     : "재시도" 라벨, 가시
        - CANCELLED : "재시도" 라벨, 가시 (사용자 취소도 재시도 가능)
        - 그 외(WAITING/FETCHING/DOWNLOADING/MERGING) : "취소" 라벨로 복원

        status 라벨의 ERROR 시 빨간색은 활성 상태 (재)진입 시 원복한다.
        """
        # 단일 출처 동기화 — 이후 update_progress 의 가드가 올바로 동작하도록
        self.item.status = status

        self.lbl_status.setText(status.value)
        # 활성 상태로 (재)진입할 때 ERROR 시 적용된 빨간 색을 원복
        self.lbl_status.setStyleSheet("")

        if status == DownloadStatus.DONE:
            # 완료 시 — 취소/재시도 자리 숨기고 "열기" 노출
            self.btn_cancel.setVisible(False)
            self.btn_open.setVisible(True)
            self.progress_bar.setValue(100)
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")

        elif status == DownloadStatus.ERROR:
            # 에러 — 버튼을 "재시도" 라벨로 전환 (숨기지 않음)
            self.btn_cancel.setText("재시도")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)
            self.lbl_status.setStyleSheet("color: #e05555;")
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")

        elif status == DownloadStatus.CANCELLED:
            # 사용자 취소 — 에러와 동일하게 재시도 가능
            self.btn_cancel.setText("재시도")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")

        elif status == DownloadStatus.MERGING:
            # 병합 단계: 상태 자리에 "병합 중" 표기, 속도/ETA 자리는 비움.
            # yt-dlp 의 postprocess 후크는 퍼센트를 제공하지 않으므로 텍스트만.
            self.lbl_status.setText("병합 중")
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")
            # 활성 상태이므로 라벨은 "취소" 로 복원
            self.btn_cancel.setText("취소")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)

        else:
            # WAITING / FETCHING / DOWNLOADING — 활성 상태로 진입.
            # 이전에 ERROR/CANCELLED 였다가 재시도로 돌아온 경우를 위해
            # "취소" 로 라벨 복원 + 열기 버튼 숨김.
            self.btn_cancel.setText("취소")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)

    def update_title(self, title: str):
        """제목 레이블 업데이트"""
        self.lbl_title.setText(title)
        self.item.title = title

    def update_meta(self, uploader: str, duration: int):
        """
        업로더·재생시간 레이블 업데이트.

        위젯 생성 시점에는 InfoWorker 가 아직 끝나지 않아 uploader/duration
        이 빈 값이거나 0 이다. _build_ui 가 박은 초기 "  •  0:00" 라벨을
        InfoWorker 완료 후 이 메서드로 덮어쓴다. update_title 과 같은 패턴
        — 라벨 갱신 + 단일 출처(self.item) 동기화.
        """
        self.item.uploader = uploader
        self.item.duration = duration
        self.lbl_meta.setText(self._format_meta(uploader, duration))

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
