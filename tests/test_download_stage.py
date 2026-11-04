# 영상·음성을 따로 받을 때 진행률이 두 번 도는 이유를 상태 문구로 보여 준다.
import pytest
from PySide6.QtWidgets import QApplication

from models.download_item import DownloadItem, DownloadStatus
from ui.download_item_widget import DownloadItemWidget
from workers.download_worker import DownloadWorker, _stream_label

VIDEO = {"vcodec": "vp9", "acodec": "none"}
AUDIO = {"vcodec": "none", "acodec": "opus"}
BOTH = {"vcodec": "avc1", "acodec": "mp4a"}


@pytest.mark.parametrize("info, label", [
    (VIDEO, "영상 받는 중"),
    (AUDIO, "음성 받는 중"),
    (BOTH, "다운로드 중"),
    ({}, "다운로드 중"),
    (None, "다운로드 중"),
])
def test_stream_label(info, label):
    assert _stream_label(info) == label


def _downloading(info):
    return {"status": "downloading", "_percent_str": "10%", "info_dict": info}


def test_worker_emits_stage_once_per_stream():
    w = DownloadWorker("u", "bestvideo+bestaudio/best", "mp4", ".")
    got = []
    w.download_stage.connect(got.append)
    for info in (VIDEO, VIDEO, AUDIO, AUDIO):
        w._on_progress(_downloading(info))
    assert got == ["영상 받는 중", "음성 받는 중"]


def _widget():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    w = DownloadItemWidget(DownloadItem(url="u", title="t"))
    w.update_status(DownloadStatus.DOWNLOADING)
    return w


def test_widget_label_uses_stage():
    w = _widget()
    w.update_download_stage("음성 받는 중")
    w.update_progress(30.0)
    assert w.lbl_status.text() == "30.0% 음성 받는 중"


def test_widget_label_default():
    w = _widget()
    w.update_progress(30.0)
    assert w.lbl_status.text() == "30.0% 다운로드 중"
