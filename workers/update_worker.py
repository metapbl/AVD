# workers/update_worker.py
# yt-dlp 업데이트를 백그라운드 스레드에서 실행하는 워커
#
# 배경: 기존에는 MainWindow 가 pip install 을 GUI 스레드에서 동기 실행해
# 그 10 초 동안 창 전체가 얼어붙어 "강제 종료된 것처럼" 보였다. 이 워커로
# 분리해 GUI 는 살아 있게 하고, 진행 로그를 실시간 시그널로 흘려 보내
# 모달 다이얼로그가 상황을 보여 준다.

import subprocess
import sys

from PySide6.QtCore import QThread, Signal


class UpdateWorker(QThread):
    """
    pip 으로 yt-dlp 를 업그레이드하는 워커 스레드.

    시그널:
        progress_text(str) : pip 출력 한 줄씩. 상태 라벨 갱신용.
        done(bool, str)    : 완료. (성공여부, 요약 메시지)
            ⚠ QThread 내장 finished 와 겹치지 않게 done 으로 둔다.
    """

    progress_text = Signal(str)
    done          = Signal(bool, str)

    def run(self):
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                # Windows 에서 콘솔 창이 튀지 않도록.
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW")
                    else 0
                ),
            )

            last_line = ""
            if proc.stdout is not None:
                for raw in proc.stdout:
                    line = raw.rstrip()
                    if not line:
                        continue
                    last_line = line
                    self.progress_text.emit(line)

            code = proc.wait()
            if code == 0:
                self.done.emit(True, "yt-dlp가 최신 버전으로 업데이트됐습니다.")
            else:
                self.done.emit(
                    False,
                    f"업데이트에 실패했습니다 (코드 {code}).\n"
                    f"마지막 출력: {last_line}\n\n"
                    "수동으로 pip install --upgrade yt-dlp 를 실행해 주세요.",
                )
        except Exception as e:
            self.done.emit(
                False,
                f"업데이트 중 오류가 발생했습니다: {e}\n\n"
                "수동으로 pip install --upgrade yt-dlp 를 실행해 주세요.",
            )
