# utils/file_utils.py
# 파일 경로, 이름, 확장자 관련 유틸리티 함수 모음

import os
import re
import unicodedata
from pathlib import Path


def normalize_unicode(text: str) -> str:
    """
    문자열을 유니코드 NFC 로 정규화한다.

    SoundCloud · macOS 등 일부 소스에서 한글이 NFD(자모 분리, U+1100~U+11FF)
    로 들어오는 경우가 있다. Windows 탐색기·일부 콘솔 폰트는 NFD 를 NFC 처럼
    합쳐 그려주기 때문에 표시상 같아 보이지만, 바이트 수준에서는 분해되어
    있어 ID3 태그·파일명에서 글자 깨짐을 유발한다. 모든 진입 지점에서
    이 함수를 통과시켜 NFC 로 통일한다.

    None / 비문자열은 안전하게 원형 반환.
    """
    if not isinstance(text, str):
        return text
    return unicodedata.normalize("NFC", text)


def normalize_info_dict(info):
    """
    yt-dlp 가 반환한 info dict 의 모든 문자열 값을 재귀적으로 NFC 로 정규화.

    dict · list · 문자열만 재귀하며, bytes / 숫자 / None 등은 그대로 둔다.
    bytes 는 raw 응답일 수 있어 decode 시도하지 않는다.
    """
    if isinstance(info, dict):
        return {k: normalize_info_dict(v) for k, v in info.items()}
    if isinstance(info, list):
        return [normalize_info_dict(v) for v in info]
    if isinstance(info, str):
        return normalize_unicode(info)
    return info


def sanitize_filename(name: str) -> str:
    """
    파일명으로 사용할 수 없는 특수문자를 제거하거나 치환
    Windows 기준으로 처리 (가장 엄격한 기준)
    """
    # 유니코드 정규화 (NFD → NFC). 한글 자모 분리 방지.
    name = normalize_unicode(name)
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


def format_duration(seconds: int | float | None) -> str:
    """
    초 단위 영상 길이를 시:분:초 형태로 변환
    예: 3661 → "1:01:01"

    yt-dlp 의 duration 은 영상에 따라 int 또는 float 로 반환되며,
    라이브/일부 플랫폼에서는 None 일 수도 있다. 경계에서 정규화한다.
    """
    if seconds is None:
        return "0:00"
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return "0:00"
    if total <= 0:
        return "0:00"

    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60

    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    """
    yt-dlp 가 진행률 메시지에 섞어 보내는 ANSI 컬러 이스케이프 시퀀스를 제거한다.
    CLI 에서는 색상 표시지만 GUI 의 QLabel 은 해석하지 못해
    □[0;32m 처럼 깨져 보인다. 출구(워커 → GUI) 단계에서 한 번 통과시킨다.
    """
    if not text:
        return text
    return _ANSI_ESCAPE_RE.sub("", text)


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
