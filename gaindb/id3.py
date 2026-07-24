# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""ID3v2 (RVA2 + TXXX) 태그 읽기/쓰기 — mp3gain 과 동일한 결과·포맷을 산출하는
독립 구현. 공개 사양(ID3v2.4·RVA2·TXXX)만 차용한다.

이 모듈은 ⑤-A(읽기) + ⑤-B(쓰기)를 담당한다. 결선(⑤-C)은 이어서 추가한다.

동작 요약:
  - 읽기: 파일 앞 ID3v2 → 없으면 끝 ID3v2.4 footer → 없으면 끝 ID3v1.
    ID3v2.2/2.3/2.4 를 모두 내부적으로 2.4 로 통일해 파싱하고,
    RVA2 / TXXX(ReplayGain) / TXXX(MP3GAIN_*) 에서 게인 정보를 추출한다.
  - 쓰기: 항상 파일 앞 단일 ID3v2.4, 전체 unsync, ext header 없음, 2KB 패딩,
    footer 없음, 임시파일(.TMP) 재기록 후 rename(os.replace).

게인 정보 구조체·문자열/포맷 헬퍼는 gaindb.tag 의 것을 재사용한다(snake_case).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, List

from gaindb.tag import MP3GainTagInfo, _atof, _fmt_gain, _fmt_peak


# ---- 오류 코드 (음수) -----------------------------------------------------

M3G_ERR_READ = -1
M3G_ERR_TAGFORMAT = -2
M3G_ERR_FILEOPEN = -3


# ---- 태그/프레임 플래그 상수 (ID3v2 사양) --------------------------------

TAGFL_UNSYNC = 0x80
TAGFL_EXTHDR = 0x40
TAGFL_EXPR = 0x20
TAGFL_FOOTER = 0x10

FRAMEFL_BAD = 0x00F0
FRAMEFL_TAGALTER = 0x4000
FRAMEFL_GROUP = 0x0040
FRAMEFL_COMPR = 0x0008
FRAMEFL_CRYPT = 0x0004
FRAMEFL_UNSYNC = 0x0002
FRAMEFL_DLEN = 0x0001

SYNCSAFE_INT_BAD = 0xFFFFFFFF


# ---- ID3v2.2 → 2.4 프레임 ID 업그레이드 테이블 (ID3v2 사양) --------------

_UPGRADE_ID3V22 = {
    b"BUF": b"RBUF", b"CNT": b"PCNT", b"COM": b"COMM", b"CRA": b"AENC",
    b"ETC": b"ETCO", b"EQU": b"EQUA", b"GEO": b"GEOB", b"IPL": b"IPLS",
    b"LNK": b"LINK", b"MCI": b"MCDI", b"MLL": b"MLLT", b"PIC": b"APIC",
    b"POP": b"POPM", b"REV": b"RVRB", b"RVA": b"RVAD", b"SLT": b"SYLT",
    b"STC": b"SYTC", b"TAL": b"TALB", b"TBP": b"TBPM", b"TCM": b"TCOM",
    b"TCO": b"TCON", b"TCR": b"TCOP", b"TDA": b"TDAT", b"TDY": b"TDLY",
    b"TEN": b"TENC", b"TFT": b"TFLT", b"TIM": b"TIME", b"TKE": b"TKEY",
    b"TLA": b"TLAN", b"TLE": b"TLEN", b"TMT": b"TMED", b"TOA": b"TOPE",
    b"TOF": b"TOFN", b"TOL": b"TOLY", b"TOR": b"TORY", b"TOT": b"TOAL",
    b"TP1": b"TPE1", b"TP2": b"TPE2", b"TP3": b"TPE3", b"TP4": b"TPE4",
    b"TPA": b"TPOS", b"TPB": b"TPUB", b"TRC": b"TSRC", b"TRD": b"TRDA",
    b"TRK": b"TRCK", b"TSI": b"TSIZ", b"TSS": b"TSSE", b"TT1": b"TIT1",
    b"TT2": b"TIT2", b"TT3": b"TIT3", b"TXT": b"TEXT", b"TXX": b"TXXX",
    b"TYE": b"TYER", b"UFI": b"UFID", b"ULT": b"USLT", b"WAF": b"WOAF",
    b"WAR": b"WOAR", b"WAS": b"WOAS", b"WCM": b"WCOM", b"WCP": b"WCOP",
    b"WPB": b"WPUB", b"WXX": b"WXXX",
}


# ---- 데이터 구조 ----------------------------------------------------------

@dataclass
class Id3Frame:
    """ID3v2 프레임 하나. data 는 헤더 제외, (필요시 unsync 디코드된) 본문 바이트."""
    frameid: bytes              # 4 바이트
    flags: int = 0
    hskip: int = 0              # group/crypt/dlen 플래그 파라미터 길이
    data: bytes = b""


@dataclass
class Id3Tag:
    offset: int = 0             # 파일 내 태그 오프셋
    length: int = 0             # 헤더/푸터 포함 전체 길이
    version: int = 0            # (major<<8)|revision; 0 = 태그 없음
    flags: int = 0
    frames: List[Id3Frame] = field(default_factory=list)


# ---- 정수/동기화 헬퍼 -----------------------------------------------------

def _get_int32(p: bytes) -> int:
    return (p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]


def _get_syncsafe_int(p: bytes) -> int:
    if (p[0] | p[1] | p[2] | p[3]) & 0x80:
        return SYNCSAFE_INT_BAD
    return (p[0] << 21) | (p[1] << 14) | (p[2] << 7) | p[3]


def _put_syncsafe_int(i: int) -> bytes:
    return bytes((
        (i >> 21) & 0x7F,
        (i >> 14) & 0x7F,
        (i >> 7) & 0x7F,
        i & 0x7F,
    ))


def _get_unsync_data(src: bytes) -> bytes:
    """unsynchronisation 디코드: 0xFF 0x00 → 0xFF. ID3v2 사양의 unsync 규칙."""
    out = bytearray()
    n = len(src)
    i = 0
    while i < n:
        out.append(src[i])
        if src[i] == 0xFF and i + 1 < n and src[i + 1] == 0x00:
            i += 1  # 삽입된 0x00 을 건너뜀
        i += 1
    return bytes(out)


# ---- ID3 전용 정수 파싱 (C sscanf 와 동일한 결과 재현) -------------------

def _atoi_or_none(s: str):
    """C atoi 와 동일한 결과이되, 정수 앞부분이 없으면 None.

    C sscanf 의 "변환 성공 개수" 검사와 동일한 결과가 되도록, 파싱 실패 시
    None 을 반환해 해당 필드를 채우지 않도록 한다.
    """
    s = s.strip()
    i = 0
    n = len(s)
    if i < n and s[i] in "+-":
        i += 1
    j = i
    while j < n and s[j].isdigit():
        j += 1
    if j == i:
        return None
    try:
        return int(s[:j])
    except ValueError:
        return None


def _scan_two_ints(s: str):
    """sscanf(s, "%d,%d") 와 동일한 결과. 둘 다 파싱되면 (a,b), 아니면 None."""
    parts = s.split(",")
    if len(parts) < 2:
        return None
    a = _atoi_or_none(parts[0])
    b = _atoi_or_none(parts[1])
    if a is None or b is None:
        return None
    return (a, b)


def _scan_undo(s: str):
    """sscanf(s, "%d,%d,%c") 와 동일한 결과. (a,b,char) 또는 None.

    C 의 %c 는 콤마 직후 첫 문자 1개를 공백 스킵 없이 읽는다.
    """
    parts = s.split(",")
    if len(parts) < 3:
        return None
    a = _atoi_or_none(parts[0])
    b = _atoi_or_none(parts[1])
    if a is None or b is None:
        return None
    c = parts[2][:1]
    if c == "":
        return None
    return (a, b, c)


# ---- RVA2 / TXXX 디코더 ---------------------------------------------------

def _decode_rva2_frame(frame: Id3Frame, info: Optional[MP3GainTagInfo]) -> int:
    """RVA2 프레임(track/album, master channel)을 디코드한다.

    info 가 주어지면 게인 정보를 채운다. info=None 이면 매칭 여부만 판정.
    매칭이면 1, 아니면 0 반환.
    """
    if frame.frameid != b"RVA2":
        return 0

    data = frame.data
    length = len(data)
    p = frame.hskip

    # identification: "track"/"album" (+ NUL), 대소문자 무관
    if p + 6 <= length and data[p:p + 6] in (b"track\0", b"TRACK\0"):
        is_album = False
        p += 6
    elif p + 6 <= length and data[p:p + 6] in (b"album\0", b"ALBUM\0"):
        is_album = True
        p += 6
    else:
        return 0

    # per-channel 데이터
    while p + 4 <= length:
        channel = data[p]
        # 16-bit signed BE = adjustment * 512
        raw = ((data[p + 1] << 8) | data[p + 2])
        if data[p + 1] & 0x80:
            raw -= 0x10000   # signed
        gain = raw / 512.0
        peakbits = data[p + 3]
        nbytes = (peakbits + 7) // 8
        if p + 4 + nbytes > length:
            break
        peak = 0.0
        if peakbits > 0:
            peak += data[p + 4]
        if peakbits > 8:
            peak += data[p + 5] / 256.0
        if peakbits > 16:
            peak += data[p + 6] / 65536.0
        if peakbits > 0:
            peak = peak / float(1 << ((peakbits - 1) & 7))
        p += 4 + nbytes
        if channel == 1:  # master volume
            if info is not None:
                if is_album:
                    info.have_album_gain = True
                    info.album_gain = gain
                    info.have_album_peak = (peakbits > 0)
                    info.album_peak = peak
                else:
                    info.have_track_gain = True
                    info.track_gain = gain
                    info.have_track_peak = (peakbits > 0)
                    info.track_peak = peak
    return 1


def _txxx_strings(frame: Id3Frame):
    """TXXX 프레임에서 (description, value) 두 문자열을 추출한다.

    인코딩 0(ISO-8859-1)/3(UTF-8) 만 허용. description 은 NUL 로 종료되고
    그 뒤가 value 다(mp3gain 과 동일한 처리). 매칭 불가 시 None.
    """
    if frame.frameid != b"TXXX":
        return None
    data = frame.data
    length = len(data)
    p = frame.hskip
    if p >= length or data[p] not in (0, 3):
        return None
    enc_byte = data[p]
    p += 1
    # description+value 를 최대 62바이트로 제한(mp3gain 과 동일한 결과).
    raw = data[p:p + 62]
    # description = 첫 NUL 까지, value = 그 다음 NUL 까지
    nul = raw.find(b"\0")
    if nul < 0:
        desc = raw
        value = b""
    else:
        desc = raw[:nul]
        rest = raw[nul + 1:]
        nul2 = rest.find(b"\0")
        value = rest if nul2 < 0 else rest[:nul2]
    enc = "utf-8" if enc_byte == 3 else "latin-1"
    try:
        return desc.decode(enc, "replace"), value.decode(enc, "replace")
    except Exception:
        return None


def _decode_txxx_frame(frame: Id3Frame, info: Optional[MP3GainTagInfo]) -> int:
    """ReplayGain 표준 TXXX 프레임을 디코드한다."""
    parsed = _txxx_strings(frame)
    if parsed is None:
        return 0
    desc, value = parsed
    key = desc.upper()
    if key == "REPLAYGAIN_ALBUM_GAIN":
        if info is not None:
            info.have_album_gain = True
            info.album_gain = _atof(value)
        return 1
    if key == "REPLAYGAIN_TRACK_GAIN":
        if info is not None:
            info.have_track_gain = True
            info.track_gain = _atof(value)
        return 1
    if key == "REPLAYGAIN_ALBUM_PEAK":
        if info is not None:
            info.have_album_peak = True
            info.album_peak = _atof(value)
        return 1
    if key == "REPLAYGAIN_TRACK_PEAK":
        if info is not None:
            info.have_track_peak = True
            info.track_peak = _atof(value)
        return 1
    if key == "REPLAYGAIN_REFERENCE_LOUDNESS":
        # 정보는 안 쓰지만 재기록 시 삭제 대상이므로 매칭으로 처리
        return 1
    return 0


def _decode_mp3gain_frame(frame: Id3Frame, info: Optional[MP3GainTagInfo]) -> int:
    """mp3gain 고유 TXXX 프레임(MP3GAIN_*)을 디코드한다."""
    parsed = _txxx_strings(frame)
    if parsed is None:
        return 0
    desc, value = parsed
    key = desc.upper()
    if key == "MP3GAIN_UNDO":
        f = _scan_undo(value)  # (left, right, char) or None
        if f is not None and info is not None:
            info.have_undo = True
            info.undo_left = f[0]
            info.undo_right = f[1]
            info.undo_wrap = f[2] in ("w", "W")
        return 1
    if key == "MP3GAIN_MINMAX":
        f = _scan_two_ints(value)
        if f is not None and info is not None:
            info.have_min_max_gain = True
            info.min_gain = f[0]
            info.max_gain = f[1]
        return 1
    if key == "MP3GAIN_ALBUM_MINMAX":
        f = _scan_two_ints(value)
        if f is not None and info is not None:
            info.have_album_min_max_gain = True
            info.album_min_gain = f[0]
            info.album_max_gain = f[1]
        return 1
    return 0


# ---- ID3v2 직렬화 헬퍼 (⑤-B1) -------------------------------------------

def _put_unsync_data(src: bytes) -> bytes:
    """unsynchronisation 인코드(ID3v2 사양의 unsync 규칙).

    0xFF 뒤에 (끝 / 0x00 / 상위3비트가 111) 이 오면 0x00 을 삽입한다.
    반환 길이가 입력과 같으면 unsync 가 불필요했다는 뜻(호출부에서 판단).
    """
    out = bytearray()
    n = len(src)
    for i in range(n):
        out.append(src[i])
        if src[i] == 0xFF and (
            i + 1 == n or src[i + 1] == 0x00 or (src[i + 1] & 0xE0) == 0xE0
        ):
            out.append(0x00)
    return bytes(out)


def _make_frame(frameid: bytes, fmt: str, *args) -> Id3Frame:
    """포맷 문자열에 따라 프레임 본문을 조립한다.

    fmt 문자: 's' = bytes 그대로(NUL 종단 없음), 'b' = 1바이트 정수,
    'h' = 16비트 BE 정수. 음수 정수도 하위 바이트만 기록(2의 보수).
    """
    body = bytearray()
    ai = 0
    for c in fmt:
        a = args[ai]
        ai += 1
        if c == "s":
            body += a
        elif c == "b":
            body.append(a & 0xFF)
        elif c == "h":
            body.append((a >> 8) & 0xFF)
            body.append(a & 0xFF)
        else:
            raise ValueError(f"bad format char {c!r}")
    return Id3Frame(frameid=frameid, flags=0, hskip=0, data=bytes(body))


def _make_rva2_frame(is_album: bool, gain: float,
                     have_peak: bool, peak: float) -> Id3Frame:
    """RVA2 프레임(track/album, master channel)을 생성한다.

    gain*512 를 int16 BE 클램프, peak*32768 을 uint16. C (int) 0방향 절단을
    Python int() 로 재현.
    """
    ident = b"album" if is_album else b"track"
    g = int(gain * 512.0)            # C (int): 0 방향 절단
    if g < -32768:
        g = -32768
    if g > 32767:
        g = 32767
    g &= 0xFFFF                      # 2의 보수 16비트
    if have_peak:
        p = int(peak * 32768.0)      # C (unsigned int)
        if p < 0:
            p = 0
        if p > 65535:
            p = 65535
        return _make_frame(b"RVA2", "sbbhbh", ident, 0, 1, g, 16, p)
    return _make_frame(b"RVA2", "sbbhb", ident, 0, 1, g, 0)


def _make_txxx_frame(description: bytes, value: bytes) -> Id3Frame:
    """TXXX 프레임 생성(인코딩 0/ISO-8859-1). "bsbs" = (0, desc, 0, value).

    description 뒤 NUL 구분자, 그 뒤 value. NUL 종단(끝)은 없음.
    """
    return _make_frame(b"TXXX", "bsbs", 0, description, 0, value)


def _write_tag(tag: Id3Tag):
    """태그를 ID3v2.4(전체 unsync, ext header 없음, 2KB 패딩, footer 없음)로
    직렬화한 바이트열을 반환한다. 프레임이 0개면 None.
    """
    if not tag.frames:
        return None

    # 원시 총 길이 계산(헤더 10 + 각 프레임 10 + unsync 데이터 길이) → 2KB 올림
    dlen = 10
    for fr in tag.frames:
        dlen += 10 + len(_put_unsync_data(fr.data))
    dlen = (dlen + 2047) & ~2047

    out = bytearray(dlen)            # 0 채움 → 패딩

    # 태그 헤더
    out[0:3] = b"ID3"
    out[3] = 4
    out[4] = 0
    out[5] = TAGFL_UNSYNC | (tag.flags & TAGFL_EXPR)
    out[6:10] = _put_syncsafe_int(dlen - 10)
    p = 10

    # 프레임
    for fr in tag.frames:
        fflags = fr.flags & ~FRAMEFL_UNSYNC
        enc = _put_unsync_data(fr.data)
        k = len(enc)
        out[p:p + 4] = fr.frameid
        out[p + 4:p + 8] = _put_syncsafe_int(k)
        if k != len(fr.data):
            fflags |= FRAMEFL_UNSYNC
        out[p + 8] = (fflags >> 8) & 0xFF
        out[p + 9] = fflags & 0xFF
        out[p + 10:p + 10 + k] = enc
        p += 10 + k

    return bytes(out)


# ---- ID3v2 파서 -----------------------------------------------------------

def _parse_v2_tag(f) -> tuple:
    """현재 위치에서 ID3v2 태그를 파싱한다.

    반환: (status, Id3Tag). status 1=성공, 0=없음, 음수=에러.
    """
    tag = Id3Tag()
    tag.offset = f.tell()
    buf = f.read(10)
    if len(buf) != 10:
        return 0, tag
    if buf[0:3] != b"ID3":
        return 0, tag

    major = buf[3]
    flags = buf[5]
    if major == 2:
        if flags & ~TAGFL_UNSYNC:
            return M3G_ERR_TAGFORMAT, tag
    elif major == 3:
        if flags & ~(TAGFL_UNSYNC | TAGFL_EXTHDR | TAGFL_EXPR):
            return M3G_ERR_TAGFORMAT, tag
    elif major == 4:
        if flags & ~(TAGFL_UNSYNC | TAGFL_EXTHDR | TAGFL_EXPR | TAGFL_FOOTER):
            return M3G_ERR_TAGFORMAT, tag
    else:
        return M3G_ERR_TAGFORMAT, tag

    dlen = _get_syncsafe_int(buf[6:10])
    if dlen == SYNCSAFE_INT_BAD:
        return M3G_ERR_TAGFORMAT, tag

    tag.flags = flags
    tag.version = (buf[3] << 8) | buf[4]
    tag.length = 10 + dlen + (10 if (flags & TAGFL_FOOTER) else 0)

    tagdata = f.read(dlen)
    if len(tagdata) != dlen:
        return M3G_ERR_TAGFORMAT, tag

    ver = tag.version >> 8

    # 2.2/2.3 전체 unsync 디코드
    if ver != 4 and (flags & TAGFL_UNSYNC):
        tagdata = _get_unsync_data(tagdata)
        dlen = len(tagdata)

    p = 0
    # extended header 스킵
    if flags & TAGFL_EXTHDR:
        if p + 6 > dlen:
            return M3G_ERR_TAGFORMAT, tag
        if ver == 4:
            k = _get_syncsafe_int(tagdata[p:p + 4])
            if k == SYNCSAFE_INT_BAD or k > dlen:
                return M3G_ERR_TAGFORMAT, tag
            p += k
        elif ver == 3:
            k = _get_int32(tagdata[p:p + 4])
            if k > dlen:
                return M3G_ERR_TAGFORMAT, tag
            p += 4 + k

    # 프레임 스캔
    while p < dlen and tagdata[p] != 0:
        if ver == 2:
            if p + 5 > dlen:
                return M3G_ERR_TAGFORMAT, tag
            frameid = _UPGRADE_ID3V22.get(bytes(tagdata[p:p + 3]), b"\0\0\0\0")
            flen = (tagdata[p + 3] << 16) | (tagdata[p + 4] << 8) | tagdata[p + 5]
            fflags = 0
            if flen > dlen:
                return M3G_ERR_TAGFORMAT, tag
            p += 6
        elif ver == 3:
            if p + 10 > dlen:
                return M3G_ERR_TAGFORMAT, tag
            frameid = bytes(tagdata[p:p + 4])
            flen = _get_int32(tagdata[p + 4:p + 8])
            fflags = (tagdata[p + 8] << 7) & 0xFF00
            if tagdata[p + 9] & 0x80:
                fflags |= FRAMEFL_COMPR | FRAMEFL_DLEN
            if tagdata[p + 9] & 0x40:
                fflags |= FRAMEFL_CRYPT
            if tagdata[p + 9] & 0x20:
                fflags |= FRAMEFL_GROUP
            if tagdata[p + 9] & 0x1F:
                fflags |= FRAMEFL_BAD
            if flen > dlen:
                return M3G_ERR_TAGFORMAT, tag
            p += 10
        elif ver == 4:
            if p + 10 > dlen:
                return M3G_ERR_TAGFORMAT, tag
            frameid = bytes(tagdata[p:p + 4])
            flen = _get_syncsafe_int(tagdata[p + 4:p + 8])
            fflags = (tagdata[p + 8] << 8) | tagdata[p + 9]
            if flen == SYNCSAFE_INT_BAD or flen > dlen:
                return M3G_ERR_TAGFORMAT, tag
            p += 10
        else:
            return M3G_ERR_TAGFORMAT, tag

        if p + flen > dlen:
            return M3G_ERR_TAGFORMAT, tag

        frameid = bytearray(frameid)

        # 미지원 프레임 드롭
        if (frameid[0] == 0 or
                bytes(frameid) == b"RVAD" or
                bytes(frameid) == b"RGAD" or
                bytes(frameid) == b"XRVA"):
            p += flen
            continue

        # 업그레이드 불가한 2.3 프레임 드롭
        if ver == 3 and (fflags & (FRAMEFL_CRYPT | FRAMEFL_BAD)):
            p += flen
            continue

        # 플래그 대비 너무 짧은 프레임 드롭
        fhskip = ((1 if fflags & FRAMEFL_GROUP else 0) +
                  (1 if fflags & FRAMEFL_CRYPT else 0) +
                  (4 if fflags & FRAMEFL_DLEN else 0))
        if fhskip > flen:
            p += flen
            continue

        # 너무 짧은 2.2 PIC(→APIC) 드롭
        if ver == 2 and bytes(frameid) == b"APIC" and flen < 6:
            p += flen
            continue

        # TYER → TDRC
        if bytes(frameid) == b"TYER":
            frameid = bytearray(b"TDRC")

        # tag alteration 시 폐기 요청 프레임 드롭
        if fflags & FRAMEFL_TAGALTER:
            p += flen
            continue

        frame = Id3Frame(frameid=bytes(frameid), flags=fflags, hskip=fhskip)

        # 프레임 데이터 복사
        if ver == 4 and (fflags & FRAMEFL_UNSYNC):
            frame.data = _get_unsync_data(tagdata[p:p + flen])
            p += flen
        elif ver == 2 and bytes(frameid) == b"APIC":
            # PIC → APIC 포맷 변환
            body = bytearray()
            body.append(tagdata[p])  # text encoding
            three = bytes(tagdata[p + 1:p + 4])
            if three == b"PNG":
                body += b"image/png\0"
            elif three == b"JPG":
                body += b"image/jpeg\0"
            elif tagdata[p + 1] == 0:
                body += tagdata[p + 1:p + 4]
                body.append(0)
            body += tagdata[p + 4:p + flen]
            frame.data = bytes(body)
            p += flen
        else:
            frame.data = bytes(tagdata[p:p + flen])
            p += flen

        # 업그레이드된 2.3 DLEN 프레임의 플래그 파라미터 재정렬
        if ver == 3 and (fflags & FRAMEFL_DLEN):
            d = bytearray(frame.data)
            k = _get_int32(d[0:4])
            if fflags & FRAMEFL_GROUP:
                d[0] = d[4]
                d[1:5] = _put_syncsafe_int(k)
            else:
                d[0:4] = _put_syncsafe_int(k)
            frame.data = bytes(d)

        tag.frames.append(frame)

    if p > dlen:
        return M3G_ERR_TAGFORMAT, tag

    return 1, tag


def _make_text_frame(frameid: bytes, *parts: bytes) -> Id3Frame:
    """간단 프레임 생성 (ID3v1 변환용). parts 를 그대로 이어붙인다."""
    return Id3Frame(frameid=frameid, flags=0, hskip=0, data=b"".join(parts))


def _parse_v1_tag(f) -> tuple:
    """ID3v1 태그를 ID3v2.4 프레임으로 변환한다."""
    tag = Id3Tag()
    tag.offset = f.tell()
    buf = f.read(128)
    if len(buf) != 128:
        return 0, tag
    if buf[0:3] != b"TAG":
        return 0, tag

    tag.length = 128
    tag.version = 0
    tag.flags = 0

    def field30(off):
        s = buf[off:off + 30]
        s = s.rstrip(b" ").rstrip(b"\0").rstrip(b" ")
        return s

    if buf[3] != 0:
        tag.frames.append(_make_text_frame(b"TIT2", b"\0", field30(3)))
    if buf[33] != 0:
        tag.frames.append(_make_text_frame(b"TPE1", b"\0", field30(33)))
    if buf[63] != 0:
        tag.frames.append(_make_text_frame(b"TALB", b"\0", field30(63)))
    if all(0x30 <= buf[93 + k] <= 0x39 for k in range(4)):
        tag.frames.append(_make_text_frame(b"TDRC", b"\0", buf[93:97]))
    if buf[97] != 0:
        tag.frames.append(
            _make_text_frame(b"COMM", b"\0", b"XXX", b"\0", field30(97)))
    if buf[125] == 0 and buf[126] != 0:
        tag.frames.append(
            _make_text_frame(b"TRCK", b"\0", str(buf[126]).encode("latin-1")))

    return 1, tag


# ---- 태그 탐색 (앞 ID3v2 → 끝 ID3v2.4 → 끝 ID3v1) -----------------------

def _search_tag(f) -> tuple:
    """파일에서 태그를 탐색한다. 반환: (status, Id3Tag)."""
    f.seek(0, 0)
    status, tag = _parse_v2_tag(f)

    id3v1_pos = 0

    if status == 0:
        f.seek(0, 2)
        pos = f.tell()

        while pos > 128:
            # ID3v2.4 footer 탐색
            f.seek(pos - 10, 0)
            buf = f.read(10)
            if len(buf) != 10:
                return M3G_ERR_READ, tag
            if (buf[0:3] == b"3DI" and buf[3] == 4 and
                    ((buf[6] | buf[7] | buf[8] | buf[9]) & 0x80) == 0):
                k = _get_syncsafe_int(buf[6:10])
                if 20 + k < pos:
                    pos -= 20 + k
                    f.seek(pos, 0)
                    status, tag = _parse_v2_tag(f)
                    break

            # ID3v1 / Lyrics3v2 탐색
            f.seek(pos - 128, 0)
            buf = f.read(3)
            if len(buf) != 3:
                return M3G_ERR_READ, tag
            if buf == b"TAG":
                pos -= 128
                id3v1_pos = pos
                if pos > 26:
                    f.seek(pos - 15, 0)
                    lyr = f.read(15)
                    if len(lyr) != 15:
                        return M3G_ERR_READ, tag
                    if lyr[6:15] == b"LYRICS200":
                        k = 0
                        ok = True
                        for j in range(6):
                            if not (0x30 <= lyr[j] <= 0x39):
                                ok = False
                                break
                            k = 10 * k + (lyr[j] - 0x30)
                        if ok and k >= 11 and k + 15 < pos:
                            pos -= k + 15
                continue

            # APE 태그 탐색
            f.seek(pos - 32, 0)
            buf = f.read(32)
            if len(buf) != 32:
                return M3G_ERR_READ, tag
            if buf[0:8] == b"APETAGEX":
                k = buf[12] | (buf[13] << 8) | (buf[14] << 16) | (buf[15] << 24)
                if buf[23] & 0x80:
                    k += 32
                if 32 <= k < pos:
                    pos -= k
                    continue

            break

    if status == 0 and id3v1_pos != 0:
        f.seek(id3v1_pos, 0)
        status, tag = _parse_v1_tag(f)

    return status, tag


# ---- 공개 API: 읽기 -------------------------------------------------------

def read_mp3gain_id3_tag(filename: str, info: MP3GainTagInfo) -> int:
    """ID3v2 태그에서 게인 정보를 읽어 info 에 채운다.

    반환: 1=태그 발견·처리, 0=태그 없음, 음수=에러.
    """
    try:
        f = open(filename, "rb")
    except OSError:
        return M3G_ERR_FILEOPEN
    try:
        status, tag = _search_tag(f)
    finally:
        f.close()

    if status == 1:
        for frame in tag.frames:
            _decode_rva2_frame(frame, info)
            _decode_txxx_frame(frame, info)
            _decode_mp3gain_frame(frame, info)

    return status


# ---- 공개 API: 쓰기/제거 (⑤-B2) -----------------------------------------

def _restore_timestamp(filename: str, saved) -> None:
    """저장해 둔 stat 으로 atime/mtime 복원. tag.py 의 동명 헬퍼와 대칭."""
    if saved is not None:
        os.utime(filename, (saved.st_atime, saved.st_mtime))


def _copy_data(inf, outf, offset: int, count: int) -> None:
    """inf 의 offset 부터 count 바이트를 outf 로 복사. count<0 이면 끝까지.

    64KB 청크로 복사한다. 에러는 예외로 전파.
    """
    bufsize = 65536
    inf.seek(offset, 0)
    remaining = count
    while remaining != 0:
        k = bufsize if (remaining < 0 or remaining > bufsize) else remaining
        chunk = inf.read(k)
        if not chunk:
            break
        outf.write(chunk)
        if remaining > 0:
            remaining -= len(chunk)


def write_mp3gain_id3_tag(
    filename: str,
    info: MP3GainTagInfo,
    save_timestamp: bool = False,
) -> int:
    """ID3v2 태그에 게인 정보를 (재)기록한다.

    항상 파일 앞 단일 ID3v2.4 태그를 쓰거나 갱신한다. 기존 RG 프레임은 제거하고
    새 프레임을 고정 순서로 append. 변경할 게 없으면(need_update 거짓) 파일을
    건드리지 않고 0 반환. 변경 시 임시파일(.TMP)에 새 태그 + 원본 잔여를 쓰고
    os.replace 로 교체.

    반환: 1=기록함, 0=변경 불필요, 음수=에러.
    """
    saved_stat = None
    if save_timestamp:
        try:
            saved_stat = os.stat(filename)
        except OSError:
            saved_stat = None

    try:
        f = open(filename, "rb")
    except OSError:
        return M3G_ERR_FILEOPEN

    try:
        status, tag = _search_tag(f)

        if status < 0:
            return status

        if status == 0:
            # 태그 없음 → 빈 태그 생성(version=0: 전체 복사 분기 표시).
            tag = Id3Tag(offset=0, length=0, version=0, flags=0, frames=[])

        # 기존 RG 프레임 제거.
        need_update = False
        kept = []
        for frame in tag.frames:
            if (_decode_rva2_frame(frame, None) == 1 or
                    _decode_txxx_frame(frame, None) == 1 or
                    _decode_mp3gain_frame(frame, None) == 1):
                need_update = True
            else:
                kept.append(frame)
        tag.frames = kept

        # 새 RG 프레임 append (TXXX 는 Winamp 호환을 위해 소문자 필드명 사용).
        if (info.have_track_gain or info.have_track_peak or
                info.have_album_gain or info.have_album_peak):
            need_update = True
            tag.frames.append(
                _make_txxx_frame(b"replaygain_reference_loudness", b"89.0 dB"))

        if info.have_track_gain:
            need_update = True
            tag.frames.append(
                _make_rva2_frame(False, info.track_gain,
                                 info.have_track_peak, info.track_peak))
            tag.frames.append(
                _make_txxx_frame(b"replaygain_track_gain",
                                 _fmt_gain(info.track_gain).encode("latin-1")))
        if info.have_track_peak:
            need_update = True
            tag.frames.append(
                _make_txxx_frame(b"replaygain_track_peak",
                                 _fmt_peak(info.track_peak).encode("latin-1")))

        if info.have_album_gain:
            need_update = True
            tag.frames.append(
                _make_rva2_frame(True, info.album_gain,
                                 info.have_album_peak, info.album_peak))
            tag.frames.append(
                _make_txxx_frame(b"replaygain_album_gain",
                                 _fmt_gain(info.album_gain).encode("latin-1")))
        if info.have_album_peak:
            need_update = True
            tag.frames.append(
                _make_txxx_frame(b"replaygain_album_peak",
                                 _fmt_peak(info.album_peak).encode("latin-1")))

        # mp3gain 고유 프레임 append.
        if info.have_min_max_gain:
            need_update = True
            tag.frames.append(
                _make_txxx_frame(
                    b"MP3GAIN_MINMAX",
                    f"{info.min_gain:03d},{info.max_gain:03d}".encode("latin-1")))
        if info.have_album_min_max_gain:
            need_update = True
            tag.frames.append(
                _make_txxx_frame(
                    b"MP3GAIN_ALBUM_MINMAX",
                    f"{info.album_min_gain:03d},{info.album_max_gain:03d}"
                    .encode("latin-1")))
        if info.have_undo:
            need_update = True
            wrap_ch = "W" if info.undo_wrap else "N"
            tag.frames.append(
                _make_txxx_frame(
                    b"MP3GAIN_UNDO",
                    f"{info.undo_left:+04d},{info.undo_right:+04d},{wrap_ch}"
                    .encode("latin-1")))

        if not need_update:
            # 변경할 게 없음 — 파일 무수정.
            return 0

        # 새 태그 직렬화.
        new_tag = _write_tag(tag)
        if new_tag is None:
            # need_update 인데 프레임이 0개인 경우(기존 RG 만 제거된 상황 등):
            # 빈 ID3v2 태그를 쓰지 않고 원본에서 기존 태그만 들어낸다.
            new_tag = b""

        # 임시파일에 새 태그 + 원본 잔여 기록.
        tmpname = filename + ".TMP"
        with open(tmpname, "wb") as outf:
            if new_tag:
                outf.write(new_tag)
            if tag.version == 0:
                # 원본에 ID3v2 없음 → 전체 복사(ID3v1 꼬리 포함 보존).
                _copy_data(f, outf, 0, -1)
            else:
                # 원본 앞 ID3v2 만 들어내고 나머지 복사.
                _copy_data(f, outf, 0, tag.offset)
                _copy_data(f, outf, tag.offset + tag.length, -1)
    finally:
        f.close()

    # 원자적 교체(Windows 포함: os.replace 가 기존 파일 덮어씀).
    os.replace(tmpname, filename)

    if save_timestamp:
        _restore_timestamp(filename, saved_stat)

    return 1


def remove_mp3gain_id3_tag(filename: str, save_timestamp: bool = False) -> int:
    """ID3v2 태그에서 게인 정보를 제거한다.

    모든 have_* 가 꺼진 빈 info 로 write 를 호출 → RG 프레임만 제거되고 append
    는 없으므로, 제거가 일어났으면 1, 없었으면 0 반환.
    """
    info = MP3GainTagInfo()  # 모든 have_* 기본 False
    return write_mp3gain_id3_tag(filename, info, save_timestamp)