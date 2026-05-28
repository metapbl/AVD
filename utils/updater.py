# utils/updater.py
# yt-dlp 버전 체크 및 업데이트, 앱 자체 업데이트를 담당하는 파일

import subprocess
import sys
import requests
import yt_dlp
from pathlib import Path


# 앱 현재 버전 (배포 시 이 값을 변경)
APP_VERSION = "1.0.0"

# GitHub 저장소 주소 (나중에 본인 저장소로 변경)
GITHUB_REPO = "metapbl/AVD"

# yt-dlp GitHub API 주소
YTDLP_API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

# 앱 GitHub API 주소
APP_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


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


class AppUpdater:
    """앱 자체 버전 체크 및 업데이트 클래스"""

    def get_current_version(self) -> str:
        """현재 앱 버전 반환"""
        return APP_VERSION

    def get_latest_release(self) -> tuple[str | None, str | None]:
        """
        GitHub에서 최신 앱 릴리즈 정보 가져오기
        반환값: (최신버전, 다운로드URL)
        """
        try:
            res = requests.get(APP_API_URL, timeout=5)
            res.raise_for_status()
            data    = res.json()
            version = data.get("tag_name")
            assets  = data.get("assets", [])
            url     = assets[0]["browser_download_url"] if assets else None
            return version, url
        except Exception as e:
            print(f"[AppUpdater] 버전 확인 실패: {e}")
            return None, None

    def is_update_available(self) -> tuple[bool, str, str]:
        """
        앱 업데이트 필요 여부 반환
        반환값: (업데이트필요여부, 현재버전, 최신버전)
        """
        current        = self.get_current_version()
        latest, _      = self.get_latest_release()

        if latest is None:
            return False, current, current

        return current != latest, current, latest

    def download_update(self, url: str, progress_callback=None) -> Path | None:
        """
        새 버전 exe 다운로드
        progress_callback(percent: int) 으로 진행률 전달
        성공 시 임시 파일 경로 반환, 실패 시 None
        """
        try:
            res     = requests.get(url, stream=True, timeout=30)
            total   = int(res.headers.get("content-length", 0))
            done    = 0
            tmp     = Path("_update_temp.exe")

            with open(tmp, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
                    done += len(chunk)
                    if total and progress_callback:
                        progress_callback(int(done / total * 100))

            return tmp
        except Exception as e:
            print(f"[AppUpdater] 다운로드 실패: {e}")
            return None

    def replace_and_restart(self, new_exe: Path):
        """
        현재 실행 중인 exe를 새 버전으로 교체 후 재시작
        배치 스크립트를 통해 실행 중인 파일 교체
        """
        current_exe = Path(sys.executable)
        bat         = Path("_update.bat")

        bat.write_text(
            f"@echo off\n"
            f"timeout /t 2 /nobreak > nul\n"
            f"move /y \"{new_exe}\" \"{current_exe}\"\n"
            f"start \"\" \"{current_exe}\"\n"
            f"del \"%~f0\"\n",
            encoding="utf-8"
        )

        subprocess.Popen(str(bat), shell=True)
        sys.exit()