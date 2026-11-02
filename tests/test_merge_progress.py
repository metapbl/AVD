# 병합 단계 진행률 — ffmpeg -progress 를 읽는 병합기 (D052).
import importlib
import shutil
import subprocess

import pytest
import yt_dlp
from yt_dlp.postprocessor.ffmpeg import FFmpegMergerPP, FFmpegPostProcessor

from core.downloader import _install_progress_merger, _merge_progress, _ProgressMergerPP

YDL_MODULE = importlib.import_module("yt_dlp.YoutubeDL")  # yt_dlp.YoutubeDL 은 클래스가 가린다


@pytest.mark.parametrize(("line", "duration", "expected"), [
    ("out_time_us=1000000\n", 4.0, (25.0, 1.0)),
    ("out_time_us=9000000", 4.0, (100.0, 9.0)),   # 100 을 넘지 않는다
    ("out_time_us=83000000", None, (None, 83.0)),  # 길이 모름 → 경과 시간만
    ("out_time_us=N/A", 4.0, None),
    ("progress=continue", 4.0, None),
    ("frame=10", 4.0, None),
])
def test_merge_progress_parses_out_time(line, duration, expected):
    assert _merge_progress(line, duration) == expected


def test_progress_merger_is_installed():
    assert YDL_MODULE.FFmpegMergerPP is _ProgressMergerPP


def test_install_skips_when_parent_changed(monkeypatch):
    monkeypatch.setattr(YDL_MODULE, "FFmpegMergerPP", FFmpegMergerPP)
    monkeypatch.setattr(FFmpegPostProcessor, "real_run_ffmpeg", lambda self, cmd: None)
    assert _install_progress_merger() is False
    assert YDL_MODULE.FFmpegMergerPP is FFmpegMergerPP


needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 가 PATH 에 없음")


@pytest.fixture
def merge_info(tmp_path):
    v, a = tmp_path / "t.f1.mp4", tmp_path / "t.f2.m4a"
    for args, out in (
        (["-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=10", "-c:v", "mpeg4"], v),
        (["-f", "lavfi", "-i", "sine=duration=2", "-c:a", "aac"], a),
    ):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, str(out)], check=True)
    return {
        "filepath": str(tmp_path / "t.mp4"), "ext": "mp4", "duration": 2,
        "vcodec": "mpeg4", "acodec": "aac",
        "requested_formats": [
            {"vcodec": "mpeg4", "acodec": "none", "protocol": "https", "filepath": str(v)},
            {"vcodec": "none", "acodec": "aac", "protocol": "https", "filepath": str(a)},
        ],
        "__files_to_merge": [str(v), str(a)],
    }


def _pp(hook):
    pp = _ProgressMergerPP(yt_dlp.YoutubeDL({"quiet": True}))
    pp.add_progress_hook(hook)
    return pp


@needs_ffmpeg
def test_merge_reports_processing(merge_info, tmp_path):
    seen = []
    _pp(seen.append).run(merge_info)

    assert (tmp_path / "t.mp4").exists()
    assert [s["status"] for s in seen].count("started") == 1
    pcts = [s["merge_percent"] for s in seen if s["status"] == "processing"]
    assert pcts and pcts == sorted(pcts) and pcts[-1] >= 90


@needs_ffmpeg
def test_cancel_during_merge_stops_ffmpeg(merge_info, tmp_path):
    def hook(s):
        if s["status"] == "processing":
            raise yt_dlp.utils.DownloadCancelled("취소")

    pp = _pp(hook)
    with pytest.raises(yt_dlp.utils.DownloadCancelled):
        pp.run(merge_info)
    assert pp._proc.poll() is not None
    assert not (tmp_path / "t.temp.mp4").exists()
