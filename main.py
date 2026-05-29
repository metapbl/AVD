# main.py
# 앱 진입점 - 여기서 실행이 시작됨

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    # QApplication 생성 - PySide6 앱의 필수 첫 단계
    app = QApplication(sys.argv)

    # 스타일 통일 — Fusion 은 OS 와 무관하게 Qt 가 자체 렌더링하는
    # 크로스플랫폼 스타일. 다크 팔레트(앱 전반의 #1e1e1e / #2b2b2b 계열)와
    # 자연스럽게 어울리고, Windows / macOS 에서 동일하게 보인다.
    # 체크박스·라디오버튼 등 indicator 위젯의 체크 마크가 Qt 내부에서
    # 그려지므로 별도 SVG / 이미지 없이 일관된 룩을 얻는다.
    # WORKLOG 3.2 "체크박스 디자인 일관화" 참조.
    app.setStyle("Fusion")

    # 앱 기본 정보 설정
    app.setApplicationName("AV Downloader")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AVDownloader")

    # 기본 폰트 설정
    font = QFont("맑은 고딕", 10)
    app.setFont(font)

    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()

    # 앱 이벤트 루프 시작
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
