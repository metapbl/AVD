# 루트 THIRD_PARTY_LICENSES 가 requirements.txt 의 모든 패키지와 exe 에 함께
# 실리는 Python·PyInstaller 를 다루는지 고정 (D011). 절 제목은 줄표 줄 다음 줄.
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).parent.parent


def section_titles() -> set[str]:
    lines = (ROOT / "THIRD_PARTY_LICENSES").read_text(encoding="utf-8").splitlines()
    return {
        name.strip().lower()
        for prev, line in pairwise(lines)
        if prev.startswith("-----")
        for name in line.split(",")
    }


def test_every_requirement_has_a_section():
    names = {
        line.split("==")[0].strip().lower()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert names - section_titles() == set()


def test_runtime_and_bootloader_have_sections():
    assert {"python", "pyinstaller"} <= section_titles()
