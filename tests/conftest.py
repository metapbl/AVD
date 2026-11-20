"""테스트 프로세스가 끝날 때 남은 Qt 위젯을 먼저 지운다 (T35)."""
import gc


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
