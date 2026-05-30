# controllers/download_manager.py
# 다운로드 워커 오케스트레이션 + 동시성 제어 큐 매니저

from PySide6.QtCore import QObject, Signal

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
      읽기·순회 용도로 참조를 받는다. ItemRegistry 같은 추상을 더 만들지
      않은 것은 이 규모에 과설계라고 판단했기 때문.
    - 진행률·속도·ETA·병합 시그널은 워커→위젯을 직접 연결한다. 매니저가
      중계하면 N 배 시그널이 늘어나는 비용 대비 얻을 게 없다. 매니저는
      "출발·종료" 같은 라이프사이클 이벤트만 다룬다.

    공개 API:
        enqueue(item_id)   : 화질 선택이 끝난 항목을 큐에 넣는다 (즉시 또는 대기)
        retry(item_id)     : ERROR / CANCELLED 항목을 큐에 다시 넣는다 (정책 A)
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
        """
        화질 선택이 끝난 항목을 큐에 진입시킨다.

        항목의 status 는 호출 시점에 이미 WAITING 으로 설정되어 있어야 한다
        (MainWindow._on_format_selected 의 책임). 매니저는 슬롯 여유를 보고
        실제 출발 여부를 결정한다.
        """
        self._dispatch_next()

    def retry(self, item_id: str):
        """
        ERROR / CANCELLED 항목의 재시도 진입점.

        정책 A: 재시도도 동시성 한도를 준수한다. 슬롯이 비어 있으면
        _dispatch_next 가 즉시 출발시키고, 슬롯이 꽉 차 있으면 잠시
        WAITING 으로 떨어졌다가 자기 차례를 기다린다.

        호출 측(MainWindow._on_retry)이 item.status 를 WAITING 으로
        전이시키고 widget.update_status(WAITING) 까지 호출한 뒤에 매니저로
        들어와야 한다. 매니저는 이전 워커 참조만 정리하고 dispatch.
        """
        prev = self.dl_workers.pop(item_id, None)
        if prev is not None:
            try:
                prev.deleteLater()
            except Exception:
                pass
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

        MainWindow._remove_item_quiet 에서 호출. 진행 중 워커의 cancel 은
        그 전에 별도로 호출되어 있어야 한다 (cancel 시그널을 받은 워커가
        자식·잔여물 정리를 수행한 뒤 cancelled 시그널을 emit 하므로,
        여기서 deleteLater 까지 가지는 않는다 — 자연 종료를 기다린다).
        """
        # dict 에서만 떼어낸다. 실제 워커 객체의 정리는 Qt 의 GC + 워커
        # 자체의 종료 흐름에 맡긴다. isRunning() 중인 워커를 강제 종료하지
        # 않는다 (cancel 흐름이 자식·잔여물 정리를 보장하는 정상 경로).
        self.dl_workers.pop(item_id, None)

    # ── 큐 매니저 본체 ───────────────────────────────

    def _dispatch_next(self):
        """
        동시성 한도 안에서 가능한 만큼 WAITING 항목들을 출발시킨다.

        삽입 순서(self.items 의 dict 순서) 가 큐 순서. 별도 큐 자료구조를
        두지 않는다 — status == WAITING 인 것이 곧 대기열.

        한 번 호출에 빈 슬롯만큼 반복 출발. 슬라이더를 6 으로 키워둔 채
        8 개를 한꺼번에 추가한 경우 한 번의 dispatch 로 6 개가 출발한다.
        """
        limit  = int(self.config.get("max_concurrent", 2))
        active = self.active_count()

        for item_id, item in self.items.items():
            if active >= limit:
                break
            if item.status != DownloadStatus.WAITING:
                continue
            # 이미 워커가 붙어 있는 WAITING (모순 상태) 방어
            existing = self.dl_workers.get(item_id)
            if existing is not None and existing.isRunning():
                continue
            self._start_worker(item_id)
            active += 1

        # 출발 못 한 WAITING 들의 순번 라벨 갱신
        self._refresh_waiting_labels()

    def _refresh_waiting_labels(self):
        """
        WAITING 항목들의 상태 라벨을 "대기 중 (N번째)" 로 다시 그린다.

        N 은 WAITING 항목들 사이의 순번 — 진행 중 항목은 카운트하지 않음 (정책 P).
        dispatch 직후 호출되어 슬롯 풀림으로 한 칸씩 당겨진 순번을 즉시 반영.
        """
        n = 0
        for item_id, item in self.items.items():
            if item.status != DownloadStatus.WAITING:
                continue
            n += 1
            widget = self.widgets.get(item_id)
            if widget is not None:
                widget.update_waiting_position(n)

    def _start_worker(self, item_id: str):
        """
        실제 DownloadWorker 를 생성·연결·기동한다.

        호출 시점에 항목 상태를 DOWNLOADING 으로 전이시키므로 _dispatch_next
        의 active 카운트 일관성이 유지된다. save_path 는 다운로드 완료 시점에
        파일 경로로 덮어쓰일 수 있어, 매번 config 에서 디렉터리를 다시 읽는다
        (사용자가 환경설정에서 폴더를 바꿨을 가능성도 흡수).
        """
        item   = self.items.get(item_id)
        widget = self.widgets.get(item_id)
        if not item or not widget:
            return

        # 이전 워커 참조 정리 (재시도 경로)
        prev = self.dl_workers.pop(item_id, None)
        if prev is not None:
            try:
                prev.deleteLater()
            except Exception:
                pass

        save_dir = self.config.get("save_path", "")
        item.save_path = save_dir

        widget.update_status(DownloadStatus.DOWNLOADING)

        worker = DownloadWorker(
            url       = item.url,
            format_id = item.format_id,
            ext       = item.ext,
            save_dir  = save_dir,
        )
        # 진행률·속도·ETA·크기·병합·코덱정보는 워커→위젯 직접 연결 (매니저 미경유).
        # 코덱 정보는 라이프사이클이 아니라 갱신 시그널이므로 progress/speed
        # 와 같은 패턴으로 위젯에 직결. 매니저 중계 시 N 배 시그널만 늘어남.
        worker.progress.connect(widget.update_progress)
        worker.speed.connect(widget.update_speed)
        worker.eta.connect(widget.update_eta)
        worker.file_size.connect(widget.update_file_size)
        worker.merging.connect(
            lambda: widget.update_status(DownloadStatus.MERGING)
        )
        worker.codec_info_resolved.connect(widget.update_format_meta_resolved)
        # 라이프사이클은 매니저가 받아 자체 시그널로 다시 emit
        worker.finished.connect(
            lambda path, iid=item_id: self._on_worker_finished(iid, path)
        )
        worker.error.connect(
            lambda err, iid=item_id: self._on_worker_error(iid, err)
        )
        worker.cancelled.connect(
            lambda iid=item_id: self._on_worker_cancelled(iid)
        )
        self.dl_workers[item_id] = worker
        worker.start()

    # ── 워커 시그널 수신 → 매니저 시그널 재발사 ────────

    def _on_worker_finished(self, item_id: str, path: str):
        self.item_done.emit(item_id, path)
        # 슬롯 한 칸 풀림 — 다음 WAITING 항목 출발
        self._dispatch_next()

    def _on_worker_error(self, item_id: str, message: str):
        self.item_error.emit(item_id, message)
        self._dispatch_next()

    def _on_worker_cancelled(self, item_id: str):
        self.item_cancelled.emit(item_id)
        self._dispatch_next()
