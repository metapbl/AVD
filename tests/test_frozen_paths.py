# 동결(exe) 빌드의 경로 판별 — config.json 은 exe 옆 (D039).
import importlib
import sys
from pathlib import Path

import pytest

from utils import config_manager, updater

REPO_ROOT = Path(config_manager.__file__).parent.parent


@pytest.fixture
def reload_config(monkeypatch):
    yield lambda: importlib.reload(config_manager)
    monkeypatch.undo()
    importlib.reload(config_manager)


def test_config_path_source_run_is_repo_root(reload_config):
    assert reload_config().CONFIG_PATH == REPO_ROOT / "config.json"


def test_config_path_frozen_is_next_to_exe(monkeypatch, tmp_path, reload_config):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "AVD.exe"))
    assert reload_config().CONFIG_PATH == tmp_path / "config.json"


# 업데이트 뒤 재시작 명령 (D041) — exe 는 argv[0] 이 exe 자신이라 빼고, 소스는 main.py 를 넘긴다
def test_restart_command_source_run(monkeypatch):
    monkeypatch.setattr(sys, "executable", r"C:\venv\python.exe")
    monkeypatch.setattr(sys, "argv", ["main.py"])
    assert updater.restart_command() == [r"C:\venv\python.exe", "main.py"]


def test_restart_command_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\AVD\AVD.exe")
    monkeypatch.setattr(sys, "argv", [r"C:\AVD\AVD.exe"])
    assert updater.restart_command() == [r"C:\AVD\AVD.exe"]
