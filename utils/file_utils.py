# utils/file_utils.py
# 파일 경로, 이름, 확장자 관련 유틸리티 함수 모음

import os
import re
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """
    파일명으로 사용할 수 없는 특수문자를 제거하거나 치환
    Windows 기준으로 처리 (가장 엄격한 기준)
    """
    # 윈도우 금지 문자 제거: \ / : * ? " < > |
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    # 앞뒤 공백 및 점 제거
    name = name.strip(". ")
    # 빈 문자열 방지
    if not name:
        name = "download"
    # 최대 파일명 길이 제한 (255자)
    return name[:200]


def ensure_dir(path: str) -> str:
    """
    경로가 존재하지 않으면 폴더를 생성
    생성된(또는 기존) 경로 문자열 반환
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def get_unique_path(save_dir: str, title: str, ext: str) -> str:
    """
    저장 경로에 같은 이름의 파일이 있으면
    (1), (2) 형태로 번호를 붙여서 고유한 경로 반환
    """
    base_name = sanitize_filename(title)
    target = Path(save_dir) / f"{base_name}.{ext}"

    counter = 1
    while target.exists():
        target = Path(save_dir) / f"{base_name} ({counter}).{ext}"
        counter += 1

    return str(target)


def format_file_size(bytes_size: int) -> str:
    """
    바이트 수를 사람이 읽기 쉬운 문자열로 변환
    예: 1048576 → "1.00 MB"
    """
    if bytes_size <= 0:
        return "알 수 없음"

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024

    return f"{bytes_size:.2f} PB"


def format_duration(seconds: int) -> str:
    """
    초 단위 영상 길이를 시:분:초 형태로 변환
    예: 3661 → "1:01:01"
    """
    if seconds <= 0:
        return "0:00"

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def open_folder(path: str):
    """
    해당 경로를 Windows 탐색기로 열기
    """
    import subprocess
    if os.path.isfile(path):
        # 파일이면 해당 파일을 탐색기에서 선택한 채로 열기
        subprocess.run(["explorer", "/select,", path])
    elif os.path.isdir(path):
        # 폴더면 그냥 열기
        subprocess.run(["explorer", path])