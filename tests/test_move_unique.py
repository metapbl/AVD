"""완료된 임시 파일을 저장 폴더로 옮기기 (열 번째 계획 작업 2, D054·D056)."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from utils.file_utils import move_unique, sweep_stale_temp_dirs


def _src(tmp_path, text, name="T.mp4", sub="tmp"):
    d = tmp_path / sub
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def save(tmp_path):
    d = tmp_path / "save"
    d.mkdir()
    return d


def test_no_collision_keeps_name(tmp_path, save):
    src = _src(tmp_path, "new")
    assert move_unique(str(src), str(save)) == str(save / "T.mp4")
    assert (save / "T.mp4").read_text(encoding="utf-8") == "new"
    assert not src.exists()


def test_collision_numbers_and_keeps_existing(tmp_path, save):
    (save / "T.mp4").write_text("old", encoding="utf-8")
    assert move_unique(str(_src(tmp_path, "a")), str(save)) == str(save / "T (1).mp4")
    assert move_unique(str(_src(tmp_path, "b")), str(save)) == str(save / "T (2).mp4")
    assert (save / "T.mp4").read_text(encoding="utf-8") == "old"
    assert (save / "T (1).mp4").read_text(encoding="utf-8") == "a"
    assert (save / "T (2).mp4").read_text(encoding="utf-8") == "b"


def test_number_goes_before_last_extension(tmp_path, save):
    (save / "a.b.mp4").write_text("old", encoding="utf-8")
    src = _src(tmp_path, "new", name="a.b.mp4")
    assert move_unique(str(src), str(save)) == str(save / "a.b (1).mp4")


def test_concurrent_moves_do_not_overwrite(tmp_path, save):
    sources = [_src(tmp_path, str(i), sub=f"tmp{i}") for i in range(8)]
    with ThreadPoolExecutor(8) as pool:
        moved = list(pool.map(lambda s: move_unique(str(s), str(save)), sources))
    assert len(set(moved)) == 8
    assert sorted(Path(p).read_text(encoding="utf-8") for p in moved) == [str(i) for i in range(8)]


def test_failed_move_keeps_source_and_leaves_no_placeholder(tmp_path, save, monkeypatch):
    src = _src(tmp_path, "new")

    def fail(_src, _dst):
        raise PermissionError("locked")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(PermissionError):
        move_unique(str(src), str(save))
    assert src.read_text(encoding="utf-8") == "new"
    assert list(save.iterdir()) == []


def _aged_dir(save, name, days):
    d = save / name
    d.mkdir()
    (d / "T.mp4").write_text("x", encoding="utf-8")
    old = time.time() - days * 86400
    os.utime(d, (old, old))
    return d


def test_sweep_removes_only_old_temp_dirs(save):
    stale = _aged_dir(save, ".avd_old", 2)
    fresh = _aged_dir(save, ".avd_new", 0)
    other_dir = _aged_dir(save, "my_folder", 2)
    other_file = save / ".avd_file"
    other_file.write_text("x", encoding="utf-8")
    os.utime(other_file, (0, 0))

    sweep_stale_temp_dirs(str(save))

    assert not stale.exists()
    assert fresh.is_dir()
    assert other_dir.is_dir()
    assert other_file.is_file()


@pytest.mark.parametrize("save_dir", ["", "missing"])
def test_sweep_without_save_dir_is_noop(tmp_path, monkeypatch, save_dir):
    monkeypatch.chdir(tmp_path)
    keep = _aged_dir(tmp_path, ".avd_cwd", 2)
    sweep_stale_temp_dirs(save_dir)
    assert keep.is_dir()


def test_manager_sweeps_on_start(save):
    from controllers.download_manager import DownloadManager

    stale = _aged_dir(save, ".avd_old", 2)
    DownloadManager({"save_path": str(save)}, {}, {})
    assert not stale.exists()
