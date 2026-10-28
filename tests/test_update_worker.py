# UpdateWorker 의 exe 배포본 분기 — pip 대신 wheel 교체 (D038, R§4 T17).
import sys
from pathlib import Path

import yt_dlp

from workers import update_worker
from workers.update_worker import UpdateWorker


def test_frozen_uses_wheel_not_pip(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    calls = []

    def fake_install(dest_dir, on_line):
        calls.append(dest_dir)
        on_line("받는 중")
        return True

    def no_popen(*_, **__):
        raise AssertionError("exe 에서 pip 을 부르면 AVD.exe 가 다시 뜬다")

    monkeypatch.setattr(update_worker, "install_ytdlp_wheel", fake_install)
    monkeypatch.setattr(update_worker.subprocess, "Popen", no_popen)

    worker = UpdateWorker()
    lines, done = [], []
    worker.progress_text.connect(lines.append)
    worker.done.connect(lambda ok, msg: done.append((ok, msg)))
    worker.run()

    assert calls == [Path(yt_dlp.__file__).parent.parent]
    assert lines == ["받는 중"]
    assert done[0][0] is True
    assert "다시 시작" in done[0][1]


def test_frozen_failure_reports_false(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(update_worker, "install_ytdlp_wheel", lambda *_, **__: False)

    worker = UpdateWorker()
    done = []
    worker.done.connect(lambda ok, msg: done.append(ok))
    worker.run()

    assert done == [False]
