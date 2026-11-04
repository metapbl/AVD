# 입력 다이얼로그의 Enter 는 주 동작을 누른다 (D060).
# 기본 버튼을 정하지 않으면 Qt 는 첫 버튼을 고른다: 화질 선택은 "취소", 환경설정은 "찾아보기".
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from core.info_fetcher import FormatInfo, VideoInfo
from ui.confirm_remove_dialog import ConfirmRemoveDialog
from ui.format_select_dialog import FormatSelectDialog
from ui.playlist_select_dialog import PlaylistSelectDialog
from ui.preferences_dialog import PreferencesDialog
from workers.playlist_probe_worker import PlaylistEntry, PlaylistResult


class _Config:
    def get(self, key, default=None):
        return default

    def set(self, key, value):
        pass


def _press_enter(dlg, target):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    dlg.show()
    target.setFocus()
    QTest.keyClick(target, Qt.Key.Key_Return)


def test_format_dialog_enter_downloads():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    fmt = FormatInfo("137", "1080p", "mp4", "1920x1080", 1, False)
    info = VideoInfo(url="u", title="t", thumbnail="", duration=1, uploader="c", formats=[fmt])
    dlg = FormatSelectDialog(info, _Config())
    selected, rejected = [], []
    dlg.format_selected.connect(selected.append)
    dlg.rejected.connect(lambda: rejected.append(True))
    _press_enter(dlg, dlg.list_formats)
    assert selected == [fmt]
    assert not rejected


def test_preferences_enter_saves_instead_of_browsing(monkeypatch):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    saved, browsed = [], []
    monkeypatch.setattr(PreferencesDialog, "_on_save", lambda self: saved.append(True))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: browsed.append(True) or "")
    dlg = PreferencesDialog(_Config())
    _press_enter(dlg, dlg.input_gain_db)
    assert saved == [True]
    assert not browsed


def test_playlist_enter_adds_and_keeps_unchecked_rows(monkeypatch):
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    added = []
    monkeypatch.setattr(PlaylistSelectDialog, "_on_confirm", lambda self: added.append(self._checked_rows()))
    entries = [PlaylistEntry("u1", "a", 1), PlaylistEntry("u2", "b", 2)]
    dlg = PlaylistSelectDialog(PlaylistResult("p", entries, 2))
    dlg._set_all(False)
    dlg.table.item(1, 0).setCheckState(Qt.CheckState.Checked)
    _press_enter(dlg, dlg.table)
    assert added == [[1]]


def test_remove_dialog_enter_stays_safe():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    dlg = ConfirmRemoveDialog(None, "t", "m", "파일 삭제")
    _press_enter(dlg, dlg)
    assert not dlg.confirmed
