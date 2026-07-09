# ui/update_progress_dialog.py
# yt-dlp 업데이트 진행 상황을 보여 주는 모달 다이얼로그
#
# 배경: 예전에는 pip install 이 GUI 스레드에서 동기로 돌아
# 10 초간 창 전체가 얼어붙었다(마치 강제 종료된 듯). 이 다이얼로그는
#   - setModal(True) 로 메인창 입력을 막고(사용자가 그동안 딴 짓 못 하게)
#   - 진행 중에는 닫기/취소 버튼을 막아(업데이트 중간에 강제 종료 방지)
#   - UpdateWorker.progress_text 를 실시간 상태 라벨에 흘려
#     "멈춘 게 아니라 진행 중"임을 눈으로 보여 준다.
#
# pip 은 정확한 % 를 주지 않으므로 진행바는 '분주(busy)' 인디케이터로 둔다.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QHBoxLayout,
)


class UpdateProgressDialog(QDialog):
    """
    yt-dlp 업데이트 진행 모달.

    사용법:
        dlg = UpdateProgressDialog(current, latest, parent)
        worker.progress_text.connect(dlg.append_line)
        worker.done.connect(dlg.on_done)   # 완료 시 닫기 허용 + 마무리
        worker.start()
        dlg.exec()                         # 모달 진입(메인창 차단)
    """

    def __init__(self, current: str, latest: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle("yt-dlp 업데이트 중")
        self.setModal(True)
        # 진행 중 사용자가 X(닫기) 로 강제 종료하지 못하게 도움말 버튼과
        # 닫기 버튼을 숨긴다. 완료되면 on_done 에서 다시 열어 준다.
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
        )
        self.setMinimumWidth(420)

        # 업데이트가 끝나기 전에는 닫힐 수 없음을 표시하는 내부 플래그
        self._finished = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        self.lbl_title = QLabel(
            f"yt-dlp를 업데이트하고 있습니다.\n현재: {current}  →  최신: {latest}"
        )
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        # 분주(busy) 진행바: 최소=최대=0 이면 Qt 가 좌우로 흐르는 애니메이션을 준다.
        self.bar = QProgressBar(self)
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

        self.lbl_status = QLabel("준비 중…")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        # 하단 버튼: 진행 중에는 비활성. 완료되면 '닫기' 로 바뀐다.
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_close = QPushButton("업데이트 중…")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

    # ── 워커 시그널 슬롯 ─────────────────────────────

    def append_line(self, line: str):
        """UpdateWorker.progress_text → 상태 라벨 갱신(마지막 줄만 표시)."""
        # pip 출력이 길 수 있어 한 줄만 잘라 보여 준다.
        text = line.strip()
        if len(text) > 80:
            text = text[:77] + "…"
        self.lbl_status.setText(text)

    def on_done(self, success: bool, message: str):
        """UpdateWorker.done → 진행 종료. 닫기 허용 + 결과 표시."""
        self._finished = True
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        self.lbl_status.setText(message)
        self.lbl_status.setStyleSheet(
            "color: %s; font-size: 12px;" % ("#4caf50" if success else "#e57373")
        )
        self.btn_close.setText("닫기")
        self.btn_close.setEnabled(True)

    # ── 강제 종료 방지 ───────────────────────────────

    def reject(self):
        # ESC 등으로 닫으려는 시도. 완료 전에는 무시한다.
        if self._finished:
            super().reject()

    def closeEvent(self, event):
        # 창 닫기(X) 시도. 완료 전에는 막는다.
        if self._finished:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        # 완료 전에는 ESC 키 무시.
        if event.key() == Qt.Key.Key_Escape and not self._finished:
            event.ignore()
            return
        super().keyPressEvent(event)
