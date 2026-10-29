# 앱 아이콘 — 창·작업표시줄 아이콘 파일 (D042).
import ctypes
import sys

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QWidget

import main


def test_icon_path_is_512_png():
    img = QImage(str(main.ICON_PATH))
    assert (img.width(), img.height()) == (512, 512)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 창 클래스 아이콘")
def test_window_class_icon_is_not_windows_default():
    # 새 폴더에서 처음 실행할 때 작업표시줄은 창 클래스 아이콘을 쓴다 (작업 13 실기기)
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    w = QWidget()
    main.set_window_class_icon(w)
    user32 = ctypes.windll.user32
    user32.GetClassLongPtrW.restype = ctypes.c_void_p
    user32.LoadIconW.restype = ctypes.c_void_p
    default = user32.LoadIconW(None, ctypes.c_void_p(32512))  # IDI_APPLICATION
    assert user32.GetClassLongPtrW(ctypes.c_void_p(int(w.winId())), -14) != default  # GCLP_HICON
