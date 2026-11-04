# 화질 목록을 열로 정렬한다 (열네 번째 계획 작업 3).
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.info_fetcher import FormatInfo, VideoInfo
from ui.format_select_dialog import FormatSelectDialog


class _Config:
    def __init__(self, last_ext=""):
        self.last_ext = last_ext

    def get(self, key, default=None):
        return self.last_ext if key == "last_chosen_ext" else default

    def set(self, key, value):
        pass


AUTO = FormatInfo("bestvideo+bestaudio/best", "최고 화질 (자동 선택)", "mp4", "최고화질", 0, False)
HD = FormatInfo("137", "1080p MP4", "mp4", "1920x1080", 1048576, False, "avc1.640028", "mp4a.40.2", 128.0)
MP3 = FormatInfo("bestaudio/best", "MP3 오디오만", "mp3", "오디오 전용", 0, True)


def _dialog(config=None):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    info = VideoInfo(url="u", title="t", thumbnail="", duration=1, uploader="c", formats=[AUTO, HD, MP3])
    return FormatSelectDialog(info, config or _Config())


def _row(dlg, row):
    item = dlg.list_formats.topLevelItem(row)
    return [item.text(col) for col in range(dlg.list_formats.columnCount())]


def test_columns_are_separate():
    dlg = _dialog()
    assert dlg.list_formats.headerItem().text(0) == "형식"
    assert dlg.list_formats.columnCount() == 4
    label, resolution, codec, size = _row(dlg, 1)
    assert (label, resolution) == ("1080p MP4", "1920x1080")
    assert "H.264" in codec
    assert size == "1.00 MB"


def test_unknown_size_and_auto_codec():
    assert _row(_dialog(), 0)[2:] == ["자동", "크기 미확인"]


def test_default_row_follows_last_extension():
    dlg = _dialog(_Config("mp3"))
    assert dlg.list_formats.currentItem().data(0, Qt.ItemDataRole.UserRole) == MP3


def test_default_row_is_first_without_history():
    dlg = _dialog()
    assert dlg.list_formats.currentItem().data(0, Qt.ItemDataRole.UserRole) == AUTO


def test_double_click_confirms_row():
    dlg = _dialog()
    got = []
    dlg.format_selected.connect(got.append)
    item = dlg.list_formats.topLevelItem(1)
    dlg.list_formats.setCurrentItem(item)
    dlg.list_formats.itemDoubleClicked.emit(item, 0)
    assert got == [HD]
