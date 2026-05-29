# ui/main_window.py
# 메인 윈도우 - 앱의 핵심 화면

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QMessageBox,
    QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from ui.add_link_dialog import AddLinkDialog
from ui.format_select_dialog import FormatSelectDialog
from ui.preferences_dialog import PreferencesDialog
from ui.confirm_remove_dialog import ConfirmRemoveDialog
from workers.info_worker import InfoWorker
from utils.config_manager import ConfigManager
from utils.updater import YtdlpUpdater
from utils.file_utils import open_folder
from core.info_fetcher import VideoInfo, FormatInfo
from workers.thumbnail_worker import ThumbnailWorker
from controllers.download_manager import DownloadManager


class MainWindow(QMainWindow):
    """AV Downloader 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.config         = ConfigManager()
        self.items          : dict[str, DownloadItem]       = {}
        self.widgets        : dict[str, DownloadItemWidget] = {}
        self.info_workers   : dict[str, InfoWorker]         = {}
        self._thumb_workers : dict[str, ThumbnailWorker]    = {}

        # 다운로드 워커 오케스트레이션은 매니저로 위임.
        # items / widgets dict 참조를 공유하므로 MainWindow 가 추가/제거를
        # 가하면 매니저의 dispatch 가 자연스럽게 따라온다.
        self.download_manager = DownloadManager(
            config  = self.config,
            items   = self.items,
            widgets = self.widgets,
            parent  = self,
        )
        self.download_manager.item_done.connect(self._on_download_done)
        self.download_manager.item_error.connect(self._on_download_error)
        self.download_manager.item_cancelled.connect(self._on_download_cancelled)

        self.setWindowTitle("AV Downloader")
        self.setMinimumSize(800, 600)
        self._build_ui()
        self._apply_style()

        # 앱 시작 시 yt-dlp 업데이트 체크
        if self.config.get("auto_update_ytdlp", True):
            self._check_ytdlp_update()

    # ── UI 구성 ──────────────────────────────────────

    def _build_ui(self):
        """전체 UI 구성"""

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 상단 툴바
        root.addWidget(self._build_toolbar())

        # 다운로드 목록 영역
        root.addWidget(self._build_list_area(), stretch=1)

        # 하단 상태바
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("mainStatusBar")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비")

    def _build_toolbar(self) -> QWidget:
        """상단 툴바 구성"""

        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(56)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        lbl_title = QLabel("AV Downloader")
        lbl_title.setObjectName("appTitle")
        layout.addWidget(lbl_title)
        layout.addStretch()

        self.btn_add = QPushButton("+ 링크 추가")
        self.btn_add.setObjectName("btnAdd")
        self.btn_add.setFixedHeight(36)
        self.btn_add.clicked.connect(self._on_add_link)
        layout.addWidget(self.btn_add)

        self.btn_clear_list = QPushButton("목록 비우기")
        self.btn_clear_list.setObjectName("btnClearList")
        self.btn_clear_list.setFixedHeight(36)
        self.btn_clear_list.clicked.connect(self._on_clear_list)
        layout.addWidget(self.btn_clear_list)

        btn_prefs = QPushButton("⚙ 설정")
        btn_prefs.setObjectName("btnPrefs")
        btn_prefs.setFixedHeight(36)
        btn_prefs.clicked.connect(self._on_preferences)
        layout.addWidget(btn_prefs)

        return toolbar

    def _build_list_area(self) -> QScrollArea:
        """다운로드 목록 스크롤 영역 구성"""

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("listScroll")
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(12, 12, 12, 12)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()

        self.lbl_empty = QLabel(
            "다운로드할 링크를 추가하세요\n\n"
            "+ 링크 추가 버튼을 클릭하거나\n"
            "URL을 클립보드에 복사한 후 버튼을 누르세요"
        )
        self.lbl_empty.setObjectName("emptyLabel")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.insertWidget(0, self.lbl_empty)

        scroll.setWidget(container)
        return scroll

    # ── 항목 라이프사이클 ────────────────────────────

    def _on_add_link(self):
        """링크 추가 버튼 클릭"""
        dialog = AddLinkDialog(self)
        dialog.link_submitted.connect(self._on_link_submitted)
        dialog.exec()

    def _on_link_submitted(self, url: str):
        """URL 입력 완료 후 영상 정보 추출 시작"""

        item = DownloadItem(url=url)
        self.items[item.item_id] = item

        widget = DownloadItemWidget(item, self)
        widget.cancel_requested.connect(self._on_cancel)
        widget.retry_requested.connect(self._on_retry)
        widget.open_requested.connect(self._on_open_folder)
        widget.remove_requested.connect(self._on_remove)
        self.widgets[item.item_id] = widget

        self.lbl_empty.setVisible(False)
        self.list_layout.insertWidget(0, widget)

        widget.update_status(DownloadStatus.FETCHING)
        self.status_bar.showMessage(f"영상 정보 가져오는 중... {url}")

        worker = InfoWorker(url)
        worker.finished.connect(
            lambda info: self._on_info_fetched(item.item_id, info)
        )
        worker.error.connect(
            lambda err: self._on_info_error(item.item_id, err)
        )
        self.info_workers[item.item_id] = worker
        worker.start()

    def _on_info_fetched(self, item_id: str, info: VideoInfo):
        """영상 정보 추출 완료"""
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.title     = info.title
        item.uploader  = info.uploader
        item.duration  = info.duration
        item.thumbnail = info.thumbnail

        widget.update_title(info.title)
        widget.update_meta(info.uploader, info.duration)
        widget.update_status(DownloadStatus.WAITING)
        self.status_bar.showMessage("화질을 선택해 주세요.")

        # ── 썸네일 다운로드 ──
        if info.thumbnail:
            if not isinstance(getattr(self, "_thumb_workers", None), dict):
                self._thumb_workers = {}

            prev = self._thumb_workers.pop(item_id, None)
            if prev is not None:
                try:
                    prev.cancel()
                except Exception:
                    pass

            thumb_worker = ThumbnailWorker(item_id, info.thumbnail)
            thumb_worker.finished.connect(
                self._on_thumb_ready, Qt.ConnectionType.QueuedConnection
            )
            thumb_worker.failed.connect(
                self._on_thumb_failed, Qt.ConnectionType.QueuedConnection
            )
            thumb_worker.finished.connect(
                lambda iid, _d, w=thumb_worker: self._cleanup_thumb_worker(w)
            )
            thumb_worker.failed.connect(
                lambda iid, _r, w=thumb_worker: self._cleanup_thumb_worker(w)
            )
            self._thumb_workers[item_id] = thumb_worker
            thumb_worker.start()

        # 다이얼로그 띄우기 직전 paint flush
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        dialog = FormatSelectDialog(info, self.config, self)
        dialog.format_selected.connect(
            lambda fmt: self._on_format_selected(item_id, fmt)
        )
        dialog.rejected.connect(
            lambda: self._on_remove(item_id, skip_confirm=True)
        )
        dialog.exec()

    def _on_thumb_ready(self, item_id: str, data: bytes):
        """썸네일 워커 완료 — GUI 스레드에서 QPixmap 생성하여 위젯에 전달."""
        widget = self.widgets.get(item_id)
        if widget is None:
            return
        try:
            widget.update_thumbnail(data)
        except RuntimeError:
            pass

    def _on_thumb_failed(self, item_id: str, reason: str):
        """썸네일 다운로드 실패 — 라벨은 기본 이모지 유지하고 조용히 무시."""
        pass

    def _cleanup_thumb_worker(self, worker):
        """완료/실패한 썸네일 워커를 dict 에서 제거."""
        if not hasattr(self, "_thumb_workers"):
            return
        for iid, w in list(self._thumb_workers.items()):
            if w is worker:
                self._thumb_workers.pop(iid, None)
                break
        try:
            worker.deleteLater()
        except Exception:
            pass

    def _on_info_error(self, item_id: str, err: str):
        """영상 정보 추출 실패"""
        widget = self.widgets.get(item_id)
        if widget:
            widget.update_status(DownloadStatus.ERROR)

        dialog = QMessageBox(self)
        dialog.setWindowTitle("오류")
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setText("영상 정보를 가져오지 못했습니다.")
        dialog.setDetailedText(err)
        dialog.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dialog.exec()
        self._on_remove(item_id, skip_confirm=True)

    # ── 다운로드 워커 매니저 위임 진입점 ──────────────

    def _on_format_selected(self, item_id: str, fmt: FormatInfo):
        """
        화질 선택 완료.

        사양(format_id / ext / save_path)을 항목에 박고 상태를 WAITING 으로
        둔 다음 매니저에 큐 진입을 위임. 실제 출발 여부는 매니저의
        _dispatch_next 가 슬롯 여유를 보고 결정한다.
        """
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.format_id = fmt.format_id
        item.ext       = fmt.ext
        item.save_path = self.config.get("save_path", "")
        item.status    = DownloadStatus.WAITING

        # 제목 라벨 우측에 ".ext" 표시 — 확장자가 확정된 이 시점에 알린다.
        widget.update_ext(fmt.ext)

        # 메타 라벨에 코덱·포맷·비트레이트 세그먼트 추가.
        # 통합 포맷(format_id == AUTO_FORMAT_ID) 은 위젯 측에서 "자동" 으로 표시.
        widget.update_format_meta(
            format_id = fmt.format_id,
            vcodec    = fmt.vcodec,
            acodec    = fmt.acodec,
            ext       = fmt.ext,
            abr       = fmt.abr,
            tbr       = fmt.tbr,
            is_audio  = fmt.is_audio,
        )

        widget.update_status(DownloadStatus.WAITING)
        self.status_bar.showMessage(f"대기열에 추가: {item.title}")

        self.download_manager.enqueue(item_id)

    def _on_retry(self, item_id: str):
        """
        재시도 버튼 클릭.

        ERROR / CANCELLED 상태의 항목을 같은 format_id / ext / save_dir 로
        다시 다운로드한다. 화질 다이얼로그는 다시 띄우지 않는다.

        정책 A: 재시도도 동시성 한도를 준수. 매니저가 슬롯 여유에 따라
        즉시 출발시키거나 잠시 WAITING 으로 둔다.
        """
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.status = DownloadStatus.WAITING
        widget.update_status(DownloadStatus.WAITING)
        self.status_bar.showMessage(f"재시도 대기열: {item.title}")

        self.download_manager.retry(item_id)

    def _on_cancel(self, item_id: str):
        """
        항목 "취소" 버튼 클릭.

        진행 중인 워커가 있을 때만 확인 다이얼로그를 띄우고 취소한다.
        WAITING 항목은 update_status 가 취소 버튼을 숨겨두므로 여기 도달
        하지 않는다.
        """
        if not self.download_manager.is_active(item_id):
            return

        reply = QMessageBox.question(
            self,
            "다운로드 취소",
            "이 다운로드를 취소하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.download_manager.cancel(item_id)

    # ── 매니저 시그널 핸들러 ─────────────────────────

    def _on_download_done(self, item_id: str, path: str):
        """
        다운로드 완료 (매니저 시그널).

        path 는 디스크에 최종 떨어진 파일 경로. yt-dlp 의 후처리(예: 비디오
        트랙 없는 m4a 자동 리네이밍) 로 인해 사용자가 화질 다이얼로그에서
        고른 ext 와 실제 파일 ext 가 다를 수 있다. 이 시점에 path 의 실제
        suffix 로 위젯·항목의 ext 를 정정해 라벨이 진실을 따라가게 한다.
        """
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.status    = DownloadStatus.DONE
        item.save_path = path

        # 실제 파일 확장자 동기화 — Path.suffix 는 ".m4a" 처럼 점 포함.
        # update_ext 가 lstrip(".") 으로 정규화하므로 그대로 넘긴다.
        # 빈 경로/빈 suffix 경계도 update_ext 측이 _ext_known=False 로 처리.
        actual_ext = Path(path).suffix.lstrip(".") if path else ""
        if actual_ext:
            item.ext = actual_ext
            widget.update_ext(actual_ext)

        widget.update_status(DownloadStatus.DONE)
        self.status_bar.showMessage(f"완료: {item.title}")

    def _on_download_error(self, item_id: str, err: str):
        """다운로드 오류 (매니저 시그널)"""
        widget = self.widgets.get(item_id)
        if widget:
            widget.update_status(DownloadStatus.ERROR)

        dialog = QMessageBox(self)
        dialog.setWindowTitle("다운로드 오류")
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setText("다운로드 중 오류가 발생했습니다.")
        dialog.setDetailedText(err)
        dialog.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dialog.exec()

    def _on_download_cancelled(self, item_id: str):
        """다운로드 취소 완료 (매니저 시그널)"""
        widget = self.widgets.get(item_id)
        if widget:
            widget.update_status(DownloadStatus.CANCELLED)
        self.status_bar.showMessage("취소됨")

    # ── 항목 제거 ────────────────────────────────────

    def _on_clear_list(self):
        """
        "목록 비우기" 버튼 클릭.

        - 진행 중 워커는 매니저에 일괄 취소 요청
        - 모든 항목을 목록에서 제거
        - 사용자가 "다운로드된 파일들 일괄 삭제" 체크 시, 완료 항목의
          디스크 파일도 모두 삭제
        """
        if not self.items:
            self.status_bar.showMessage("목록이 비어 있습니다.")
            return

        active_count = self.download_manager.active_count()
        done_with_file_count = sum(
            1 for it in self.items.values()
            if it.status == DownloadStatus.DONE
            and it.save_path
            and Path(it.save_path).is_file()
        )

        message = "목록의 모든 항목을 제거하시겠습니까?"
        if active_count > 0:
            message += f"\n\n진행 중인 다운로드 {active_count}개는 취소됩니다."

        checkbox_text = (
            "다운로드된 파일들 일괄 삭제"
            if done_with_file_count > 0
            else None
        )

        dlg = ConfirmRemoveDialog(
            self,
            title         = "목록 비우기",
            message       = message,
            checkbox_text = checkbox_text,
        )
        dlg.exec()
        if not dlg.confirmed:
            return

        # 1) 진행 중 워커 일괄 취소
        self.download_manager.cancel_all()

        # 2) (체크 시) 완료 항목의 디스크 파일 삭제
        if dlg.delete_disk_files:
            for it in list(self.items.values()):
                if (
                    it.status == DownloadStatus.DONE
                    and it.save_path
                    and Path(it.save_path).is_file()
                ):
                    try:
                        Path(it.save_path).unlink(missing_ok=True)
                    except OSError:
                        pass

        # 3) 모든 항목 위젯 제거
        for item_id in list(self.items.keys()):
            self._remove_item_quiet(item_id)

        self.lbl_empty.setVisible(True)
        self.status_bar.showMessage("목록을 비웠습니다.")

    def _remove_item_quiet(self, item_id: str):
        """
        다이얼로그·확인 없이 항목을 정리하는 내부 헬퍼.

        _on_clear_list 의 일괄 처리와 _on_remove 의 단건 처리가 같은 정리
        루틴을 공유한다.
        """
        # 진행 중 썸네일 워커 무효화
        tw_dict = getattr(self, "_thumb_workers", None)
        if isinstance(tw_dict, dict):
            tw = tw_dict.pop(item_id, None)
            if tw is not None:
                try:
                    tw.cancel()
                except Exception:
                    pass

        widget = self.widgets.pop(item_id, None)
        if widget:
            self.list_layout.removeWidget(widget)
            widget.deleteLater()

        self.items.pop(item_id, None)
        self.info_workers.pop(item_id, None)
        # 다운로드 워커 참조는 매니저가 보유 — 매니저에 위임해 정리.
        # 진행 중이었다면 그 위 단계에서 cancel 이 호출되어 있고, cancelled
        # 시그널은 _on_download_cancelled 로 들어와 위젯이 이미 없는 상태를
        # 만나면 조용히 무시되도록 가드되어 있다.
        self.download_manager.forget(item_id)

    def _on_open_folder(self, item_id: str):
        """폴더 열기 버튼 클릭"""
        item = self.items.get(item_id)
        if item and item.save_path:
            open_folder(item.save_path)

    def _on_remove(self, item_id: str, skip_confirm: bool = False):
        """
        항목 ✕ 버튼 클릭.

        분기 (상태별):
        - 진행 중 (DOWNLOADING / MERGING / FETCHING):
            "진행 중인 다운로드를 취소하고 목록에서 제거하시겠습니까?"
        - 완료(DONE) + 디스크 파일 존재:
            "이 항목을 목록에서 제거하시겠습니까?" + "다운로드된 파일 삭제" 체크
        - 그 외 (WAITING / ERROR / CANCELLED / DONE 인데 파일 없음):
            "이 항목을 목록에서 제거하시겠습니까?"

        WAITING 항목 제거 시 뒤쪽 WAITING 들의 순번이 한 칸씩 당겨진다 —
        _remove_item_quiet 가 매니저의 forget 을 호출하지만 dispatch 까지는
        부르지 않으므로, 여기서 명시적으로 한 번 더 dispatch 를 깨워야
        순번 라벨이 즉시 갱신된다.

        skip_confirm=True 는 시스템 경로(InfoWorker 에러, FormatSelectDialog
        rejected)에서 자동 정리 시 사용.
        """
        item = self.items.get(item_id)
        if item is None:
            return

        is_active = self.download_manager.is_active(item_id)

        is_done_with_file = (
            item.status == DownloadStatus.DONE
            and bool(item.save_path)
            and Path(item.save_path).is_file()
        )

        delete_file = False
        if not skip_confirm:
            if is_active:
                message       = (
                    "진행 중인 다운로드를 취소하고 목록에서 제거하시겠습니까?"
                )
                checkbox_text = None
            elif is_done_with_file:
                message       = "이 항목을 목록에서 제거하시겠습니까?"
                checkbox_text = "다운로드된 파일 삭제"
            else:
                message       = "이 항목을 목록에서 제거하시겠습니까?"
                checkbox_text = None

            dlg = ConfirmRemoveDialog(
                self,
                title         = "항목 제거",
                message       = message,
                checkbox_text = checkbox_text,
            )
            dlg.exec()
            if not dlg.confirmed:
                return
            delete_file = dlg.delete_disk_files

        # 활성 워커가 있으면 매니저에 취소 위임
        if is_active:
            self.download_manager.cancel(item_id)

        # 디스크 파일 삭제 (위젯 제거 전)
        if delete_file and is_done_with_file:
            try:
                Path(item.save_path).unlink(missing_ok=True)
            except OSError:
                pass

        # 위젯·dict 정리
        self._remove_item_quiet(item_id)

        if not self.widgets:
            self.lbl_empty.setVisible(True)

        # WAITING 항목 제거 시 뒤쪽 WAITING 들의 순번이 한 칸씩 당겨진다.
        # 활성 항목 ✕ 경로는 매니저의 cancelled 콜백이 dispatch 를 부르므로
        # 거기서도 라벨이 갱신되지만, WAITING / 완료 / 에러 항목의 ✕ 경로는
        # 콜백을 거치지 않으므로 매니저의 enqueue 를 한 번 깨워 dispatch
        # (no-op + label refresh) 를 강제한다.
        self.download_manager.enqueue(item_id)

    def _on_preferences(self):
        """환경설정 버튼 클릭"""
        dialog = PreferencesDialog(self.config, self)
        dialog.exec()

    def _check_ytdlp_update(self):
        """앱 시작 시 yt-dlp 업데이트 체크"""
        from PySide6.QtCore import QTimer

        def check():
            updater = YtdlpUpdater()
            needed, current, latest = updater.is_update_available()
            if needed:
                reply = QMessageBox.question(
                    self,
                    "yt-dlp 업데이트",
                    f"yt-dlp 새 버전이 있습니다.\n\n"
                    f"현재: {current}\n"
                    f"최신: {latest}\n\n"
                    f"지금 업데이트 하시겠습니까?",
                )
                if reply == QMessageBox.StandardButton.Yes:
                    success = updater.update()
                    if success:
                        QMessageBox.information(
                            self, "완료",
                            "yt-dlp가 최신 버전으로 업데이트됐습니다."
                        )
                    else:
                        QMessageBox.warning(
                            self, "실패",
                            "업데이트에 실패했습니다.\n"
                            "수동으로 pip install --upgrade yt-dlp 를 실행해 주세요."
                        )

        QTimer.singleShot(3000, check)

    # ── 스타일 ───────────────────────────────────────

    def _apply_style(self):
        """전체 앱 스타일 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background: #1e1e1e;
            }
            QWidget#toolbar {
                background: #2b2b2b;
                border-bottom: 1px solid #3a3a3a;
            }
            QLabel#appTitle {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#btnAdd {
                background: #4a90d9;
                color: #ffffff;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnAdd:hover { background: #5aa0e9; }
            QPushButton#btnClearList {
                background: #555;
                color: #ccc;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
            }
            QPushButton#btnClearList:hover { background: #e05555; color: #fff; }
            QPushButton#btnPrefs {
                background: #444;
                color: #ccc;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
            }
            QPushButton#btnPrefs:hover { background: #555; }
            QScrollArea#listScroll {
                background: #1e1e1e;
                border: none;
            }
            QLabel#emptyLabel {
                color: #555555;
                font-size: 14px;
                line-height: 1.8;
            }
            QStatusBar#mainStatusBar {
                background: #2b2b2b;
                color: #888888;
                font-size: 11px;
            }
        """)
