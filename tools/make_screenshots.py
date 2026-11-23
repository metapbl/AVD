# tools/make_screenshots.py
# README 스크린샷을 표본 데이터로 그려 docs/images/ 에 쓴다 (D089, metarche readme.md §7).
# 실제 경로·이름·계정이 화면에 나오지 않도록 손 캡처 대신 이 스크립트를 쓴다.
# 실행: venv\Scripts\python tools/make_screenshots.py   (화면이 바뀌면 다시 돌리고 파일 이름의 v 를 올린다)

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# 오프스크린 플랫폼은 시스템 글꼴을 스스로 찾지 못해 글자가 네모가 된다 — 글꼴 폴더를 알려 준다
_FONT_DIRS = {"win32": Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", "darwin": Path("/System/Library/Fonts")}
if sys.platform in _FONT_DIRS:
    os.environ.setdefault("QT_QPA_FONTDIR", str(_FONT_DIRS[sys.platform]))
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

OUT = ROOT / "docs" / "images"
VERSION = "v1"


def _thumbnail(top: str, bottom: str) -> bytes:
    """썸네일 대신 쓰는 그라데이션 그림 (제3자 이미지 없음)."""
    pixmap = QPixmap(320, 180)
    painter = QPainter(pixmap)
    gradient = QLinearGradient(0, 0, 320, 180)
    gradient.setColorAt(0, QColor(top))
    gradient.setColorAt(1, QColor(bottom))
    painter.fillRect(pixmap.rect(), gradient)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(data)


def main() -> None:
    from utils import config_manager

    # 표본 설정 — 저장 경로를 실제 폴더 대신 "Downloads" 로 보인다
    config_manager.CONFIG_PATH = Path(tempfile.mkdtemp()) / "config.json"

    from core.info_fetcher import (
        AUTO_FORMAT_ID,
        COMPAT_FORMAT_ID,
        M4A_FORMAT_ID,
        MP3_FORMAT_ID,
        FormatInfo,
        VideoInfo,
    )
    from models.download_item import DownloadItem, DownloadStatus
    from ui import theme
    from ui.download_item_widget import DownloadItemWidget
    from ui.format_select_dialog import FormatSelectDialog
    from ui.main_window import MainWindow
    from utils.i18n import apply_language

    app = QApplication(sys.argv)
    theme.apply_theme(app, "light")
    apply_language(app, "en")
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.config.set("save_path", "Downloads")
    window._refresh_save_path()
    window.resize(900, 520)
    samples = [
        ("Sunrise over the harbor — timelapse", DownloadStatus.DOWNLOADING, ("#f6a04d", "#5b3a8c")),
        ("Morning jazz session", DownloadStatus.DONE, ("#2b6cb0", "#81e6d9")),
        ("Mountain trail walk", DownloadStatus.ERROR, ("#2f855a", "#c6f6d5")),
        ("City lights at night", DownloadStatus.WAITING, ("#1a202c", "#805ad5")),
    ]
    for title, status, colors in samples:
        item = DownloadItem(url="https://example.com/watch", title=title, duration=245)
        window.items[item.item_id] = item
        widget = DownloadItemWidget(item, window)
        window.widgets[item.item_id] = widget  # 테마를 바꿀 때 다시 칠하는 대상
        window.list_layout.insertWidget(window.list_layout.count() - 1, widget)
        widget.update_thumbnail(_thumbnail(*colors))
        widget.update_status(status)
        if status == DownloadStatus.DOWNLOADING:
            widget.update_progress(42.0)
            widget.update_speed("3.2MiB/s")
            widget.update_eta("0:38")
            widget.update_file_size("54.10 / 128.80 MiB")
        elif status == DownloadStatus.WAITING:
            widget.update_waiting_position(1)
    window.lbl_empty.setVisible(False)
    window._refresh_summary()
    window.show()

    formats = [
        FormatInfo(AUTO_FORMAT_ID, "Best quality (auto)", "mp4", "3840x2160", 512_000_000, False,
                   "av01.0.12M.08", "opus", 160.0, 0.0),
        FormatInfo(COMPAT_FORMAT_ID, "Most compatible (H.264 + AAC)", "mp4", "1920x1080", 182_000_000, False,
                   "avc1.640028", "mp4a.40.2", 128.0, 0.0),
        FormatInfo("401+bestaudio/best", "4K 2160p MP4", "mp4", "3840x2160", 498_000_000, False, "av01.0.12M.08",
                   "opus", 160.0, 0.0),
        FormatInfo("137+bestaudio/best", "1080p MP4", "mp4", "1920x1080", 176_000_000, False, "avc1.640028",
                   "opus", 160.0, 0.0),
        FormatInfo("136+bestaudio/best", "720p MP4", "mp4", "1280x720", 92_000_000, False, "avc1.4d401f",
                   "opus", 160.0, 0.0),
        FormatInfo(MP3_FORMAT_ID, "MP3 audio only", "mp3", "Audio only", 0, True, "", "mp3", 320.0, 0.0),
        FormatInfo(M4A_FORMAT_ID, "M4A audio (original)", "m4a", "Audio only", 0, True, "", "mp4a", 128.0, 0.0),
    ]
    info = VideoInfo(url="https://example.com/watch", title=samples[0][0], thumbnail="", duration=245,
                     uploader="Sample Channel", formats=formats)
    dialog = FormatSelectDialog(info, window.config, window)
    dialog.show()

    OUT.mkdir(parents=True, exist_ok=True)
    for mode in ("light", "dark"):
        theme.apply_theme(app, mode)
        for _ in range(5):
            app.processEvents()
        window.grab().save(str(OUT / f"main-{mode}-{VERSION}.png"))
        dialog.grab().save(str(OUT / f"format-{mode}-{VERSION}.png"))
    print(f"{OUT} — main/format × light/dark ({VERSION})")


if __name__ == "__main__":
    main()
