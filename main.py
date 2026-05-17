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