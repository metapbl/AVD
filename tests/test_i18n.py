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
