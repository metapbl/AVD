# ui/main_window.py
# 메인 윈도우 - 앱의 핵심 화면

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QMessageBox,
    QStatusBar
)
from PySide6.QtCore import Qt

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
from controllers.playlist_flow import PlaylistFlow


# ── 플레이리스트 URL 판정 ────────────────────────────
# yt-dlp 풀 추출을 돌리기 전에 URL 문자열만으로 플레이리스트 여부를 가른다.
def _is_playlist_url(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    return ("list=" in low) or ("/playlist" in low)


class MainWindow(QMainWindow):
    """AV Downloader 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.config         = ConfigManager()
        self.items          : dict[str, DownloadItem]       = {}
        self.widgets        : dict[str, DownloadItemWidget] = {}
        self.info_workers   : dict[str, InfoWorker]         = {}
        self._thumb_workers : dict[str, ThumbnailWorker]    = {}

        # ── InfoWorker 동시성 게이트 ──
        # 단일 항목 경로와 플레이리스트 경로를 같은 게이트로 통일.
        # max_concurrent 를 한도로 정보 추출을 흘려보낸다.
        self._info_pending : list[str] = []
        self._info_running : set[str]  = set()

        # ── 플레이리스트 사전결정 항목 ──
        # item_id → (format_id, ext). 정보 추출 완료 시 화질 다이얼로그를
        # 건너뛰고 곧장 큐로 보내는 항목들.
        self._predetermined : dict[str, tuple[str, str]] = {}

        # 다운로드 워커 오케스트레이션은 매니저로 위임.
        self.download_manager = DownloadManager(
            config  = self.config,
            items   = self.items,
            widgets = self.widgets,
            parent  = self,
        )
        self.download_manager.item_done.connect(self._on_download_done)
        self.download_manager.item_error.connect(self._on_download_error)
        self.download_manager.item_cancelled.connect(self._on_download_cancelled)

        # ── 플레이리스트 플로우 (단일 인스턴스) ──
        self.playlist_flow = PlaylistFlow(self)
        self.playlist_flow.entry_ready.connect(self._on_playlist_entry)
        self.playlist_flow.status.connect(self._on_playlist_status)
        self.playlist_flow.finished.connect(self._on_playlist_finished)

        self.setWindowTitle("AV Downloader")
        self.setMinimumSize(800, 600)
        self._build_ui()
        self._apply_style()

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

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_list_area(), stretch=1)

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
        """
        URL 입력 완료.

        플레이리스트 URL 이면 PlaylistFlow 에 위임. 단일 영상 URL 이면
        항목·위젯을 만들고 InfoWorker 게이트에 태운다.
        """
        if _is_playlist_url(url):
            if self.playlist_flow.is_busy:
                self.status_bar.showMessage(
                    "이미 플레이리스트를 처리 중입니다. 잠시 후 다시 시도해 주세요."
                )
                return
            self.playlist_flow.start(url)
            return

        # 단일 영상 — 맨 위에 추가(기존 동작).
        self._spawn_item(url, predetermined=None, append=False)

    def _spawn_item(
        self,
        url: str,
        predetermined: tuple[str, str] | None,
        append: bool = False,
    ):
        """
        URL 하나에 대해 DownloadItem·위젯을 만들고 InfoWorker 게이트에 태운다.

        predetermined 가 None 이면 정보 추출 후 화질 다이얼로그를 띄우는 기존
        경로. (format_id, ext) 면 플레이리스트 출신으로 다이얼로그를 건너뛴다.

        append: False 면 맨 위(insertWidget 0), True 면 맨 아래(스트레치 앞).
        items dict 삽입 순서(= 다운로드 큐 순서)는 양쪽 모두 호출 순서를
        따르므로, append 는 화면 표시 위치에만 영향을 준다.
        """
        item = DownloadItem(url=url)
        self.items[item.item_id] = item

        widget = DownloadItemWidget(item, self)
        widget.cancel_requested.connect(self._on_cancel)
        widget.retry_requested.connect(self._on_retry)
        widget.open_requested.connect(self._on_open_folder)
        widget.remove_requested.connect(self._on_remove)
        self.widgets[item.item_id] = widget

        self.lbl_empty.setVisible(False)
        if append:
            self.list_layout.insertWidget(self.list_layout.count() - 1, widget)
        else:
            self.list_layout.insertWidget(0, widget)

        widget.update_status(DownloadStatus.FETCHING)

        if predetermined is not None:
            self._predetermined[item.item_id] = predetermined

        self._enqueue_info(item.item_id)

    # ── InfoWorker 동시성 게이트 ─────────────────────

    def _enqueue_info(self, item_id: str):
        """정보 추출 대기열에 항목을 넣고 디스패치를 깨운다."""
        self._info_pending.append(item_id)
        self._dispatch_info()

    def _dispatch_info(self):
        """대기열의 항목들을 동시성 한도 안에서 InfoWorker 로 출발시킨다."""
        limit = int(self.config.get("max_concurrent", 2))

        while self._info_pending and len(self._info_running) < limit:
            item_id = self._info_pending.pop(0)

            if item_id not in self.items:
                self._predetermined.pop(item_id, None)
                continue

            self._info_running.add(item_id)
            item = self.items[item_id]

            worker = InfoWorker(item.url)
            # "작업 결과" 는 info_ready 로 받는다 (내장 finished 와 다른 이름).
            worker.info_ready.connect(
                lambda info, iid=item_id: self._on_info_fetched(iid, info)
            )
            worker.error.connect(
                lambda err, iid=item_id: self._on_info_error(iid, err)
            )
            # "객체 소멸·dict 정리" 는 QThread 내장 finished 에 건다 — run() 이
            # 진짜로 끝난 시점. 결과 핸들러 안에서 일찍 정리하면 run() 종료 전
            # GC 로 QThread 가 파괴되어 크래시가 난다.
            worker.finished.connect(
                lambda w=worker, iid=item_id: self._on_info_thread_finished(iid, w),
                Qt.ConnectionType.QueuedConnection,
            )
            self.info_workers[item_id] = worker
            worker.start()

    def _release_info_slot(self, item_id: str):
        """
        InfoWorker 한 개의 작업이 끝났을 때 슬롯(running 카운트)을 회수하고
        다음 대기 항목을 깨운다.

        주의: 여기서 워커 객체를 제거하지 않는다. 객체 소멸은 QThread 내장
        finished 에 연결된 _on_info_thread_finished 가 run() 종료 시점에
        한다. 슬롯 회수(작업 결과 시점)와 객체 수명(스레드 종료 시점)을
        분리해 크래시를 막는다.
        """
        self._info_running.discard(item_id)
        self._dispatch_info()

    def _on_info_thread_finished(self, item_id: str, worker):
        """
        InfoWorker 의 QThread 내장 finished — 스레드가 진짜로 종료된 시점.
        이때 객체를 안전하게 소멸시킨다. dict 의 현재 워커가 넘겨받은 worker
        와 동일할 때만 pop (재시도로 새 워커가 붙은 경우 보존).
        """
        current = self.info_workers.get(item_id)
        if current is worker:
            self.info_workers.pop(item_id, None)
        try:
            worker.deleteLater()
        except Exception:
            pass

    def _on_info_fetched(self, item_id: str, info: VideoInfo):
        """영상 정보 추출 완료"""
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            self._predetermined.pop(item_id, None)
            self._release_info_slot(item_id)
            return

        item.title     = info.title
        item.uploader  = info.uploader
        item.duration  = info.duration
        item.thumbnail = info.thumbnail

        widget.update_title(info.title)
        widget.update_meta(info.uploader, info.duration)

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
            thumb_worker.thumb_ready.connect(
                self._on_thumb_ready, Qt.ConnectionType.QueuedConnection
            )
            thumb_worker.failed.connect(
                self._on_thumb_failed, Qt.ConnectionType.QueuedConnection
            )
            # 객체 소멸은 QThread 내장 finished 에 건다.
            thumb_worker.finished.connect(
                lambda w=thumb_worker: self._cleanup_thumb_worker(w),
                Qt.ConnectionType.QueuedConnection,
            )
            self._thumb_workers[item_id] = thumb_worker
            thumb_worker.start()

        # ── 사전결정 항목 (플레이리스트 출신) ──
        predetermined = self._predetermined.pop(item_id, None)
        if predetermined is not None:
            format_id, ext = predetermined
            self._apply_format(item_id, format_id, ext, info)
            self._release_info_slot(item_id)
            return

        # ── 단일 항목 경로 — 화질 선택 다이얼로그 ──
        widget.update_status(DownloadStatus.WAITING)
        self.status_bar.showMessage("화질을 선택해 주세요.")

        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        dialog = FormatSelectDialog(info, self.config, self)
        dialog.format_selected.connect(
            lambda fmt: self._on_format_selected(item_id, fmt)
        )
        dialog.rejected.connect(
            lambda: self._on_remove(item_id, skip_confirm=True)
        )
        # 다이얼로그를 띄우기 전에 슬롯을 회수 — 사용자가 오래 열어둬도 다음
        # 추출이 막히지 않게 한다. (정보 추출은 이미 끝났다.)
        self._release_info_slot(item_id)
        dialog.exec()

    def _apply_format(
        self, item_id: str, format_id: str, ext: str, info: VideoInfo
    ):
        """
        화질/형태가 정해진 항목에 사양을 박고 큐에 진입시킨다.
        사전결정 경로(_on_info_fetched)와 _on_format_selected 의 공통 처리.
        """
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.format_id = format_id
        item.ext       = ext
        item.save_path = self.config.get("save_path", "")
        item.status    = DownloadStatus.WAITING

        widget.update_ext(ext)

        matched = next(
            (f for f in info.formats if f.format_id == format_id), None
        )
        if matched is not None:
            widget.update_format_meta(
                format_id = matched.format_id,
                vcodec    = matched.vcodec,
                acodec    = matched.acodec,
                ext       = matched.ext,
                abr       = matched.abr,
                tbr       = matched.tbr,
                is_audio  = matched.is_audio,
            )
        else:
            widget.update_format_meta(
                format_id = format_id,
                vcodec    = "",
                acodec    = "",
                ext       = ext,
                abr       = 0.0,
                tbr       = 0.0,
                is_audio  = (format_id == "bestaudio/best"),
            )

        widget.update_status(DownloadStatus.WAITING)
        self.status_bar.showMessage(f"대기열에 추가: {item.title}")
        self.download_manager.enqueue(item_id)

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
        """
        썸네일 워커 객체 소멸 — QThread 내장 finished 에 연결되어 호출.
        dict 에서 빼고 deleteLater.
        """
        if not hasattr(self, "_thumb_workers"):
            try:
                worker.deleteLater()
            except Exception:
                pass
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
        """
        영상 정보 추출 실패.

        단일 항목은 에러 다이얼로그 후 정리. 플레이리스트 출신(사전결정)은
        다이얼로그를 N 번 띄우지 않도록 조용히 ERROR 상태로만 둔다.
        """
        was_predetermined = item_id in self._predetermined
        self._predetermined.pop(item_id, None)

        widget = self.widgets.get(item_id)
        if widget:
            widget.update_status(DownloadStatus.ERROR)

        self._release_info_slot(item_id)

        if was_predetermined:
            self.status_bar.showMessage("일부 항목의 정보를 가져오지 못했습니다.")
            return

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

    # ── 플레이리스트 플로우 콜백 ─────────────────────

    def _on_playlist_entry(self, url: str, format_id: str, ext: str):
        """
        PlaylistFlow 가 펼친 항목 하나 — 사전결정 사양과 함께 게이트에 태운다.
        append=True — 원래 순서대로 목록 맨 아래로 차례차례 쌓는다.
        """
        self._spawn_item(url, predetermined=(format_id, ext), append=True)

    def _on_playlist_status(self, message: str):
        """PlaylistFlow 상태 메시지 → 상태바."""
        self.status_bar.showMessage(message)

    def _on_playlist_finished(self):
        """PlaylistFlow 종료 — 항목들은 이미 게이트에 올라갔다."""
        pass

    # ── 다운로드 워커 매니저 위임 진입점 ──────────────

    def _on_format_selected(self, item_id: str, fmt: FormatInfo):
        """화질 선택 완료 (단일 항목 다이얼로그 경로)."""
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.format_id = fmt.format_id
        item.ext       = fmt.ext
        item.save_path = self.config.get("save_path", "")
        item.status    = DownloadStatus.WAITING

        widget.update_ext(fmt.ext)

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

        정보 추출조차 끝나지 않은(제목 기본값) 플레이리스트 항목의 재시도는
        정보 추출부터 다시. 그 외는 같은 format_id 로 다운로드 재시도.
        """
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        never_fetched = (item.duration == 0 and not item.uploader)
        if never_fetched:
            fmt_id = (
                "bestaudio/best" if item.ext == "mp3"
                else "bestvideo+bestaudio/best"
            )
            self._predetermined[item_id] = (fmt_id, item.ext or "mp4")
            widget.update_status(DownloadStatus.FETCHING)
            self.status_bar.showMessage(f"정보 재요청: {item.url}")
            self._enqueue_info(item_id)
            return

        item.status = DownloadStatus.WAITING
        widget.update_status(DownloadStatus.WAITING)
        self.status_bar.showMessage(f"재시도 대기열: {item.title}")

        self.download_manager.retry(item_id)

    def _on_cancel(self, item_id: str):
        """항목 '취소' 버튼 클릭."""
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
        """다운로드 완료 (매니저 시그널)."""
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.status    = DownloadStatus.DONE
        item.save_path = path

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
        """'목록 비우기' 버튼 클릭."""
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

        self.download_manager.cancel_all()

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

        for item_id in list(self.items.keys()):
            self._remove_item_quiet(item_id)

        self.lbl_empty.setVisible(True)
        self.status_bar.showMessage("목록을 비웠습니다.")

    def _remove_item_quiet(self, item_id: str):
        """다이얼로그·확인 없이 항목을 정리하는 내부 헬퍼."""
        # 진행 중 썸네일 워커 무효화 (객체 소멸은 내장 finished 가 처리).
        tw_dict = getattr(self, "_thumb_workers", None)
        if isinstance(tw_dict, dict):
            tw = tw_dict.get(item_id)
            if tw is not None:
                try:
                    tw.cancel()
                except Exception:
                    pass

        # 정보 추출 게이트에서 제거. InfoWorker 객체 소멸은 내장 finished
        # 슬롯이 처리하므로 여기서 강제 종료하지 않는다.
        if item_id in self._info_pending:
            self._info_pending.remove(item_id)
        self._info_running.discard(item_id)
        self._predetermined.pop(item_id, None)

        widget = self.widgets.pop(item_id, None)
        if widget:
            self.list_layout.removeWidget(widget)
            widget.deleteLater()

        self.items.pop(item_id, None)
        self.download_manager.forget(item_id)

        # 게이트 슬롯이 풀렸을 수 있으니 다음 대기 항목을 깨운다.
        self._dispatch_info()

    def _on_open_folder(self, item_id: str):
        """폴더 열기 버튼 클릭"""
        item = self.items.get(item_id)
        if item and item.save_path:
            open_folder(item.save_path)

    def _on_remove(self, item_id: str, skip_confirm: bool = False):
        """항목 ✕ 버튼 클릭."""
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

        if is_active:
            self.download_manager.cancel(item_id)

        if delete_file and is_done_with_file:
            try:
                Path(item.save_path).unlink(missing_ok=True)
            except OSError:
                pass

        self._remove_item_quiet(item_id)

        if not self.widgets:
            self.lbl_empty.setVisible(True)

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
