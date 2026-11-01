# utils/updater.py
# yt-dlp 버전 체크 및 업데이트, 앱 자체 업데이트를 담당하는 파일

import hashlib
import io
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests
import yt_dlp

# 앱 현재 버전 (배포 시 이 값을 변경)
APP_VERSION = "1.0.2"

# yt-dlp GitHub API 주소
YTDLP_API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

# yt-dlp PyPI 정보 주소 (exe 배포본의 wheel 교체용)
PYPI_YTDLP_URL = "https://pypi.org/pypi/yt-dlp/json"


def restart_command() -> list[str]:
    """지금 앱을 같은 방식으로 다시 띄우는 명령 (D041). exe 는 argv[0] 이 exe 자신이라 뺀다"""
    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]
    return [sys.executable, *sys.argv]


def install_ytdlp_wheel(dest_dir: Path, on_line=print) -> bool:
    """
    exe 배포본용 yt-dlp 업데이트 (D038). pip 이 없으니 PyPI 의 순수 파이썬
    wheel 을 받아 sha256 대조 뒤 dest_dir/yt_dlp 폴더를 통째로 바꾼다.
    다시 시작해야 적용된다. 성공 시 True, 실패 시 기존 폴더를 그대로 두고 False
    """
    target = dest_dir / "yt_dlp"
    old    = dest_dir / "yt_dlp.old"
    try:
        res = requests.get(PYPI_YTDLP_URL, timeout=10)
        res.raise_for_status()
        wheel = next(
            u for u in res.json()["urls"]
            if u["filename"].endswith("-py3-none-any.whl")
        )
        on_line(f"받는 중: {wheel['filename']}")
        res = requests.get(wheel["url"], timeout=60)
        res.raise_for_status()
        if hashlib.sha256(res.content).hexdigest() != wheel["digests"]["sha256"]:
            on_line("받은 파일의 sha256 이 PyPI 값과 달라 버립니다.")
            return False

        with tempfile.TemporaryDirectory(dir=dest_dir) as tmp:
            with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
                zf.extractall(tmp, [m for m in zf.namelist() if m.startswith("yt_dlp/")])
            on_line("yt-dlp 폴더 교체 중")
            shutil.rmtree(old, ignore_errors=True)  # 지난번 실패의 찌꺼기
            target.rename(old)
            try:
                (Path(tmp) / "yt_dlp").rename(target)
            except Exception:
                old.rename(target)
                raise
        shutil.rmtree(old, ignore_errors=True)
        return True
    except Exception as e:
        on_line(f"업데이트 실패: {e}")
        return False


class YtdlpUpdater:
    """yt-dlp 버전 체크 및 업데이트 클래스"""

    def get_current_version(self) -> str:
        """현재 설치된 yt-dlp 버전 반환"""
        return yt_dlp.version.__version__

    def get_latest_version(self) -> str | None:
        """
        GitHub에서 yt-dlp 최신 버전 태그 가져오기
        네트워크 오류 시 None 반환
        """
        try:
            res = requests.get(YTDLP_API_URL, timeout=5)
            res.raise_for_status()
            return res.json().get("tag_name")
        except Exception as e:
            print(f"[YtdlpUpdater] 버전 확인 실패: {e}")
            return None

    def is_update_available(self) -> tuple[bool, str, str]:
        """
        업데이트 필요 여부 반환
        반환값: (업데이트필요여부, 현재버전, 최신버전)
        """
        current = self.get_current_version()
        latest  = self.get_latest_version()

        if latest is None:
            return False, current, current

        return current != latest, current, latest

    def update(self) -> bool:
        """
        yt-dlp를 최신 버전으로 업그레이드
        성공 시 True, 실패 시 False 반환
        """
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip",
                "install", "--upgrade", "yt-dlp"
            ])
            return True
        except Exception as e:
            print(f"[YtdlpUpdater] 업데이트 실패: {e}")
            return False
