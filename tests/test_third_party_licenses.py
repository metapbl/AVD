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


def test_qt_source_links_match_pinned_version():
    # PySide6 핀을 올리면 소스 안내도 함께 고치게 한다 (D064).
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    version = next(
        line.split("==")[1].strip()
        for line in requirements.splitlines()
        if line.startswith("PySide6==")
    )
    major_minor = ".".join(version.split(".")[:2])
    text = (ROOT / "THIRD_PARTY_LICENSES").read_text(encoding="utf-8")
    assert f"/QtForPython/pyside6/PySide6-{version}-src/" in text
    assert f"/official_releases/qt/{major_minor}/{version}/single/" in text
    assert f"/archive/qt/{major_minor}/{version}/single/" in text


def test_runtime_and_bootloader_have_sections():
    assert {"python", "pyinstaller"} <= section_titles()
