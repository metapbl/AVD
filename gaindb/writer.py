"""
gaindb.writer - MP3 global_gain 무손실 조정 (쓰기)

각 프레임의 global_gain 필드를 ±N 하여 음량을 조정한다.
재인코딩 없음 -> 무손실. CRC 보호 프레임은 헤더 CRC를 재계산한다.

clean-room: MPEG 사이드 정보 레이아웃과 게인 적용 규칙(사양)만 참조해 독립 구현.

취소·진행률(GUI/워커 대응):
  apply_gain·scan_gain 은 순수 파이썬 프레임 순회라 디코딩이 없다. 초장시간
  곡(수 시간)에서는 이 순회만으로도 수 분이 걸리는데, 예전에는 취소 확인
  지점이 없어 취소를 눌러도 워커가 이 루프에 갇혀 반응하지 못했다. 이제 두
  함수는 선택적 should_cancel/on_progress 콜백을 받아, 순회 중 일정 간격으로
  취소를 확인하고(취소 시 GainCancelled) 바이트 오프셋 기반 진행률(0~1)을
  방출한다. 취소 확인은 '파일에 쓰기 전 순회 단계'에서만 한다 — apply_gain 은
  메모리(bytearray)에서 모두 고친 뒤 마지막에 한 번에 쓰므로, 순회 중 취소해도
  파일은 원본 그대로 남는다(부분 기록 없음).
"""

from gaindb.frame import (
    _BitReader,
    _is_valid_header,
    _parse_header,
    _skip_id3v2,
    _looks_like_info_frame,
)

CRC16_POLYNOMIAL = 0x8005

# 취소·진행률 콜백을 확인하는 프레임 간격. 너무 잦으면 오버헤드, 너무 뜸하면
# 취소 반응이 느리다. 10시간 곡(≈130만 프레임)에서 4096 이면 약 300여 회
# 확인 → 취소 반응 수십 ms, 진행바도 충분히 부드럽다.
_CALLBACK_INTERVAL = 4096


class GainCancelled(Exception):
    """apply_gain/scan_gain 이 should_cancel 로 취소됐을 때 던진다(정상 취소).

    DecodeCancelled 와 성격이 같다(실패가 아니라 사용자 취소). 워커는 이를
    failed 가 아니라 정상 취소로 구분해 처리한다. 파일에 쓰기 전 순회 단계
    에서만 발생하므로, 이 예외가 던져진 시점에 파일은 원본 그대로다.
    """


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


def apply_gain(path: str, left_change: int, right_change: int = None,
               wrap: bool = False, should_cancel=None, on_progress=None) -> int:
    """
    MP3 파일의 모든 프레임 global_gain 을 무손실 조정한다.
    right_change 가 None 이면 좌우 동일 게인으로 적용한다.
    채널별(left != right) 적용은 stereo/dual 채널 파일에서만 허용된다
    (원본 changeGain: joint stereo·mono 는 거부 — mode 1·3).
    반환값: 수정한 프레임 수.

    should_cancel: 인자 없는 콜백. 순회 중 _CALLBACK_INTERVAL 프레임마다 호출해
      True 면 GainCancelled 를 던진다(파일 write 전이라 파일은 원본 그대로).
    on_progress: fraction(0~1) 을 받는 콜백. 순회 진행률(바이트 오프셋/전체
      길이)을 같은 간격으로 방출한다.
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
    since_cb = 0
    total_len = original_len if original_len > 0 else 1
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

        # 취소·진행률: 파일에 쓰기 전(메모리 수정 단계)에서만 확인하므로,
        # 여기서 취소해도 아직 파일은 손대지 않았다(부분 기록 없음).
        since_cb += 1
        if since_cb >= _CALLBACK_INTERVAL:
            since_cb = 0
            if should_cancel is not None and should_cancel():
                raise GainCancelled()
            if on_progress is not None:
                on_progress(pos / total_len)

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

    if on_progress is not None:
        on_progress(1.0)

    return count


def scan_gain(path: str, should_cancel=None, on_progress=None):
    """모든 프레임의 global_gain 최소/최대값을 수정 없이 수집한다.

    원본 mp3gain.c 의 scanFrameGain 동등. 디코딩 없이 사이드 정보의
    global_gain 필드만 읽어 파일 전체의 min/max 를 구한다. 0-gain 프레임도
    포함한다(원본 동작).

    should_cancel/on_progress: apply_gain 과 동일(순회 중 간격마다 취소 확인·
      진행률 방출). 취소 시 GainCancelled. 읽기만 하므로 파일은 안 바뀐다.

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
    since_cb = 0
    total_len = len(data) if len(data) > 0 else 1
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

        # 취소·진행률(읽기 전용이라 언제 멈춰도 안전).
        since_cb += 1
        if since_cb >= _CALLBACK_INTERVAL:
            since_cb = 0
            if should_cancel is not None and should_cancel():
                raise GainCancelled()
            if on_progress is not None:
                on_progress(pos / total_len)

        pos += frame.frame_len
        if not (pos + 4 <= len(data) and _is_valid_header(data, pos)):
            scan = pos
            while scan + 4 <= len(data) and not _is_valid_header(data, scan):
                scan += 1
            pos = scan

    if on_progress is not None:
        on_progress(1.0)

    if max_gain < 0:
        return None, None
    return min_gain, max_gain
