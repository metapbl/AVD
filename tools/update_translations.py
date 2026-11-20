# tools/update_translations.py
# 코드에서 화면 문구를 모아 i18n/avd_{언어}.ts 를 갱신하고 .qm 을 만든다 (F17, D083).
# 실행: venv\Scripts\python tools/update_translations.py

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N_DIR = ROOT / "i18n"
SOURCE_DIRS = ["controllers", "core", "models", "ui", "utils", "workers"]
# 한국어는 원문이라 번역 파일이 없다
TARGETS = ["en", "zh_CN", "ja", "es", "ru"]


def source_files() -> list[Path]:
    files = [ROOT / "main.py"]
    for d in SOURCE_DIRS:
        files += sorted((ROOT / d).rglob("*.py"))
    return files


def _tool(name: str) -> str:
    # venv 의 Scripts\(Windows)·bin/(macOS) 에 python 과 함께 있다
    return str(Path(sys.executable).parent / name)


def update(i18n_dir: Path = I18N_DIR) -> None:
    i18n_dir.mkdir(exist_ok=True)
    files = [str(f.relative_to(ROOT)) for f in source_files()]
    for lang in TARGETS:
        ts = i18n_dir / f"avd_{lang}.ts"
        # 줄 번호를 남기지 않아 코드만 움직여도 .ts 가 바뀌지 않게 한다
        subprocess.run([_tool("pyside6-lupdate"), *files, "-ts", str(ts), "-no-obsolete",
                        "-locations", "none", "-source-language", "ko_KR", "-target-language", lang],
                       cwd=ROOT, check=True, capture_output=True)
        subprocess.run([_tool("pyside6-lrelease"), str(ts), "-qm", str(ts.with_suffix(".qm"))],
                       cwd=ROOT, check=True, capture_output=True)


if __name__ == "__main__":
    update()
    print(f"갱신: {I18N_DIR}")
