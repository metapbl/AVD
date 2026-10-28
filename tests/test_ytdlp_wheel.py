# exe 배포본의 yt-dlp 교체 — PyPI wheel 받기·sha256 대조·폴더 교체 (D038).
# 네트워크는 가짜 응답, wheel 은 테스트에서 만든 zip 이다.
import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from utils import updater

WHEEL_URL = "https://files.example/yt_dlp-NEW-py3-none-any.whl"


def make_wheel() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("yt_dlp/__init__.py", "")
        zf.writestr("yt_dlp/version.py", "__version__ = 'NEW'\n")
        zf.writestr("yt_dlp-NEW.dist-info/METADATA", "Name: yt-dlp\n")
    return buf.getvalue()


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def dest(tmp_path):
    (tmp_path / "yt_dlp").mkdir()
    (tmp_path / "yt_dlp" / "version.py").write_text("__version__ = 'OLD'\n")
    return tmp_path


def fake_pypi(monkeypatch, sha256: str):
    wheel = make_wheel()
    index = {"urls": [
        {"filename": "yt_dlp-NEW.tar.gz", "url": "x", "digests": {"sha256": "x"}},
        {"filename": "yt_dlp-NEW-py3-none-any.whl", "url": WHEEL_URL,
         "digests": {"sha256": sha256 or hashlib.sha256(wheel).hexdigest()}},
    ]}

    def get(url, **_):
        if url == updater.PYPI_YTDLP_URL:
            return FakeResponse(payload=index)
        assert url == WHEEL_URL
        return FakeResponse(content=wheel)

    monkeypatch.setattr(updater.requests, "get", get)


def version_of(dest: Path) -> str:
    return (dest / "yt_dlp" / "version.py").read_text()


def test_install_replaces_folder(monkeypatch, dest):
    fake_pypi(monkeypatch, sha256="")
    assert updater.install_ytdlp_wheel(dest, on_line=lambda _: None) is True
    assert "NEW" in version_of(dest)
    assert not (dest / "yt_dlp.old").exists()
    assert not (dest / "yt_dlp-NEW.dist-info").exists()


def test_sha256_mismatch_keeps_old(monkeypatch, dest):
    fake_pypi(monkeypatch, sha256="0" * 64)
    assert updater.install_ytdlp_wheel(dest, on_line=lambda _: None) is False
    assert "OLD" in version_of(dest)


def test_swap_failure_restores_old(monkeypatch, dest):
    fake_pypi(monkeypatch, sha256="")
    real_rename = Path.rename

    def rename(self, target):
        if self.parent != dest:  # 임시 폴더 → yt_dlp 로 옮기는 두 번째 이동만 실패
            raise OSError("locked")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", rename)
    assert updater.install_ytdlp_wheel(dest, on_line=lambda _: None) is False
    assert "OLD" in version_of(dest)
    assert not (dest / "yt_dlp.old").exists()
