"""오류 원문의 ANSI 색 코드 제거 (아홉 번째 계획 작업 2)."""
from yt_dlp.utils import DownloadError

RAW = "\x1b[0;31mERROR:\x1b[0m [youtube] x: Private video"
CLEAN = "ERROR: [youtube] x: Private video"


def _errors(worker):
    got = []
    worker.error.connect(got.append)
    return got


class _FailingDownloader:
    msg = RAW

    def download(self, **_):
        raise DownloadError(self.msg)


def test_download_worker_strips_ansi(monkeypatch):
    import workers.download_worker as dw
    monkeypatch.setattr(dw, "Downloader", _FailingDownloader)
    w = dw.DownloadWorker("u", "best", "mp4", ".")
    got = _errors(w)
    w.run()
    assert len(got) == 1 and "\x1b" not in got[0] and CLEAN in got[0]


def test_download_worker_retries_ansi_transient(monkeypatch):
    import workers.download_worker as dw

    class _Transient(_FailingDownloader):
        msg = "\x1b[0;31mERROR:\x1b[0m HTTP Error 503: Service Unavailable"

    monkeypatch.setattr(dw, "Downloader", _Transient)
    w = dw.DownloadWorker("u", "best", "mp4", ".")
    monkeypatch.setattr(w, "_sleep_cancellable", lambda _s: False)
    retries = []
    w.retrying.connect(lambda cur, mx: retries.append(cur))
    got = _errors(w)
    w.run()
    assert retries == [1, 2, 3]
    assert got == ["ERROR: HTTP Error 503: Service Unavailable"]


def test_info_worker_strips_ansi():
    from workers.info_worker import InfoWorker

    class _Fetcher:
        def fetch(self, _url):
            raise DownloadError(RAW)

    w = InfoWorker("u")
    w._fetcher = _Fetcher()
    got = _errors(w)
    w.run()
    assert got == [CLEAN]


def test_playlist_probe_worker_strips_ansi(monkeypatch):
    import workers.playlist_probe_worker as pw

    class _YDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def extract_info(self, *_a, **_k):
            raise DownloadError(RAW)

    monkeypatch.setattr(pw.yt_dlp, "YoutubeDL", _YDL)
    w = pw.PlaylistProbeWorker("u")
    got = _errors(w)
    w.run()
    assert got == [CLEAN]
