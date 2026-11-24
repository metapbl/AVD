"""화면 언어 결정과 번역기 교체 (F17, D084)."""
import json

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from utils import config_manager
from utils.i18n import apply_language, resolve_language


@pytest.mark.parametrize("setting, locale_name, expected", [
    ("system", "ja_JP", "ja"),
    ("system", "de_DE", "en"),
    ("system", "zh_CN", "zh_CN"),
    ("system", "zh_SG", "zh_CN"),
    ("system", "zh_TW", "en"),
    ("system", "es_MX", "es"),
    ("system", "ru_RU", "ru"),
    ("system", "ko_KR", "ko"),
    ("system", "en_GB", "en"),
    ("ko", "en_US", "ko"),
    ("zh_CN", "ja_JP", "zh_CN"),
    ("xx", "ja_JP", "ja"),  # 모르는 값은 system 처럼
])
def test_resolve_language(setting, locale_name, expected):
    assert resolve_language(setting, locale_name) == expected


def test_old_config_without_key_follows_system(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"language": "ko"}), encoding="utf-8")
    monkeypatch.setattr(config_manager, "CONFIG_PATH", path)
    assert config_manager.ConfigManager().get("ui_language") == "system"


def _ok_text():
    box = QMessageBox()
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    return box.button(QMessageBox.StandardButton.Ok).text()


def test_switching_language_replaces_previous_translator():
    app = QApplication.instance() or QApplication([])
    try:
        apply_language(app, "ko")
        assert _ok_text() == "확인"
        apply_language(app, "ja")
        apply_language(app, "en")  # 앞의 ko·ja 번역기가 남아 있으면 OK 가 번역된다
        assert _ok_text() == "OK"
    finally:
        apply_language(app, "en")


def _fake_qm(folder, pairs):
    """(문맥, 원문, 번역) 몇 개만 담은 avd_en.qm 을 folder 에 만든다."""
    import subprocess
    import sys
    from pathlib import Path
    from xml.sax.saxutils import escape

    body = "".join(
        f"<context><name>{c}</name><message><source>{escape(s)}</source>"
        f"<translation>{escape(t)}</translation></message></context>"
        for c, s, t in pairs
    )
    ts = folder / "avd_en.ts"
    ts.write_text(f'<?xml version="1.0" encoding="utf-8"?><TS version="2.1" language="en">{body}</TS>',
                  encoding="utf-8")
    lrelease = Path(sys.executable).parent / "pyside6-lrelease"
    subprocess.run([str(lrelease), str(ts), "-qm", str(folder / "avd_en.qm")], check=True, capture_output=True)


def test_open_windows_switch_language_without_restart(tmp_path, monkeypatch):
    from models.download_item import DownloadItem, DownloadStatus
    from ui.download_item_widget import DownloadItemWidget
    from ui.main_window import MainWindow
    from utils import i18n

    app = QApplication.instance() or QApplication([])
    _fake_qm(tmp_path, [
        ("MainWindow", "링크 추가", "Add link"),
        ("DownloadStatus", "다운로드 중", "Downloading"),
        ("DownloadItemWidget", "취소", "Cancel"),
        ("DownloadItemWidget", "대기 중 ({0}번째)", "Waiting (#{0})"),
    ])
    monkeypatch.setattr(i18n, "I18N_DIR", tmp_path)
    window = MainWindow()
    active = DownloadItemWidget(DownloadItem(url="u", title="t"))
    active.update_status(DownloadStatus.DOWNLOADING)
    waiting = DownloadItemWidget(DownloadItem(url="u2", title="t2"))
    waiting.update_status(DownloadStatus.WAITING)
    waiting.update_waiting_position(2)
    try:
        apply_language(app, "en")
        app.processEvents()
        assert window.btn_add.text() == "Add link"
        assert active.lbl_status.text() == "Downloading"
        assert active.btn_cancel.text() == "Cancel"
        assert waiting.lbl_status.text() == "Waiting (#2)"

        apply_language(app, "ko")
        app.processEvents()
        assert window.btn_add.text() == "링크 추가"
        assert waiting.lbl_status.text() == "대기 중 (2번째)"
    finally:
        apply_language(app, "ko")


def test_preferences_language_applies_on_save(tmp_path, monkeypatch):
    import json

    from PySide6.QtWidgets import QDialog

    from ui import main_window as mw
    from ui.main_window import MainWindow
    from ui.preferences_dialog import PreferencesDialog
    from utils import i18n

    app = QApplication.instance() or QApplication([])
    _fake_qm(tmp_path, [("MainWindow", "링크 추가", "Add link")])
    monkeypatch.setattr(i18n, "I18N_DIR", tmp_path)
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_manager, "CONFIG_PATH", config_path)
    window = MainWindow()

    class Dialog(PreferencesDialog):
        def exec(self):
            names = [self.combo_language.itemText(i) for i in range(self.combo_language.count())]
            assert names[1:] == ["English", "한국어", "简体中文", "日本語", "Español", "Русский"]
            self.combo_language.setCurrentIndex(self.combo_language.findData("en"))
            self._on_save()
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(mw, "PreferencesDialog", Dialog)
    window._on_preferences()
    app.processEvents()
    assert window.btn_add.text() == "Add link"
    assert json.loads(config_path.read_text(encoding="utf-8"))["ui_language"] == "en"


def test_same_source_cancel_keeps_two_meanings_in_english():
    # 원문 "취소" 가 배너 버튼(Cancel)과 목록 요약(Canceled)에 함께 쓰인다 — 구분 표시로 나눈다
    from models.download_item import DownloadItem, DownloadStatus
    from ui.main_window import MainWindow, _summary_text

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    apply_language(app, "en")
    app.processEvents()
    item = DownloadItem(url="u", status=DownloadStatus.CANCELLED)
    assert window.btn_banner_cancel.text() == "Cancel"
    assert _summary_text({item.item_id: item}) == "Canceled 1"


@pytest.mark.parametrize("platform, code, family", [
    ("win32", "ja", "Yu Gothic UI"),
    ("win32", "zh_CN", "Microsoft YaHei UI"),
    ("win32", "ko", "Malgun Gothic"),
    ("win32", "ru", "Malgun Gothic"),
    ("darwin", "ja", "Hiragino Sans"),
    ("darwin", "zh_CN", "PingFang SC"),
    ("darwin", "en", "Apple SD Gothic Neo"),
])
def test_font_family_per_language(platform, code, family):
    from utils.i18n import font_family

    assert font_family(code, platform) == family


def test_apply_language_switches_app_font():
    from utils.i18n import font_family

    app = QApplication.instance() or QApplication([])
    apply_language(app, "ja")
    assert app.font().family() == font_family("ja")
    apply_language(app, "en")
    assert app.font().family() == font_family("en")


@pytest.mark.parametrize("ui_language, expected", [
    # QLocale.system().uiLanguages()[0] — Windows "표시 언어" 의 BCP 47 이름 (검토 지적 1)
    ("ko-Kore-KR", "ko"),
    ("ja-JP", "ja"),
    ("zh-Hans-CN", "zh_CN"),
    ("zh-Hans-SG", "zh_CN"),
    ("zh-Hant-TW", "en"),
    ("zh-Hant-HK", "en"),
    ("en-US", "en"),
    ("es-419", "es"),
    ("ru", "ru"),
    ("de-DE", "en"),
])
def test_resolve_language_from_os_display_language(ui_language, expected):
    assert resolve_language("system", ui_language) == expected


def test_startup_and_settings_read_os_display_language():
    from pathlib import Path

    # 형식(지역) 설정이 아니라 표시 언어를 쓴다 — 두 호출 자리 모두
    for path in ("main.py", "ui/main_window.py"):
        source = (Path(__file__).parent.parent / path).read_text(encoding="utf-8")
        assert "QLocale.system().uiLanguages()" in source and "QLocale.system().name()" not in source, path


def test_confirm_dialog_default_title_follows_language(tmp_path, monkeypatch):
    from ui.confirm_remove_dialog import ConfirmRemoveDialog
    from utils import i18n

    app = QApplication.instance() or QApplication([])
    _fake_qm(tmp_path, [("ConfirmRemoveDialog", "확인", "Confirm")])
    monkeypatch.setattr(i18n, "I18N_DIR", tmp_path)
    apply_language(app, "en")
    assert ConfirmRemoveDialog().windowTitle() == "Confirm"


def test_apply_changes_language_with_settings_still_open(tmp_path, monkeypatch):
    # 적용(D091) — 메인 창과 열린 환경설정 창이 함께 바뀌고, 보던 페이지가 그대로
    from ui import main_window as mw
    from ui.main_window import MainWindow
    from ui.preferences_dialog import PreferencesDialog
    from utils import i18n

    app = QApplication.instance() or QApplication([])
    _fake_qm(tmp_path, [
        ("MainWindow", "링크 추가", "Add link"),
        ("PreferencesDialog", "일반", "General"),
        ("PreferencesDialog", "적용", "Apply"),
    ])
    monkeypatch.setattr(i18n, "I18N_DIR", tmp_path)
    monkeypatch.setattr(config_manager, "CONFIG_PATH", tmp_path / "config.json")
    window = MainWindow()
    seen = {}

    class Dialog(PreferencesDialog):
        def exec(self):
            self.nav.setCurrentRow(2)
            self.combo_language.setCurrentIndex(self.combo_language.findData("en"))
            self.btn_apply.click()
            for _ in range(3):  # 다시 그리기는 다음 차례로 미뤄져 있다
                app.processEvents()
            seen.update(nav=self.nav.item(0).text(), row=self.nav.currentRow(), apply=self.btn_apply.text(),
                        main=window.btn_add.text())
            return 0

    monkeypatch.setattr(mw, "PreferencesDialog", Dialog)
    window._on_preferences()
    assert seen == {"nav": "General", "row": 2, "apply": "Apply", "main": "Add link"}
