# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""
gaindb.frame - MP3 Layer III 프레임 파서 (읽기 전용)

MP3 파일을 순회하며 각 프레임의 global_gain 값을 읽는다.
공개된 MPEG 오디오 프레임 구조 사양만 참조해 독립 구현.
이 단계는 디코딩이 아니라 사이드 정보의 게인 필드만 읽으므로 외부 의존성 없음.
"""

from dataclasses import dataclass


# MPEG 버전 인덱스: (h[1] >> 3) & 0x03  ->  0=MPEG2.5, 1=reserved, 2=MPEG2, 3=MPEG1
# Layer III 기준 비트레이트 테이블 (kbps). 인덱스 0=free, 15=bad.
# 행 인덱스는 위 MPEG 버전 인덱스와 동일하게 맞춘다.
_BITRATE = (
    # MPEG2.5 (Layer III)
    (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0),
    # reserved (사용 안 함)
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    # MPEG2 (Layer III)
    (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0),
    # MPEG1 (Layer III)
    (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0),
)

# 샘플링 주파수 테이블 (Hz). 인덱스 0..2 유효, 3=bad.
_SAMPLERATE = (
    (11025, 12000, 8000, 0),   # MPEG2.5
    (0, 0, 0, 0),              # reserved
    (22050, 24000, 16000, 0),  # MPEG2
    (44100, 48000, 32000, 0),  # MPEG1
)

# 채널 모드: (h[3] >> 6) & 0x03  ->  0=stereo, 1=joint stereo, 2=dual channel, 3=mono
_MODE_MONO = 3


@dataclass
class FrameInfo:
    """한 프레임의 파싱 결과."""
    offset: int            # 파일 내 프레임 시작 바이트 오프셋
    mpegver: int           # 3=MPEG1, 2=MPEG2, 0=MPEG2.5
    has_crc: bool          # CRC 16비트 보호 필드 존재 여부
    bitrate_kbps: int      # 비트레이트 (kbps)
    samplerate_hz: int     # 샘플링 주파수 (Hz)
    padding: int           # 패딩 비트 (0 또는 1)
    mode: int              # 채널 모드 (0=stereo, 1=joint, 2=dual, 3=mono)
    nchan: int             # 채널 수 (1 또는 2)
    frame_len: int         # 프레임 전체 바이트 길이 (패딩 포함)
    gains: list            # 이 프레임의 global_gain 값 리스트 (granule*channel 순서)


class _BitReader:
    """바이트열의 특정 시작점부터 비트 단위로 진행하는 리더/라이터."""

    # 두 바이트에 걸친 8비트 덮어쓰기용 마스킹 상수(비트오프셋별 자명한 값)
    _MASK_LEFT = (0x00, 0x80, 0xC0, 0xE0, 0xF0, 0xF8, 0xFC, 0xFE)
    _MASK_RIGHT = (0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01)

    def __init__(self, data, byte_pos: int, bit_pos: int = 0):
        self.data = data
        self.byte_pos = byte_pos
        self.bit_pos = bit_pos  # 0..7, 현재 바이트 안에서의 비트 오프셋(MSB부터)

    def skip(self, nbits: int) -> None:
        total = self.bit_pos + nbits
        self.byte_pos += total >> 3
        self.bit_pos = total & 7

    def peek8(self) -> int:
        """현재 비트 위치에서 8비트를 정수로 엿본다(위치 이동 없음)."""
        hi = self.data[self.byte_pos]
        lo = self.data[self.byte_pos + 1]
        val = ((hi << 8) | lo) >> (8 - self.bit_pos)
        return val & 0xFF

    def set8(self, val: int) -> None:
        """현재 비트 위치에 8비트 값을 덮어쓴다(위치 이동 없음).
        data 는 변경 가능한 bytearray 여야 한다."""
        b = self.bit_pos
        shifted = (val & 0xFF) << (8 - b)
        self.data[self.byte_pos] = (self.data[self.byte_pos] & self._MASK_LEFT[b]) | (shifted >> 8)
        self.data[self.byte_pos + 1] = (self.data[self.byte_pos + 1] & self._MASK_RIGHT[b]) | (shifted & 0xFF)


def _is_valid_header(data: bytes, pos: int) -> bool:
    """pos 위치의 4바이트가 유효한 Layer III 프레임 헤더인지 검사."""
    if pos + 4 > len(data):
        return False
    b0, b1, b2 = data[pos], data[pos + 1], data[pos + 2]
    if b0 != 0xFF:
        return False
    if (b1 & 0xE0) != 0xE0:          # 싱크 상위 3비트
        return False
    if (b1 & 0x18) == 0x08:          # reserved MPEG 버전
        return False
    if (b1 & 0x06) != 0x02:          # Layer III 아님
        return False
    if (b2 & 0xF0) == 0xF0:          # bad bitrate
        return False
    if (b2 & 0xF0) == 0x00:          # free format (미지원)
        return False
    if (b2 & 0x0C) == 0x0C:          # bad samplerate
        return False
    return True


def _frame_length(mpegver: int, bitridx: int, freqidx: int, padding: int) -> int:
    """프레임 전체 바이트 길이 계산."""
    bitbase = 1152 if mpegver == 3 else 576
    bitrate = _BITRATE[mpegver][bitridx] * 1000
    samplerate = _SAMPLERATE[mpegver][freqidx]
    base = (bitbase * bitrate // samplerate) // 8
    return base + padding


def _parse_header(data: bytes, pos: int) -> FrameInfo:
    """유효성 검사를 통과한 위치에서 헤더 필드를 추출한다."""
    b1, b2, b3 = data[pos + 1], data[pos + 2], data[pos + 3]
    mpegver = (b1 >> 3) & 0x03
    has_crc = (b1 & 0x01) == 0          # protection bit 0 == CRC 존재
    bitridx = (b2 >> 4) & 0x0F
    freqidx = (b2 >> 2) & 0x03
    padding = (b2 >> 1) & 0x01
    mode = (b3 >> 6) & 0x03
    nchan = 1 if mode == _MODE_MONO else 2
    return FrameInfo(
        offset=pos,
        mpegver=mpegver,
        has_crc=has_crc,
        bitrate_kbps=_BITRATE[mpegver][bitridx],
        samplerate_hz=_SAMPLERATE[mpegver][freqidx],
        padding=padding,
        mode=mode,
        nchan=nchan,
        frame_len=_frame_length(mpegver, bitridx, freqidx, padding),
        gains=[],
    )


def _read_global_gains(data: bytes, frame: FrameInfo) -> list:
    """사이드 정보로 진입해 global_gain 값들을 읽는다."""
    # 사이드 정보 시작: 헤더 4바이트 + (CRC 있으면 2바이트)
    side_start = frame.offset + (6 if frame.has_crc else 4)
    nchan = frame.nchan
    gains = []

    if frame.mpegver == 3:  # MPEG1
        # main_data_begin 9비트 -> side_start +1바이트, 비트오프셋 1
        reader = _BitReader(data, side_start + 1, 1)
        reader.skip(5 if nchan == 1 else 3)   # private bits
        reader.skip(nchan * 4)                # scfsi[ch][band]
        for _gr in range(2):                  # granule 2개
            for _ch in range(nchan):
                reader.skip(21)
                gains.append(reader.peek8())  # peek는 위치 불변
                reader.skip(38)               # gain(8) 포함 이후 블록까지
    else:  # MPEG2 / MPEG2.5
        # main_data_begin 8비트 -> side_start +1바이트, 비트오프셋 0
        reader = _BitReader(data, side_start + 1, 0)
        reader.skip(1 if nchan == 1 else 2)   # private bits
        for _ch in range(nchan):              # granule 1개뿐
            reader.skip(21)
            gains.append(reader.peek8())
            reader.skip(42)

    return gains


def _skip_id3v2(data: bytes) -> int:
    """파일 앞에 ID3v2 태그가 있으면 그 뒤의 오프셋을 반환, 없으면 0."""
    if len(data) >= 10 and data[0:3] == b"ID3" and data[3] != 0xFF and data[4] != 0xFF:
        # synchsafe 크기 (각 바이트 하위 7비트)
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        return size + 10
    return 0


def _looks_like_info_frame(data: bytes, frame: FrameInfo) -> bool:
    """첫 프레임이 Xing/Info(LAME) 정보 프레임인지 검사."""
    if frame.mpegver == 3:
        side_len = 4 + (17 if frame.nchan == 1 else 32)
    else:
        side_len = 4 + (9 if frame.nchan == 1 else 17)
    if frame.has_crc:
        side_len += 2
    tag_pos = frame.offset + side_len
    if tag_pos + 4 > len(data):
        return False
    tag = data[tag_pos:tag_pos + 4]
    return tag in (b"Xing", b"Info")


def parse_file(path: str):
    """
    MP3 파일을 순회하며 FrameInfo 리스트를 생성하는 제너레이터.
    각 프레임마다 global_gain 값을 채워 yield 한다.
    """
    with open(path, "rb") as f:
        data = f.read()

    pos = _skip_id3v2(data)

    # 첫 유효 프레임 탐색
    while pos + 4 <= len(data) and not _is_valid_header(data, pos):
        pos += 1

    first = True
    while pos + 4 <= len(data) and _is_valid_header(data, pos):
        frame = _parse_header(data, pos)
        if frame.frame_len <= 0 or pos + frame.frame_len > len(data):
            break

        # 첫 프레임이 Xing/Info 정보 프레임이면 게인 읽지 말고 건너뜀
        if first and _looks_like_info_frame(data, frame):
            first = False
            pos += frame.frame_len
            continue
        first = False

        frame.gains = _read_global_gains(data, frame)
        yield frame

        pos += frame.frame_len
        # 다음 위치가 유효 헤더가 아니면 재동기화 시도
        if not (pos + 4 <= len(data) and _is_valid_header(data, pos)):
            scan = pos
            while scan + 4 <= len(data) and not _is_valid_header(data, scan):
                scan += 1
            pos = scan