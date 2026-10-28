# 특성 테스트: workers/download_worker.py 의 모듈 수준 파싱 함수.
# 기대값은 2026-10-28 현재 코드의 동작이다 (고칠 때 이 테스트를 함께 바꾼다).
import pytest

from workers.download_worker import (
    _format_eta_secs,
    _is_transient_error,
    _is_unknown_size,
    _normalize_size_str,
    _parse_eta_secs,
    _split_size_str,
)


@pytest.mark.parametrize("msg", [
    "ERROR: unable to download video data: HTTP Error 403: Forbidden",  # 토큰 만료 (T3)
    "HTTP Error 429: Too Many Requests",
    "HTTP Error 503: Service Unavailable",
    "Read timed out",
    "Connection reset by peer",
    "Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>",
])
def test_transient_errors(msg):
    assert _is_transient_error(msg) is True


@pytest.mark.parametrize("msg", [
    # 포장된 영구 4xx 는 일시 패턴 "unable to download webpage" 보다 먼저 영구로 (T4)
    "Unable to download webpage: HTTP Error 404: Not Found",
    "HTTP Error 400: Bad Request",
    "HTTP Error 401: Unauthorized",
    "HTTP Error 410: Gone",
    # 403 이 섞여도 영구 패턴이 우선
    "Video unavailable. This video is private (HTTP Error 403)",
    "Sign in to confirm you're not a bot",
    "Unsupported URL: https://example.com",
    # 어디에도 안 걸리면 보수적으로 영구
    "something completely different",
    "",
])
def test_permanent_or_unknown_errors(msg):
    assert _is_transient_error(msg) is False


def test_transient_error_none_message():
    # 타입 힌트는 str 이지만 코드가 None 을 받아 준다 (msg or "") — 그 동작을 고정
    assert _is_transient_error(None) is False  # pyright: ignore[reportArgumentType]


def test_transient_error_case_insensitive():
    assert _is_transient_error("http error 502") is True
    assert _is_transient_error("HTTP ERROR 404") is False


@pytest.mark.parametrize("s, expected", [
    ("00:42", 42),
    ("1:23:45", 1 * 3600 + 23 * 60 + 45),
    ("~0:42", 42),
    ("  12:05  ", 12 * 60 + 5),
    ("", -1),
    ("~", -1),
    ("42", -1),            # 콜론 없는 단일 숫자는 실패
    ("1:2:3:4", -1),
    ("ab:cd", -1),
    ("Unknown", -1),
])
def test_parse_eta_secs(s, expected):
    assert _parse_eta_secs(s) == expected


@pytest.mark.parametrize("secs, is_estimate, expected", [
    (42, False, "0:42"),
    (42, True, "약 0:42"),
    (0, False, "0:00"),
    (3599, False, "59:59"),
    (3600, False, "1:00:00"),
    (3725, True, "약 1:02:05"),
    (-1, False, ""),
    (-1, True, ""),
])
def test_format_eta_secs(secs, is_estimate, expected):
    assert _format_eta_secs(secs, is_estimate) == expected


@pytest.mark.parametrize("s, expected", [
    ("48.20MiB", ("48.20", "MiB")),
    ("1.25GiB", ("1.25", "GiB")),
    ("  512KiB ", ("512", "KiB")),
    ("10.0 MiB", ("10.0", "MiB")),
    ("123", ("123", "")),          # 단위 없음
    ("MiB", ("MiB", "")),          # 숫자 없음
    ("", ("", "")),
])
def test_split_size_str(s, expected):
    assert _split_size_str(s) == expected


@pytest.mark.parametrize("s, expected", [
    ("48.20MiB", "48.20 MiB"),
    ("1.25GiB", "1.25 GiB"),
    (" 123 ", "123"),
    ("Unknown", "Unknown"),
])
def test_normalize_size_str(s, expected):
    assert _normalize_size_str(s) == expected


@pytest.mark.parametrize("s, expected", [
    ("", True),
    ("Unknown", True),
    ("Unknown ETA", True),
    (" N / A ", True),
    ("--:--", True),
    ("00:00:00", True),
    ("48.20MiB", False),
    ("0B", False),
])
def test_is_unknown_size(s, expected):
    assert _is_unknown_size(s) is expected
