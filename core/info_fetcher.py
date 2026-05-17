# core/info_fetcher.py
# URL에서 영상 정보(제목, 썸네일, 화질 목록 등)를 추출하는 파일

import yt_dlp
from dataclasses import dataclass


@dataclass
class FormatInfo:
    """선택 가능한 화질/형식 하나를 표현하는 데이터 클래스"""
    format_id   : str   # yt-dlp 내부 포맷 ID
    label       : str   # UI에 표시할 이름 (예: "1080p MP4")
    ext         : str   # 확장자 (mp4, webm, mp3 등)
    resolution  : str   # 해상도 문자열 (예: "1920x1080")
    filesize    : int   # 예상 파일 크기 (바이트, 0이면 알 수 없음)
    is_audio    : bool  # 오디오 전용 여부


@dataclass
class VideoInfo:
    """추출된 영상 전체 정보"""
    url         : str
    title       : str
    thumbnail   : str
    duration    : int               # 초 단위
    uploader    : str
    formats     : list[FormatInfo]  # 선택 가능한 포맷 목록


class InfoFetcher:
    """URL에서 영상 정보를 추출하는 클래스"""

    def fetch(self, url: str) -> VideoInfo:
        """
        URL을 받아 VideoInfo 반환
        실패 시 예외 발생
        """
        ydl_opts = {
            "quiet"             : True,
            "no_warnings"       : True,
            "extract_flat"      : False,
            "js_runtimes"       : {"node": {}},        # ← 수정
            "remote_components" : ["ejs:github"],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return VideoInfo(
            url         = url,
            title       = info.get("title", "제목 없음"),
            thumbnail   = info.get("thumbnail", ""),
            duration    = info.get("duration", 0),
            uploader    = info.get("uploader", ""),
            formats     = self._parse_formats(info),
        )

    def _parse_formats(self, info: dict) -> list[FormatInfo]:
        """
        yt-dlp가 반환한 포맷 목록을 FormatInfo 리스트로 정리
        화질 높은 순으로 정렬
        """
        formats = info.get("formats", [])
        result  = []

        # 통합 포맷 (최고 화질 자동 선택) 먼저 추가
        result.append(FormatInfo(
            format_id   = "bestvideo+bestaudio/best",
            label       = "최고 화질 (자동 선택)",
            ext         = "mp4",
            resolution  = "최고화질",
            filesize    = 0,
            is_audio    = False,
        ))

        # 영상 포맷 파싱
        video_formats = []
        for f in formats:
            if f.get("vcodec", "none") == "none":
                continue
            height = f.get("height")
            if not height:
                continue
            video_formats.append(f)

        # 높은 해상도 순 정렬 후 중복 해상도 제거
        seen_heights = set()
        for f in sorted(video_formats,
                        key=lambda x: x.get("height", 0),
                        reverse=True):
            height = f.get("height", 0)
            if height in seen_heights:
                continue
            seen_heights.add(height)

            width   = f.get("width", 0)
            ext     = f.get("ext", "mp4")
            size    = f.get("filesize") or f.get("filesize_approx") or 0

            result.append(FormatInfo(
                format_id   = f"{f['format_id']}+bestaudio/best",
                label       = f"{height}p {ext.upper()}",
                ext         = "mp4",
                resolution  = f"{width}x{height}",
                filesize    = size,
                is_audio    = False,
            ))

        # MP3 오디오 전용 옵션 추가
        result.append(FormatInfo(
            format_id   = "bestaudio/best",
            label       = "MP3 오디오만",
            ext         = "mp3",
            resolution  = "오디오 전용",
            filesize    = 0,
            is_audio    = True,
        ))

        return result