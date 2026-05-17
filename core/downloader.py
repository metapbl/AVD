# core/downloader.py
# yt-dlp를 사용해 실제 다운로드를 수행하는 파일

import yt_dlp
from pathlib import Path
from utils.file_utils import ensure_dir


class Downloader:
    """yt-dlp 기반 다운로드 실행 클래스"""

    def __init__(self):
        self._cancelled = False  # 취소 플래그

    def cancel(self):
        """다운로드 취소 요청"""
        self._cancelled = True

    def download(
        self,
        url              : str,
        format_id        : str,
        ext              : str,
        save_dir         : str,
        progress_hook,
        postprocess_hook,
    ):
        """
        실제 다운로드 실행
        progress_hook(d)    : 진행률 딕셔너리 전달
        postprocess_hook(d) : 후처리 상태 딕셔너리 전달
        """
        self._cancelled = False
        ensure_dir(save_dir)

        # 오디오 전용 여부 판단
        is_audio = ext in ("mp3", "m4a", "wav", "aac")

        # ── 후처리기 구성 ─────────────────────────────────
        # 순서가 중요. yt-dlp 는 리스트 순서대로 후처리를 실행한다.
        # 1) (오디오 모드) ExtractAudio  : 컨테이너 변환
        # 2) FFmpegMetadata              : 제목·업로더·날짜 등 메타 임베드
        # 3) EmbedThumbnail              : 썸네일 박기
        # 단, EmbedThumbnail 은 jpg/png 만 안정적으로 받으므로
        # YouTube 가 주는 webp 썸네일을 jpg 로 미리 변환해 둔다.
        postprocessors = []

        if is_audio:
            postprocessors.append({
                "key"             : "FFmpegExtractAudio",
                "preferredcodec"  : ext,
                "preferredquality": "192",
            })

        # 메타데이터 임베드 — 제목·업로더·업로드 일자·원본 URL 등
        postprocessors.append({
            "key": "FFmpegMetadata",
            "add_metadata": True,
        })

        # 썸네일 임베드 — 파일 아이콘·앨범 아트로 사용됨
        postprocessors.append({
            "key": "EmbedThumbnail",
            "already_have_thumbnail": False,
        })

        # ── yt-dlp 옵션 구성 ─────────────────────────────
        ydl_opts = {
            "format"             : format_id,
            "outtmpl"            : str(Path(save_dir) / "%(title)s.%(ext)s"),
            "merge_output_format": ext if not is_audio else None,
            "quiet"              : True,
            "no_warnings"        : True,

            # JS 챌린지 해결
            "js_runtimes"        : {"node": {}},
            "remote_components"  : ["ejs:github"],

            # ── 썸네일 / 메타데이터 임베드 핵심 ──
            "writethumbnail"     : True,        # 썸네일을 임시로 받아둔다
            "embedthumbnail"     : True,        # 파일에 임베드 (안전망)
            "addmetadata"        : True,        # 메타데이터 임베드 (안전망)
            "postprocessors"     : postprocessors,

            # webp → jpg 변환. mp4/mp3 컨테이너가 webp 를 잘 못 받기 때문.
            "postprocessor_args" : {
                "thumbnailsconvertor": ["-y"],
            },

            # 콜백
            "progress_hooks"     : [self._wrap_hook(progress_hook)],
            "postprocessor_hooks": [postprocess_hook],
        }

        # MP3 의 경우, ID3v2.3 으로 강제 저장 (Windows·구형 플레이어 호환).
        if ext == "mp3":
            ydl_opts["postprocessor_args"]["ffmpeg"] = [
                "-id3v2_version", "3",
                "-write_id3v1", "1",
            ]

        # webp 썸네일을 jpg 로 변환하는 후처리기를 EmbedThumbnail 앞에 삽입
        # (이미 위 postprocessors 리스트에 EmbedThumbnail 이 있음)
        # FFmpegThumbnailsConvertor 는 EmbedThumbnail 직전에 자동 실행되도록
        # yt-dlp 가 알아서 처리하지만, 명시적으로 넣어두면 안정적이다.
        convert_pp = {
            "key"   : "FFmpegThumbnailsConvertor",
            "format": "jpg",
            "when"  : "before_dl",
        }
        # EmbedThumbnail 앞에 삽입
        embed_idx = next(
            (i for i, p in enumerate(ydl_opts["postprocessors"])
             if p.get("key") == "EmbedThumbnail"),
            len(ydl_opts["postprocessors"])
        )
        ydl_opts["postprocessors"].insert(embed_idx, convert_pp)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    def _wrap_hook(self, original_hook):
        """
        취소 플래그를 체크하는 래퍼 훅
        취소 요청 시 yt-dlp 다운로드 중단
        """
        def hook(d):
            if self._cancelled:
                raise yt_dlp.utils.DownloadCancelled("사용자가 취소했습니다.")
            original_hook(d)
        return hook