# 최고 호환·M4A 선택지 (F13, D072~D074) — 행 구성과 포맷 문자열이 실제로 고르는 것.
import yt_dlp

from controllers.playlist_flow import PlaylistFlow
from core.info_fetcher import (
    AUTO_FORMAT_ID,
    COMPAT_FORMAT_ID,
    M4A_FORMAT_ID,
    MP3_FORMAT_ID,
    InfoFetcher,
)

H264 = {"format_id": "137", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "none",
        "height": 1080, "width": 1920, "tbr": 4000, "protocol": "https"}
AV1_4K = {"format_id": "401", "ext": "mp4", "vcodec": "av01.0.12M.08", "acodec": "none",
          "height": 2160, "width": 3840, "tbr": 12000, "protocol": "https"}
AAC = {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2",
       "abr": 129.5, "tbr": 129.5, "protocol": "https"}
OPUS = {"format_id": "251", "ext": "webm", "vcodec": "none", "acodec": "opus",
        "abr": 160.0, "tbr": 160.0, "protocol": "https"}
YOUTUBE = [AAC, OPUS, H264, AV1_4K]


def _rows(formats):
    return InfoFetcher()._parse_formats({"formats": formats})


def _pick(selector, formats):
    """yt-dlp 가 이 포맷 문자열로 실제로 고르는 format_id 목록."""
    ydl = yt_dlp.YoutubeDL({"quiet": True})
    ctx = {"formats": formats, "has_merged_format": False, "incomplete_formats": True}
    (chosen,) = list(ydl.build_format_selector(selector)(ctx))
    return [f["format_id"] for f in chosen.get("requested_formats", [chosen])]


def test_row_order_and_kinds():
    rows = _rows(YOUTUBE)
    assert [r.format_id for r in rows[:4]] == [
        AUTO_FORMAT_ID, COMPAT_FORMAT_ID, MP3_FORMAT_ID, M4A_FORMAT_ID]
    assert [r.label for r in rows[4:]] == ["4K 2160p MP4", "1080p MP4"]  # 높은 순, 통칭 (D075)
    compat, m4a = rows[1], rows[3]
    assert (compat.ext, compat.is_audio) == ("mp4", False)
    assert (m4a.ext, m4a.is_audio) == ("m4a", True)


def test_m4a_row_shows_source_aac_bitrate_not_opus():
    assert _rows(YOUTUBE)[3].abr == 129.5


def test_m4a_row_without_m4a_source_has_no_bitrate():
    assert _rows([OPUS, H264])[3].abr == 0.0


def test_compat_picks_h264_and_aac_even_when_4k_av1_exists():
    assert _pick(COMPAT_FORMAT_ID, YOUTUBE) == ["137", "140"]
    assert _pick(AUTO_FORMAT_ID, YOUTUBE) == ["401", "251"]  # 기존 동작 — 4K AV1 + Opus


def test_compat_falls_back_when_no_h264():
    assert _pick(COMPAT_FORMAT_ID, [OPUS, AV1_4K]) == ["401", "251"]  # 받기는 한다


def test_m4a_picks_aac_source_and_falls_back():
    assert _pick(M4A_FORMAT_ID, YOUTUBE) == ["140"]
    assert _pick(M4A_FORMAT_ID, [OPUS, H264]) == ["251"]


def test_8k_row_label():
    eight_k = {**AV1_4K, "format_id": "702", "height": 4320, "width": 7680}
    assert _rows([eight_k])[4].label == "8K 4320p MP4"


def test_playlist_modes_map_to_the_same_constants():
    to = PlaylistFlow._mode_to_format
    assert to("video") == (AUTO_FORMAT_ID, "mp4")
    assert to("video_compat") == (COMPAT_FORMAT_ID, "mp4")
    assert to("audio") == (MP3_FORMAT_ID, "mp3")
    assert to("audio_m4a") == (M4A_FORMAT_ID, "m4a")
    assert to("???") == (AUTO_FORMAT_ID, "mp4")  # 모르는 값은 지금처럼 영상


# ── 화질 선택 창: 고른 행 기억 ──────────────────────────
from PySide6.QtWidgets import QApplication

from core.info_fetcher import VideoInfo
from ui.download_item_widget import DownloadItemWidget
from ui.format_select_dialog import FormatSelectDialog
from ui.playlist_select_dialog import PlaylistSelectDialog
from workers.playlist_probe_worker import PlaylistEntry, PlaylistResult


class _Config(dict):
    set = dict.__setitem__


def _dialog(config):
    QApplication.instance() or QApplication([])
    info = VideoInfo(url="u", title="t", thumbnail="", duration=0, uploader="c", formats=_rows(YOUTUBE))
    return FormatSelectDialog(info, config)


def _choose(dlg, label_start):
    tree = dlg.list_formats
    row = next(i for i in range(tree.topLevelItemCount())
               if tree.topLevelItem(i).text(0).startswith(label_start))
    tree.setCurrentItem(tree.topLevelItem(row))
    dlg._on_confirm()


def _current(dlg):
    return dlg.list_formats.currentItem().text(0)


def test_dialog_codec_column_for_new_rows():
    dlg = _dialog(_Config())  # 창을 잡고 있어야 목록이 살아 있다
    tree = dlg.list_formats
    codec = {tree.topLevelItem(i).text(0): tree.topLevelItem(i).text(2)
             for i in range(tree.topLevelItemCount())}
    assert codec["최고 호환 (H.264 + AAC)"] == "H.264 / AAC"
    assert codec["M4A 오디오 (원본 그대로)"] == "AAC 130kbps"


def test_dialog_first_row_without_memory():
    assert _current(_dialog(_Config())) == "최고 화질 (자동 선택)"


def test_dialog_remembers_fixed_rows_with_same_ext():
    config = _Config()
    _choose(_dialog(config), "최고 호환")
    assert _current(_dialog(config)) == "최고 호환 (H.264 + AAC)"  # mp4 첫 행(최고 화질)이 아니다
    _choose(_dialog(config), "M4A")
    assert _current(_dialog(config)) == "M4A 오디오 (원본 그대로)"


def test_dialog_resolution_row_falls_back_to_ext():
    config = _Config()
    _choose(_dialog(config), "최고 호환")
    _choose(_dialog(config), "1080p")
    assert config["last_chosen_format_id"] == ""
    assert _current(_dialog(config)) == "최고 화질 (자동 선택)"  # 지금까지의 동작 — mp4 첫 행


def test_playlist_dialog_emits_chosen_mode_and_defaults_to_video():
    QApplication.instance() or QApplication([])
    entry = PlaylistEntry(url="u", title="t", duration=0)
    got = []
    for pick in (None, "audio_m4a", "video_compat"):
        dlg = PlaylistSelectDialog(PlaylistResult(title="p", entries=[entry], total_found=1))
        dlg.confirmed.connect(lambda entries, mode: got.append(mode))
        for rb in dlg._mode_group.buttons():
            if rb.property("mode") == pick:
                rb.setChecked(True)
        dlg._on_confirm()
    assert got == ["video", "audio_m4a", "video_compat"]


def test_compat_row_hides_ext_until_resolved():
    QApplication.instance() or QApplication([])
    from models.download_item import DownloadItem
    w = DownloadItemWidget(DownloadItem(url="u"))
    w.update_ext("mp4")
    w.update_format_meta(COMPAT_FORMAT_ID, "avc1", "mp4a", "mp4", 0.0, 0.0, False)
    assert w._ext_known is False  # 오디오 전용 사이트면 mp4 가 아니다 (D051)


def test_m4a_download_skips_chapters_so_thumbnail_embed_works(monkeypatch, tmp_path):
    """챕터 있는 영상의 m4a 는 ffmpeg 썸네일 임베드가 실패한다 (2026-11-11 실측)."""
    from core.downloader import Downloader

    seen = {}

    class _YDL:
        def __init__(self, opts):
            seen["pps"] = opts["postprocessors"]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def add_post_processor(self, *a, **kw):
            pass

        def download(self, urls):
            pass

    monkeypatch.setattr(yt_dlp, "YoutubeDL", _YDL)

    def chapters(ext):
        Downloader().download("u", "f", ext, str(tmp_path), lambda d: None, lambda d: None)
        return next(p for p in seen["pps"] if p["key"] == "FFmpegMetadata")["add_chapters"]

    assert chapters("m4a") is False
    assert chapters("mp3") is True and chapters("mp4") is True  # 기존 동작
