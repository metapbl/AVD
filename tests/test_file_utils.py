# 특성 테스트: utils/file_utils.py 의 파일명·길이 함수.
# 기대값은 2026-10-28 현재 코드의 동작이다 (고칠 때 이 테스트를 함께 바꾼다).
import unicodedata

import pytest

from utils.file_utils import (
    format_duration,
    get_unique_path,
    normalize_unicode,
    sanitize_filename,
)

NFC = "한글 제목"
NFD = unicodedata.normalize("NFD", NFC)


def test_normalize_unicode_nfd_to_nfc():
    # 자모 분리(NFD)는 바이트로 판정한다 — 화면에선 같아 보인다 (T9)
    assert NFD != NFC
    assert normalize_unicode(NFD) == NFC
    assert normalize_unicode(NFC) == NFC


@pytest.mark.parametrize("value", [None, 123, b"bytes"])
def test_normalize_unicode_non_str_passthrough(value):
    assert normalize_unicode(value) is value


@pytest.mark.parametrize("name, expected", [
    ('a\\b/c:d*e?f"g<h>i|j', "a_b_c_d_e_f_g_h_i_j"),   # Windows 금지 문자 9종
    ("  title.  ", "title"),                           # 앞뒤 공백·점 제거
    ("...", "download"),                               # 비면 기본 이름
    ("", "download"),
    ("a" * 300, "a" * 200),                            # 200자 자름
])
def test_sanitize_filename(name, expected):
    assert sanitize_filename(name) == expected


def test_sanitize_filename_nfd_to_nfc():
    assert sanitize_filename(NFD) == NFC


def test_get_unique_path_numbering(tmp_path):
    first = get_unique_path(str(tmp_path), "video", "mp4")
    assert first == str(tmp_path / "video.mp4")

    (tmp_path / "video.mp4").touch()
    assert get_unique_path(str(tmp_path), "video", "mp4") == str(tmp_path / "video (1).mp4")

    (tmp_path / "video (1).mp4").touch()
    assert get_unique_path(str(tmp_path), "video", "mp4") == str(tmp_path / "video (2).mp4")


def test_get_unique_path_sanitizes_title(tmp_path):
    assert get_unique_path(str(tmp_path), "a:b", "mp3") == str(tmp_path / "a_b.mp3")


@pytest.mark.parametrize("seconds, expected", [
    (None, "0:00"),
    (0, "0:00"),
    (-5, "0:00"),
    ("abc", "0:00"),
    (59, "0:59"),
    (59.9, "0:59"),        # float 는 버림
    (60, "1:00"),
    (3599, "59:59"),
    (3600, "1:00:00"),
    (3661, "1:01:01"),
    (36000, "10:00:00"),
])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected
