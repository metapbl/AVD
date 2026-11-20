"""번역 파일 검사 (F17, D083) — 감싸지 않은 문구, .ts·.qm 최신, 자리표시자, 완결성."""
import ast
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools import update_translations as ut

HANGUL = re.compile("[가-힣]")
PLACEHOLDER = re.compile(r"\{[^{}]*\}|%\d+")
QSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)  # 스타일시트 주석의 한글은 화면에 안 보인다
TRANSLATE_CALLS = {"tr", "translate", "QT_TRANSLATE_NOOP"}
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}
# 언어 이름은 번역하지 않는다 (D084)
NOT_UI = {"utils/i18n.py"}
# 아직 tr() 로 감싸지 않은 파일 — 작업 3~5 에서 줄여 비운다
PENDING = {
    "main.py",
    "ui/about_dialog.py",
    "ui/add_link_dialog.py",
    "ui/confirm_remove_dialog.py",
    "ui/error_detail_dialog.py",
    "ui/format_select_dialog.py",
    "ui/playlist_select_dialog.py",
    "ui/preferences_dialog.py",
    "ui/update_progress_dialog.py",
}
# 번역을 다 채운 언어 — 작업 7(en)·8(나머지) 에서 늘린다
COMPLETE = set()


def _rel(path: Path) -> str:
    return path.relative_to(ut.ROOT).as_posix()


def _untranslated_hangul(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant):
            skip.add(id(body[0].value))  # docstring
        if isinstance(node, (ast.Raise, ast.Assert)):
            skip.update(id(n) for n in ast.walk(node))  # 예외 원문은 "자세히" 원문이라 번역하지 않는다 (F17)
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in TRANSLATE_CALLS or name == "print" \
                    or (name in LOG_METHODS and isinstance(node.func, ast.Attribute)):
                skip.update(id(n) for n in ast.walk(node))
    return [f"{_rel(path)}:{n.lineno} {n.value!r}" for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and HANGUL.search(QSS_COMMENT.sub("", n.value)) and id(n) not in skip]


def test_no_unwrapped_hangul_in_ui_code():
    found = []
    for path in ut.source_files():
        rel = _rel(path)
        if rel not in NOT_UI and rel not in PENDING:
            found += _untranslated_hangul(path)
    assert found == []


def test_pending_files_still_need_wrapping():
    # 다 감싼 파일이 목록에 남아 검사를 피하지 않게 한다
    done = [rel for rel in PENDING if not _untranslated_hangul(ut.ROOT / rel)]
    assert done == []


def test_ts_and_qm_are_current(tmp_path):
    for f in ut.I18N_DIR.glob("avd_*.ts"):
        shutil.copy(f, tmp_path)
    ut.update(tmp_path)
    for lang in ut.TARGETS:
        for ext in (".ts", ".qm"):
            name = f"avd_{lang}{ext}"
            assert (tmp_path / name).read_bytes() == (ut.I18N_DIR / name).read_bytes(), \
                f"{name} 가 코드와 다릅니다 — python tools/update_translations.py"


def _messages(lang: str):
    root = ET.parse(ut.I18N_DIR / f"avd_{lang}.ts").getroot()
    return root.iter("message")


@pytest.mark.parametrize("lang", ut.TARGETS)
def test_placeholders_match(lang):
    wrong = []
    for m in _messages(lang):
        source, translation = m.findtext("source", ""), m.findtext("translation", "")
        if translation and sorted(PLACEHOLDER.findall(source)) != sorted(PLACEHOLDER.findall(translation)):
            wrong.append(f"{source!r} → {translation!r}")
    assert wrong == []


@pytest.mark.parametrize("lang", sorted(COMPLETE))
def test_translation_complete(lang):
    missing = [m.findtext("source") for m in _messages(lang)
               if m.find("translation").get("type") == "unfinished" or not m.findtext("translation")]
    assert missing == []
