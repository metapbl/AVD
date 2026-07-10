"""
gaindb/decode.py

MP3 → PCM 디코딩 모듈.

원본 디코더(mpglibDBL)를 옮기지 않고, 외부 ffmpeg/ffprobe 를 subprocess 로
호출해 PCM 샘플을 얻는다(프로젝트 방침: 디코더 직접 구현 안 함).

ReplayGain 분석기(analysis.py)에 입력을 공급하는 단계.
출력 샘플 스케일은 원본 ReplayGain 사양(16비트 정수, ±32768)에 맞춘다.
ffmpeg 의 f32le 는 ±1.0 정규화 출력이므로 32768 을 곱해 스케일을 일치시킨다.

모노 처리(원본 mp3gain 정합): 원본은 모노 신호를 원진폭 그대로 한 채널로
분석하고, 라우드니스 계산에서 좌우를 동일 신호로 취급한다((lsum+rsum)*0.5).
ffmpeg 의 -ac 2 up-mix 는 모노를 스테레오로 펼치며 각 채널을 1/√2 로 감쇠해
평균제곱을 절반(=3dB 낮게)으로 만들어 원본과 어긋난다. 따라서 모노 파일은
-ac 1 로 원진폭 그대로 디코딩한 뒤 코드에서 left=right 로 복제한다(감쇠 없음).
스테레오/조인트/듀얼(2채널)은 기존대로 -ac 2 로 그대로 받는다.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

# ReplayGain 사양에서 지원하는 샘플레이트(Hz). 이 목록 밖이면 분석 불가.
SUPPORTED_SAMPLE_RATES = frozenset(
    (96000, 88200, 64000, 48000, 44100, 32000,
     24000, 22050, 16000, 12000, 11025, 8000)
)

# f32le(±1.0) → 원본 사양의 16비트 정수 스케일(±32768)로 맞추는 계수.
_PCM_SCALE = 32768.0


class DecodeError(RuntimeError):
    """ffmpeg/ffprobe 호출 실패 또는 디코딩 불가 상황."""


def _probe_stream_info(path: Path) -> tuple[int, int]:
    """ffprobe 로 첫 오디오 스트림의 (샘플레이트 Hz, 채널 수)를 조회한다."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels",
        "-of", "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, check=True,
        )
    except FileNotFoundError as exc:
        raise DecodeError(
            "ffprobe not found. Make sure ffmpeg (including ffprobe) "
            "is installed and on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", "replace").strip()
        raise DecodeError(f"ffprobe failed: {stderr}") from exc

    try:
        info = json.loads(proc.stdout.decode("utf-8", "replace"))
        stream = info["streams"][0]
        rate = int(stream["sample_rate"])
        channels = int(stream["channels"])
    except (ValueError, KeyError, IndexError) as exc:
        raise DecodeError(
            f"Could not read stream info from ffprobe output: {path}"
        ) from exc

    return rate, channels


def decode_pcm(path: str | Path) -> tuple[np.ndarray, np.ndarray, int]:
    """
    MP3 파일을 디코딩해 (left, right, sample_rate) 를 반환한다.

    - left, right: np.ndarray(dtype=float64), 원본 사양 스케일(±32768).
      모노 원본은 -ac 1 로 원진폭 그대로 디코딩해 좌우를 동일 신호로 복제한다
      (ffmpeg -ac 2 up-mix 의 1/√2 감쇠를 피해 원본 mp3gain 과 정합).
      스테레오(2채널)는 -ac 2 로 그대로 받는다.
    - sample_rate: int(Hz). ReplayGain 지원 목록에 없으면 DecodeError.

    실패 시 DecodeError 를 던진다.
    """
    path = Path(path)
    if not path.is_file():
        raise DecodeError(f"File not found: {path}")

    sample_rate, channels = _probe_stream_info(path)
    if sample_rate not in SUPPORTED_SAMPLE_RATES:
        raise DecodeError(
            f"Unsupported sample rate: {sample_rate} Hz "
            f"(supported: {sorted(SUPPORTED_SAMPLE_RATES, reverse=True)})"
        )

    # 모노는 원진폭 유지 위해 1채널로, 그 외는 2채널로 디코딩.
    # (원본 샘플레이트 유지: -ar 강제 금지. 32비트 float LE.)
    out_channels = 1 if channels == 1 else 2
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-i", str(path),
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-ac", str(out_channels),
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, check=True,
        )
    except FileNotFoundError as exc:
        raise DecodeError(
            "ffmpeg not found. Make sure it is installed and on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", "replace").strip()
        raise DecodeError(f"ffmpeg decoding failed: {stderr}") from exc

    raw = proc.stdout
    if len(raw) == 0:
        raise DecodeError(f"Decoding produced no output: {path}")

    samples = np.frombuffer(raw, dtype="<f4")

    if out_channels == 1:
        # 모노: 원진폭 그대로 좌우 복제. float64 승격 + 사양 스케일.
        mono = samples.astype(np.float64) * _PCM_SCALE
        return mono, mono.copy(), sample_rate

    # 스테레오: 2채널 인터리브이므로 짝수 길이여야 한다.
    if samples.size % 2 != 0:
        # 비정상 종료 등으로 마지막 샘플이 잘린 경우 한 샘플 버린다.
        samples = samples[: samples.size - 1]

    frames = samples.reshape(-1, 2)
    # float64 로 승격(필터 누산 정밀도) + 원본 사양 스케일로 변환.
    left = frames[:, 0].astype(np.float64) * _PCM_SCALE
    right = frames[:, 1].astype(np.float64) * _PCM_SCALE

    return left, right, sample_rate
