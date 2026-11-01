# 형식 선택·플레이리스트 창 — 사이트가 준 제목·채널명은 서식으로 해석하지 않는다 (SECURITY_POLICY §4).
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from core.info_fetcher import VideoInfo
from ui.format_select_dialog import FormatSelectDialog
from ui.playlist_select_dialog import PlaylistSelectDialog
from workers.playlist_probe_worker import PlaylistResult

HTML = "<b>굵게</b> & <a href='x'>링크</a>"


class _Config:
    def get(self, key, default=None):
        return default


def _labels_with(dlg, text):
    return [lbl for lbl in dlg.findChildren(QLabel) if text in lbl.text()]


def test_format_dialog_title_and_uploader_are_plain_text():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    info = VideoInfo(url="u", title=HTML, thumbnail="", duration=0, uploader=HTML + "채널", formats=[])
    dlg = FormatSelectDialog(info, _Config())
    title, meta = _labels_with(dlg, HTML)
    assert title.text() == HTML
    assert title.textFormat() == meta.textFormat() == Qt.TextFormat.PlainText


def test_playlist_dialog_title_is_plain_text():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    dlg = PlaylistSelectDialog(PlaylistResult(title=HTML, entries=[], total_found=0))
    (lbl,) = _labels_with(dlg, HTML)
    assert lbl.textFormat() == Qt.TextFormat.PlainText
