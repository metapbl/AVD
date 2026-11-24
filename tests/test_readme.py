"""README 6개 언어 (D085, metarche readme.md §6) — 파일·구조·링크·앵커."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILES = ["README.md", "README.ko.md", "README.zh-CN.md", "README.ja.md", "README.es.md", "README.ru.md"]
# 번역본 맨 위 안내 문장 (readme.md §5)
NOTICE = {
    "README.ko.md": "이 문서는 영어판을 AI로 번역한 것입니다. 내용이 다르면 영어판을 따릅니다.",
    "README.zh-CN.md": "本文档由 AI 从英文版翻译而来。如有出入，以英文版为准。",
    "README.ja.md": "この文書は英語版を AI で翻訳したものです。内容が異なる場合は英語版に従ってください。",
    "README.es.md": "Este documento es una traducción automática con IA de la versión en inglés. "
                    "Si hay diferencias, prevalece la versión en inglés.",
    "README.ru.md": "Этот документ переведён с английской версии с помощью ИИ. "
                    "При расхождениях ориентируйтесь на английскую версию.",
}
LINK = re.compile(r'(?:href="|\]\()([^")\s]+)')


def _text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def _slug(heading: str) -> str:
    # GitHub 의 제목 앵커: 소문자, 글자·숫자·공백·하이픈만 남기고 공백은 하이픈
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(name) -> set[str]:
    return {_slug(h) for h in re.findall(r"^#{1,6} (.+)$", _text(name), re.MULTILINE)}


def test_every_language_file_is_linked_and_exists():
    for name in FILES:
        text = _text(name)
        for other in FILES:
            assert f'<a href="{other}">' in text, (name, other)


@pytest.mark.parametrize("name", FILES[1:])
def test_translation_matches_english_shape(name):
    en, tr = _text("README.md"), _text(name)
    assert tr.count("\n## ") == en.count("\n## ")
    assert tr.count("\n### ") == en.count("\n### ")
    assert tr.count("img.shields.io") == en.count("img.shields.io")
    assert NOTICE[name] in tr.split("# AVD")[0]


@pytest.mark.parametrize("name", FILES)
def test_relative_links_and_anchors_resolve(name):
    broken = []
    for target in LINK.findall(_text(name)):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _, anchor = target.partition("#")
        file = path or name
        exists = (ROOT / file).exists()
        if not exists or (anchor and file.endswith(".md") and anchor not in anchors(file)):
            broken.append(target)
    assert broken == []


@pytest.mark.parametrize("name", FILES)
def test_no_internal_paths_or_addresses(name):
    text = _text(name)
    assert not re.search(r"[A-Za-z]:\\Users|/Users/|\b\d{1,3}(\.\d{1,3}){3}\b|@gmail\.com", text)


@pytest.mark.parametrize("lang", ["ko", "en", "zh_CN", "ja", "es", "ru"])
def test_app_cookie_help_link_opens_that_language_readme_section(lang):
    from PySide6.QtWidgets import QApplication

    from ui.about_dialog import REPO_URL
    from ui.preferences_dialog import cookie_help_url
    from utils.i18n import apply_language

    apply_language(QApplication.instance() or QApplication([]), lang)
    file, _, anchor = cookie_help_url().removeprefix(REPO_URL + "/blob/main/").partition("#")
    assert file == {"ko": "README.ko.md", "en": "README.md"}.get(lang, f"README.{lang.replace('_', '-')}.md")
    assert anchor in anchors(file)


SHOTS = [f"docs/images/{screen}-{theme}-v2.png" for screen in ("main", "format") for theme in ("light", "dark")]


@pytest.mark.parametrize("name", FILES)
def test_screenshots_are_shared_and_described(name):
    # readme.md §7 — 모든 언어가 같은 이미지, 이미지마다 alt 글, 라이트가 왼쪽
    imgs = re.findall(r'<img alt="([^"]+)" src="(docs/images/[^"]+)"', _text(name))
    assert [src for _, src in imgs] == SHOTS
    assert all(alt.strip() for alt, _ in imgs)


@pytest.mark.parametrize("path", SHOTS)
def test_screenshot_files_exist_and_are_small(path):
    file = ROOT / path
    assert file.is_file() and file.stat().st_size <= 2 * 1024 * 1024
