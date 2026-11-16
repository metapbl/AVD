"""로그인 쿠키 사용 (스물일곱 번째 계획 작업 1, F15, D078·D079)."""
import os
from unittest.mock import MagicMock

import pytest
import yt_dlp
from PySide6.QtWidgets import QApplication

from core.downloader import Downloader, cookie_opts, open_ydl
from core.info_fetcher import InfoFetcher
from ui.main_window import _friendly_error
from ui.preferences_dialog import PreferencesDialog
from utils.config_manager import DEFAULT_CONFIG
from workers.info_worker import InfoWorker
from workers.playlist_probe_worker import PlaylistProbeWorker

# yt-dlp 가 쓰는 머리글과 다르게 적는다 — yt-dlp 가 다시 쓰면 내용이 바뀌어 드러난다.
_COOKIES_TXT = (
    "# Netscape HTTP Cookie File\n"
    "# 사용자가 내보낸 파일\n"
    ".example.com\tTRUE\t/\tTRUE\t4102444800\tSID\tsecret-value\n"
)


@pytest.fixture
def cookie_file(tmp_path):
    path = tmp_path / "cookies.txt"
    path.write_text(_COOKIES_TXT, encoding="utf-8")
    os.utime(path, (1_700_000_000, 1_700_000_000))
    return path


def _snapshot(path):
    return path.read_bytes(), path.stat().st_mtime


# ── 설정 → yt-dlp 옵션 ─────────────────────────────

def test_default_config_is_off():
    assert DEFAULT_CONFIG["cookie_source"] == "none"
    assert DEFAULT_CONFIG["cookie_file"] == ""
    assert "cookie_browser" not in DEFAULT_CONFIG  # 브라우저는 Firefox 하나 (D080)


def test_cookie_opts_none():
    assert cookie_opts({"cookie_source": "none", "cookie_file": "x"}) == {}
    assert cookie_opts({}) == {}


def test_cookie_opts_firefox():
    assert cookie_opts({"cookie_source": "firefox"}) == {"cookiesfrombrowser": ("firefox",)}
    # 예전 값(브라우저 목록 시절)은 쿠키 없이 — 아직 배포 전이라 옮기지 않는다
    assert cookie_opts({"cookie_source": "browser", "cookie_browser": "chrome"}) == {}


def test_cookie_opts_file():
    assert cookie_opts({"cookie_source": "file", "cookie_file": "C:/c.txt"}) == {"cookiefile": "C:/c.txt"}
    assert cookie_opts({"cookie_source": "file", "cookie_file": ""}) == {}


# ── 사용자 cookies.txt 를 고치지 않는다 (실제 yt-dlp) ──

def test_real_ytdlp_reads_cookie_file_without_rewriting(cookie_file):
    before = _snapshot(cookie_file)
    with open_ydl({"quiet": True}, {"cookiefile": str(cookie_file)}) as ydl:
        assert [c.name for c in ydl.cookiejar] == ["SID"]
    assert _snapshot(cookie_file) == before


def test_missing_cookie_file_fails_and_is_not_created(tmp_path):
    path = tmp_path / "없음.txt"
    with pytest.raises(Exception, match="failed to load cookies"):
        open_ydl({"quiet": True}, {"cookiefile": str(path)})
    assert not path.exists()


def test_browser_read_failure_says_cookies(monkeypatch):
    # yt-dlp 는 원인 문구만 담은 DownloadError 를 던진다 (2026-11-16 실기: Chrome·Edge 실패가 일반 안내로 나옴)
    import yt_dlp.cookies
    from yt_dlp.utils import DownloadError

    def fail(*a, **k):
        raise DownloadError("Failed to decrypt with DPAPI. See  https://github.com/yt-dlp/yt-dlp/issues/10927")

    monkeypatch.setattr(yt_dlp.cookies, "extract_cookies_from_browser", fail)
    with pytest.raises(Exception) as err:
        open_ydl({"quiet": True}, {"cookiesfrombrowser": ("firefox",)})
    assert "로그인 쿠키를 읽지 못했습니다" in _friendly_error(str(err.value))[0]


def test_no_cookies_keeps_opts_unchanged():
    with open_ydl({"quiet": True}, {}) as ydl:
        assert "cookiefile" not in ydl.params or ydl.params["cookiefile"] is None
        assert ydl.params.get("cookiesfrombrowser") is None


# ── 세 경로(정보·플레이리스트·다운로드)가 쿠키 옵션을 쓴다 ──

class _FakeYDL:
    """넘어온 옵션만 잡고 아무것도 받지 않는다. 마지막 인스턴스를 남긴다."""
    last = None

    def __init__(self, opts):
        self.params = dict(opts)
        self.cookiejar = []
        type(self).last = self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def add_post_processor(self, *a, **kw):
        pass

    def download(self, urls):
        pass

    def extract_info(self, url, download=False):
        return {"title": "t", "formats": [], "entries": []}


def _check_used(opts_key, value):
    p = _FakeYDL.last.params
    if opts_key == "cookiefile":
        # 불러온 뒤 비워 둔다 — close() 가 사용자 파일에 다시 쓰지 않게
        assert p["cookiefile"] is None
    else:
        assert p[opts_key] == value


@pytest.mark.parametrize("cookies", [
    {"cookiesfrombrowser": ("firefox",)},
    "FILE",
])
def test_all_call_sites_use_cookies(monkeypatch, tmp_path, cookie_file, cookies):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", _FakeYDL)
    if cookies == "FILE":
        cookies = {"cookiefile": str(cookie_file)}
    (key, value), = cookies.items()

    Downloader().download("u", "best", "mp4", str(tmp_path), lambda d: None, lambda d: None,
                          cookies=cookies)
    _check_used(key, value)

    InfoFetcher().fetch("u", cookies=cookies)
    _check_used(key, value)

    PlaylistProbeWorker("u", cookies=cookies).run()
    _check_used(key, value)

    InfoWorker("u", cookies=cookies).run()
    _check_used(key, value)


def test_download_worker_passes_cookies(monkeypatch, tmp_path):
    from workers.download_worker import DownloadWorker
    seen = []
    monkeypatch.setattr(Downloader, "download", lambda self, **kw: seen.append(kw["cookies"]))
    DownloadWorker("u", "best", "mp4", str(tmp_path), cookies={"cookiesfrombrowser": ("firefox",)}).run()
    assert seen and seen[0] == {"cookiesfrombrowser": ("firefox",)}


def test_download_manager_builds_cookies_from_config(monkeypatch):
    import controllers.download_manager as dm
    fake_worker = MagicMock()
    monkeypatch.setattr(dm, "DownloadWorker", fake_worker)
    config = {"save_path": "", "cookie_source": "firefox"}
    manager = dm.DownloadManager(config, {"a": MagicMock()}, {"a": MagicMock()})
    manager._start_worker("a")
    assert fake_worker.call_args.kwargs["cookies"] == {"cookiesfrombrowser": ("firefox",)}


def test_playlist_flow_passes_cookies(monkeypatch):
    import controllers.playlist_flow as pf
    fake_worker = MagicMock()
    monkeypatch.setattr(pf, "PlaylistProbeWorker", fake_worker)
    monkeypatch.setattr(pf, "QThread", MagicMock())
    pf.PlaylistFlow(None).start("u", cookies={"cookiefile": "c.txt"})
    assert fake_worker.call_args.kwargs["cookies"] == {"cookiefile": "c.txt"}


# ── 오류 안내 ──────────────────────────────────────

def test_cookie_load_failure_is_explained():
    title, desc = _friendly_error("ERROR: failed to load cookies")
    assert "로그인 쿠키를 읽지 못했습니다" in title
    assert "Firefox" in desc and "cookies.txt" in desc


@pytest.mark.parametrize("raw", [
    "ERROR: [youtube] x: Sign in to confirm you're not a bot",
    "ERROR: [youtube] x: Private video",
    "ERROR: [youtube] x: Sign in to confirm your age. This video may be inappropriate (age restricted)",
])
def test_login_errors_point_to_preferences(raw):
    _, desc = _friendly_error(raw)
    assert "추후 지원" not in desc
    assert "환경설정" in desc and "로그인 쿠키" in desc


@pytest.mark.parametrize("raw, title", [
    ("ERROR: [youtube] x: Sign in to confirm your age. This video may be inappropriate for some users.",
     "연령 제한"),
    ("ERROR: [youtube] x: This video is age-restricted and YouTube is requiring account verification",
     "연령 제한"),
    ("ERROR: [youtube] x: Sign in to confirm you're not a bot", "봇 감지"),
])
def test_age_restriction_is_not_mistaken_for_bot(raw, title):
    assert title in _friendly_error(raw)[0]


# ── 환경설정 ───────────────────────────────────────

class _DictConfig(dict):
    def set(self, key, value):
        self[key] = value


def _dialog(config):
    QApplication.instance() or QApplication([])
    return PreferencesDialog(config)


def test_preferences_default_is_off():
    dlg = _dialog(_DictConfig(DEFAULT_CONFIG))
    assert dlg._cookie_radios["none"].isChecked()
    assert list(dlg._cookie_radios) == ["none", "firefox", "file"]  # 브라우저 목록 없음 (D080)


@pytest.mark.parametrize("source, file_shown", [("none", False), ("firefox", False), ("file", True)])
def test_preferences_shows_file_row_only_for_file(source, file_shown):
    # 2026-11-16 실기 피드백: 고르지 않은 출처의 입력은 보이지 않아야 한다
    dlg = _dialog(_DictConfig(DEFAULT_CONFIG))
    dlg._cookie_radios[source].setChecked(True)
    assert dlg.cookie_file_row.isHidden() is not file_shown


def test_preferences_note_follows_choice():
    # B안 (2026-11-16 사용자 선택): 고른 선택에 필요한 말만 한 줄
    dlg = _dialog(_DictConfig(DEFAULT_CONFIG))
    notes = {}
    for source in ("none", "firefox", "file"):
        dlg._cookie_radios[source].setChecked(True)
        notes[source] = dlg.lbl_cookie_note.text()
    assert "켜세요" in notes["none"]
    assert "Firefox 에 로그인한 계정" in notes["firefox"]
    assert "cookies.txt" in notes["file"] and "만드는 법" in notes["file"]
    assert "만드는 법" not in notes["none"] + notes["firefox"]


def test_cookie_help_link_points_to_readme_section():
    from pathlib import Path

    from ui.about_dialog import REPO_URL
    from ui.preferences_dialog import COOKIE_HELP_URL

    assert COOKIE_HELP_URL == REPO_URL + "#로그인-쿠키"
    readme = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    assert "\n## 로그인 쿠키\n" in readme  # 링크가 가리키는 절이 있어야 한다

    dlg = _dialog(_DictConfig(DEFAULT_CONFIG))
    dlg._cookie_radios["file"].setChecked(True)
    assert f'href="{COOKIE_HELP_URL}"' in dlg.lbl_cookie_note.text()
    assert dlg.lbl_cookie_note.openExternalLinks()


def test_preferences_saves_and_reloads_firefox():
    config = _DictConfig(DEFAULT_CONFIG)
    dlg = _dialog(config)
    dlg._cookie_radios["firefox"].setChecked(True)
    dlg._on_save()
    assert config["cookie_source"] == "firefox"
    assert "cookie_browser" not in config
    again = _dialog(config)  # 변수에 쥐어야 창이 먼저 지워지지 않는다
    assert again._cookie_radios["firefox"].isChecked()


def test_preferences_saves_file_path_only(cookie_file):
    config = _DictConfig(DEFAULT_CONFIG)
    dlg = _dialog(config)
    dlg._cookie_radios["file"].setChecked(True)
    dlg.input_cookie_file.setText(str(cookie_file))
    dlg._on_save()
    assert (config["cookie_source"], config["cookie_file"]) == ("file", str(cookie_file))
    # 설정에는 출처만 — 쿠키 값이 들어가지 않는다
    assert "secret-value" not in repr(dict(config))
    again = _dialog(config)
    assert again.input_cookie_file.text() == str(cookie_file)
