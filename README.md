# AV Downloader

yt-dlp 기반의 영상·오디오 다운로더입니다. YouTube를 비롯해 yt-dlp가 지원하는 1000여 개 사이트에서 동작하며, PySide6로 작성된 데스크톱 GUI를 제공합니다.

> 이 저장소는 1인 개발 + AI 협업으로 진행됩니다. 협업 규칙은 [`CLAUDE.md`](CLAUDE.md), 요구사항·진행 상황·설계 근거는 [`docs/`](docs/) 아래 문서에 정리되어 있습니다.

## 주요 기능

- 영상·오디오(MP3/M4A) 다운로드와 자동 메타데이터·썸네일 임베드
- 포맷 선택 다이얼로그 (해상도/코덱/컨테이너) 및 마지막 선택 확장자 기억
- 다중 동시 다운로드와 대기열(WAITING 큐, 사용자 지정 동시 실행 수)
- 진행률·속도·남은 시간(ETA) 실시간 표시, HLS 등 ETA 미상 시 추정값 `~M:SS` 표기
- 클립보드 URL 자동 감지, yt-dlp 자체 업데이트 체크
- 다운로드 취소·재시도, 디스크 파일 동시 삭제 옵션, 부분 파일(`.part`/`.ytdl`) 정리
- 한글 파일명·태그의 NFC 정규화 (Windows NFC ↔ macOS APFS NFD 호환)
- MP3 음량 정규화 — 번들 `gaindb/` 서브패키지가 ReplayGain 트랙 모드로 무손실 게인을 적용합니다(목표 dB는 설정에서 조절, `numpy`/`scipy` 필요)
- 다크 테마 GUI

## 요구 사항

- **Python 3.12 이상** (3.15 에서 개발·검증)
- **ffmpeg / ffprobe** — 영상·오디오 병합, MP3·M4A 변환, 메타데이터·썸네일 임베드에 필요합니다. 시스템 PATH에 등록되어 있어야 합니다.
  - Windows: [공식 빌드](https://www.gyan.dev/ffmpeg/builds/) 다운로드 후 PATH 등록, 또는 `winget install Gyan.FFmpeg`
- **Node.js** (선택이지만 YouTube에는 사실상 필수) — yt-dlp가 YouTube의 자바스크립트 챌린지를 해결하기 위해 외부 JS 런타임(EJS)을 요구합니다. Node.js / Deno / Bun 중 하나면 됩니다.
  - Windows: [Node.js 공식 사이트](https://nodejs.org/) 또는 `winget install OpenJS.NodeJS`
  - 배경: [yt-dlp EJS Wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS)
- **운영체제**: Windows 11에서 개발·검증되었습니다. macOS/Linux는 일부 경로(폴더 열기, 폰트 등)가 아직 분기 처리되지 않아 제한적으로 동작합니다.

## 설치

```bash
git clone https://github.com/metapbl/AVD.git AV_Downloader
cd AV_Downloader

python -m venv venv
venv\Scripts\activate          # Windows (PowerShell)
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

## 실행

```bash
python main.py
```

첫 실행 시 사용자 홈 폴더의 `Downloads`가 저장 경로로 지정되며, 앱 내 **⚙ 설정**에서 변경할 수 있습니다. 설정은 앱 폴더(`main.py` 옆)의 `config.json`에 저장됩니다.

## 디렉터리 구조

```
AV_Downloader/
├── main.py                       # 엔트리 포인트
├── CLAUDE.md                     # AI 협업 규칙
├── CHANGELOG.md                  # 변경 이력
├── README.md                     # (이 문서)
├── requirements.txt              # 앱 의존성
├── requirements-dev.txt          # 개발 도구 (pytest·ruff)
├── pyproject.toml                # ruff·pytest 설정
├── core/
│   ├── downloader.py             # yt-dlp 래퍼 + PostProcessor 파이프라인
│   └── info_fetcher.py           # 사전 메타데이터/포맷 조회
├── models/
│   └── download_item.py          # DownloadItem 데이터 모델, 상태 Enum
├── controllers/
│   ├── download_manager.py       # 동시 다운로드 디스패치·대기열·라이프사이클
│   └── playlist_flow.py          # 플레이리스트 목록 조회 → 선택 → 일괄 등록
├── ui/
│   ├── main_window.py            # 메인 윈도우
│   ├── download_item_widget.py   # 다운로드 항목 위젯
│   ├── add_link_dialog.py        # URL 추가 다이얼로그
│   ├── format_select_dialog.py   # 포맷 선택 다이얼로그
│   ├── playlist_select_dialog.py # 플레이리스트 항목 선택 다이얼로그
│   ├── confirm_remove_dialog.py  # 삭제 확인 다이얼로그
│   ├── preferences_dialog.py     # 설정 다이얼로그
│   └── update_progress_dialog.py # yt-dlp 업데이트 진행 모달
├── utils/
│   ├── config_manager.py         # JSON 설정 입출력
│   ├── file_utils.py             # 파일·프로세스·유니코드 유틸
│   └── updater.py                # yt-dlp / 앱 업데이트 체크
├── workers/
│   ├── download_worker.py        # 다운로드 백그라운드 스레드
│   ├── info_worker.py            # 정보 조회 백그라운드 스레드
│   ├── playlist_probe_worker.py  # 플레이리스트 목록 조회 스레드
│   ├── thumbnail_worker.py       # 썸네일 다운로드 백그라운드 스레드
│   └── update_worker.py          # yt-dlp 업데이트 스레드
├── gaindb/                       # MP3 음량 정규화 서브패키지 (LGPL-2.1-or-later)
├── assets/                       # 아이콘
└── docs/                         # PRD·진행 상황·참고 문서·계획
```

다운로드 큐와 동시 실행 디스패치는 `controllers/download_manager.py`(`DownloadManager`, `QObject` 상속)가 담당하며, `MainWindow`는 UI 이벤트와 표시만 책임집니다. 자세한 배경은 [`docs/legacy/ADR.md`의 ADR-003](docs/legacy/ADR.md) 참조.

## 사용된 주요 라이브러리

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 영상 추출 핵심 엔진
- [PySide6](https://doc.qt.io/qtforpython-6/) — GUI 프레임워크 (Qt for Python)
- [requests](https://requests.readthedocs.io/) — 썸네일·업데이트 체크
- [psutil](https://pypi.org/project/psutil/) — 다운로드 취소 시 ffmpeg/Node 자식 프로세스 정리

## 문서

- [`CLAUDE.md`](CLAUDE.md) — AI 협업 규칙, 실행·테스트 명령, 이 프로젝트에서 지켜야 할 규칙
- [`docs/PRD.md`](docs/PRD.md) — 목적·범위·기능 요구사항 (승인본)
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — 현재 상태·다음 할 일·미해결 문제
- [`docs/REFERENCE.md`](docs/REFERENCE.md) — 구조, 외부 사양·제약, 반복해서 부딪힌 함정 대장
- [`docs/discovery/DECISIONS.md`](docs/discovery/DECISIONS.md) — 결정 기록 (버린 안 포함)
- [`CHANGELOG.md`](CHANGELOG.md) — 날짜별 변경 이력
- [`docs/legacy/`](docs/legacy/) — 2026-10 이전 문서 (WORKLOG·ADR·LESSONS, 참고용)

## 라이선스

이 프로젝트는 **폴더 경계 이중 라이선스**입니다.

- **AVD 본체** — MIT License. 전문은 [LICENSE](LICENSE), 저작권·서드파티 고지는 [NOTICE](NOTICE) 를 참조하세요.
- **번들 서브패키지 `gaindb/`** — **GNU LGPL v2.1 or later**. mp3gain(LGPL-2.1-or-later) C 소스에서 개작·파생된 부분을 포함하므로 원본과 같은 조건으로 배포합니다. 전문은 [`gaindb/LICENSE`](gaindb/LICENSE), mp3gain 원저작자 고지와 변경 내역은 [`gaindb/NOTICE`](gaindb/NOTICE), 의존성 고지는 [`gaindb/THIRD_PARTY_LICENSES`](gaindb/THIRD_PARTY_LICENSES) 에 있습니다. 상류 저장소는 <https://github.com/metapbl/GainDB> (번들 버전 0.5.1).

AVD 본체는 `gaindb.api` 의 공개 함수만 호출하므로 LGPL-2.1 §5 의 "라이브러리를 사용하는 저작물"에 해당하며, 본체의 MIT 라이선싱은 영향을 받지 않습니다. 이는 PySide6(LGPLv3)를 동적 링크로 사용하는 구조와 동일합니다.

배포 방침 — LGPL 준수를 위해 배포물의 `gaindb/` 는 사용자가 자기 수정본으로 교체할 수 있도록 실행 파일에 묶지 않고 평문 `.py` 로 배치하며(onedir 구성), 각 GitHub Release 에 해당 태그의 소스 아카이브를 실행 파일과 함께 첨부합니다.

## 배포 방침

**비영리 무료 공개.** 이 프로젝트는 GitHub 에서 오픈소스로 무료 배포되며, 유료 판매·유료 에디션·상업적 재판매를 하지 않습니다.

**DRM 우회 금지 방침.** DRM(기술적 보호조치) 우회나 유료·인증 전용 콘텐츠에 대한 무단 접근을 돕는 기능은 도입하지 않습니다. 관련 기능 요청은 이 방침을 기준으로 판단합니다.

## 면책

이 도구는 개인적 학습과 백업 목적으로 사용하시기 바랍니다. 각 사이트의 이용 약관과 저작권법을 준수하는 것은 사용자의 책임입니다. 사용자는 자신의 책임 아래 합법적인 범위에서만 이 도구를 사용해야 하며, 그로 인해 발생하는 모든 결과와 책임은 사용자에게 있습니다.

이 소프트웨어는 **어떠한 보증도 없이(WITHOUT ANY WARRANTY)** "있는 그대로" 제공됩니다. 상품성이나 특정 목적 적합성에 대한 묵시적 보증도 포함되지 않습니다(MIT 및 LGPL-2.1 양쪽의 무보증 조항).
