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
# 진행바 정책 (2026-07-10 개정):
#   초기 구현은 busy 인디케이터(setRange(0,0))였는데, Fusion 스타일 +
#   모달 exec() 환경의 Windows 에서 애니메이션이 안 돌고 100% 로 꽉 찬
#   막대처럼 보였다. pip 은 신뢰할 % 를 주지 않으므로(다운로드는 순식간,
#   설치 단계는 % 없음) 결정(0~100) 진행바 + "단계 기반 의사 진행률" 로
#   바꾼다. pip 출력 단계를 인식해 막대를 계단식으로 올려, Windows 에서도
#   막대가 왼쪽→오른쪽으로 실제로 차오르는 것이 보이게 한다. 다운로드
#   라인의 "받은/전체 MB" 는 있으면 그 구간(15~55%) 안에서 반영한다.

import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QHBoxLayout,
)


# pip 다운로드 진행 라인의 "3.2/3.2 MB" 같은 받은/전체 용량 패턴.
_SIZE_RE = re.compile(r"([\d.]+)\s*/\s*([\d.]+)\s*(k|K|M|G)?i?B", re.IGNORECASE)


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
        # 단계 기반 의사 진행률의 현재 값(단조 증가만 허용 — 뒤로 안 감).
        self._pct = 0
        # 완료 전까지 막대가 절대 굳어 보이지 않도록, 진행이 없어도 아주
        # 조금씩 기어가게 하는 heartbeat 타이머(살아 있음 신호).
        self._heartbeat = QTimer(self)
        self._heartbeat.setInterval(400)
        self._heartbeat.timeout.connect(self._creep)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        self.lbl_title = QLabel(
            f"yt-dlp를 업데이트하고 있습니다.\n현재: {current}  →  최신: {latest}"
        )
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        # 결정(0~100) 진행바. busy 모드는 Windows/Fusion 에서 100% 로 굳어
        # 보였기에 쓰지 않는다. 값은 _bump/_set_pct 로 단조 증가시킨다.
        self.bar = QProgressBar(self)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(True)
        self.bar.setFormat("%p%")
        layout.addWidget(self.bar)

        self.lbl_status = QLabel("준비 중…")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        # 다이얼로그가 뜨는 즉시 heartbeat 시작(막대가 살아 움직이도록).
        self._set_pct(3)
        self._heartbeat.start()

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
        """UpdateWorker.progress_text → 상태 라벨 + 단계 기반 진행률 갱신.

        pip 은 신뢰할 전체 % 를 주지 않으므로, 출력 단계를 인식해 막대를
        계단식으로 올린다. 각 단계의 목표 하한(floor)까지 _set_pct 로 올리고,
        그 사이 heartbeat 가 조금씩 더 채운다. 단조 증가만 허용.
        """
        raw = line.strip()
        low = raw.lower()

        # 다운로드 진행 라인은 "downloading" 단어 없이 "1.6/3.2 MB 27 MB/s"
        # 형태로만 오는 경우가 많다. 그래서 크기 패턴을 단어보다 먼저,
        # 단어와 무관하게 검사해 15~55% 구간에 매핑한다.
        size_m = _SIZE_RE.search(raw)

        # 단계 인식 → 목표 진행률 하한. pip 표준 출력 문구 기준.
        if "collecting" in low or "requirement already satisfied" in low:
            self._bump(10)
        elif "downloading" in low or size_m is not None:
            # 다운로드 구간. 받은/전체 MB 가 있으면 15~55% 로 매핑, 없으면 15%.
            self._bump(15)
            if size_m is not None:
                try:
                    got = float(size_m.group(1))
                    total = float(size_m.group(2))
                    if total > 0:
                        frac = max(0.0, min(1.0, got / total))
                        self._bump(15 + int(frac * 40))  # 15→55
                except ValueError:
                    pass
        elif "installing" in low or "attempting uninstall" in low:
            self._bump(60)
        elif "uninstalling" in low:
            self._bump(70)
        elif "successfully uninstalled" in low:
            self._bump(85)
        elif "successfully installed" in low:
            self._bump(95)

        # 상태 라벨: 한 줄만, 길면 잘라서.
        if raw:
            text = raw if len(raw) <= 80 else raw[:77] + "…"
            self.lbl_status.setText(text)

    def on_done(self, success: bool, message: str):
        """UpdateWorker.done → 진행 종료. 닫기 허용 + 결과 표시."""
        self._finished = True
        self._heartbeat.stop()
        self._set_pct(100)
        self.lbl_status.setText(message)
        self.lbl_status.setStyleSheet(
            "color: %s; font-size: 12px;" % ("#4caf50" if success else "#e57373")
        )
        self.btn_close.setText("닫기")
        self.btn_close.setEnabled(True)

    # ── 진행률 헬퍼 ──────────────────────────────────

    def _set_pct(self, value: int):
        """진행률을 value 로 설정(0~100, 단조 증가만)."""
        value = max(0, min(100, int(value)))
        if value < self._pct:
            return
        self._pct = value
        self.bar.setValue(value)

    def _bump(self, floor: int):
        """현재 진행률을 최소 floor 까지 끌어올린다(이미 크면 유지)."""
        if floor > self._pct:
            self._set_pct(floor)

    def _creep(self):
        """heartbeat: 완료 전이면 막대를 아주 조금씩 전진시켜 '살아 있음' 표시.

        다음 단계 하한을 넘지 않도록 최대 95% 까지만, 매 틱 +1 로 기어간다.
        단계 이벤트가 오면 _bump 가 훌쩍 끌어올리므로, creep 은 '정체 구간에
        서도 막대가 미세하게 움직인다'는 인상만 담당한다.
        """
        if self._finished:
            return
        if self._pct < 95:
            self._set_pct(self._pct + 1)

    # ── 강제 종료 방지 ───────────────────────────────

    def reject(self):
        # ESC 등으로 닫으려는 시도. 완료 전에는 무시한다.
        if self._finished:
            self._heartbeat.stop()
            super().reject()

    def closeEvent(self, event):
        # 창 닫기(X) 시도. 완료 전에는 막는다.
        if self._finished:
            self._heartbeat.stop()
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        # 완료 전에는 ESC 키 무시.
        if event.key() == Qt.Key.Key_Escape and not self._finished:
            event.ignore()
            return
        super().keyPressEvent(event)
