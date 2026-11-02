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
    ("progress=end", 4.0, (100.0, 4.0)),   # 마지막 out_time 은 길이보다 조금 짧다 — 끝은 100
    ("progress=end", None, None),
    ("frame=10", 4.0, None),
])
def test_merge_progress_parses_out_time(line, duration, expected):
    assert _merge_progress(line, duration) == expected


def test_progress_merger_is_installed():
    assert YDL_MODULE.FFmpegMergerPP is _ProgressMergerPP


def test_progress_merger_keeps_merger_key():
    # hook 의 "postprocessor" 와 postprocessor_args 키가 이 값이다 — 워커가 "Merger" 로 거른다
    assert _ProgressMergerPP.pp_key() == "Merger"


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


# ── 워커·위젯 연결 (작업 3) ──

def _worker():
    from workers.download_worker import DownloadWorker
    w = DownloadWorker("u", "bestvideo+bestaudio/best", "mp4", ".")
    got = []
    w.merge_progress.connect(lambda pct, secs: got.append((pct, secs)))
    return w, got


def test_worker_emits_merge_progress():
    w, got = _worker()
    w._on_postprocess({"status": "processing", "postprocessor": "Merger",
                       "merge_percent": 42.0, "merge_secs": 10.0, "info_dict": {}})
    w._on_postprocess({"status": "processing", "postprocessor": "Merger",
                       "merge_percent": None, "merge_secs": 83.0, "info_dict": {}})
    assert got == [(42.0, 10.0), (-1.0, 83.0)]


def test_worker_started_still_emits_merging_only():
    w, got = _worker()
    merging = []
    w.merging.connect(lambda: merging.append(1))
    w._on_postprocess({"status": "started", "postprocessor": "Merger", "info_dict": {}})
    assert merging == [1] and got == []


def _widget():
    from PySide6.QtWidgets import QApplication

    from models.download_item import DownloadItem, DownloadStatus
    from ui.download_item_widget import DownloadItemWidget
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    w = DownloadItemWidget(DownloadItem(url="u", title="t"))
    w.update_status(DownloadStatus.MERGING)
    return w


def test_widget_shows_merge_percent():
    w = _widget()
    w.update_merge_progress(42.0, 10.0)
    assert w.progress_bar.value() == 42
    assert w.lbl_status.text() == "병합 중 42%"


def test_widget_bar_matches_rounded_label():
    w = _widget()
    w.update_merge_progress(99.6, 10.0)
    assert w.progress_bar.value() == 100
    assert w.lbl_status.text() == "병합 중 100%"


def test_widget_shows_elapsed_without_duration():
    w = _widget()
    w.update_merge_progress(-1.0, 83.0)
    assert w.lbl_status.text() == "병합 중 1:23"


@pytest.mark.parametrize("late", ["DONE", "CANCELLED"])
def test_widget_ignores_late_merge_progress(late):
    from models.download_item import DownloadStatus
    w = _widget()
    w.update_status(DownloadStatus[late])
    before = (w.progress_bar.value(), w.lbl_status.text())
    w.update_merge_progress(42.0, 10.0)
    assert (w.progress_bar.value(), w.lbl_status.text()) == before
