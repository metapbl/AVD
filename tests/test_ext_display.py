# 확장자 표시 정직화 — "자동 선택" 은 확장자를 숨겼다가 확정된 값으로 채운다 (D051, D053).
from PySide6.QtWidgets import QApplication

from core.info_fetcher import InfoFetcher
from models.download_item import DownloadItem
from ui.download_item_widget import AUTO_FORMAT_ID, DownloadItemWidget
from workers.download_worker import DownloadWorker


def _widget():
    app = QApplication.instance() or QApplication([])  # noqa: F841 — 위젯에 필요
    w = DownloadItemWidget(DownloadItem(url="u", title="제목"))
    w.lbl_title.resize(600, 20)  # 폭 0 이면 확장자 없이 제목만 박힌다
    return w


def _select(w, format_id, ext, is_audio=False):
    # MainWindow._on_format_selected 와 같은 순서
    w.update_ext(ext)
    w.update_format_meta(format_id=format_id, vcodec="", acodec="", ext=ext,
                         abr=0.0, tbr=0.0, is_audio=is_audio)


def test_auto_format_hides_ext_until_resolved():
    w = _widget()
    _select(w, AUTO_FORMAT_ID, "mp4")
    assert ".mp4" not in w.lbl_title.text()

    w.update_format_meta_resolved("none", "aac", "m4a", 128.0, 128.0)
    assert ".m4a" in w.lbl_title.text()


def test_explicit_format_shows_ext_immediately():
    w = _widget()
    _select(w, "137+140", "mp4")
    assert ".mp4" in w.lbl_title.text()


def test_mp3_keeps_ext_against_resolved():
    w = _widget()
    _select(w, "bestaudio/best", "mp3", is_audio=True)
    w.update_format_meta_resolved("none", "opus", "webm", 160.0, 160.0)
    assert ".mp3" in w.lbl_title.text()
    assert ".webm" not in w.lbl_title.text()


def test_auto_format_row_still_downloads_as_mp4():
    rows = InfoFetcher()._parse_formats({"formats": []})
    auto = next(r for r in rows if r.format_id == AUTO_FORMAT_ID)
    assert auto.ext == "mp4"  # merge_output_format 로 넘어가는 값 (D051)


def _worker():
    w = DownloadWorker("u", AUTO_FORMAT_ID, "mp4", ".")
    emitted = []
    w.codec_info_resolved.connect(lambda *a: emitted.append(a))
    return w, emitted


def test_merge_part_progress_sends_blank_ext():
    w, emitted = _worker()
    part = {"format_id": "137", "ext": "webm", "vcodec": "vp9", "acodec": "none"}
    w._on_progress({"status": "finished", "filename": "C:/d/제목.f137.webm", "info_dict": part})
    assert emitted and emitted[-1][2] == ""


def test_single_format_downloading_sends_ext():
    w, emitted = _worker()
    single = {"format_id": "http_aac", "ext": "m4a", "vcodec": "none", "acodec": "aac"}
    w._on_progress({"status": "downloading", "filename": "C:/d/제목.m4a",
                    "_percent_str": "10%", "info_dict": single})
    assert emitted and emitted[-1][2] == "m4a"


def test_merger_started_sends_final_ext():
    w, emitted = _worker()
    final = {"format_id": "137+140", "ext": "mp4", "vcodec": "vp9", "acodec": "opus"}
    w._on_postprocess({"status": "started", "postprocessor": "Merger", "info_dict": final})
    assert emitted and emitted[-1][2] == "mp4"
