# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""
gaindb/decode.py

MP3 → PCM 디코딩 모듈.

원본 디코더를 이식하지 않고, 외부 ffmpeg/ffprobe 를 subprocess 로 호출해 PCM
샘플을 얻는다(프로젝트 방침: 디코더 직접 구현 안 함).

ReplayGain 분석기(analysis.py)에 입력을 공급하는 단계.
출력 샘플 스케일은 ReplayGain 사양(16비트 정수, ±32768)에 맞춘다.
ffmpeg 의 f32le 는 ±1.0 정규화 출력이므로 32768 을 곱해 스케일을 일치시킨다.

모노 처리(mp3gain 결과 정합): mp3gain 은 모노 신호를 원진폭 그대로 한 채널로
분석하고, 라우드니스 계산에서 좌우를 동일 신호로 취급한다((lsum+rsum)*0.5).
ffmpeg 의 -ac 2 up-mix 는 모노를 스테레오로 펼치며 각 채널을 1/√2 로 감쇠해
평균제곱을 절반(=3dB 낮게)으로 만들어 mp3gain 결과와 어긋난다. 따라서 모노
파일은 -ac 1 로 원진폭 그대로 디코딩한 뒤 코드에서 left=right 로 복제한다(감쇠
없음). 스테레오/조인트/듀얼(2채널)은 기존대로 -ac 2 로 그대로 받는다.

취소·진행률(GUI 대응):
  긴 곡(수 시간)을 통째로 받으면 취소가 파일 경계에서만 반영돼 UI 가 굳은
  것처럼 보인다. 그래서 ffmpeg 를 Popen 으로 띄우고 stdout 을 청크로 읽으며,
  청크마다 취소 콜백(should_cancel)과 진행률 콜백(on_progress)을 호출한다.
  취소가 서면 진행 중 ffmpeg 프로세스를 즉시 kill 하고 DecodeCancelled 를
  던진다(취소는 실패가 아니라 정상 흐름이라 별도 예외로 구분). 진행률은
  ffprobe 로 얻은 duration 으로 예측한 총 PCM 바이트 대비 누적 바이트 비율
  이며, VBR·컨테이너 오차가 있어 근사값이다(0~1 로 클램프).

메모리(초장시간 곡):
  decode_pcm 은 곡 전체 PCM 을 배열로 반환하므로 수 시간짜리 곡에서 수십 GB
  메모리를 쓴다(짧은 곡·테스트용). analyze_file 등 실사용 경로는 청크를 흘려
  보내는 decode_pcm_streaming 을 써서 곡 전체를 메모리에 올리지 않는다.

파일 핸들:
  Popen 은 subprocess.run 과 달리 stdout/stderr 파이프를 자동으로 닫지 않아
  ResourceWarning 이 난다. 그래서 두 디코드 함수 모두 `with proc:` 컨텍스트로
  감싸 블록을 벗어날 때 파이프가 확실히 닫히게 한다.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

import numpy as np

# ReplayGain 사양에서 지원하는 샘플레이트(Hz). 이 목록 밖이면 분석 불가.
SUPPORTED_SAMPLE_RATES = frozenset(
    (96000, 88200, 64000, 48000, 44100, 32000,
     24000, 22050, 16000, 12000, 11025, 8000)
)

# f32le(±1.0) → ReplayGain 사양의 16비트 정수 스케일(±32768)로 맞추는 계수.
_PCM_SCALE = 32768.0

# stdout 청크 크기(바이트). 취소 응답성과 오버헤드의 균형점(512KB).
_CHUNK_SIZE = 512 * 1024

# f32le 한 샘플의 바이트 수(진행률 예측용).
_BYTES_PER_SAMPLE = 4


class DecodeError(RuntimeError):
    """ffmpeg/ffprobe 호출 실패 또는 디코딩 불가 상황."""


class DecodeCancelled(DecodeError):
    """디코딩 중 should_cancel 이 True 를 반환해 취소된 경우.

    DecodeError 의 하위라 기존에 DecodeError 만 잡던 코드도 안전하게 걸러낸다.
    호출자(워커)는 이 예외를 '실패'가 아니라 '정상 취소'로 다뤄야 한다.
    """


def _probe_stream_info(path: Path) -> tuple[int, int, float]:
    """ffprobe 로 첫 오디오 스트림의 (샘플레이트 Hz, 채널 수, duration 초)를 조회.

    duration 은 진행률 예측용 근사값이다(스트림 우선, 없으면 format 에서).
    구하지 못하면 0.0 을 돌려준다(진행률은 무한 진행처럼 처리됨).
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels,duration:format=duration",
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

    # duration: 스트림 값 우선, 없으면 format 값, 둘 다 없으면 0.0.
    duration = 0.0
    for src in (stream.get("duration"), info.get("format", {}).get("duration")):
        try:
            if src is not None:
                duration = float(src)
                if duration > 0.0:
                    break
        except (ValueError, TypeError):
            continue

    return rate, channels, duration


def _spawn_ffmpeg(path: Path, out_channels: int) -> subprocess.Popen:
    """f32le PCM 을 stdout 으로 뱉는 ffmpeg 프로세스를 띄운다(공통 헬퍼).

    -ar 을 강제하지 않아 원본 샘플레이트를 유지한다. 32비트 float LE 출력.
    ffmpeg 부재 시 DecodeError 로 변환한다.
    """
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
        return subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise DecodeError(
            "ffmpeg not found. Make sure it is installed and on PATH."
        ) from exc


def _resolve_channels(path: Path) -> tuple[int, int, int, float]:
    """공통 전처리: 파일 존재·샘플레이트 검증 후 (sr, out_channels, ch, dur) 반환."""
    if not path.is_file():
        raise DecodeError(f"File not found: {path}")

    sample_rate, channels, duration = _probe_stream_info(path)
    if sample_rate not in SUPPORTED_SAMPLE_RATES:
        raise DecodeError(
            f"Unsupported sample rate: {sample_rate} Hz "
            f"(supported: {sorted(SUPPORTED_SAMPLE_RATES, reverse=True)})"
        )
    out_channels = 1 if channels == 1 else 2
    return sample_rate, out_channels, channels, duration


def decode_pcm(
    path: str | Path,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    """
    MP3 파일을 디코딩해 (left, right, sample_rate) 를 반환한다(곡 전체 배열).

    짧은 곡·테스트용이다. 초장시간 곡은 메모리를 크게 쓰므로 실사용 경로는
    decode_pcm_streaming 을 쓴다.

    - left, right: np.ndarray(dtype=float64), ReplayGain 사양 스케일(±32768).
      모노 원본은 -ac 1 로 원진폭 그대로 디코딩해 좌우를 동일 신호로 복제한다
      (ffmpeg -ac 2 up-mix 의 1/√2 감쇠를 피해 mp3gain 결과와 정합).
      스테레오(2채널)는 -ac 2 로 그대로 받는다.
    - sample_rate: int(Hz). ReplayGain 지원 목록에 없으면 DecodeError.

    should_cancel: 청크마다 호출되는 취소 콜백. True 면 ffmpeg 를 kill 하고
      DecodeCancelled 를 던진다(기본 None = 취소 없음).
    on_progress: 청크마다 호출되는 진행률 콜백(0.0~1.0). duration 기반 근사이며
      완료 시 1.0 으로 한 번 더 호출한다(기본 None = 콜백 없음).

    실패 시 DecodeError, 취소 시 DecodeCancelled 를 던진다.
    """
    path = Path(path)
    sample_rate, out_channels, _channels, duration = _resolve_channels(path)

    # 진행률 예측용 총 PCM 바이트(근사). duration 이 0 이면 예측 불가(0 유지).
    expected_bytes = int(
        duration * sample_rate * out_channels * _BYTES_PER_SAMPLE
    )

    proc = _spawn_ffmpeg(path, out_channels)
    chunks: list[bytes] = []
    read_bytes = 0

    # with proc: 블록을 벗어날 때 stdout/stderr 파이프를 자동으로 닫는다.
    with proc:
        try:
            assert proc.stdout is not None
            while True:
                # 취소 확인(청크 경계). 서면 즉시 kill 하고 정리 후 예외.
                if should_cancel is not None and should_cancel():
                    proc.kill()
                    raise DecodeCancelled(f"Decoding cancelled: {path}")

                chunk = proc.stdout.read(_CHUNK_SIZE)
                if not chunk:
                    break  # EOF: ffmpeg 가 stdout 을 닫음(정상 종료 흐름).
                chunks.append(chunk)
                read_bytes += len(chunk)

                if on_progress is not None and expected_bytes > 0:
                    frac = read_bytes / expected_bytes
                    on_progress(frac if frac < 1.0 else 1.0)

            proc.wait()
        finally:
            # 예외 경로(취소 포함)에서 프로세스가 남지 않도록 안전 정리.
            if proc.poll() is None:
                proc.kill()
                proc.wait()

        # ffmpeg 가 오류로 끝났으면(취소가 아닌 경우) 실패로 처리.
        # (with 블록 안이라 아래에서 stderr 를 읽어도 파이프가 아직 열려 있다.)
        if proc.returncode not in (0, None):
            stderr = b""
            if proc.stderr is not None:
                stderr = proc.stderr.read()
            raise DecodeError(
                f"ffmpeg decoding failed: "
                f"{stderr.decode('utf-8', 'replace').strip()}"
            )

    if on_progress is not None:
        on_progress(1.0)  # 완료 마무리(근사 오차 보정).

    raw = b"".join(chunks)
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
    # float64 로 승격(필터 누산 정밀도) + ReplayGain 사양 스케일로 변환.
    left = frames[:, 0].astype(np.float64) * _PCM_SCALE
    right = frames[:, 1].astype(np.float64) * _PCM_SCALE

    return left, right, sample_rate


def decode_pcm_streaming(
    path: str | Path,
    on_chunk: Callable[[np.ndarray, np.ndarray], None],
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[float], None] | None = None,
    chunk_seconds: float = 10.0,
) -> int:
    """MP3 를 디코딩하며 오디오를 청크로 흘려보낸다(곡 전체를 모으지 않음).

    통짜 반환하는 decode_pcm 과 달리, 약 chunk_seconds 분량이 쌓일 때마다
    on_chunk(left, right) 를 호출하고 그 배열을 버린다. 초장시간 곡(수 시간)도
    청크 하나 크기의 메모리로 처리하기 위한 경로다(analyze_file 이 이걸 쓴다).

    - left, right: np.ndarray(float64), ReplayGain 사양 스케일(±32768). 모노는
      원진폭(-ac 1)으로 디코딩 후 좌우 동일 신호로 복제한다(decode_pcm 과 동일).

    should_cancel: 청크마다 확인. True 면 ffmpeg 를 kill 하고 DecodeCancelled.
    on_progress: 청크마다 호출되는 진행률 콜백(0~1, duration 기반 근사).
    chunk_seconds: on_chunk 로 넘길 오디오 청크의 대략 길이(초).

    반환: 처리한 sample_rate(Hz). 실패 시 DecodeError, 취소 시 DecodeCancelled.
    """
    path = Path(path)
    sample_rate, out_channels, _channels, duration = _resolve_channels(path)

    expected_bytes = int(
        duration * sample_rate * out_channels * _BYTES_PER_SAMPLE
    )

    # 한 오디오 청크로 넘길 프레임 수(정수). frame = out_channels 샘플.
    frames_per_chunk = max(1, int(sample_rate * chunk_seconds))
    bytes_per_frame = out_channels * _BYTES_PER_SAMPLE
    chunk_target_bytes = frames_per_chunk * bytes_per_frame

    def _emit(buf: bytes) -> None:
        """프레임 정렬된 바이트 buf 를 left/right 로 나눠 on_chunk 에 넘긴다."""
        if not buf:
            return
        samples = np.frombuffer(buf, dtype="<f4")
        if out_channels == 1:
            mono = samples.astype(np.float64) * _PCM_SCALE
            on_chunk(mono, mono.copy())
        else:
            frames = samples.reshape(-1, 2)
            left = frames[:, 0].astype(np.float64) * _PCM_SCALE
            right = frames[:, 1].astype(np.float64) * _PCM_SCALE
            on_chunk(left, right)

    proc = _spawn_ffmpeg(path, out_channels)
    pending = b""          # 프레임 경계에 안 맞는 잔여 바이트 이월
    accum = bytearray()    # on_chunk 로 넘길 청크 누적
    read_bytes = 0

    with proc:
        try:
            assert proc.stdout is not None
            while True:
                if should_cancel is not None and should_cancel():
                    proc.kill()
                    raise DecodeCancelled(f"Decoding cancelled: {path}")

                raw = proc.stdout.read(_CHUNK_SIZE)
                if not raw:
                    break
                read_bytes += len(raw)

                if on_progress is not None and expected_bytes > 0:
                    frac = read_bytes / expected_bytes
                    on_progress(frac if frac < 1.0 else 1.0)

                data = pending + raw
                # 프레임 경계까지만 취하고 나머지는 이월.
                usable = len(data) - (len(data) % bytes_per_frame)
                pending = data[usable:]
                accum += data[:usable]

                # 청크 목표량을 넘으면 프레임 정렬 상태로 방출.
                while len(accum) >= chunk_target_bytes:
                    _emit(bytes(accum[:chunk_target_bytes]))
                    del accum[:chunk_target_bytes]

            proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

        if proc.returncode not in (0, None):
            stderr = b""
            if proc.stderr is not None:
                stderr = proc.stderr.read()
            raise DecodeError(
                f"ffmpeg decoding failed: "
                f"{stderr.decode('utf-8', 'replace').strip()}"
            )

    # 남은 누적분 방출(마지막 청크). pending(프레임 미달 바이트)은 버린다
    # (decode_pcm 이 홀수 잔여 샘플을 버리는 것과 동일 취지).
    if accum:
        _emit(bytes(accum))

    if on_progress is not None:
        on_progress(1.0)

    return sample_rate
