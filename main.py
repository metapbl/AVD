# main.py
# 앱 진입점 - 여기서 실행이 시작됨

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from utils.updater import APP_VERSION

# 동결 빌드에서도 main.py 는 _internal\ 에 있다고 보므로 datas 경로와 맞는다 (AVD.spec)
ICON_PATH = Path(__file__).resolve().parent / "assets" / "icons" / "avd.png"


def set_window_class_icon(window):
    """창 클래스 아이콘을 앱 아이콘으로 바꾼다 (Windows).

    Qt 는 exe 의 `IDI_ICON1` 리소스만 찾고 없으면 Windows 기본 아이콘을 넣는데,
    PyInstaller 는 아이콘을 번호 1 로 싣는다. 새 폴더에서 처음 실행할 때 작업표시줄이
    이 클래스 아이콘을 써서 기본 아이콘이 뜬다 (작업 13 실기기). 창을 띄우기 전에 부른다.
    """
    if sys.platform != "win32":
        return
    import ctypes
    user32 = ctypes.windll.user32
    user32.LoadImageW.restype = ctypes.c_void_p
    user32.SetClassLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    ico = str(ICON_PATH.with_suffix(".ico"))
    hwnd = int(window.winId())  # 네이티브 창을 지금 만든다
    for index, metric in ((-14, 11), (-34, 49)):  # GCLP_HICON·SM_CXICON, GCLP_HICONSM·SM_CXSMICON
        size = user32.GetSystemMetrics(metric)
        hicon = user32.LoadImageW(None, ico, 1, size, size, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
        if hicon:
            user32.SetClassLongPtrW(hwnd, index, hicon)


def main():
    # 소스 실행 때 작업표시줄이 python.exe 아이콘으로 묶이지 않게 앱 ID 를 따로 준다 (D042)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("metapbl.AVD")

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
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("AVDownloader")
    app.setWindowIcon(QIcon(str(ICON_PATH)))

    # 기본 폰트 설정
    font = QFont("맑은 고딕", 10)
    app.setFont(font)

    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    set_window_class_icon(window)
    window.show()

    # 앱 이벤트 루프 시작
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
