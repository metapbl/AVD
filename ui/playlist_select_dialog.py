# ui/playlist_select_dialog.py
# 플레이리스트 항목 선택 + 출력 형태 선택 다이얼로그.
# probe 로 받은 항목 목록을 체크박스 표로 보여주고, 받을 항목과
# 출력 형태(영상/음원)를 한 번에 고르게 한다.

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal

from utils.file_utils import format_duration


class PlaylistSelectDialog(QDialog):
    """
    플레이리스트 항목·형태 선택 다이얼로그.

    시그널:
        confirmed : 확인 시 (선택된 PlaylistEntry 리스트, 형태 문자열) 전달.
                    형태는 "video" 또는 "audio".

    설계 메모:
    - 항목은 기본 전체 체크. "전체 선택"/"전체 해제" 로 일괄 토글.
    - 형태(영상/음원) 는 라디오 단일 선택, 기본 "영상".
    - 확인 시 체크된 항목이 0 개면 확인 버튼이 비활성 — 빈 추가 방지.
    - 입력 entries 의 순서를 보존한다(원래 플레이리스트 순서).
    """

    confirmed = Signal(list, str)  # (entries, mode)

    # 체크 상태 컬럼 외 데이터 컬럼
    _COL_CHECK = 0
    _COL_TITLE = 1
    _COL_DUR   = 2

    def __init__(self, result, parent=None):
        """
        result: PlaylistProbeWorker 가 emit 한 PlaylistResult.
        """
        super().__init__(parent)
        self._entries = list(result.entries)
        self._total_found = result.total_found
        self._pl_title = result.title

        self.setWindowTitle("플레이리스트 선택")
        self.setMinimumSize(640, 520)
        self.setModal(True)
        self._build_ui()
        self._apply_style()
        self._refresh_confirm_enabled()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # 안내 — 플레이리스트 제목과 개수. 상한 도달 시 그 사실을 알린다.
        n = len(self._entries)
        head = f"\"{self._pl_title}\" — {n}개 항목"
        if n >= 500:
            head += " (상한 500개까지 표시)"
        lbl = QLabel(head)
        lbl.setObjectName("dialogLabel")
        lbl.setWordWrap(True)
        root.addWidget(lbl)

        # 항목 표
        self.table = QTableWidget(n, 3)
        self.table.setHorizontalHeaderLabels(["", "제목", "길이"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self._COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self._COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self._COL_DUR, QHeaderView.ResizeMode.ResizeToContents)

        for row, entry in enumerate(self._entries):
            chk = QTableWidgetItem()
            chk.setFlags(chk.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row, self._COL_CHECK, chk)

            title_item = QTableWidgetItem(entry.title)
            self.table.setItem(row, self._COL_TITLE, title_item)

            dur_text = format_duration(entry.duration) if entry.duration else ""
            dur_item = QTableWidgetItem(dur_text)
            self.table.setItem(row, self._COL_DUR, dur_item)

        # 체크 상태 변경 시 확인 버튼 활성 재계산
        self.table.itemChanged.connect(lambda _it: self._refresh_confirm_enabled())
        root.addWidget(self.table, stretch=1)

        # 전체 선택/해제
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)
        btn_all = QPushButton("전체 선택")
        btn_all.setObjectName("btnGhost")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("전체 해제")
        btn_none.setObjectName("btnGhost")
        btn_none.clicked.connect(lambda: self._set_all(False))
        toggle_row.addWidget(btn_all)
        toggle_row.addWidget(btn_none)
        toggle_row.addStretch()
        root.addLayout(toggle_row)

        # 출력 형태 선택
        mode_row = QHBoxLayout()
        mode_row.setSpacing(16)
        mode_label = QLabel("형태:")
        mode_label.setObjectName("dialogLabel")
        self.rb_video = QRadioButton("영상 (최고 화질)")
        self.rb_audio = QRadioButton("음원만 (MP3)")
        self.rb_video.setChecked(True)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.rb_video)
        self._mode_group.addButton(self.rb_audio)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.rb_video)
        mode_row.addWidget(self.rb_audio)
        mode_row.addStretch()
        root.addLayout(mode_row)

        # 확인/취소
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setFixedSize(90, 32)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        self.btn_confirm = QPushButton("추가")
        self.btn_confirm.setObjectName("btnConfirm")
        self.btn_confirm.setFixedSize(90, 32)
        self.btn_confirm.clicked.connect(self._on_confirm)
        btn_row.addWidget(self.btn_confirm)
        root.addLayout(btn_row)

    def _set_all(self, checked: bool):
        """모든 행의 체크 상태를 일괄 변경."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        # itemChanged 가 행마다 발사되지 않도록 블록 후 한 번만 재계산.
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            self.table.item(row, self._COL_CHECK).setCheckState(state)
        self.table.blockSignals(False)
        self._refresh_confirm_enabled()

    def _checked_rows(self) -> list[int]:
        """현재 체크된 행 인덱스 목록 (원래 순서 보존)."""
        rows = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self._COL_CHECK)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                rows.append(row)
        return rows

    def _refresh_confirm_enabled(self):
        """체크된 항목이 하나도 없으면 '추가' 비활성."""
        self.btn_confirm.setEnabled(bool(self._checked_rows()))

    def _on_confirm(self):
        """확인 — 체크된 항목과 형태를 시그널로 전달하고 accept."""
        rows = self._checked_rows()
        if not rows:
            return
        chosen = [self._entries[r] for r in rows]
        mode = "video" if self.rb_video.isChecked() else "audio"
        self.confirmed.emit(chosen, mode)
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; }
            QLabel#dialogLabel { color: #cccccc; font-size: 13px; }
            QTableWidget {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                gridline-color: #3a3a3a;
                font-size: 12px;
            }
            QHeaderView::section {
                background: #333;
                color: #ccc;
                border: none;
                padding: 4px;
                font-size: 12px;
            }
            QTableWidget::item:selected { background: #34507a; }
            QRadioButton { color: #cccccc; font-size: 13px; }
            QPushButton#btnGhost {
                background: #444; color: #ccc;
                border-radius: 4px; padding: 4px 12px; font-size: 12px;
            }
            QPushButton#btnGhost:hover { background: #555; }
            QPushButton#btnCancel {
                background: #444; color: #ccc;
                border-radius: 4px; font-size: 12px;
            }
            QPushButton#btnCancel:hover { background: #555; }
            QPushButton#btnConfirm {
                background: #4a90d9; color: #fff;
                border-radius: 4px; font-size: 12px; font-weight: bold;
            }
            QPushButton#btnConfirm:hover { background: #5aa0e9; }
            QPushButton#btnConfirm:disabled { background: #3a4a5a; color: #888; }
        """)
