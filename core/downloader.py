import importlib
import inspect
import itertools
import os
import subprocess
import tempfile
import unicodedata
from pathlib import Path

import yt_dlp
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.postprocessor.ffmpeg import (
    FFmpegMergerPP,
    FFmpegPostProcessor,
    FFmpegPostProcessorError,
)
from yt_dlp.utils import Popen, encodeArgument, shell_quote, variadic

from utils.file_utils import ensure_dir

# MP3 후처리 비트레이트 (kbps). 단일 출처 — 이 값을 바꾸면
# info_fetcher 의 MP3 항목 라벨도 자동으로 따라온다.
# FFmpegExtractAudio 의 preferredquality 는 문자열이라 str() 로 감싼다.
MP3_BITRATE_KBPS = 192


class _NFCNormalizePP(PostProcessor):
    """후처리 체인의 pre_process 단계 (extract_info 직후, 다운로드/파일명
    결정/메타 임베드 모두에 앞섬) 에 끼워, info dict 의 문자열 값을
    재귀적으로 NFC 로 정규화한다. SoundCloud · macOS 등에서 NFD 로 들어온
    한글 메타가 ID3 TIT2 / m4a ©nam atom / 파일명에 NFD 로 박히는 것을 차단.

    동시에 FFmpegMetadataPP 의 webpage_url → comment 자동 매핑도 차단 —
    yt-dlp 소스의 _get_metadata_opts 가 add(('purl','comment'),'webpage_url')
    로 comment 에 영상 URL 을 박는데, 그 뒤에 도는 meta_<key> regex 루프가
    우리 meta_comment 값을 최종으로 덮어쓰는 메커니즘을 이용한다.

    meta_comment 를 "빈 문자열" 로 둔다(2026-07-10 개정). 빈 값이면 ffmpeg 가
    comment 프레임 자체를 만들지 않아(실측 확인) URL 도, 깨질 텍스트도 남지
    않는다. URL 보관은 별도로 박히는 purl 태그가 담당하므로 정보 손실 없음.

    ⚠ 과거엔 여기 description 을 넣었으나(REFERENCE T8), FFmpeg 가 comment 를
      비표준 TXXX:comment 프레임에 UTF-16 으로 쓰는 탓에 한글 Windows 의
      일부 플레이어·탐색기 '주석' 열에서 "?뱀떊怨쇱쓽…" mojibake 로 보였다.
      제목/아티스트(표준 TIT2/TPE1)는 멀쩡한데 주석만 깨진 원인이 이것.
      YouTube description 은 링크·해시태그 범벅이라 태그로서 가치도 낮아 뺀다.
    """

    def run(self, info):
        self._normalize_in_place(info)
        # description 이 아니라 빈 문자열. 위 docstring 의 근거 참고.
        info["meta_comment"] = ""
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


def _merge_progress(line: str, duration: float | None) -> tuple[float | None, float] | None:
    """ffmpeg `-progress` 한 줄 → (퍼센트 또는 None, 처리한 초). out_time_us 줄이 아니면 None."""
    key, _, value = line.strip().partition("=")
    if key == "progress" and value == "end":
        # 마지막 out_time 은 길이보다 조금 짧아 100 에 닿지 않는다 — 끝났으면 100
        return (100.0, float(duration)) if duration else None
    if key != "out_time_us":
        return None
    try:
        secs = max(int(value), 0) / 1e6
    except ValueError:  # 첫 블록은 "N/A"
        return None
    pct = min(secs / duration * 100, 100.0) if duration else None
    return pct, secs


class _ProgressMergerPP(FFmpegMergerPP):
    """yt-dlp 병합기에 진행률을 더한다 (D052).

    부모 real_run_ffmpeg 는 ffmpeg 출력을 끝날 때 한꺼번에 읽어 진행률을 낼 수
    없으므로, 같은 명령에 `-progress pipe:1` 을 더해 줄 단위로 읽고 후처리 hook
    {"status": "processing", "merge_percent", "merge_secs"} 로 알린다. hook 이
    던지는 취소 예외는 ffmpeg 를 끝내고 다시 던진다.

    run 은 오버라이드하지 않는다 — PostProcessorMetaClass 가 하위 클래스의 run 을
    다시 감싸 started/finished hook 이 두 번 나가고, 그러면 슬롯이 두 번 풀린다.
    """

    _info: dict | None = None  # started hook 이 채운다 (run 앞에서 항상 불림)
    _proc: Popen | None = None

    @classmethod
    def pp_key(cls):
        # 클래스 이름에서 만들면 "_ProgressMerger" — hook 의 postprocessor 이름과
        # postprocessor_args 키가 바뀌어 워커가 병합을 못 알아본다
        return FFmpegMergerPP.pp_key()

    def _hook_progress(self, status, info_dict):
        if status.get("status") == "started":
            self._info = info_dict
        super()._hook_progress(status, info_dict)

    def real_run_ffmpeg(self, input_path_opts, output_path_opts, *, expected_retcodes=(0,)):
        # 명령 조립은 yt-dlp 2026.10.26 FFmpegPostProcessor.real_run_ffmpeg 와 같다
        self.check_version()

        oldest_mtime = min(
            os.stat(path).st_mtime for path, _ in input_path_opts if path)

        cmd = [self.executable, encodeArgument("-y"), "-progress", "pipe:1", "-nostats"]
        if self.basename == "ffmpeg":
            cmd += [encodeArgument("-loglevel"), encodeArgument("repeat+info")]

        def make_args(file, args, name, number):
            keys = [f"_{name}{number}", f"_{name}"]
            if name == "o":
                args += ["-movflags", "+faststart"]
                if number == 1:
                    keys.append("")
            args += self._configuration_args(self.basename, keys)
            if name == "i":
                args.append("-i")
            return (
                [encodeArgument(arg) for arg in args]
                + [self._ffmpeg_filename_argument(file)])

        for arg_type, path_opts in (("i", input_path_opts), ("o", output_path_opts)):
            cmd += itertools.chain.from_iterable(
                make_args(path, list(opts), arg_type, i + 1)
                for i, (path, opts) in enumerate(path_opts) if path)

        self.write_debug(f"ffmpeg command line: {shell_quote(cmd)}")
        duration = (self._info or {}).get("duration")
        # stderr 는 파일로 — 파이프로 두면 stdout 을 읽는 동안 가득 차 ffmpeg 가 멈춘다
        with tempfile.TemporaryFile() as err:
            self._proc = proc = Popen(
                cmd, text=True, stdout=subprocess.PIPE, stderr=err, stdin=subprocess.DEVNULL)
            with proc:
                try:
                    for line in proc.stdout:
                        got = _merge_progress(line, duration)
                        if got:
                            self._hook_progress(
                                {"status": "processing", "merge_percent": got[0], "merge_secs": got[1]},
                                self._info)
                except BaseException:  # 취소 예외 포함 — 반쯤 쓴 출력 파일을 남기지 않는다
                    proc.kill(timeout=None)
                    for out_path, _ in output_path_opts:
                        if out_path and os.path.exists(out_path):
                            os.remove(out_path)
                    raise
            err.seek(0)
            stderr = err.read().decode("utf-8", "replace")

        if proc.returncode not in variadic(expected_retcodes):
            self.write_debug(stderr)
            raise FFmpegPostProcessorError(stderr.strip().splitlines()[-1])
        for out_path, _ in output_path_opts:
            if out_path:
                self.try_utime(out_path, oldest_mtime, oldest_mtime)
        return stderr


def _install_progress_merger() -> bool:
    """yt-dlp 가 병합할 때 만드는 FFmpegMergerPP 를 _ProgressMergerPP 로 바꾼다.

    자동 업데이트로 부모 구조가 바뀌었으면 바꾸지 않는다 — 병합은 원래대로,
    진행률만 없다 (D052).
    """
    ydl_module = importlib.import_module("yt_dlp.YoutubeDL")  # yt_dlp.YoutubeDL 은 클래스가 가린다
    params = list(inspect.signature(FFmpegPostProcessor.real_run_ffmpeg).parameters)
    if (
        params != ["self", "input_path_opts", "output_path_opts", "expected_retcodes"]
        or getattr(ydl_module, "FFmpegMergerPP", None) is not FFmpegMergerPP
    ):
        return False
    ydl_module.FFmpegMergerPP = _ProgressMergerPP
    return True


_install_progress_merger()


# YouTube JS 챌린지 옵션. 정보 추출·플레이리스트 확인·다운로드가 함께 쓴다 —
# 어긋나면 목록에 보인 포맷을 다운로드 때 못 찾는다 (D055). 옵션을 빼면 yt-dlp 는
# 자동 탐지가 아니라 Deno 만 켜므로, 고정하지 않으려면 모두 켜 둔다 (D003).
JS_CHALLENGE_OPTS = {
    "js_runtimes"      : {"node": {}, "deno": {}, "bun": {}},
    "remote_components": ["ejs:github"],
}

_BASE_OPTS = {
    "quiet"                : True,
    "no_warnings"          : True,
    **JS_CHALLENGE_OPTS,
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
                # MP3 비트레이트는 모듈 상수에서 일괄 관리. info_fetcher 의
                # 표시 라벨도 같은 상수를 참조하므로 한 곳만 바꾸면 양쪽이 따라온다.
                # FFmpegExtractAudio 의 preferredquality 는 문자열을 요구.
                "preferredquality": str(MP3_BITRATE_KBPS),
            })
        postprocessors.append({
            "key": "FFmpegMetadata",
            "add_metadata": True,
            # m4a 에 챕터를 넣으면 텍스트 트랙이 생겨 ffmpeg 썸네일 임베드가 실패한다
            # ("Tag text incompatible", 2026-11-11 실측). m4a 는 챕터를 넣지 않는다.
            "add_chapters": ext != "m4a",
        })
        postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

        ydl_opts = {
            **_BASE_OPTS,
            "format"             : format_id,
            "outtmpl"            : str(Path(save_dir) / "%(title)s.%(ext)s"),
            "windowsfilenames"   : True,    # yt-dlp 자체 sanitize
            "trim_file_name"     : 180,    # 임시 폴더 이름만큼 경로 여유 (D056)
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
            # ID3v2.3(UTF-16) 로 태그를 쓴다. 한글 제목·아티스트가 온전히 담긴다.
            # ⚠ ID3v1(-write_id3v1 1) 은 절대 켜지 않는다: ID3v1 규격은 인코딩
            #   개념이 없어 FFmpeg 가 UTF-8 바이트를 그대로 밀어 넣는데, 한글
            #   Windows 의 탐색기·플레이어가 이를 CP949 로 디코딩해 제목이
            #   "?뱀떊怨쇱쓽…" 식 mojibake 로 깨졌다(2026-07-10 실기 확인).
            #   v1 을 빼면 최신 플레이어는 v2.3 을 읽어 한글이 정상 표시된다.
            ydl_opts["postprocessor_args"]["ffmpeg"] = [
                "-id3v2_version", "3",
            ]
            ydl_opts["postprocessor_args"]["extractaudio"] = [
                "-metadata", "major_brand=",
                "-metadata", "minor_version=",
                "-metadata", "compatible_brands=",
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
