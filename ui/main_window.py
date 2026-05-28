# ui/main_window.py
# 메인 윈도우 - 앱의 핵심 화면

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QMessageBox,
    QStatusBar
)
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QPixmap, QDesktopServices

from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from ui.add_link_dialog import AddLinkDialog
from ui.format_select_dialog import FormatSelectDialog
from ui.preferences_dialog import PreferencesDialog
from ui.confirm_remove_dialog import ConfirmRemoveDialog
from workers.info_worker import InfoWorker
from workers.download_worker import DownloadWorker
from utils.config_manager import ConfigManager
from utils.updater import YtdlpUpdater
from utils.file_utils import open_folder
from core.info_fetcher import VideoInfo, FormatInfo
from workers.thumbnail_worker import ThumbnailWorker

class MainWindow(QMainWindow):
    """AV Downloader 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.config         = ConfigManager()
        self.items          : dict[str, DownloadItem]       = {}
        self.widgets        : dict[str, DownloadItemWidget] = {}
        self.info_workers   : dict[str, InfoWorker]         = {}
        self.dl_workers     : dict[str, DownloadWorker]     = {}
        self._thumb_workers: dict[str, ThumbnailWorker] = {}
        
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

        # 앱 타이틀
        lbl_title = QLabel("AV Downloader")
        lbl_title.setObjectName("appTitle")
        layout.addWidget(lbl_title)
        layout.addStretch()

        # 링크 추가 버튼
        self.btn_add = QPushButton("+ 링크 추가")
        self.btn_add.setObjectName("btnAdd")
        self.btn_add.setFixedHeight(36)
        self.btn_add.clicked.connect(self._on_add_link)
        layout.addWidget(self.btn_add)

        # 목록 비우기 버튼 (구 "전체 취소").
        # 동작 재정의: 진행 중인 워커는 취소하고, 모든 항목을 목록에서 제거.
        # 체크박스로 "다운로드된 파일들 일괄 삭제" 옵션 노출 (기본 해제).
        self.btn_clear_list = QPushButton("목록 비우기")
        self.btn_clear_list.setObjectName("btnClearList")
        self.btn_clear_list.setFixedHeight(36)
        self.btn_clear_list.clicked.connect(self._on_clear_list)
        layout.addWidget(self.btn_clear_list)

        # 환경설정 버튼
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

        # 빈 화면 안내 레이블
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

    # ── 이벤트 핸들러 ────────────────────────────────

    def _on_add_link(self):
        """링크 추가 버튼 클릭"""
        dialog = AddLinkDialog(self)
        dialog.link_submitted.connect(self._on_link_submitted)
        dialog.exec()

    def _on_link_submitted(self, url: str):
        """URL 입력 완료 후 영상 정보 추출 시작"""

        # DownloadItem 생성
        item = DownloadItem(url=url)
        self.items[item.item_id] = item

        # 위젯 생성 후 목록에 추가
        widget = DownloadItemWidget(item, self)
        widget.cancel_requested.connect(self._on_cancel)
        widget.retry_requested.connect(self._on_retry)
        widget.open_requested.connect(self._on_open_folder)
        widget.remove_requested.connect(self._on_remove)
        self.widgets[item.item_id] = widget

        # 빈 화면 레이블 숨기기
        self.lbl_empty.setVisible(False)

        # 목록 맨 위에 삽입
        self.list_layout.insertWidget(0, widget)

        # 상태 업데이트
        widget.update_status(DownloadStatus.FETCHING)
        self.status_bar.showMessage(f"영상 정보 가져오는 중... {url}")

        # 영상 정보 추출 워커 시작
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

        # 아이템 정보 업데이트
        item.title     = info.title
        item.uploader  = info.uploader
        item.duration  = info.duration
        item.thumbnail = info.thumbnail

        widget.update_title(info.title)
        widget.update_meta(info.uploader, info.duration)
        widget.update_status(DownloadStatus.WAITING)
        self.status_bar.showMessage("화질을 선택해 주세요.")

        # ── 썸네일 다운로드 ──
        # v7: QPixmap 이 아닌 bytes 를 받는 워커로 교체.
        #     item_id 동봉 + dict 로 관리 (늦은 시그널 차단).
        if info.thumbnail:
            from workers.thumbnail_worker import ThumbnailWorker
            # 타입 보장 — 과거 버전이 list 로 초기화해뒀던 경우까지 방어
            if not isinstance(getattr(self, "_thumb_workers", None), dict):
                self._thumb_workers = {}

            # 같은 item_id 의 이전 워커가 남아있으면 무효화
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
            # 워커 종료 시 자동 정리
            thumb_worker.finished.connect(
                lambda iid, _d, w=thumb_worker: self._cleanup_thumb_worker(w)
            )
            thumb_worker.failed.connect(
                lambda iid, _r, w=thumb_worker: self._cleanup_thumb_worker(w)
            )
            self._thumb_workers[item_id] = thumb_worker
            thumb_worker.start()

        # 다이얼로그 띄우기 직전 — 위젯 트리가 paint-ready 가 되도록 한 번 flush.
        # 이게 없으면 modal 이벤트 루프가 paint 를 한 번 건너뛰는 경계 케이스 발생.
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        # 화질 선택 다이얼로그 표시
        dialog = FormatSelectDialog(info, self.config, self)
        dialog.format_selected.connect(
            lambda fmt: self._on_format_selected(item_id, fmt)
        )
        dialog.rejected.connect(
            lambda: self._on_remove(item_id, skip_confirm=True)
        )
        dialog.exec()

    def _on_thumb_ready(self, item_id: str, data: bytes):
        """
        썸네일 워커 완료 — GUI 스레드에서 QPixmap 생성하여 위젯에 전달.
        v7 신규: bytes → 위젯 내부에서 QPixmap 변환.
        """
        widget = self.widgets.get(item_id)
        if widget is None:
            # 사용자가 이미 항목을 지운 경우 — 무시
            return
        try:
            widget.update_thumbnail(data)
        except RuntimeError:
            # 위젯이 파괴된 경우
            pass

    def _on_thumb_failed(self, item_id: str, reason: str):
        """썸네일 다운로드 실패 — 라벨은 기본 이모지 유지하고 조용히 무시."""
        # 필요 시 status_bar 로깅:
        # self.status_bar.showMessage(f"썸네일 로드 실패: {reason}", 3000)
        pass

    def _cleanup_thumb_worker(self, worker):
        """완료/실패한 썸네일 워커를 dict 에서 제거."""
        if not hasattr(self, "_thumb_workers"):
            return
        # 값으로 찾아 제거
        for iid, w in list(self._thumb_workers.items()):
            if w is worker:
                self._thumb_workers.pop(iid, None)
                break
        # QThread 정리 — finished 이후엔 안전하게 deleteLater
        try:
            worker.deleteLater()
        except Exception:
            pass

    def _on_info_error(self, item_id: str, err: str):
        """영상 정보 추출 실패"""
        widget = self.widgets.get(item_id)
        if widget:
            widget.update_status(DownloadStatus.ERROR)

        # 복사 가능한 오류 다이얼로그
        dialog = QMessageBox(self)
        dialog.setWindowTitle("오류")
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setText("영상 정보를 가져오지 못했습니다.")
        dialog.setDetailedText(err)   # ← 펼치면 전체 오류 텍스트 표시
        dialog.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dialog.exec()
        # 시스템 경로로 도달한 자동 정리 — 사용자의 ✕ 클릭이 아니므로 확인 생략
        self._on_remove(item_id, skip_confirm=True)

    def _on_format_selected(self, item_id: str, fmt: FormatInfo):
        """화질 선택 완료 후 다운로드 시작"""
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.format_id = fmt.format_id
        item.ext       = fmt.ext
        item.save_path = self.config.get("save_path", "")

        widget.update_status(DownloadStatus.DOWNLOADING)
        self.status_bar.showMessage(f"다운로드 중: {item.title}")

        # 다운로드 워커 시작
        worker = DownloadWorker(
            url       = item.url,
            format_id = item.format_id,
            ext       = item.ext,
            save_dir  = item.save_path,
        )
        worker.progress.connect(widget.update_progress)
        worker.speed.connect(widget.update_speed)
        worker.eta.connect(widget.update_eta)
        worker.merging.connect(
            lambda: widget.update_status(DownloadStatus.MERGING)
        )
        worker.finished.connect(
            lambda path: self._on_download_done(item_id, path)
        )
        worker.error.connect(
            lambda err: self._on_download_error(item_id, err)
        )
        worker.cancelled.connect(
            lambda: self._on_download_cancelled(item_id)
        )
        self.dl_workers[item_id] = worker
        worker.start()

    def _on_download_done(self, item_id: str, path: str):
        """다운로드 완료"""
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        item.status    = DownloadStatus.DONE
        item.save_path = path
        widget.update_status(DownloadStatus.DONE)
        self.status_bar.showMessage(f"완료: {item.title}")

    def _on_download_error(self, item_id: str, err: str):
        """다운로드 오류"""
        widget = self.widgets.get(item_id)
        if widget:
            widget.update_status(DownloadStatus.ERROR)

        dialog = QMessageBox(self)
        dialog.setWindowTitle("다운로드 오류")
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setText("다운로드 중 오류가 발생했습니다.")
        dialog.setDetailedText(err)   # ← 펼치면 전체 오류 텍스트 표시
        dialog.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dialog.exec()

    def _on_download_cancelled(self, item_id: str):
        """다운로드 취소 완료"""
        widget = self.widgets.get(item_id)
        if widget:
            widget.update_status(DownloadStatus.CANCELLED)
        self.status_bar.showMessage("취소됨")

    def _on_cancel(self, item_id: str):
        """
        항목 "취소" 버튼 클릭.

        진행 중인 워커가 있을 때만 확인 다이얼로그를 띄우고 취소한다.
        진행 중이 아닌 경우(이미 끝났거나 에러 상태)는 도달하지 말아야 할
        경로지만(버튼이 "재시도" 라벨이 됐을 테니), 방어적으로 무시한다.
        """
        worker = self.dl_workers.get(item_id)
        if worker is None or not worker.isRunning():
            return

        reply = QMessageBox.question(
            self,
            "다운로드 취소",
            "이 다운로드를 취소하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,   # 기본값 No — 실수 방지
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        worker.cancel()

    def _on_retry(self, item_id: str):
        """
        재시도 버튼 클릭.

        ERROR / CANCELLED 상태의 항목을 같은 format_id / ext / save_dir 로
        다시 다운로드한다. 화질 다이얼로그는 다시 띄우지 않는다 — 사용자가
        한 번 고른 사양을 그대로. 잔여물(.part / .ytdl) 은 이전 워커가
        취소/에러 종료 시점에 _cleanup_residue 로 이미 정리했으므로 yt-dlp 는
        깨끗한 상태에서 처음부터 받는다.
        """
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        # 이전 워커 참조 정리 — isRunning() 은 False 일 것이지만 명시적 pop
        prev = self.dl_workers.pop(item_id, None)
        if prev is not None:
            try:
                prev.deleteLater()
            except Exception:
                pass

        # save_path 는 다운로드 완료 시점에 파일 경로로 덮어쓰일 수 있다.
        # 재시도에서는 저장 디렉터리가 필요하므로 config 의 최신 값을 다시 읽는다
        # (사용자가 환경설정에서 폴더를 바꿨을 가능성도 흡수).
        save_dir = self.config.get("save_path", "")
        item.save_path = save_dir

        widget.update_status(DownloadStatus.DOWNLOADING)
        self.status_bar.showMessage(f"재시도 중: {item.title}")

        worker = DownloadWorker(
            url       = item.url,
            format_id = item.format_id,
            ext       = item.ext,
            save_dir  = save_dir,
        )
        worker.progress.connect(widget.update_progress)
        worker.speed.connect(widget.update_speed)
        worker.eta.connect(widget.update_eta)
        worker.merging.connect(
            lambda: widget.update_status(DownloadStatus.MERGING)
        )
        worker.finished.connect(
            lambda path: self._on_download_done(item_id, path)
        )
        worker.error.connect(
            lambda err: self._on_download_error(item_id, err)
        )
        worker.cancelled.connect(
            lambda: self._on_download_cancelled(item_id)
        )
        self.dl_workers[item_id] = worker
        worker.start()

    def _on_clear_list(self):
        """
        "목록 비우기" 버튼 클릭 (구 "전체 취소").

        동작:
        - 진행 중 워커는 모두 취소 시그널 송신
        - 모든 항목을 목록에서 제거
        - 사용자가 "다운로드된 파일들 일괄 삭제" 체크 시, 완료된 항목의
          디스크 파일도 모두 삭제

        다이얼로그는 ConfirmRemoveDialog 한 종류로 통일. 본문에 진행 중
        개수 M 을 명시하고, 완료 파일이 1개 이상일 때만 체크박스 노출.
        """
        if not self.items:
            self.status_bar.showMessage("목록이 비어 있습니다.")
            return

        # 통계 — 본문/체크박스 노출 결정용
        active_count = sum(
            1 for w in self.dl_workers.values() if w.isRunning()
        )
        done_with_file_count = sum(
            1 for it in self.items.values()
            if it.status == DownloadStatus.DONE
            and it.save_path
            and Path(it.save_path).is_file()
        )

        # 본문 구성 — 진행 중 항목이 있을 때만 그 줄을 덧붙임
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

        # 1) 진행 중 워커 일괄 취소 — 워커가 자식 프로세스·잔여물 정리
        for worker in list(self.dl_workers.values()):
            if worker.isRunning():
                try:
                    worker.cancel()
                except Exception:
                    pass

        # 2) (체크 시) 완료된 항목의 디스크 파일 삭제 — 항목 dict 비우기 전에
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
                        # 권한 / 잠금 — 조용히 통과
                        pass

        # 3) 모든 항목 위젯 제거
        for item_id in list(self.items.keys()):
            self._remove_item_quiet(item_id)

        # 4) 빈 화면 표시
        self.lbl_empty.setVisible(True)
        self.status_bar.showMessage("목록을 비웠습니다.")

    def _remove_item_quiet(self, item_id: str):
        """
        다이얼로그·확인 없이 항목을 정리하는 내부 헬퍼.

        _on_clear_list 의 일괄 처리와 _on_remove 의 단건 처리가 같은 정리
        루틴을 공유한다. _on_remove 가 자체 다이얼로그를 띄운 뒤, 실제
        정리는 이 함수로 위임한다.
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
        self.dl_workers.pop(item_id, None)

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
            (체크박스 없음 — 산출물이 아직 없으므로)
        - 완료(DONE) + 디스크 파일 존재:
            "이 항목을 목록에서 제거하시겠습니까?"
            + 체크박스 "다운로드된 파일 삭제" (기본 해제)
        - 그 외 (DONE 인데 파일 없음, ERROR, CANCELLED, WAITING):
            "이 항목을 목록에서 제거하시겠습니까?"
            (체크박스 없음)

        skip_confirm=True 는 시스템 경로(InfoWorker 에러, FormatSelectDialog
        rejected)에서 자동 정리 시 사용 — 사용자의 ✕ 클릭이 아니므로 다이얼로그
        를 건너뛰고 바로 정리한다.
        """
        item = self.items.get(item_id)
        if item is None:
            return

        # 통계 — 분기 결정용
        worker = self.dl_workers.get(item_id)
        is_active = worker is not None and worker.isRunning()

        is_done_with_file = (
            item.status == DownloadStatus.DONE
            and bool(item.save_path)
            and Path(item.save_path).is_file()
        )

        # 다이얼로그 분기
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

        # 활성 워커가 있으면 취소 — 잔여물 정리는 워커가 함
        if is_active:
            try:
                worker.cancel()
            except Exception:
                pass

        # 디스크 파일 삭제 (위젯 제거 전)
        if delete_file and is_done_with_file:
            try:
                Path(item.save_path).unlink(missing_ok=True)
            except OSError:
                # 권한 / 잠금 — 조용히 통과
                pass

        # 위젯·dict 정리
        self._remove_item_quiet(item_id)

        # 목록이 비면 빈 화면 레이블 표시
        if not self.widgets:
            self.lbl_empty.setVisible(True)

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

        # 앱 완전히 뜬 후 3초 뒤에 체크 (시작 속도 영향 최소화)
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
