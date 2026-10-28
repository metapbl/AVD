# 동결(exe) 빌드의 경로 판별 — config.json 은 exe 옆 (D039).
import importlib
import sys
from pathlib import Path

import pytest

from utils import config_manager

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
