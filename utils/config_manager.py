# utils/config_manager.py
# 앱 설정을 JSON 파일로 저장하고 불러오는 파일

import json
from pathlib import Path


# 설정 파일 저장 위치 (앱 폴더 안에 config.json)
CONFIG_PATH = Path(__file__).parent.parent / "config.json"

# 기본 설정값
# 기본 설정값
DEFAULT_CONFIG = {
    "save_path"         : str(Path.home() / "Downloads"),  # 기본 저장 경로
    "max_concurrent"    : 2,       # 동시 다운로드 최대 개수
    "default_format"    : "bestvideo+bestaudio/best",  # 기본 화질
    "default_ext"       : "mp4",   # 기본 확장자 (UI 노출 안 함, 잔존 키)
    "last_chosen_ext"   : "",      # FormatSelectDialog 가 기억하는 직전 선택 확장자
    "auto_update_ytdlp" : True,    # yt-dlp 자동 업데이트 여부
    "theme"             : "dark",  # UI 테마 (dark / light)
    "language"          : "ko",    # 언어 설정
}


class ConfigManager:
    """앱 설정을 관리하는 클래스"""

    def __init__(self):
        self._config = {}
        self.load()

    def load(self):
        """설정 파일을 불러옴. 없으면 기본값으로 생성"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # 기본값 기준으로 병합 (새로 추가된 키 누락 방지)
                self._config = {**DEFAULT_CONFIG, **saved}
            except Exception:
                # 파일이 손상된 경우 기본값으로 초기화
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self.save()  # 최초 실행 시 파일 생성

    def save(self):
        """현재 설정을 파일에 저장"""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ConfigManager] 설정 저장 실패: {e}")

    def get(self, key: str, fallback=None):
        """설정값 읽기"""
        return self._config.get(key, fallback)

    def set(self, key: str, value):
        """설정값 쓰기 후 자동 저장"""
        self._config[key] = value
        self.save()

    def get_all(self) -> dict:
        """전체 설정값 반환"""
        return self._config.copy()