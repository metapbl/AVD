"""항목별 임시 폴더에서 끝낸 뒤 저장 폴더로 옮기기 (열 번째 계획 작업 3, D056).

앞쪽 테스트는 실제 yt-dlp·ffmpeg 를 로컬 서버에 붙여 돌린다 (인터넷 없음).
"""
import functools
import hashlib
import http.server
import json
import shutil
import subprocess
import threading
from pathlib import Path
from typing import ClassVar

import pytest
from yt_dlp.utils import DownloadCancelled

import workers.download_worker as dw
from workers.download_worker import DownloadWorker

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg 필요 (R§2)")


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
    return float(json.loads(out)["format"]["duration"])


def _hash(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    """서버 파일은 4초, 저장 폴더에 미리 둘 파일은 1초 — 길이로 원본을 구분한다."""
    root = tmp_path_factory.mktemp("media")
    srv = root / "srv"
    old = root / "old"
    srv.mkdir()
    old.mkdir()
    video = ["-f", "lavfi", "-i", "testsrc=d={d}:s=160x90", "-f", "lavfi", "-i", "sine=d={d}",
             "-shortest", "-c:v", "libx264", "-c:a", "aac"]
    _ffmpeg(*[a.format(d=4) for a in video], str(srv / "av.mp4"))
    _ffmpeg(*[a.format(d=1) for a in video], str(old / "av.mp4"))
    _ffmpeg("-f", "lavfi", "-i", "sine=d=4", "-c:a", "aac", str(srv / "a.m4a"))
    _ffmpeg("-f", "lavfi", "-i", "sine=d=1", "-c:a", "aac", str(old / "a.m4a"))
    _ffmpeg("-f", "lavfi", "-i", "testsrc=d=20:s=160x90", "-c:v", "libx264", "-g", "25",
            "-f", "hls", "-hls_time", "1", "-hls_playlist_type", "vod", str(srv / "hls.m3u8"))

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(srv)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/", old
    server.shutdown()


def _run(url, fmt, ext, save):
    worker = DownloadWorker(url, fmt, ext, str(save))
    done, errors = [], []
    worker.download_finished.connect(done.append)
    worker.error.connect(errors.append)
    worker.run()
    assert errors == []
    return done[0]


def _no_temp_left(save):
    assert list(Path(save).glob(".avd_*")) == []


@needs_ffmpeg
def test_existing_m4a_survives_mp3_request(media, tmp_path):
    base, old = media
    shutil.copy(old / "a.m4a", tmp_path / "a.m4a")
    before = _hash(tmp_path / "a.m4a")

    path = _run(base + "a.m4a", "bestaudio/best", "mp3", tmp_path)

    assert Path(path) == tmp_path / "a.mp3"
    assert _duration(path) == pytest.approx(4, abs=0.2)
    assert _hash(tmp_path / "a.m4a") == before
    _no_temp_left(tmp_path)


@needs_ffmpeg
def test_existing_video_survives_mp3_request(media, tmp_path):
    base, old = media
    shutil.copy(old / "av.mp4", tmp_path / "av.mp4")
    before = _hash(tmp_path / "av.mp4")

    path = _run(base + "av.mp4", "bestaudio/best", "mp3", tmp_path)

    assert Path(path) == tmp_path / "av.mp3"
    assert _duration(path) == pytest.approx(4, abs=0.2)
    assert _hash(tmp_path / "av.mp4") == before
    _no_temp_left(tmp_path)


@needs_ffmpeg
def test_same_name_gets_number_and_keeps_existing(media, tmp_path):
    base, old = media
    shutil.copy(old / "av.mp4", tmp_path / "av.mp4")
    before = _hash(tmp_path / "av.mp4")

    path = _run(base + "av.mp4", "best", "mp4", tmp_path)

    assert Path(path) == tmp_path / "av (1).mp4"
    assert _duration(path) == pytest.approx(4, abs=0.2)
    assert _hash(tmp_path / "av.mp4") == before
    _no_temp_left(tmp_path)


@needs_ffmpeg
def test_cancel_during_fragment_download_removes_temp(media, tmp_path):
    # 조각 다운로더는 취소 때 .part 를 닫지 않아 GC 전까지 파일이 잠긴다 (R§4 T25)
    base, _ = media
    w = DownloadWorker(base + "hls.m3u8", "best", "mp4", str(tmp_path))
    got = _signals(w)
    w.progress.connect(lambda _pct: w.cancel())
    w.run()
    assert got["cancelled"]
    _no_temp_left(tmp_path)


class _FakeDownloader:
    """시도별 동작을 바꿔 끼운다. 각 시도의 작업 폴더를 기록한다."""
    actions: ClassVar[list] = []
    dirs: ClassVar[list] = []

    def cancel(self):
        pass

    def download(self, url, format_id, ext, save_dir, progress_hook, postprocess_hook):
        type(self).dirs.append(save_dir)
        (Path(save_dir) / "T.f1.mp4").write_text("part", encoding="utf-8")
        action = type(self).actions.pop(0)
        if isinstance(action, Exception):
            raise action
        out = Path(save_dir) / f"T.{ext}"
        out.write_text("done", encoding="utf-8")
        postprocess_hook({"status": "finished", "postprocessor": "Metadata",
                          "info_dict": {"filepath": str(out)}})


@pytest.fixture
def fake(monkeypatch):
    _FakeDownloader.actions = []
    _FakeDownloader.dirs = []
    monkeypatch.setattr(dw, "Downloader", _FakeDownloader)
    monkeypatch.setattr(dw, "_BACKOFF_SCHEDULE", [0])
    return _FakeDownloader


def _signals(worker):
    got = {"done": [], "error": [], "cancelled": []}
    worker.download_finished.connect(got["done"].append)
    worker.error.connect(got["error"].append)
    worker.cancelled.connect(lambda: got["cancelled"].append(True))
    return got


def test_works_in_item_temp_dir_then_moves(fake, tmp_path):
    fake.actions = [None]
    w = DownloadWorker("u", "best", "mp4", str(tmp_path))
    got = _signals(w)
    w.run()
    assert Path(fake.dirs[0]).parent == tmp_path
    assert Path(fake.dirs[0]).name.startswith(".avd_")
    assert got["done"] == [str(tmp_path / "T.mp4")]
    assert (tmp_path / "T.mp4").read_text(encoding="utf-8") == "done"
    _no_temp_left(tmp_path)


@pytest.mark.parametrize("action, key", [
    (DownloadCancelled("취소"), "cancelled"),
    (RuntimeError("HTTP Error 404: Not Found"), "error"),
])
def test_cancel_or_error_removes_only_temp(fake, tmp_path, action, key):
    (tmp_path / "T.mp4").write_text("old", encoding="utf-8")
    fake.actions = [action]
    w = DownloadWorker("u", "best", "mp4", str(tmp_path))
    got = _signals(w)
    w.run()
    assert got[key]
    assert got["done"] == []
    assert (tmp_path / "T.mp4").read_text(encoding="utf-8") == "old"
    _no_temp_left(tmp_path)


def test_retry_uses_fresh_temp_dir(fake, tmp_path):
    transient = next(p for p in dw._TRANSIENT_PATTERNS if dw._is_transient_error(p))
    fake.actions = [RuntimeError(transient), None]
    w = DownloadWorker("u", "best", "mp4", str(tmp_path))
    got = _signals(w)
    w.run()
    assert len(fake.dirs) == 2
    assert fake.dirs[0] != fake.dirs[1]
    assert got["done"] == [str(tmp_path / "T.mp4")]
    _no_temp_left(tmp_path)


def test_failed_move_keeps_temp_and_names_it(fake, tmp_path, monkeypatch):
    def fail(_src, _dst):
        raise PermissionError("locked")

    monkeypatch.setattr(dw, "move_unique", fail)
    fake.actions = [None]
    w = DownloadWorker("u", "best", "mp4", str(tmp_path))
    got = _signals(w)
    w.run()
    assert got["done"] == []
    assert fake.dirs[0] in got["error"][0]
    assert (Path(fake.dirs[0]) / "T.mp4").is_file()


def test_missing_output_is_error_and_keeps_temp(fake, tmp_path, monkeypatch):
    # 결과 경로를 모르면 완료로 치지 않는다 — 받은 파일이 임시 폴더에 있을 수 있다
    def no_hook(self, url, format_id, ext, save_dir, progress_hook, postprocess_hook):
        type(self).dirs.append(save_dir)

    monkeypatch.setattr(_FakeDownloader, "download", no_hook)
    w = DownloadWorker("u", "best", "mp4", str(tmp_path))
    got = _signals(w)
    w.run()
    assert got["done"] == []
    assert fake.dirs[0] in got["error"][0]
    assert Path(fake.dirs[0]).is_dir()


def test_gain_runs_before_move(fake, tmp_path, monkeypatch):
    import gaindb.api

    seen = []

    def analyze(path, target_db):
        seen.append(path)
        return {"status": "ok", "clip_state": "none"}

    monkeypatch.setattr(gaindb.api, "analyze_file", analyze)
    monkeypatch.setattr(dw, "apply_file_track_gain", lambda path, target_db, seed: {"steps": 0})
    fake.actions = [None]
    w = DownloadWorker("u", "bestaudio/best", "mp3", str(tmp_path), gain_enabled=True)
    got = _signals(w)
    w.run()
    assert Path(seen[0]).parent.name.startswith(".avd_")
    assert got["done"] == [str(tmp_path / "T.mp3")]
