"""
gaindb.writer - MP3 global_gain 무손실 조정 (쓰기)

각 프레임의 global_gain 필드를 ±N 하여 음량을 조정한다.
재인코딩 없음 -> 무손실. CRC 보호 프레임은 헤더 CRC를 재계산한다.

clean-room: MPEG 사이드 정보 레이아웃과 게인 적용 규칙(사양)만 참조해 독립 구현.
"""

from gaindb.frame import (
    _BitReader,
    _is_valid_header,
    _parse_header,
    _skip_id3v2,
    _looks_like_info_frame,
)

CRC16_POLYNOMIAL = 0x8005


def _apply_one(gain: int, change: int, wrap: bool) -> int:
    """게인 적용 규칙(사양 1.4)."""
    if wrap:
        return (gain + change) & 0xFF
    if gain == 0:
        return 0  # 0-gain 프레임은 건드리지 않는다
    result = gain + change
    if result > 255:
        return 255
    if result < 0:
        return 0
    return result


def _crc_update(value: int, crc: int) -> int:
    value &= 0xFF
    value <<= 8
    for _ in range(8):
        value <<= 1
        crc <<= 1
        if (crc ^ value) & 0x10000:
            crc ^= CRC16_POLYNOMIAL
    return crc & 0xFFFF


def _rewrite_crc(data: bytearray, frame_offset: int, header_len: int) -> None:
    """프레임 헤더의 CRC 16비트(byte4,5)를 재계산해 덮어쓴다.
    헤더의 byte2,3 과 byte6.. header_len 까지를 대상으로 한다."""
    crc = 0xFFFF
    crc = _crc_update(data[frame_offset + 2], crc)
    crc = _crc_update(data[frame_offset + 3], crc)
    for i in range(6, header_len):
        crc = _crc_update(data[frame_offset + i], crc)
    data[frame_offset + 4] = (crc >> 8) & 0xFF
    data[frame_offset + 5] = crc & 0xFF


def _change_frame_gain(data: bytearray, frame, left: int, right: int, wrap: bool) -> None:
    """한 프레임의 모든 global_gain 을 채널별 변화량으로 수정한다."""
    side_start = frame.offset + (6 if frame.has_crc else 4)
    nchan = frame.nchan
    change = (left, right)

    if frame.mpegver == 3:  # MPEG1
        reader = _BitReader(data, side_start + 1, 1)
        reader.skip(5 if nchan == 1 else 3)
        reader.skip(nchan * 4)
        for _gr in range(2):
            for ch in range(nchan):
                reader.skip(21)
                gain = reader.peek8()
                reader.set8(_apply_one(gain, change[ch], wrap))
                reader.skip(38)
    else:  # MPEG2 / MPEG2.5
        reader = _BitReader(data, side_start + 1, 0)
        reader.skip(1 if nchan == 1 else 2)
        for ch in range(nchan):
            reader.skip(21)
            gain = reader.peek8()
            reader.set8(_apply_one(gain, change[ch], wrap))
            reader.skip(42)

    # CRC 보호 프레임이면 헤더 CRC 재계산
    if frame.has_crc:
        if frame.mpegver == 3:
            header_len = 23 if nchan == 1 else 38
        else:
            header_len = 15 if nchan == 1 else 23
        _rewrite_crc(data, frame.offset, header_len)


def apply_gain(path: str, left_change: int, right_change: int = None, wrap: bool = False) -> int:
    """
    MP3 파일의 모든 프레임 global_gain 을 무손실 조정한다.
    right_change 가 None 이면 좌우 동일 게인으로 적용한다.
    채널별(left != right) 적용은 stereo/dual 채널 파일에서만 허용된다
    (원본 changeGain: joint stereo·mono 는 거부 — mode 1·3).
    반환값: 수정한 프레임 수.
    """
    if right_change is None:
        right_change = left_change

    if left_change == 0 and right_change == 0:
        return 0

    with open(path, "rb") as f:
        data = bytearray(f.read())

    original_len = len(data)
    single_channel = (left_change != right_change)

    pos = _skip_id3v2(data)
    while pos + 4 <= len(data) and not _is_valid_header(data, pos):
        pos += 1

    count = 0
    first = True
    while pos + 4 <= len(data) and _is_valid_header(data, pos):
        frame = _parse_header(data, pos)
        if frame.frame_len <= 0 or pos + frame.frame_len > len(data):
            break

        if first and _looks_like_info_frame(data, frame):
            first = False
            pos += frame.frame_len
            continue
        first = False

        # 단일 채널(좌우 비대칭) 게인은 stereo(0)·dual channel(2) 에서만 허용.
        # 원본 changeGain 은 mode 비트 & 0x01 이 참인 joint stereo(1)·mono(3) 를 거부.
        if single_channel and frame.mode in (1, 3):
            raise ValueError(
                "per-channel gain cannot be applied to mono or joint stereo files"
            )

        _change_frame_gain(data, frame, left_change, right_change, wrap)
        count += 1

        pos += frame.frame_len
        if not (pos + 4 <= len(data) and _is_valid_header(data, pos)):
            scan = pos
            while scan + 4 <= len(data) and not _is_valid_header(data, scan):
                scan += 1
            pos = scan

    if len(data) != original_len:
        raise RuntimeError("file length changed - lossless guarantee violated")

    with open(path, "wb") as f:
        f.write(data)

    return count


def scan_gain(path: str):
    """모든 프레임의 global_gain 최소/최대값을 수정 없이 수집한다.

    원본 mp3gain.c 의 scanFrameGain 동등. 디코딩 없이 사이드 정보의
    global_gain 필드만 읽어 파일 전체의 min/max 를 구한다. 0-gain 프레임도
    포함한다(원본 동작).

    반환: (min_gain, max_gain) 튜플. 유효 프레임이 하나도 없으면 (None, None).
    """
    with open(path, "rb") as f:
        data = bytearray(f.read())

    pos = _skip_id3v2(data)
    while pos + 4 <= len(data) and not _is_valid_header(data, pos):
        pos += 1

    min_gain = 256
    max_gain = -1
    first = True
    while pos + 4 <= len(data) and _is_valid_header(data, pos):
        frame = _parse_header(data, pos)
        if frame.frame_len <= 0 or pos + frame.frame_len > len(data):
            break

        if first and _looks_like_info_frame(data, frame):
            first = False
            pos += frame.frame_len
            continue
        first = False

        side_start = frame.offset + (6 if frame.has_crc else 4)
        nchan = frame.nchan

        if frame.mpegver == 3:  # MPEG1
            reader = _BitReader(data, side_start + 1, 1)
            reader.skip(5 if nchan == 1 else 3)
            reader.skip(nchan * 4)
            for _gr in range(2):
                for _ch in range(nchan):
                    reader.skip(21)
                    gain = reader.peek8()
                    if gain < min_gain:
                        min_gain = gain
                    if gain > max_gain:
                        max_gain = gain
                    reader.skip(38)
        else:  # MPEG2 / MPEG2.5
            reader = _BitReader(data, side_start + 1, 0)
            reader.skip(1 if nchan == 1 else 2)
            for _ch in range(nchan):
                reader.skip(21)
                gain = reader.peek8()
                if gain < min_gain:
                    min_gain = gain
                if gain > max_gain:
                    max_gain = gain
                reader.skip(42)

        pos += frame.frame_len
        if not (pos + 4 <= len(data) and _is_valid_header(data, pos)):
            scan = pos
            while scan + 4 <= len(data) and not _is_valid_header(data, scan):
                scan += 1
            pos = scan

    if max_gain < 0:
        return None, None
    return min_gain, max_gain
