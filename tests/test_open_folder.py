"""완료 항목 폴더 열기의 OS 분기 (F16, D081)."""
import subprocess
import sys

import pytest

from utils.file_utils import open_folder


@pytest.fixture
def calls(monkeypatch):
    seen = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: seen.append(args))
    return seen


@pytest.fixture
def file(tmp_path):
    p = tmp_path / "T.mp4"
    p.write_text("x", encoding="utf-8")
    return str(p)


def test_mac_file_reveals_in_finder(monkeypatch, calls, file):
    monkeypatch.setattr(sys, "platform", "darwin")
    open_folder(file)
    assert calls == [["open", "-R", file]]


def test_mac_dir_opens_in_finder(monkeypatch, calls, tmp_path):
    monkeypatch.setattr(sys, "platform", "darwin")
    open_folder(str(tmp_path))
    assert calls == [["open", str(tmp_path)]]


def test_windows_file_selects_in_explorer(monkeypatch, calls, file):
    monkeypatch.setattr(sys, "platform", "win32")
    open_folder(file)
    assert calls == [["explorer", "/select,", file]]


def test_missing_path_does_nothing(calls, tmp_path):
    open_folder(str(tmp_path / "none"))
    assert calls == []
