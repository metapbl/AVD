# core/downloader.py
# yt-dlp를 사용해 실제 다운로드를 수행하는 파일

import yt_dlp
from pathlib import Path
from utils.file_utils import ensure_dir, normalize_info_dict, sanitize_filename


# ── 모듈 공통 yt-dlp 옵션 ─────────────────────────────────
# probe 와 본 다운로드 양쪽이 공유해야 하는 옵션을 한 곳에 모은다.
# - quiet/no_warnings   : 콘솔 잡음 억제
# - js_runtimes/remote_components : YouTube EJS 챌린지 해결 (Node.js 필수)
# - socket_timeout 이하 : 일시적 stall 흡수. yt-dlp 기본값은 짧아서
#   urllib3 ReadTimeoutError 가 그대로 DownloadError 로 전파됨.
#   여기서 내부 재시도로 흡수시킨다. 지수 백오프 상한 30초.
_BASE_OPTS = {
    "quiet"                : True,
    "no_warnings"          : True,

    # JS 챌린지 해결
    "js_runtimes"          : {"node": {}},
    "remote_components"    : ["ejs:github"],

    # ── 회복력 (Read timed out 대비) ──
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

        # ── 사전 정보 추출 + NFC 정규화 ─────────────────
        # yt-dlp 가 본 다운로드 시 자체적으로 extract_info 를 다시 돌리면
        # 원본 NFD 메타가 그대로 FFmpegMetadataPP 에 흘러들어가 ID3/atom
        # 으로 박힌다. 이를 막기 위해 우리가 먼저 정보를 받아 NFC 화한 뒤,
        # ydl.download() 대신 ydl.process_ie_result(probed, download=True)
        # 로 호출한다. 이렇게 하면 yt-dlp 는 재추출 없이 우리 NFC dict 를
        # 그대로 후처리 체인에 넘긴다.
        probe_opts = {
            **_BASE_OPTS,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(probe_opts) as ydl_probe:
            probed = ydl_probe.extract_info(url, download=False)
        probed = normalize_info_dict(probed)

        nfc_title = sanitize_filename(probed.get("title", "download"))

        # outtmpl 에 박을 때 % 는 yt-dlp 변수 도입자이므로 escape.
        outtmpl_title = nfc_title.replace("%", "%%")

        # ── 후처리기 구성 ─────────────────────────────────
        # 순서가 중요. yt-dlp 는 리스트 순서대로 후처리를 실행한다.
        # 1) (오디오 모드) ExtractAudio  : 컨테이너 변환
        # 2) FFmpegMetadata              : 제목·업로더·날짜 등 메타 임베드
        # 3) EmbedThumbnail              : 썸네일 박기
        # FFmpegMetadata 는 info dict 의 title/artist/... 를 그대로
        # -metadata 인자로 변환하므로, 위에서 NFC 화한 probed 를
        # process_ie_result 로 넘기는 것만으로 NFC 가 보장된다.
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
            **_BASE_OPTS,

            "format"             : format_id,
            # title 자리는 NFC 로 우리가 직접 박고, ext 만 yt-dlp 가 치환.
            "outtmpl"            : str(Path(save_dir) / f"{outtmpl_title}.%(ext)s"),
            "merge_output_format": ext if not is_audio else None,

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
            "postprocessor_hooks": [self._wrap_hook(postprocess_hook)],
        }

        # MP3 한정: ID3v2.3 강제 (Windows 호환).
        # 이전엔 -map_metadata -1 로 m4a ftyp 박스 잔재(major_brand 등)를
        # 끊었으나, FFmpegMetadataPP 가 박는 -metadata title=... 까지 함께
        # 무효화되어 ID3 title 이 통째로 사라지는 부작용이 확인됨. NFC
        # title 보존을 우선해 -map_metadata -1 을 제거. major_brand 잔재는
        # 무해한 메타 노이즈로 받아들이고, 후속 항목에서 선별 제거를 검토.
        if ext == "mp3":
            ydl_opts["postprocessor_args"]["ffmpeg"] = [
                "-id3v2_version", "3",
                "-write_id3v1", "1",
            ]

        # webp 썸네일을 jpg 로 변환하는 후처리기를 EmbedThumbnail 앞에 삽입
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

        # ── 본 다운로드 실행 ─────────────────────────────
        # ydl.download(url) 대신 process_ie_result(probed, download=True).
        # 후자는 yt-dlp 가 정보를 다시 받아오지 않고 우리가 NFC 화한
        # probed 를 그대로 후처리 체인에 넘긴다.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.process_ie_result(probed, download=True)

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
