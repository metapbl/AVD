# ui/confirm_remove_dialog.py
# 항목 제거·취소·목록 비우기 작업에서 공통으로 쓰는 확인 다이얼로그.
#
# 설계 원칙:
# - 다이얼로그의 본질 질문은 항상 "목록에서 제거할지" 하나.
# - "디스크 파일도 삭제" 는 옵셔널 체크박스로 분리 (기본 해제).
# - 버튼은 Yes/No 가 아니라 "제거" / "닫기" — 동작을 라벨로 명시.
# - 기본 포커스는 "닫기" — 엔터 잘못 눌러도 사고 방지.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QPushButton,
)


class ConfirmRemoveDialog(QDialog):
    """
    제거 확인 다이얼로그.

    호출 후 결과 두 가지:
    - confirmed         : True 면 사용자가 "제거" 를 눌렀음
    - delete_disk_files : 체크박스가 있고 체크되어 있으면 True
                          (체크박스가 없는 다이얼로그는 항상 False)

    호출 예:
        dlg = ConfirmRemoveDialog(
            parent,
            title="항목 제거",
            message="이 항목을 목록에서 제거하시겠습니까?",
            checkbox_text="다운로드된 파일 삭제",   # 또는 None
        )
        dlg.exec()
        if dlg.confirmed:
            ... dlg.delete_disk_files 를 보고 처리 ...
    """

    def __init__(
        self,
        parent          = None,
        title           : str       = "확인",
        message         : str       = "",
        checkbox_text   : str | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        # 결과 보관 — exec() 종료 후 호출자가 읽음
        self.confirmed         : bool = False
        self.delete_disk_files : bool = False

        # 체크박스 핸들 — checkbox_text 가 None 이면 만들지 않음
        self._chk: QCheckBox | None = None

        self._build_ui(message, checkbox_text)
        self._apply_style()

    def _build_ui(self, message: str, checkbox_text: str | None):
        """UI 구성"""

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        # 메시지 — 여러 줄 가능 (본문에 \n 포함 케이스)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setObjectName("confirmMessage")
        lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        root.addWidget(lbl)

        # 옵셔널 체크박스
        if checkbox_text is not None:
            self._chk = QCheckBox(checkbox_text)
            self._chk.setChecked(False)   # 기본 해제 — 디스크 삭제는 명시적 동의 필요
            self._chk.setObjectName("confirmCheck")
            root.addWidget(self._chk)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_close = QPushButton("닫기")
        btn_close.setObjectName("confirmClose")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self._on_close)
        # 기본 포커스 — 엔터 잘못 눌러도 사고 방지
        btn_close.setDefault(True)
        btn_close.setAutoDefault(True)

        btn_remove = QPushButton("제거")
        btn_remove.setObjectName("confirmRemove")
        btn_remove.setFixedWidth(80)
        btn_remove.clicked.connect(self._on_remove)
        btn_remove.setDefault(False)
        btn_remove.setAutoDefault(False)

        # 화면상 순서: 닫기(기본) → 제거. Windows 의 통상 배치(취소 우측)와
        # 다르지만, 위험한 액션을 우측 끝에 두면 마우스 미끄러짐이 잦다.
        # 기본 포커스가 닫기이므로 엔터는 안전한 쪽으로 향한다.
        btn_row.addWidget(btn_close)
        btn_row.addWidget(btn_remove)
        root.addLayout(btn_row)

    def _apply_style(self):
        """다이얼로그 스타일 — 메인 윈도우의 다크 테마와 결을 맞춤"""
        self.setStyleSheet("""
            QDialog {
                background: #2b2b2b;
            }
            QLabel#confirmMessage {
                color: #e0e0e0;
                font-size: 13px;
            }
            QCheckBox#confirmCheck {
                color: #c0c0c0;
                font-size: 12px;
                spacing: 8px;
            }
            QPushButton#confirmClose {
                background: #555;
                color: #fff;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton#confirmClose:hover { background: #666; }
            QPushButton#confirmRemove {
                background: #555;
                color: #fff;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton#confirmRemove:hover { background: #e05555; }
        """)

    def _on_close(self):
        """닫기 — confirmed 는 False 로 유지"""
        self.confirmed = False
        self.delete_disk_files = False
        self.reject()

    def _on_remove(self):
        """제거 — 체크박스 상태를 읽어 결과에 반영"""
        self.confirmed = True
        self.delete_disk_files = bool(self._chk and self._chk.isChecked())
        self.accept()
