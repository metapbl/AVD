# utils/i18n.py
# 화면 언어 결정과 번역기 교체 (F17, D083, D084)

from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QTranslator

# 언어 코드 → 그 언어로 쓴 이름 (환경설정 콤보에 그대로 보인다, 번역하지 않음)
LANGUAGES = {
    "en": "English",
    "ko": "한국어",
    "zh_CN": "简体中文",
    "ja": "日本語",
    "es": "Español",
    "ru": "Русский",
}

# 앱 번역 파일 폴더 — 동결 빌드도 utils/ 와 같은 _internal\ 아래에 둔다 (AVD.spec)
I18N_DIR = Path(__file__).parent.parent / "i18n"

_installed: list = []


def resolve_language(setting: str, locale_name: str) -> str:
    """설정값과 OS 로캘 이름(QLocale.name(), 예: "ja_JP")으로 화면 언어 코드를 정한다.
    system 이나 모르는 값이면 OS 언어, 지원하지 않으면 English."""
    if setting in LANGUAGES:
        return setting
    if locale_name in ("zh_CN", "zh_SG"):  # 간체 지역만 (D084)
        return "zh_CN"
    lang = locale_name.split("_")[0]
    return lang if lang in LANGUAGES and lang != "zh" else "en"


def apply_language(app, code: str) -> None:
    """앞서 설치한 번역기를 지우고 code 의 앱 번역(한국어는 원문이라 없음)과 Qt 기본 번역을 설치한다.
    설치·제거마다 Qt 가 열린 위젯에 LanguageChange 이벤트를 보낸다."""
    for translator in _installed:
        app.removeTranslator(translator)
    _installed.clear()
    qt_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    sources = [(f"qtbase_{code}", qt_dir)]
    if code != "ko":
        sources.append((f"avd_{code}", str(I18N_DIR)))
    for name, folder in sources:
        translator = QTranslator(app)
        if translator.load(name, folder):  # 파일이 없으면 원문(앱 한국어, Qt 영어)으로 둔다
            app.installTranslator(translator)
            _installed.append(translator)
