"""gaindb/tag.py — 태그 처리 (4단계).

원본 mp3gain apetag.c 와 동일한 결과·포맷을 산출하는 clean-room 독립 구현.
공개 사양(APEv2 포맷·필드명)과 관찰된 동작만 차용하고 코드는 독립 작성한다.
이 파일 단계 ①: APEv2 읽기 파서 (전 필드 + otherFields 보존 + Lyrics3/ID3v1 꼬리 감지).

원본 대응:
  struct MP3GainTagInfo   -> MP3GainTagInfo
  struct APETagStruct     -> ApeTag
  struct FileTagsStruct   -> FileTags
  ReadMP3APETag           -> _read_ape_tag
  ReadMP3Lyrics3v2Tag     -> _read_lyrics3v2_tag
  ReadMP3ID3v1Tag         -> _read_id3v1_tag
  ReadMP3GainAPETag       -> read_mp3gain_ape_tag
  WriteMP3GainTag         -> _write_mp3gain_tag        (⑤-C; useId3 분기 래퍼)
  (main 의 태그 읽기 분기) -> read_mp3gain_tags          (⑤-C; APE→ID3 순서)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import BinaryIO, Optional

# 원본: enum { MAX_FIELD_SIZE = 1024*1024 } — 이보다 큰 필드는 오류로 간주.
MAX_FIELD_SIZE = 1024 * 1024

# APE 푸터/헤더는 고정 32바이트 (struct APETagFooterStruct).
APE_FOOTER_SIZE = 32

# APE Flags bit31: 이 태그에 헤더가 존재함(footer 의 bit31) 또는
# "이것이 헤더다"(header 의 bit31). 원본의 1<<31.
APE_FLAG_HAS_HEADER = 1 << 31


def _read_le32(b: bytes, off: int = 0) -> int:
    """원본 Read_LE_Uint32: 리틀엔디언 4바이트 부호 없는 정수."""
    return b[off] | (b[off + 1] << 8) | (b[off + 2] << 16) | (b[off + 3] << 24)


def _strlen_max(b: bytes, start: int, max_len: int) -> int:
    """원본 strlen_max: start 부터 NUL 까지의 길이, 단 max_len 으로 상한."""
    n = 0
    while n < max_len and b[start + n] != 0:
        n += 1
    return n


@dataclass
class MP3GainTagInfo:
    """원본 struct MP3GainTagInfo 대응.

    APE/ID3 공용 게인 정보 컨테이너. 읽기 시 인식한 필드만 have_* 가 True.
    """

    have_track_gain: bool = False
    have_track_peak: bool = False
    have_album_gain: bool = False
    have_album_peak: bool = False
    have_undo: bool = False
    have_min_max_gain: bool = False
    have_album_min_max_gain: bool = False

    track_gain: float = 0.0
    track_peak: float = 0.0
    album_gain: float = 0.0
    album_peak: float = 0.0

    undo_left: int = 0
    undo_right: int = 0
    undo_wrap: bool = False

    # 원본은 unsigned char (0~255). 프레임 global_gain 의 현재 min/max.
    min_gain: int = 0
    max_gain: int = 0
    album_min_gain: int = 0
    album_max_gain: int = 0

    # 원본: dirty(로드 후 변경 여부), recalc(재계산 필요 비트마스크).
    # 쓰기/오케스트레이션 단계(③~)에서 사용. 읽기 단계에서는 건드리지 않음.
    dirty: bool = False
    recalc: int = 0


@dataclass
class ApeTag:
    """원본 struct APETagStruct 대응.

    footer/header 는 원본 32바이트를 그대로 보존(Version/Flags/Reserved 유지).
    LE 정수 접근은 _read_le32 헬퍼로. other_fields 는 인식 못 한 필드들의
    원본 바이트(각 필드의 vsize/flags 헤더 포함)를 그대로 이어붙인 블록.
    """

    have_header: bool = False
    header: Optional[bytes] = None        # 32바이트 또는 None
    footer: bytes = b""                   # 32바이트
    other_fields: bytes = b""             # 비-mp3gain 필드 원본 바이트
    other_fields_size: int = 0
    original_tag_size: int = 0            # 파일에서 깎인 총 바이트(헤더 있으면 +32)


@dataclass
class FileTags:
    """원본 struct FileTagsStruct 대응.

    tag_offset 는 오디오 본문이 끝나고 모든 꼬리 태그가 시작되는 위치.
    """

    tag_offset: int = 0
    ape_tag: Optional[ApeTag] = None
    lyrics3_tag: Optional[bytes] = None
    lyrics3_tag_size: int = 0
    id3v1_tag: Optional[bytes] = None


def _lyrics3_number6(b: bytes) -> int:
    """원본 Lyrics3GetNumber6: 6자리 ASCII 숫자. 비숫자면 0."""
    n = 0
    for i in range(6):
        c = b[i]
        if c < 0x30 or c > 0x39:  # '0'..'9'
            return 0
        n = n * 10 + (c - 0x30)
    return n


def _read_id3v1_tag(f: BinaryIO, file_tags: FileTags, tag_offset: int) -> int:
    """원본 ReadMP3ID3v1Tag.

    tag_offset 직전 128바이트가 'TAG' 로 시작하면 ID3v1 으로 보고 보존.
    찾으면 새 tag_offset(=128 깎은 값) 반환, 아니면 원래 tag_offset 그대로 반환.
    """
    if tag_offset < 128:
        return tag_offset
    f.seek(tag_offset - 128)
    tmp = f.read(128)
    if len(tmp) != 128 or tmp[:3] != b"TAG":
        return tag_offset
    file_tags.id3v1_tag = tmp
    return tag_offset - 128


def _read_lyrics3v2_tag(f: BinaryIO, file_tags: FileTags, tag_offset: int) -> int:
    """원본 ReadMP3Lyrics3v2Tag.

    Lyrics3v2 는 정의상 그 뒤에 ID3v1(128B)이 붙어 있다. 구조:
      ... LYRICSBEGIN <body> <6자리길이> LYRICS200 <ID3v1 128B>
    감지되면 ID3v1 을 보존하고, Lyrics3 전체(128 + footer(15) + body)를 보존.
    찾으면 깎은 tag_offset, 아니면 원래 값 반환.
    """
    if tag_offset < 128:
        return tag_offset
    f.seek(tag_offset - 128)
    tmpid3 = f.read(128)
    if len(tmpid3) != 128 or tmpid3[:3] != b"TAG":
        return tag_offset
    # ID3v1 보존 (Lyrics3 는 정의상 id3v1 을 포함).
    file_tags.id3v1_tag = tmpid3

    # Lyrics3v2 footer 는 ID3v1 바로 앞 15바이트: Length[6] + ID[9].
    if tag_offset < 128 + 15:
        return tag_offset
    f.seek(tag_offset - 128 - 15)
    footer = f.read(15)
    if len(footer) != 15 or footer[6:15] != b"LYRICS200":
        return tag_offset

    body_len = _lyrics3_number6(footer[0:6])
    # 원본: tag_offset - 128 - sizeof(T) - len 위치에 'LYRICSBEGIN' 가 있어야 함.
    if tag_offset < 128 + 15 + body_len:
        return tag_offset
    f.seek(tag_offset - 128 - 15 - body_len)
    begin = f.read(11)
    if len(begin) != 11 or begin != b"LYRICSBEGIN":
        return tag_offset

    # 전체 Lyrics3 태그(footer + body + 뒤의 id3v1 128) 보존.
    tag_len = 128 + body_len + 15
    new_offset = tag_offset - tag_len
    f.seek(new_offset)
    file_tags.lyrics3_tag = f.read(tag_len)
    file_tags.lyrics3_tag_size = tag_len
    return new_offset


def _read_ape_tag(
    f: BinaryIO, info: MP3GainTagInfo, file_tags: FileTags, tag_offset: int
) -> int:
    """원본 ReadMP3APETag.

    tag_offset 직전에서 APEv1/v2 푸터를 찾아 파싱한다.
    인식 필드(REPLAYGAIN_*, MP3GAIN_*)는 info 에 채우고, 나머지는 ape_tag.other_fields
    에 원본 바이트 그대로 보존. 찾으면 깎은 tag_offset, 아니면 원래 값 반환.

    APE 푸터/헤더 구조(각 4바이트 LE): ID[8] Version[8..] Length[12..]
    TagCount[16..] Flags[20..] Reserved[24..32].
    """
    if tag_offset < APE_FOOTER_SIZE:
        return tag_offset

    # 푸터 읽기 (파일 끝 직전 32바이트).
    f.seek(tag_offset - APE_FOOTER_SIZE)
    footer = f.read(APE_FOOTER_SIZE)
    if len(footer) != APE_FOOTER_SIZE or footer[0:8] != b"APETAGEX":
        return tag_offset

    version = _read_le32(footer, 8)
    if version not in (1000, 2000):
        return tag_offset

    tag_len = _read_le32(footer, 12)  # 푸터 포함·헤더 제외 길이
    if tag_len < APE_FOOTER_SIZE or tag_offset < tag_len:
        return tag_offset

    orig_tag_count = _read_le32(footer, 16)  # TagCount: offset 16
    footer_flags = _read_le32(footer, 20)    # Flags:    offset 20

    # 필드 데이터(푸터 직전 tag_len - 32 바이트) 읽기.
    body_len = tag_len - APE_FOOTER_SIZE
    f.seek(tag_offset - tag_len)
    body = f.read(body_len)
    if len(body) != body_len:
        return tag_offset

    ape = ApeTag()
    ape.footer = footer
    # other_fields 는 최대 body 크기. 인식 못 한 필드 바이트를 누적.
    other = bytearray()
    other_count = 0

    p = 0
    remaining_count = orig_tag_count
    while p < body_len and remaining_count > 0:
        remaining_count -= 1
        if body_len - p < 8:
            break
        vsize = _read_le32(body, p)
        # flags = _read_le32(body, p + 4)  # 보존만, 해석 안 함
        field_start = p          # vsize/flags 포함 필드 시작(원본의 'p - 8' 대응)
        p += 8

        remaining = body_len - p
        isize = _strlen_max(body, p, remaining)
        # 경계/크기 검사 (원본과 동일).
        if isize >= remaining or vsize > MAX_FIELD_SIZE or isize + 1 + vsize > remaining:
            break

        name = body[p : p + isize].decode("ascii", errors="replace")
        value_bytes = body[p + isize + 1 : p + isize + 1 + vsize]
        value = value_bytes.decode("utf-8", errors="replace")

        recognized = _store_ape_field(name, value, info)

        if not recognized:
            # 인식 못 한 필드는 vsize/flags 헤더 포함 원본 바이트 그대로 보존.
            block_len = 8 + isize + 1 + vsize
            other += body[field_start : field_start + block_len]
            other_count += 1

        p += isize + 1 + vsize

    ape.other_fields = bytes(other)
    ape.other_fields_size = len(other)

    new_offset = tag_offset - tag_len
    ape.original_tag_size = tag_len

    # 헤더 존재 시(footer flags bit31) 추가로 32바이트 읽고 깎음.
    if footer_flags & APE_FLAG_HAS_HEADER:
        if new_offset < APE_FOOTER_SIZE:
            # 원본은 여기서 return (이미 ape 는 세팅됨). 보수적으로 보존만.
            file_tags.ape_tag = ape
            return new_offset
        new_offset -= APE_FOOTER_SIZE
        f.seek(new_offset)
        ape.header = f.read(APE_FOOTER_SIZE)
        ape.have_header = True
        ape.original_tag_size += APE_FOOTER_SIZE

    file_tags.ape_tag = ape
    return new_offset


def _store_ape_field(name: str, value: str, info: MP3GainTagInfo) -> bool:
    """APE 필드 하나를 info 에 반영. 인식했으면 True, 아니면 False(=otherFields 행).
    APEv2 게인 필드를 인식해 info 에 반영한다. 매칭은 대소문자 무시.
    UNDO/MINMAX 의 고정 오프셋 슬라이싱은 태그 값 포맷("+003,+003,W" ·
    "001,153")에서 도출된 것이며, 원본과 동일한 결과를 낸다.
    """
    upper = name.upper()

    if upper == "REPLAYGAIN_TRACK_GAIN":
        info.have_track_gain = True
        info.track_gain = _atof(value)
    elif upper == "REPLAYGAIN_TRACK_PEAK":
        info.have_track_peak = True
        info.track_peak = _atof(value)
    elif upper == "REPLAYGAIN_ALBUM_GAIN":
        info.have_album_gain = True
        info.album_gain = _atof(value)
    elif upper == "REPLAYGAIN_ALBUM_PEAK":
        info.have_album_peak = True
        info.album_peak = _atof(value)
    elif upper == "MP3GAIN_UNDO":
        # value 형식: "+003,+003,W" — 포맷상 [0:4],[5:9],[10] 슬라이싱.
        info.have_undo = True
        info.undo_left = _atoi(value[0:4])
        info.undo_right = _atoi(value[5:9])
        info.undo_wrap = value[10:11] in ("w", "W")
    elif upper == "MP3GAIN_MINMAX":
        # value 형식: "001,153" — 포맷상 [0:3],[4:7] 슬라이싱.
        info.have_min_max_gain = True
        info.min_gain = _atoi(value[0:3])
        info.max_gain = _atoi(value[4:7])
    elif upper == "MP3GAIN_ALBUM_MINMAX":
        info.have_album_min_max_gain = True
        info.album_min_gain = _atoi(value[0:3])
        info.album_max_gain = _atoi(value[4:7])
    else:
        return False
    return True


def _atof(s: str) -> float:
    """원본 atof 동작 모사: 앞부분의 숫자만 파싱, 실패 시 0.0."""
    s = s.strip()
    # atof 는 앞에서부터 파싱 가능한 데까지. 가장 단순·안전하게 시도.
    end = 0
    seen_dot = False
    seen_e = False
    for i, c in enumerate(s):
        if c in "+-" and (i == 0 or s[i - 1] in "eE"):
            end = i + 1
        elif c.isdigit():
            end = i + 1
        elif c == "." and not seen_dot and not seen_e:
            seen_dot = True
            end = i + 1
        elif c in "eE" and not seen_e and end > 0:
            seen_e = True
            end = i + 1
        else:
            break
    try:
        return float(s[:end]) if end > 0 else 0.0
    except ValueError:
        return 0.0


def _atoi(s: str) -> int:
    """원본 atoi 동작 모사: 앞부분의 정수만 파싱, 실패 시 0."""
    s = s.strip()
    end = 0
    for i, c in enumerate(s):
        if c in "+-" and i == 0:
            end = i + 1
        elif c.isdigit():
            end = i + 1
        else:
            break
    try:
        return int(s[:end]) if end > 0 and s[:end] not in ("+", "-") else 0
    except ValueError:
        return 0


def read_mp3gain_ape_tag(filename: str):
    """원본 ReadMP3GainAPETag.

    파일 끝에서부터 APE / Lyrics3v2(+ID3v1) / ID3v1 꼬리를 반복 감지하며
    tag_offset 을 위로 깎는다. 한 바퀴에 아무것도 안 깎이면 종료.
    최종 tag_offset 이 오디오 본문 끝(= 태그 시작) 위치.

    반환: (info, file_tags)
    """
    with open(filename, "rb") as f:
        f.seek(0, 2)  # SEEK_END
        file_size = f.tell()
        tag_offset = file_size

        info = MP3GainTagInfo()
        file_tags = FileTags()
        file_tags.lyrics3_tag_size = 0

        while True:
            offs_bk = tag_offset
            tag_offset = _read_ape_tag(f, info, file_tags, tag_offset)
            tag_offset = _read_lyrics3v2_tag(f, file_tags, tag_offset)
            tag_offset = _read_id3v1_tag(f, file_tags, tag_offset)
            if offs_bk == tag_offset:
                break

        if 0 <= tag_offset <= file_size:
            file_tags.tag_offset = tag_offset
        else:
            # 손상된 태그 정보: 파일 끝으로 기본 처리(원본 동작).
            file_tags.tag_offset = file_size

    return info, file_tags


# ---------------------------------------------------------------------------
# 4단계 ②: APEv2 쓰기 (원본 WriteMP3GainAPETag 동등)
# ---------------------------------------------------------------------------

def _write_le32(value: int) -> bytes:
    """원본 Write_LE_Uint32: 리틀엔디언 4바이트."""
    return bytes((
        value & 0xFF,
        (value >> 8) & 0xFF,
        (value >> 16) & 0xFF,
        (value >> 24) & 0xFF,
    ))


def _fmt_gain(value: float) -> str:
    """원본 '%-+9.6f' + ' dB'.

    C 의 %-+9.6f: 부호 강제(+/-), 최소폭 9, 소수 6자리, 좌측정렬(폭 미달 시
    오른쪽 공백). 6자리 소수면 부호+정수1+점+6 = 최소 9자리라 보통 폭 충족.
    원본은 이 9바이트만 memcpy 후 ' dB' 3바이트를 붙인다.
    """
    s = f"{value:+.6f}"          # 부호 강제, 소수 6자리
    s = s.ljust(9)              # 최소폭 9, 좌측정렬
    # 원본은 valueString 의 앞 9바이트만 복사. 폭 초과 시(예: -10.5) 잘릴 수 있으나
    # 게인 dB 는 통상 한 자리 정수라 9 이내. 원본과 동일하게 앞 9바이트 사용.
    return s[:9] + " dB"


def _fmt_peak(value: float) -> str:
    """원본 '%-8.6f': 부호 없음, 최소폭 8, 소수 6자리, 좌측정렬. 앞 8바이트 사용."""
    s = f"{value:.6f}"
    s = s.ljust(8)
    return s[:8]


def _ape_field(name: str, value: str) -> bytes:
    """APE 필드 하나를 원본 바이트 레이아웃으로 직렬화.

    레이아웃: vsize[4 LE] + flags[4 LE]=0 + name(ASCII) + '\\0' + value(UTF-8).
    """
    name_b = name.encode("ascii")
    value_b = value.encode("utf-8")
    return (
        _write_le32(len(value_b))
        + _write_le32(0)
        + name_b
        + b"\x00"
        + value_b
    )


def _make_ape_footer(
    is_header: bool, tag_len: int, tag_count: int, base: Optional[bytes]
) -> bytes:
    """APE 푸터 또는 헤더 32바이트 생성 (원본 WriteMP3GainAPETag 의 footer/header 구성).

    is_header=True 이면 Flags 에 bit29(이것이 헤더)를 추가로 켠다.
    Length 는 '자신을 제외한 상대편 32바이트 + 본문' = tag_len - 32 (원본은 항상
    헤더+푸터 둘 다 쓰므로 newTagLength - sizeof(other 한쪽) 로 계산되며 동일값).
    base 가 주어지면(기존 footer/header 보존) Version/Reserved 등을 유지하고
    Length·TagCount·Flags(헤더비트)만 갱신. 없으면 v2000 으로 새로 만든다.
    """
    if base is not None and len(base) == APE_FOOTER_SIZE:
        buf = bytearray(base)
    else:
        buf = bytearray(APE_FOOTER_SIZE)
        buf[0:8] = b"APETAGEX"
        buf[8:12] = _write_le32(2000)          # Version
        buf[24:32] = b"\x00" * 8                # Reserved

    buf[12:16] = _write_le32(tag_len - APE_FOOTER_SIZE)  # Length
    buf[16:20] = _write_le32(tag_count)                  # TagCount

    # Flags: 항상 "태그에 헤더 있음"(bit31). 헤더면 "이것이 헤더"(bit29) 추가.
    flags = APE_FLAG_HAS_HEADER
    if is_header:
        flags |= (1 << 29)
    buf[20:24] = _write_le32(flags)

    return bytes(buf)


def _restore_timestamp(filename: str, saved) -> None:
    if saved is not None:
        os.utime(filename, (saved.st_atime, saved.st_mtime))


def write_mp3gain_ape_tag(
    filename: str,
    info: MP3GainTagInfo,
    file_tags: FileTags,
    save_timestamp: bool = False,
) -> bool:
    """원본 WriteMP3GainAPETag 동등.

    file_tags 는 read_mp3gain_ape_tag 로 미리 채워져 있어야 한다(tag_offset,
    보존된 otherFields/Lyrics3/ID3v1). info 의 have_* 에 따라 mp3gain/ReplayGain
    필드를 기록한다. 새 태그는 항상 header(32)+otherFields+mp3gain필드+footer(32)
    구조. 쓸 필드가 하나도 없으면(otherFields 도 없고 have_* 도 전부 False) APE
    태그를 쓰지 않고 꼬리만 남긴다.

    반환: 성공 시 True.
    """
    saved_stat = None
    if save_timestamp:
        try:
            saved_stat = os.stat(filename)
        except OSError:
            saved_stat = None

    ape = file_tags.ape_tag

    # otherFields(보존된 비-mp3gain 필드) 와 그 개수.
    if ape is not None:
        other_fields = ape.other_fields
        other_count = _count_ape_fields(other_fields)
    else:
        other_fields = b""
        other_count = 0

    # mp3gain/ReplayGain 필드를 원본 순서대로 직렬화.
    fields = bytearray()
    field_count = 0

    if info.have_min_max_gain:
        fields += _ape_field(
            "MP3GAIN_MINMAX",
            f"{info.min_gain:03d},{info.max_gain:03d}",
        )
        field_count += 1
    if info.have_album_min_max_gain:
        fields += _ape_field(
            "MP3GAIN_ALBUM_MINMAX",
            f"{info.album_min_gain:03d},{info.album_max_gain:03d}",
        )
        field_count += 1
    if info.have_undo:
        wrap_ch = "W" if info.undo_wrap else "N"
        fields += _ape_field(
            "MP3GAIN_UNDO",
            f"{info.undo_left:+04d},{info.undo_right:+04d},{wrap_ch}",
        )
        field_count += 1
    if info.have_track_gain:
        fields += _ape_field("REPLAYGAIN_TRACK_GAIN", _fmt_gain(info.track_gain))
        field_count += 1
    if info.have_track_peak:
        fields += _ape_field("REPLAYGAIN_TRACK_PEAK", _fmt_peak(info.track_peak))
        field_count += 1
    if info.have_album_gain:
        fields += _ape_field("REPLAYGAIN_ALBUM_GAIN", _fmt_gain(info.album_gain))
        field_count += 1
    if info.have_album_peak:
        fields += _ape_field("REPLAYGAIN_ALBUM_PEAK", _fmt_peak(info.album_peak))
        field_count += 1

    new_tag_count = other_count + field_count
    body = other_fields + bytes(fields)
    # 새 태그 총 길이 = 헤더(32) + 본문 + 푸터(32).
    new_tag_length = APE_FOOTER_SIZE * 2 + len(body)

    # 기존 태그가 새 태그보다 길면 파일을 tag_offset 까지 truncate (원본 동작).
    if ape is not None and ape.original_tag_size > new_tag_length:
        with open(filename, "r+b") as f:
            f.truncate(file_tags.tag_offset)

    base_footer = ape.footer if ape is not None else None
    base_header = ape.header if (ape is not None and ape.have_header) else None

    new_header = _make_ape_footer(True, new_tag_length, new_tag_count, base_header)
    new_footer = _make_ape_footer(False, new_tag_length, new_tag_count, base_footer)

    with open(filename, "r+b") as f:
        f.seek(file_tags.tag_offset)
        if new_tag_count > 0:
            f.write(new_header)
            f.write(body)
            f.write(new_footer)
        # 보존된 꼬리 재기록: Lyrics3 가 있으면 그것만(정의상 id3v1 포함),
        # 없으면 id3v1 단독.
        if file_tags.lyrics3_tag_size > 0 and file_tags.lyrics3_tag is not None:
            f.write(file_tags.lyrics3_tag)
        elif file_tags.id3v1_tag is not None:
            f.write(file_tags.id3v1_tag)
        # 새 끝 위치에서 잘라내기(꼬리가 짧아진 경우 잔여 바이트 제거).
        f.truncate()

    if save_timestamp:
        _restore_timestamp(filename, saved_stat)

    return True


def _count_ape_fields(blob: bytes) -> int:
    """otherFields 블롭에 들어 있는 APE 필드 개수를 센다.

    각 필드: vsize[4]+flags[4]+name+'\\0'+value. write 시 footer TagCount 계산용.
    """
    count = 0
    p = 0
    n = len(blob)
    while p + 8 <= n:
        vsize = _read_le32(blob, p)
        p += 8
        isize = _strlen_max(blob, p, n - p)
        if p + isize + 1 + vsize > n:
            break
        p += isize + 1 + vsize
        count += 1
    return count


def remove_mp3gain_ape_tag(filename: str, save_timestamp: bool = False) -> bool:
    """원본 RemoveMP3GainAPETag 동등.

    APE 태그를 읽어, mp3gain/ReplayGain 필드가 하나라도 있으면(have_* OR)
    dirty 로 표시한 뒤 have_* 를 전부(undo 포함) 끄고 다시 쓴다. write 의
    new_tag_count > 0 분기 덕분에, 남는 필드(otherFields)가 없으면 APE 태그가
    통째로 제거되고 꼬리(Lyrics3/ID3v1)만 남는다. 원래 mp3gain 필드가 없던
    파일이면(dirty 아님) 파일을 전혀 건드리지 않는다.

    반환: 항상 True (원본 동작).
    """
    info, file_tags = read_mp3gain_ape_tag(filename)

    # 읽은 직후 mp3gain 필드가 하나라도 있으면 변경 대상.
    info.dirty = (
        info.have_album_gain
        or info.have_album_peak
        or info.have_track_gain
        or info.have_track_peak
        or info.have_min_max_gain
        or info.have_album_min_max_gain
        or info.have_undo
    )

    # 전부 끈다(undo 포함). write 가 켜진 필드만 쓰므로 결과적으로 mp3gain 제거.
    info.have_album_gain = False
    info.have_album_peak = False
    info.have_track_gain = False
    info.have_track_peak = False
    info.have_min_max_gain = False
    info.have_album_min_max_gain = False
    info.have_undo = False

    if info.dirty:
        write_mp3gain_ape_tag(filename, info, file_tags, save_timestamp)

    return True


# ---------------------------------------------------------------------------
# 4단계 ⑤-C: useId3 분기 래퍼 (원본 WriteMP3GainTag / main 의 태그 읽기 분기 동등)
# ---------------------------------------------------------------------------

def _write_mp3gain_tag(
    filename: str,
    info: MP3GainTagInfo,
    file_tags: FileTags,
    save_timestamp: bool = False,
    use_id3: bool = False,
) -> None:
    """원본 WriteMP3GainTag 동등.

    use_id3 이면 ID3v2 로 기록하고, 기록이 실패하지 않았으면(>= 0) stale APE
    태그를 제거한다(원본 비대칭: APE 로 쓸 때는 stale ID3 를 건드리지 않음).
    use_id3 가 아니면 APE 로만 기록한다.

    id3 모듈은 순환 import 회피를 위해 함수 내부에서 import (id3.py 가 이
    모듈을 import 하므로).
    """
    if use_id3:
        from gaindb.id3 import write_mp3gain_id3_tag
        if write_mp3gain_id3_tag(filename, info, save_timestamp) >= 0:
            remove_mp3gain_ape_tag(filename, save_timestamp)
    else:
        write_mp3gain_ape_tag(filename, info, file_tags, save_timestamp)


def read_mp3gain_tags(filename: str, use_id3: bool = False):
    """원본 main 의 태그 읽기 분기 동등 (APE → 필요 시 ID3 덮어쓰기).

    항상 APE 를 먼저 읽고, use_id3 이면: (1) APE 에서 게인 관련 필드를 하나라도
    읽었으면 dirty 를 켜 ID3v2 로의 업그레이드를 강제하고, (2) ID3v2 를 읽어
    같은 info 에 덮어쓴다(ID3 값이 있으면 APE 값을 덮음).

    반환: (info, file_tags). file_tags 는 APE 쓰기 경로에서만 의미가 있다.
    """
    info, file_tags = read_mp3gain_ape_tag(filename)

    if use_id3:
        from gaindb.id3 import read_mp3gain_id3_tag
        if (info.have_track_gain or info.have_album_gain or
                info.have_min_max_gain or info.have_album_min_max_gain or
                info.have_undo):
            # APE 에 mp3gain 정보가 있으면 ID3v2 로 업그레이드 강제.
            info.dirty = True
        read_mp3gain_id3_tag(filename, info)

    return info, file_tags


def change_gain_and_tag(
    filename: str,
    left_change: int,
    right_change: int,
    info: MP3GainTagInfo,
    file_tags: FileTags,
    wrap: bool = False,
    save_timestamp: bool = False,
    use_id3: bool = False,
    should_cancel=None,
    on_progress=None,
) -> bool:
    """원본 mp3gain.c 의 changeGainAndTag 동등.

    실제 프레임 게인을 적용(writer.apply_gain)한 뒤, 성공하면 info 를 일관 갱신하고
    태그를 다시 쓴다. undo 는 항상 누적, gain/peak/minmax 는 좌우 변화량이
    같을 때만 갱신(좌우 다르면 채널 분리라 의미가 깨지므로 건드리지 않음).

    dB 차감 상수 1.505 는 5*log10(2)(1스텝당 dB)의 소수 3자리 근사값이며,
    표준 mp3gain 과 수치를 일치시키기 위해 같은 값을 쓴다.
    태그 쓰기는 _write_mp3gain_tag 래퍼로 분기(use_id3 에 따라 ID3/APE).

    should_cancel/on_progress: apply_gain 으로 그대로 통과한다(초장시간 곡의
    프레임 순회 중 취소·진행률). 취소되면 apply_gain 이 GainCancelled 를 던지며,
    그 시점에 파일은 원본 그대로이고 태그도 아직 쓰지 않았다(안전).

    반환: 게인을 적용하고 태그를 갱신했으면 True, 변화량이 0이면 False.
    """
    # writer 는 순환 import 회피를 위해 함수 내부에서 import.
    from gaindb.writer import apply_gain

    if left_change == 0 and right_change == 0:
        return False

    # 실제 프레임 게인 적용. 예외 없이 반환되면 성공(원본의 !changeGain 대응).
    # 취소 시 apply_gain 이 GainCancelled 를 던지고, 파일·태그 모두 미변경이다.
    apply_gain(filename, left_change, right_change, wrap,
               should_cancel=should_cancel, on_progress=on_progress)

    # --- undo 누적 (항상) ---
    if not info.have_undo:
        info.undo_left = 0
        info.undo_right = 0
    info.dirty = True
    info.undo_right -= right_change
    info.undo_left -= left_change
    info.undo_wrap = wrap
    info.have_undo = True  # undo 가 0 이 되어도 제거하지 않음(원본: 파일 단축 회피)

    # --- 좌우가 같을 때만 나머지 필드 갱신 ---
    if left_change == right_change:
        dbl_gain_change = left_change * 1.505  # 5*log10(2) 의 3자리 근사

        if info.have_track_gain:
            info.track_gain -= dbl_gain_change
        if info.have_track_peak:
            info.track_peak *= 2.0 ** (left_change / 4.0)
        if info.have_album_gain:
            info.album_gain -= dbl_gain_change
        if info.have_album_peak:
            info.album_peak *= 2.0 ** (left_change / 4.0)

        if info.have_min_max_gain:
            cur_min = info.min_gain + left_change
            cur_max = info.max_gain + left_change
            if wrap:
                if cur_min < 0 or cur_min > 255 or cur_max < 0 or cur_max > 255:
                    # wrap 으로 진짜 min/max 를 잃음 → 정보 폐기(원본 동작)
                    info.have_min_max_gain = False
            else:
                # minGain: 원래 0 이면 0 유지(0-gain 보존), 아니면 0~255 클램프
                info.min_gain = (
                    0 if info.min_gain == 0
                    else 0 if cur_min < 0
                    else 255 if cur_min > 255
                    else cur_min
                )
                # maxGain: 단순 0~255 클램프
                info.max_gain = (
                    0 if cur_max < 0 else 255 if cur_max > 255 else cur_max
                )

        if info.have_album_min_max_gain:
            cur_min = info.album_min_gain + left_change
            cur_max = info.album_max_gain + left_change
            if wrap:
                if cur_min < 0 or cur_min > 255 or cur_max < 0 or cur_max > 255:
                    info.have_album_min_max_gain = False
            else:
                info.album_min_gain = (
                    0 if info.album_min_gain == 0
                    else 0 if cur_min < 0
                    else 255 if cur_min > 255
                    else cur_min
                )
                info.album_max_gain = (
                    0 if cur_max < 0 else 255 if cur_max > 255 else cur_max
                )

    # --- 태그 다시 쓰기 (use_id3 분기는 _write_mp3gain_tag 래퍼가 처리) ---
    _write_mp3gain_tag(filename, info, file_tags, save_timestamp, use_id3)
    return True
