# controllers/download_manager.py
# 다운로드 워커 오케스트레이션 + 동시성 제어 큐 매니저

from PySide6.QtCore import QObject, Signal, Qt

from models.download_item import DownloadItem, DownloadStatus
from workers.download_worker import DownloadWorker


class DownloadManager(QObject):
    """
    DownloadWorker 들의 라이프사이클과 동시성 한도를 관리한다.

    설계 메모:
    - InfoWorker / ThumbnailWorker 는 항목 라이프사이클(정보 추출·썸네일)에
      묶여 있고 큐 정책과 무관하므로 MainWindow 가 그대로 보유한다.
      매니저는 다운로드 단계(DownloadWorker) 만 책임진다.
    - items / widgets dict 는 MainWindow 가 단일 소유자이고, 매니저는
      읽기·순회 용도로 참조를 받는다.
    - 진행률·속도·ETA·병합 시그널은 워커→위젯을 직접 연결한다.

    워커 수명 관리 (크래시 방지):
    - DownloadWorker 의 "작업 결과" 는 download_finished/error/cancelled 로
      받는다 (QThread 내장 finished 를 가리지 않는 이름).
    - 워커 "객체 소멸·dict 정리" 는 QThread 내장 finished(스레드가 진짜로
      종료된 시점) 에 건다. run() 막바지의 결과 시그널 핸들러 안에서 객체를
      정리하면 run() 종료 전 GC 로 QThread 가 파괴되어 "Destroyed while
      thread is still running" 크래시가 난다. 결과 처리와 객체 수명을 서로
      다른 시그널로 분리하는 것이 핵심.

    공개 API:
        enqueue(item_id)   : 화질 선택이 끝난 항목을 큐에 넣는다
        retry(item_id)     : ERROR / CANCELLED 항목을 큐에 다시 넣는다
        cancel(item_id)    : 단건 취소 시그널을 워커에 송신
        cancel_all()       : 진행 중 워커 일괄 취소
        is_active(item_id) : 해당 항목의 워커가 isRunning() 인지
        active_count()     : 진행 중 워커 수

    매니저가 발사하는 시그널 (라이프사이클만):
        item_done(item_id, path)
        item_error(item_id, message)
        item_cancelled(item_id)
    """

    item_done      = Signal(str, str)
    item_error     = Signal(str, str)
    item_cancelled = Signal(str)

    def __init__(
        self,
        config,
        items   : dict,    # dict[str, DownloadItem]
        widgets : dict,    # dict[str, DownloadItemWidget]
        parent  = None,
    ):
        super().__init__(parent)
        self.config  = config
        self.items   = items
        self.widgets = widgets
        self.dl_workers: dict[str, DownloadWorker] = {}

    # ── 공개 조회 ────────────────────────────────────

    def is_active(self, item_id: str) -> bool:
        """해당 항목의 워커가 실제로 돌고 있는가."""
        w = self.dl_workers.get(item_id)
        return w is not None and w.isRunning()

    def active_count(self) -> int:
        """현재 진행 중인 워커 수."""
        return sum(1 for w in self.dl_workers.values() if w.isRunning())

    # ── 공개 라이프사이클 진입점 ──────────────────────

    def enqueue(self, item_id: str):
        """화질 선택이 끝난 항목을 큐에 진입시킨다."""
        self._dispatch_next()

    def retry(self, item_id: str):
        """ERROR / CANCELLED 항목의 재시도 진입점."""
        # 이전 워커 객체 정리는 내장 finished 슬롯이 이미 했거나, 아직
        # 살아있다면 그쪽이 할 것이다. 여기서는 dict 참조만 떼어낸다.
        self.dl_workers.pop(item_id, None)
        self._dispatch_next()

    def cancel(self, item_id: str):
        """단건 취소 — 워커에 cancel 시그널 송신. 잔여물 정리는 워커가 함."""
        w = self.dl_workers.get(item_id)
        if w is not None and w.isRunning():
            try:
                w.cancel()
            except Exception:
                pass

    def cancel_all(self):
        """진행 중 모든 워커에 취소 시그널 송신."""
        for w in list(self.dl_workers.values()):
            if w.isRunning():
                try:
                    w.cancel()
                except Exception:
                    pass

    def forget(self, item_id: str):
        """
        항목 제거 시 매니저가 보유한 워커 참조도 정리.

        dict 에서만 떼어낸다. 실제 워커 객체의 소멸은 QThread 내장 finished
        슬롯(_on_worker_thread_finished)이 스레드 종료 시점에 deleteLater 로
        처리한다. isRunning() 중인 워커를 강제 종료하지 않는다.
        """
        self.dl_workers.pop(item_id, None)

    # ── 큐 매니저 본체 ───────────────────────────────

    def _dispatch_next(self):
        """동시성 한도 안에서 가능한 만큼 WAITING 항목들을 출발시킨다."""
        limit  = int(self.config.get("max_concurrent", 2))
        active = self.active_count()

        for item_id, item in self.items.items():
            if active >= limit:
                break
            if item.status != DownloadStatus.WAITING:
                continue
            existing = self.dl_workers.get(item_id)
            if existing is not None and existing.isRunning():
                continue
            self._start_worker(item_id)
            active += 1

        self._refresh_waiting_labels()

    def _refresh_waiting_labels(self):
        """WAITING 항목들의 상태 라벨을 '대기 중 (N번째)' 로 다시 그린다."""
        n = 0
        for item_id, item in self.items.items():
            if item.status != DownloadStatus.WAITING:
                continue
            n += 1
            widget = self.widgets.get(item_id)
            if widget is not None:
                widget.update_waiting_position(n)

    def _start_worker(self, item_id: str):
        """실제 DownloadWorker 를 생성·연결·기동한다."""
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        # 이전 워커 dict 참조 정리 (재시도 경로). 객체 소멸은 그 워커의
        # 내장 finished 슬롯이 이미 처리했거나 곧 처리한다.
        self.dl_workers.pop(item_id, None)

        save_dir = self.config.get("save_path", "")
        item.save_path = save_dir

        widget.update_status(DownloadStatus.DOWNLOADING)

        worker = DownloadWorker(
            url       = item.url,
            format_id = item.format_id,
            ext       = item.ext,
            save_dir  = save_dir,
        )
        # 진행률·속도·ETA·크기·병합·코덱정보는 워커→위젯 직접 연결.
        worker.progress.connect(widget.update_progress)
        worker.speed.connect(widget.update_speed)
        worker.eta.connect(widget.update_eta)
        worker.file_size.connect(widget.update_file_size)
        worker.merging.connect(
            lambda: widget.update_status(DownloadStatus.MERGING)
        )
        worker.codec_info_resolved.connect(widget.update_format_meta_resolved)
        # "작업 결과" 는 download_finished/error/cancelled 로 받는다.
        worker.download_finished.connect(
            lambda path, iid=item_id: self._on_worker_finished(iid, path)
        )
        worker.error.connect(
            lambda err, iid=item_id: self._on_worker_error(iid, err)
        )
        worker.cancelled.connect(
            lambda iid=item_id: self._on_worker_cancelled(iid)
        )
        # "객체 소멸·dict 정리" 는 QThread 내장 finished 에 건다 — run() 이
        # 진짜로 끝난 시점. QueuedConnection 으로 두어, 종료 처리가 현재
        # 시그널 스택을 빠져나온 뒤 안전하게 실행되게 한다.
        worker.finished.connect(
            lambda w=worker, iid=item_id: self._on_worker_thread_finished(iid, w),
            Qt.ConnectionType.QueuedConnection,
        )
        self.dl_workers[item_id] = worker
        worker.start()

    # ── 워커 시그널 수신 → 매니저 시그널 재발사 ────────

    def _on_worker_finished(self, item_id: str, path: str):
        """다운로드 작업 결과(완료). 다음 항목 출발."""
        self.item_done.emit(item_id, path)
        self._dispatch_next()

    def _on_worker_error(self, item_id: str, message: str):
        self.item_error.emit(item_id, message)
        self._dispatch_next()

    def _on_worker_cancelled(self, item_id: str):
        self.item_cancelled.emit(item_id)
        self._dispatch_next()

    def _on_worker_thread_finished(self, item_id: str, worker):
        """
        QThread 내장 finished — 스레드가 진짜로 종료된 시점.

        이때 비로소 워커 객체를 안전하게 소멸시킨다. dict 의 현재 워커가
        넘겨받은 worker 와 동일할 때만 pop (재시도로 새 워커가 이미 붙은
        경우 그건 건드리지 않는다).
        """
        current = self.dl_workers.get(item_id)
        if current is worker:
            self.dl_workers.pop(item_id, None)
        try:
            worker.deleteLater()
        except Exception:
            pass
