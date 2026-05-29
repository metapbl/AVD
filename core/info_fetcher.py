# core/info_fetcher.py
# URL에서 영상 정보(제목, 썸네일, 화질 목록 등)를 추출하는 파일

import yt_dlp
from dataclasses import dataclass

from utils.file_utils import normalize_info_dict


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
            "js_runtimes"       : {"node": {}},
            "remote_components" : ["ejs:github"],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # SoundCloud · macOS 등 일부 소스의 NFD 한글을 NFC 로 정규화.
        # 이 한 줄로 title · uploader · description · formats 내부 문자열까지
        # 재귀적으로 NFC 가 보장된다.
        info = normalize_info_dict(info)

        return VideoInfo(
            url       = url,
            title     = info.get("title", "제목 없음"),
            thumbnail = self._pick_thumbnail(info),
            duration  = info.get("duration", 0),
            uploader  = info.get("uploader", ""),
            formats   = self._parse_formats(info),
        )
    
    def _pick_thumbnail(self, info: dict) -> str:
        """
        info dict 에서 가장 적절한 썸네일 URL 을 고른다.

        yt-dlp 의 `info["thumbnail"]` 은 단일 best 후보 한 개만 들어 있고
        YouTube 의 maxresdefault.jpg 처럼 실제로는 404 인 URL 이 들어오는
        경우가 있다. 그래서 `info["thumbnails"]` 리스트(품질·preference 정보
        포함)를 먼저 살펴 best 를 직접 고른다.

        선정 규칙:
            1. `thumbnails` 후보 중 url 이 문자열이고 http(s) 로 시작하는
               항목만 추림.
            2. 점수 = (preference, width*height, 원래 인덱스) 튜플로
               내림차순 정렬해 1 위 채택. preference·해상도 정보가 없으면
               0 으로 간주.
            3. 후보가 비어 있으면 `info["thumbnail"]` 로 폴백.
            4. 둘 다 없으면 빈 문자열.
        """
        thumbnails = info.get("thumbnails") or []

        scored = []
        for idx, t in enumerate(thumbnails):
            if not isinstance(t, dict):
                continue
            url = t.get("url")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                continue
            preference = t.get("preference") or 0
            width      = t.get("width")  or 0
            height     = t.get("height") or 0
            area       = width * height
            scored.append((preference, area, idx, url))

        if scored:
            # preference → area → 원래 인덱스 순으로 내림차순. 정보가 전혀
            # 없으면 (0, 0, idx) 가 되어 yt-dlp 가 마지막에 둔(보통 best)
            # 후보가 채택된다.
            scored.sort(reverse=True)
            return scored[0][3]

        fallback = info.get("thumbnail", "")
        return fallback if isinstance(fallback, str) else ""

    def _parse_formats(self, info: dict) -> list[FormatInfo]:
        """
        yt-dlp가 반환한 포맷 목록을 FormatInfo 리스트로 정리
        화질 높은 순으로 정렬

        현재 정책: 비디오는 무조건 MP4 로 머지 (Downloader.merge_output_format).
        그래서 사용자에게 보이는 라벨도 yt-dlp 의 raw ext (webm/mp4) 가 아니라
        실제 결과 컨테이너인 "MP4" 로 통일한다. 라벨이 진실을 말하도록 하는
        것이 거짓 라벨(예: "1080p WEBM" 인데 파일은 .mp4)을 피하는 정공법.
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
            size    = f.get("filesize") or f.get("filesize_approx") or 0

            # 라벨의 ext 표기는 항상 "MP4" — 실제 머지 결과와 일치.
            # yt-dlp 의 raw ext (webm 등) 는 사용자에게 노출하지 않는다.
            result.append(FormatInfo(
                format_id   = f"{f['format_id']}+bestaudio/best",
                label       = f"{height}p MP4",
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
