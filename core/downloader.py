import unicodedata
import yt_dlp
from pathlib import Path
from yt_dlp.postprocessor.common import PostProcessor

from utils.file_utils import ensure_dir


class _NFCNormalizePP(PostProcessor):
    """후처리 체인의 pre_process 단계 (extract_info 직후, 다운로드/파일명
    결정/메타 임베드 모두에 앞섬) 에 끼워, info dict 의 문자열 값을
    재귀적으로 NFC 로 정규화한다. SoundCloud · macOS 등에서 NFD 로 들어온
    한글 메타가 ID3 TIT2 / m4a ©nam atom / 파일명에 NFD 로 박히는 것을 차단.

    동시에 FFmpegMetadataPP 의 webpage_url → comment 자동 매핑도 차단 —
    yt-dlp 소스의 _get_metadata_opts 가 add() 호출 뒤에 도는 meta_<key>
    regex 루프가 우리 meta_comment 값을 최종으로 덮어쓰는 메커니즘 이용.
    description 이 있으면 그것을, 없으면 빈 문자열. URL 보관은 별도로 박히는
    purl 태그가 담당하므로 정보 손실 없음.
    """

    def run(self, info):
        self._normalize_in_place(info)
        info["meta_comment"] = info.get("description") or ""
        return [], info

    @staticmethod
    def _normalize_in_place(obj):
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                if isinstance(value, str):
                    obj[key] = unicodedata.normalize("NFC", value)
                elif isinstance(value, (dict, list)):
                    _NFCNormalizePP._normalize_in_place(value)
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                if isinstance(value, str):
                    obj[i] = unicodedata.normalize("NFC", value)
                elif isinstance(value, (dict, list)):
                    _NFCNormalizePP._normalize_in_place(value)


_BASE_OPTS = {
    "quiet"                : True,
    "no_warnings"          : True,
    # YouTube JS 챌린지 — 사용 가능한 런타임(node/deno/bun) 자동 탐지에 맡김.
    # 명시 고정은 외부 환경 변화에 취약하다는 것이 통제 실험으로 확인됨.
    "socket_timeout"       : 30,
    "retries"              : 10,
    "fragment_retries"     : float("inf"),
    "file_access_retries"  : 5,
    "retry_sleep_functions": {
        "http"    : lambda n: min(2 ** n, 30),
        "fragment": lambda n: min(2 ** n, 30),
    },
}


class Downloader:
    def __init__(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def download(self, url, format_id, ext, save_dir, progress_hook, postprocess_hook):
        self._cancelled = False
        ensure_dir(save_dir)

        is_audio = ext in ("mp3", "m4a", "wav", "aac")

        postprocessors = []
        if is_audio:
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": ext,
                "preferredquality": "192",
            })
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
        postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

        ydl_opts = {
            **_BASE_OPTS,
            "format"             : format_id,
            "outtmpl"            : str(Path(save_dir) / "%(title)s.%(ext)s"),
            "windowsfilenames"   : True,    # yt-dlp 자체 sanitize
            "trim_file_name"     : 200,
            "merge_output_format": ext if not is_audio else None,
            "writethumbnail"     : True,
            "embedthumbnail"     : True,
            "addmetadata"        : True,
            "postprocessors"     : postprocessors,
            "postprocessor_args" : {"thumbnailsconvertor": ["-y"]},
            "progress_hooks"     : [self._wrap_hook(progress_hook)],
            "postprocessor_hooks": [self._wrap_hook(postprocess_hook)],
        }

        if ext == "mp3":
            ydl_opts["postprocessor_args"]["ffmpeg"] = [
                "-id3v2_version", "3",
                "-write_id3v1", "1",
            ]

        convert_pp = {
            "key"   : "FFmpegThumbnailsConvertor",
            "format": "jpg",
            "when"  : "before_dl",
        }
        embed_idx = next(
            (i for i, p in enumerate(ydl_opts["postprocessors"])
             if p.get("key") == "EmbedThumbnail"),
            len(ydl_opts["postprocessors"])
        )
        ydl_opts["postprocessors"].insert(embed_idx, convert_pp)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.add_post_processor(_NFCNormalizePP(), when="pre_process")
            ydl.download([url])

    def _wrap_hook(self, original_hook):
        def hook(d):
            if self._cancelled:
                raise yt_dlp.utils.DownloadCancelled("사용자가 취소했습니다.")
            original_hook(d)
        return hook
