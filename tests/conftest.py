"""테스트 프로세스가 끝날 때 남은 Qt 위젯을 먼저 지운다 (T35). 테스트마다 번역기를 걷어 낸다 (F17)."""
import gc

import pytest


@pytest.fixture(autouse=True)
def _no_translator_left():
    # 언어를 바꾼 테스트 뒤에 번역기·글꼴이 남으면 다른 테스트의 문구·크기가 바뀐다
    from PySide6.QtWidgets import QApplication

    from utils import i18n

    app = QApplication.instance()
    font = app.font() if app is not None else None
    yield
    app = QApplication.instance()
    if font is not None:
        app.setFont(font)
    for translator in i18n._installed:
        if app is not None:
            app.removeTranslator(translator)
    i18n._installed.clear()


@pytest.fixture(autouse=True)
def _no_ytdlp_update_check(monkeypatch):
    # 주 창이 실제로 새 버전을 확인하면 "업데이트할까요?" 창이 떠 테스트가 멈춘다
    from ui.main_window import MainWindow

    monkeypatch.setattr(MainWindow, "_check_ytdlp_update", lambda self: None)


def pytest_unconfigure(config):
    # 위젯이 QApplication 보다 늦게 파괴되면 종료 때 0xC0000409 로 죽는다 (테스트는 모두 통과한 뒤)
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        w.close()
        w.deleteLater()
    app.processEvents()
    gc.collect()
