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
        progress_hook,           # 진행률 콜백 함수
        postprocess_hook,        # 후처리(병합 등) 콜백 함수
    ):
        """
        실제 다운로드 실행
        progress_hook(d)      : 진행률 딕셔너리 전달
        postprocess_hook(d)   : 후처리 상태 딕셔너리 전달
        """
        self._cancelled = False

        # 저장 폴더 없으면 생성
        ensure_dir(save_dir)

        # 오디오 전용 여부 판단
        is_audio = ext in ("mp3", "m4a", "wav", "aac")

        # yt-dlp 옵션 구성
        ydl_opts = {
            # 화질/형식 선택
            "format"             : format_id,

            # 저장 경로 템플릿
            "outtmpl"            : str(
                                     Path(save_dir) /
                                     "%(title)s.%(ext)s"
                                   ),

            # ffmpeg 관련 설정
            "merge_output_format": ext if not is_audio else None,

            # 터미널 출력 억제
            "quiet"              : True,
            "no_warnings"        : True,

            # JS 챌린지 해결 설정
            "js_runtimes"        : {"node": {}},
            "remote_components"  : ["ejs:github"],

            # 취소 체크 함수가 포함된 진행률 콜백
            "progress_hooks"     : [self._wrap_hook(progress_hook)],

            # 후처리 콜백 (영상+음성 병합 완료 시점 감지)
            "postprocessor_hooks": [postprocess_hook],
        }

        # 오디오 전용이면 MP3 변환 후처리기 추가
        if is_audio:
            ydl_opts["postprocessors"] = [{
                "key"             : "FFmpegExtractAudio",
                "preferredcodec"  : ext,
                "preferredquality": "192",  # 192kbps
            }]

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