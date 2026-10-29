# 앱 아이콘 — 창·작업표시줄 아이콘 파일 (D042).
from PySide6.QtGui import QImage

import main


def test_icon_path_is_512_png():
    img = QImage(str(main.ICON_PATH))
    assert (img.width(), img.height()) == (512, 512)
