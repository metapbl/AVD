"""병합·다운로드 뒤 후처리 단계 라벨 (아홉 번째 계획 작업 1)."""
import pytest


def _worker():
    from workers.download_worker import DownloadWorker
    w = DownloadWorker("u", "bestvideo+bestaudio/best", "mp4", ".")
    got = []
    w.postprocess_stage.connect(got.append)
    return w, got


@pytest.mark.parametrize("pp, label", [
    ("FFmpegExtractAudio", "MP3 변환 중"),
    ("FFmpegMetadata", "태그 기록 중"),
    ("FFmpegThumbnailsConvertor", "썸네일 넣는 중"),
    ("EmbedThumbnail", "썸네일 넣는 중"),
])
def test_worker_emits_stage_on_started(pp, label):
    w, got = _worker()
    w._on_postprocess({"status": "started", "postprocessor": pp, "info_dict": {}})
    assert got == [label]


@pytest.mark.parametrize("d", [
    {"status": "finished", "postprocessor": "FFmpegMetadata"},
    {"status": "started", "postprocessor": "Merger"},
    {"status": "started", "postprocessor": "MoveFiles"},
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
