"""정보 추출·플레이리스트 확인·다운로드의 JS 옵션 통일 (열 번째 계획 작업 1, D055)."""
import yt_dlp


class _FakeYDL:
    """넘어온 옵션만 잡고 아무것도 받지 않는다."""
    opts = None

    def __init__(self, opts):
        type(self).opts = opts

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


def _js(opts):
    return opts["js_runtimes"], opts["remote_components"]


def test_all_call_sites_share_runtime_opts(monkeypatch, tmp_path):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", _FakeYDL)

    from core.downloader import Downloader
    from core.info_fetcher import InfoFetcher
    from workers.playlist_probe_worker import PlaylistProbeWorker

    Downloader().download("u", "best", "mp4", str(tmp_path), lambda d: None, lambda d: None)
    download = _js(_FakeYDL.opts)

    InfoFetcher().fetch("u")
    info = _js(_FakeYDL.opts)

    PlaylistProbeWorker("u").run()
    probe = _js(_FakeYDL.opts)

    assert download == info == probe


def test_runtime_not_pinned(monkeypatch, tmp_path):
    # 하나만 지정하면 다른 런타임만 있는 PC 에서 일부 포맷을 잃는다 (R§4 T23)
    monkeypatch.setattr(yt_dlp, "YoutubeDL", _FakeYDL)

    from core.downloader import Downloader

    Downloader().download("u", "best", "mp4", str(tmp_path), lambda d: None, lambda d: None)
    runtimes, _ = _js(_FakeYDL.opts)
    assert {"node", "deno", "bun"} <= set(runtimes)
