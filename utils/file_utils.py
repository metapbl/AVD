# utils/file_utils.py
# 파일 경로, 이름, 확장자 관련 유틸리티 함수 모음

import os
import logging
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


# ── 자식 프로세스 추적 헬퍼 ─────────────────────────────────
# yt-dlp 는 다운로드/후처리 과정에서 ffmpeg.exe 와 node.exe(EJS 챌린지) 를
# 자식 프로세스로 띄운다. 사용자가 취소를 누른 직후에도 이 자식들이 살아
# 있으면 Windows 의 파일 잠금 때문에 .part / .ytdl 잔여물 삭제가 실패한다.
#
# 동시 다운로드 환경에서 "내 워커가 띄운 자식만" 안전하게 잡으려면 ──
# 다른 워커의 자식까지 죽이면 그쪽 다운로드가 망가지므로 ── 워커가
# 시작 직전에 자기 부모(=앱) 프로세스의 자식 PID 를 스냅샷하고, 취소
# 시점에 다시 스냅샷해서 "내가 도는 동안 새로 늘어난 PID" 만 종료한다.

_psutil_logger = logging.getLogger(__name__)


def snapshot_child_pids() -> set[int]:
    """
    현재 우리 파이썬 프로세스의 모든 자손 PID 집합을 반환.

    psutil 이 설치되어 있지 않거나 (선택 의존성) 권한 문제로 조회가
    실패하면 빈 집합을 반환한다. 호출자는 빈 집합을 "추적 불가" 의
    의미로 받아들여 자식 종료 로직 자체를 우회한다.
    """
    try:
        import psutil
    except ImportError:
        _psutil_logger.warning(
            "psutil 이 설치되어 있지 않아 자식 프로세스 추적을 건너뜁니다."
        )
        return set()

    try:
        me = psutil.Process(os.getpid())
        return {child.pid for child in me.children(recursive=True)}
    except psutil.Error:
        # NoSuchProcess / AccessDenied — 무시하고 빈 집합
        return set()


def terminate_pids(pids: set[int], grace_seconds: float = 5.0) -> None:
    """
    주어진 PID 집합의 프로세스들을 우아하게 종료시킨다.

    먼저 terminate() 로 SIGTERM 상당의 신호를 보내고, grace_seconds 안에
    종료되지 않으면 kill() 로 강제 종료한다. 동시에 여러 PID 를 처리하므로
    개별 PID 의 wait 가 직렬로 누적되지 않도록 일괄 terminate 후 일괄 wait
    하는 패턴을 쓴다.

    psutil 미설치 / 빈 집합 / 이미 죽은 PID 는 조용히 통과한다.
    """
    if not pids:
        return

    try:
        import psutil
    except ImportError:
        return

    procs: list = []
    for pid in pids:
        try:
            procs.append(psutil.Process(pid))
        except psutil.NoSuchProcess:
            continue
        except psutil.Error:
            continue

    # 1단계: 일괄 terminate
    for p in procs:
        try:
            p.terminate()
        except psutil.Error:
            pass

    # 2단계: 일괄 대기
    gone, alive = psutil.wait_procs(procs, timeout=grace_seconds)

    # 3단계: 여전히 살아 있으면 강제 종료
    for p in alive:
        try:
            p.kill()
        except psutil.Error:
            pass
