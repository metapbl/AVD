<p align="center">
  <strong>Language:</strong>
  <a href="README.md">English</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.zh-CN.md">简体中文</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.ru.md">Русский</a>
</p>

이 문서는 영어판을 AI로 번역한 것입니다. 내용이 다르면 영어판을 따릅니다.

# AVD

<p align="center">
  <a href="https://github.com/metapbl/AVD/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/metapbl/AVD?style=flat-square"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square"></a>
  <a href="#요구-사항"><img alt="Python 3.12+" src="https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="#요구-사항"><img alt="Platform: Windows | macOS" src="https://img.shields.io/badge/platform-Windows_%7C_macOS-lightgrey?style=flat-square"></a>
</p>

yt-dlp 기반의 Python 영상·오디오 다운로더 — YouTube 와 1000여 개 사이트를 지원합니다.

## 주요 기능

AV Downloader 는 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 를 창 하나로 다루는 데스크톱 앱(PySide6)입니다. 명령줄 없이 받을 수 있습니다.

- 영상·오디오(MP3/M4A) 다운로드, 메타데이터와 썸네일을 파일에 넣기
- 화질 선택 창: 최고 화질, 최고 호환(H.264 + AAC), 해상도별, MP3 또는 M4A. 마지막 선택을 기억합니다
- 여러 개 동시 다운로드와 대기열, 진행률·속도·남은 시간 실시간 표시
- 플레이리스트: 원하는 항목만 골라 받기 (최대 500개)
- 함께 들어 있는 `gaindb` 패키지로 MP3 음량 정규화 (무손실 ReplayGain)
- 로그인 쿠키(Firefox 또는 cookies.txt)로 연령 제한 영상처럼 본인 계정이 볼 수 있는 영상 받기
- 클립보드 링크, Ctrl+V, 끌어다 놓기, 여러 줄 한 번에 붙여넣기
- 다크·라이트 테마, 6개 언어 (English, 한국어, 简体中文, 日本語, Español, Русский)
- yt-dlp 를 스스로 최신으로 유지하고, 같은 이름의 파일을 덮어쓰지 않습니다

## 요구 사항

- **Windows 11** (배포본은 Windows x64). **macOS** 는 소스에서 실행하면 동작합니다. Linux 는 지원하지 않습니다: 다운로드 폴더 열기가 동작하지 않습니다.
- PATH 에 있는 **ffmpeg / ffprobe** — 병합, MP3/M4A 변환, 태그 넣기에 씁니다. Windows: `winget install Gyan.FFmpeg` 또는 [Gyan 빌드](https://www.gyan.dev/ffmpeg/builds/).
- PATH 에 있는 **Node.js** — 일반적으로는 선택이지만 YouTube 에는 필요합니다. YouTube 가 yt-dlp 에 자바스크립트 챌린지를 풀게 하기 때문입니다 ([yt-dlp EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS)). Deno 나 Bun 도 됩니다. Windows: `winget install OpenJS.NodeJS`.
- **Python 3.12 이상** — 소스에서 실행할 때만.

## 설치

### 배포본 (Windows x64)

1. [Releases](https://github.com/metapbl/AVD/releases) 에서 `AVD-v{버전}-win64.zip` 을 받아 원하는 곳에 풉니다. `AVD` 폴더가 생깁니다.
2. ffmpeg 와 Node.js 를 설치합니다 ([요구 사항](#요구-사항) 참고). 배포본에는 들어 있지 않습니다.
3. `AVD\AVD.exe` 를 실행합니다. Python 은 필요 없습니다.

설정은 `AVD.exe` 옆의 `config.json` 에 저장되므로, 폴더째 옮기면 설정도 따라갑니다.

### 소스에서

```bash
git clone https://github.com/metapbl/AVD.git
cd AVD
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
```

가상 환경을 만들고 그 안에 앱의 패키지를 설치합니다. macOS 에서는 `venv\Scripts\python` 대신 `venv/bin/python` 을 씁니다. `requirements.txt` 는 일부러 예전 yt-dlp 를 고정해 두었고, 앱이 처음 시작할 때 새 버전으로 바꿉니다.

## 빠른 시작

```bash
venv\Scripts\python main.py
```

**AV Downloader** 와 버전이 제목인 창이 시스템 언어로 열리고, 빈 목록에 링크 추가 안내가 보입니다. 영상 링크를 복사해 창에서 **Ctrl+V** 를 누르고, 화질을 고른 뒤 **다운로드** 를 누릅니다. 파일은 `다운로드` 폴더에 저장되고, 끝나면 **📂 열기** 로 볼 수 있습니다.

## 사용법

- **링크 추가** — **+ 링크 추가** 버튼, Ctrl+V, 또는 창으로 끌어다 놓기. 링크마다 화질 선택 창이 차례로 뜨고, 플레이리스트 링크는 고를 목록이 뜹니다.
- **화질** — *최고 화질 (자동 선택)* 은 yt-dlp 가 고릅니다. *최고 호환* 은 거의 어디서나 재생되는 H.264 + AAC MP4 를 고릅니다. MP3 와 M4A 는 오디오만 저장합니다.
- **설정 (⚙)** — 저장 폴더, 동시 다운로드 수(1–3 권장), 로그인 쿠키, MP3 음량 정규화, yt-dlp 자동 업데이트 확인, 언어, 테마. **저장** 을 누르면 재시작 없이 적용됩니다.
- **파일** — 같은 이름의 파일은 덮어쓰지 않고 새 파일을 `제목 (1).mp4` 처럼 저장합니다. 다운로드 중에는 저장 폴더에 `.avd_*` 작업 폴더가 보이고, 항목이 끝나면 사라집니다. 앱이 강제 종료되어 남은 작업 폴더는 하루 뒤 앱을 시작할 때 지워집니다.

## 로그인 쿠키

연령 제한처럼 로그인해야 볼 수 있는 영상은 본인 계정의 쿠키로 받을 수 있습니다. **⚙ 설정 > 로그인 쿠키** 에서 켭니다. 기본은 꺼져 있습니다.

- **Firefox 에서 읽기** — Firefox 에서 해당 사이트(YouTube 등)에 로그인해 두고 이것을 고릅니다. 가장 간단합니다.
- **cookies.txt 파일** — Chrome, Edge 등 다른 브라우저는 쿠키를 파일로 내보내 지정합니다. Windows 의 Chrome·Edge 는 쿠키를 자기 전용으로 암호화해 직접 읽을 수 없습니다.

cookies.txt 만드는 법 (Chrome, Edge):

1. Chrome 웹 스토어에서 **Get cookies.txt LOCALLY** 확장을 설치합니다 (yt-dlp 문서가 권하는 확장). 이름이 비슷한 다른 확장 중에는 쿠키를 외부로 보낸 사례가 있으니 이름을 정확히 확인하세요.
2. **시크릿(InPrivate) 창** 을 열고 사이트에 로그인합니다. 일반 창의 쿠키는 사이트가 곧 바꿔서 내보낸 파일이 쓸모없어집니다.
3. 그 창에서 확장을 눌러 해당 사이트의 쿠키를 **Export** 하고, 시크릿 창을 닫습니다.
4. AVD 의 **cookies.txt 파일** 옆 **찾아보기** 로 그 파일을 지정합니다.

알아 둘 점:

- cookies.txt 에는 로그인 정보가 들어 있습니다. 남에게 주지 말고, 다 쓰면 지우세요.
- AVD 는 쿠키를 복사·저장하지 않고, cookies.txt 를 고치지 않습니다. 설정에는 고른 방식과 파일 경로만 남습니다.
- 로그인한 계정으로 짧은 시간에 많이 받으면 사이트가 그 계정을 제한할 수 있습니다.
- DRM 이 걸린 콘텐츠는 쿠키가 있어도 받지 않습니다 ([배포 방침](#배포-방침)).

## 프로젝트 상태

- **Windows 11** 에서 소스 실행과 배포본 모두로 개발·검증합니다. 모든 변경마다 자동 테스트(pytest)를 돌립니다.
- **macOS** 소스 실행은 지원하지만 아직 실제 Mac 에서 확인하지 않았습니다. macOS 앱 번들은 없습니다.
- 한국어 화면이 원문입니다. 영어는 AI 번역을 개발자가 검토했고, 简体中文·日本語·Español·Русский 는 AI 번역입니다. 고쳐 주시면 환영합니다(아래 참고).
- 개발자 한 명이 AI 도우미와 함께 만듭니다. 릴리스 사이에 기능이 바뀔 수 있습니다. [CHANGELOG.md](CHANGELOG.md) 를 보세요.

## 도움말과 기여

- **질문과 버그** — [이슈](https://github.com/metapbl/AVD/issues) 를 열어 주세요. 다운로드 오류라면 실패한 항목의 **자세히** 에 나오는 글을 함께 붙여 주세요.
- **Pull Request** — 번역 수정과 작은 버그 수정은 환영합니다. 큰 변경은 먼저 이슈를 열어 방향을 맞춰 주세요.
- **Pull Request 를 보내기 전에** 테스트와 린터를 돌려 주세요:

  ```bash
  venv\Scripts\python -m pip install -r requirements-dev.txt
  venv\Scripts\python -m pytest
  venv\Scripts\ruff check .
  ```

  개발 도구를 설치하고, 전체 테스트를 돌리고, 코드 스타일을 검사합니다. 세 명령 모두 오류 없이 끝나야 합니다.
- **번역** 은 `i18n/avd_{언어}.ts` 에 있고 Qt Linguist(`venv\Scripts\pyside6-linguist`)로 고칠 수 있습니다. 고친 뒤 `venv\Scripts\python tools/update_translations.py` 를 돌려 `.qm` 파일을 다시 만들고 둘 다 커밋하세요.
- 프로젝트 규칙과 설계 기록은 [AGENTS.md](AGENTS.md) 와 [docs/](docs/) 에 있습니다 (한국어).

## 보안

취약점은 GitHub 로 비공개 제보해 주세요: 저장소의 **Security** 탭 → **Report a vulnerability**. 공개 이슈로 올리지 마세요.

## 배포 방침

**무료 배포.** 저작자는 AVD 를 GitHub 에서 오픈소스로 무료 배포하며, 판매하거나 유료 에디션을 제공하지 않습니다. 이는 저작자의 배포 방식을 설명할 뿐이며, 아래 라이선스에 제한을 더하지 않습니다.

**DRM 우회 금지.** DRM(기술적 보호조치)을 우회하거나 유료·제한 콘텐츠에 무단으로 접근하는 것을 돕는 기능은 넣지 않으며, 기능 요청도 이 방침으로 판단합니다. [로그인 쿠키](#로그인-쿠키) 는 본인 계정이 이미 볼 수 있는 콘텐츠를 위한 것으로 무단 접근이 아니며, DRM 이 걸린 콘텐츠는 여전히 받지 않습니다.

## 면책

이 도구는 개인 학습과 백업 용도로 쓰세요. 각 사이트의 이용 약관과 저작권법을 지키는 것은 사용자의 책임이며, 법이 허용하는 범위에서만 자기 책임으로 사용해야 합니다.

이 소프트웨어는 상품성이나 특정 목적 적합성에 대한 묵시적 보증을 포함해 **어떠한 보증도 없이** "있는 그대로" 제공됩니다 (MIT 와 LGPL-2.1 양쪽의 무보증 조항).

## 크레딧

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 다운로드 엔진
- [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python) — GUI
- [requests](https://requests.readthedocs.io/) — 썸네일과 업데이트 확인
- [psutil](https://pypi.org/project/psutil/) — 취소할 때 ffmpeg/Node 자식 프로세스 정리
- [numpy](https://numpy.org/) 와 [SciPy](https://scipy.org/) — `gaindb` 의 음량 분석
- [GainDB](https://github.com/metapbl/GainDB) — mp3gain 에서 파생한 MP3 음량 정규화

## 라이선스

AVD 는 폴더마다 라이선스가 다릅니다.

- **AVD 본체** — `MIT`. 전문은 [LICENSE](LICENSE), 저작권과 서드파티 고지는 [NOTICE](NOTICE) 를 보세요.
- **함께 들어 있는 `gaindb/` 패키지** — `LGPL-2.1-or-later`. mp3gain(LGPL-2.1-or-later) 에서 가져와 고친 코드가 있어 같은 조건으로 배포합니다. [gaindb/LICENSE](gaindb/LICENSE), [gaindb/NOTICE](gaindb/NOTICE), [gaindb/THIRD_PARTY_LICENSES](gaindb/THIRD_PARTY_LICENSES) 를 보세요. 상류: <https://github.com/metapbl/GainDB> (번들 버전 1.1.2).

AVD 는 `gaindb.api` 의 공개 함수만 부르므로 LGPL-2.1 §5 의 "라이브러리를 사용하는 저작물"이며, MIT 라이선싱은 영향을 받지 않습니다 — PySide6(LGPLv3)를 동적 링크로 쓰는 것과 같습니다. PySide6·Qt 소스를 받는 곳은 [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES) 의 PySide6 절에 있습니다. LGPL 을 지키기 위해 배포본의 `gaindb/` 는 자기 수정본으로 바꿀 수 있는 평문 `.py` 로 두고, 각 GitHub 릴리스에 그 태그의 소스 아카이브를 함께 올립니다.
