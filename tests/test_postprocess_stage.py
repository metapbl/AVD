"""병합·다운로드 뒤 후처리 단계 라벨 (아홉 번째 계획 작업 1)."""
import pytest
from yt_dlp.postprocessor import (
    EmbedThumbnailPP,
    FFmpegExtractAudioPP,
    FFmpegMergerPP,
    FFmpegMetadataPP,
    FFmpegThumbnailsConvertorPP,
)


def _worker():
    from workers.download_worker import DownloadWorker
    w = DownloadWorker("u", "bestvideo+bestaudio/best", "mp4", ".")
    got = []
    w.postprocess_stage.connect(got.append)
    return w, got


@pytest.mark.parametrize("pp_class, label", [
    (FFmpegExtractAudioPP, "MP3 변환 중"),
    (FFmpegMetadataPP, "태그 기록 중"),
    (EmbedThumbnailPP, "썸네일 넣는 중"),
])
def test_worker_emits_stage_on_started(pp_class, label):
    # hook 이름은 yt-dlp 의 pp_key() 그대로 — "FFmpeg" 접두사가 빠진다 (R§4 T22)
    w, got = _worker()
    w._on_postprocess({"status": "started", "postprocessor": pp_class.pp_key(), "info_dict": {}})
    assert got == [label]


@pytest.mark.parametrize("d", [
    {"status": "finished", "postprocessor": FFmpegMetadataPP.pp_key()},
    {"status": "started", "postprocessor": FFmpegMergerPP.pp_key()},
    {"status": "started", "postprocessor": "MoveFiles"},
    # 썸네일 변환은 다운로드 전에 돌아 라벨이 거짓이 된다
    {"status": "started", "postprocessor": FFmpegThumbnailsConvertorPP.pp_key()},
])
def test_worker_ignores_other_hooks(d):
    w, got = _worker()
    w._on_postprocess({**d, "info_dict": {}})
    assert got == []


def _widget(status):
    from PySide6.QtWidgets import QApplication

    from models.download_item import DownloadItem, DownloadStatus
    from ui.download_item_widget import DownloadItemWidget
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    w = DownloadItemWidget(DownloadItem(url="u", title="t"))
    w.update_status(DownloadStatus[status])
    return w


def test_widget_shows_stage_after_merge():
    w = _widget("MERGING")
    w.update_merge_progress(100.0, 10.0)
    w.update_postprocess_stage("태그 기록 중")
    assert w.lbl_status.text() == "태그 기록 중"
    assert w.progress_bar.value() == 100


def test_widget_shows_stage_while_downloading():
    w = _widget("DOWNLOADING")
    w.update_progress(100.0)
    w.update_postprocess_stage("MP3 변환 중")
    assert w.lbl_status.text() == "MP3 변환 중"
    assert w.progress_bar.value() == 100


@pytest.mark.parametrize("late", ["DONE", "ERROR", "CANCELLED"])
def test_widget_ignores_late_stage(late):
    w = _widget(late)
    before = (w.progress_bar.value(), w.lbl_status.text())
    w.update_postprocess_stage("태그 기록 중")
    assert (w.progress_bar.value(), w.lbl_status.text()) == before
