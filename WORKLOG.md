# AV_Downloader 작업 로그

> 이 문서는 AV_Downloader 의 작업 진척, 결정 사항, 잔여 과제를 추적합니다.
> 프로젝트의 변하지 않는 정보(기술 스택·폴더 구조·코딩 컨벤션 등)는 `CLAUDE.md` 에 별도로 관리하며, 이 파일은 시간과 함께 자라는 정보만 담습니다.

---

## 문서 구조

이 파일은 네 섹션 + 부록 한 개로 구성됩니다.

- **섹션 1 — 빠른 안내**: 새 세션 시작 시 어떻게 이 문서를 활용할지.
- **섹션 2 — Changelog**: 별도 파일 `CHANGELOG.md` 로 분리. 이 파일에는 안내 한 단락만 남음.
- **섹션 3 — 현재와 다음**: 진행 중인 작업과 단기·중기·장기 로드맵.
- **섹션 4 — ADR (결정 기록)**: 아키텍처·중대 버그 해결 등 큰 결정의 맥락과 결과.
- **부록 A — 학습된 교훈**: 같은 실수를 반복하지 않기 위한 사례별 메모.

각 섹션은 서로 다른 시간 척도를 가집니다. `CHANGELOG.md` 는 한 번 적은 줄을 절대 지우지 않고 누적됩니다. 섹션 3 은 유동적이며 항목이 완료되면 `CHANGELOG.md` 로 옮기고 섹션 3 에서는 즉시 삭제합니다 (✅ 마커를 남기지 않음 — 누적 비용 회피). 섹션 4 는 큰 결정이 있을 때만 새 항목이 추가됩니다.

---

## 1. 빠른 안내

### 1.1. 새 세션 시작 방법

`CLAUDE.md` 의 "11. 새 세션 시작 방법" 섹션을 따른다. 환경별(claude.ai 웹 채팅 / Claude Code) 절차가 거기에 정리되어 있다.

### 1.2. 작업 완료 시 갱신 규칙

- 의미 단위가 끝나 커밋이 발생하면 → [`CHANGELOG.md`](./CHANGELOG.md) 의 맨 위에 항목 추가 (헤더에 7자리 해시 배지, 긴 본문은 `<details>` 로 접기)
- 큰 결정(아키텍처·중대 버그 해결)이 있으면 → 섹션 4 (ADR) 에 새 항목 추가
- 새 할 일이 생기면 → 섹션 3 (현재와 다음) 의 적절한 위치에 추가
- 섹션 3 의 항목이 완료되면 → `CHANGELOG.md` 의 해당 커밋 항목에 흡수하고 섹션 3 에서는 즉시 삭제. ✅ 마커는 남기지 않는다.

---

## 2. Changelog

시간 역순 변경 이력은 별도 파일 [`CHANGELOG.md`](./CHANGELOG.md) 로 분리되었습니다. 새 항목은 그쪽에 추가하십시오.

이 문서(WORKLOG) 는 "지금 무엇을 하고 있고, 왜 그렇게 하기로 했는가" 에 집중합니다. CHANGELOG 는 "무엇이 바뀌었는가" 만 append-only 로 누적합니다. 두 문서의 역할 분담:

- **CHANGELOG.md**: 시간 역순 커밋 단위 변경 이력. 각 항목은 7자리 해시 배지를 헤더에 포함하며, 본문은 `<details>` 로 접혀 필요할 때만 펼쳐 봄.
- **WORKLOG.md** (이 파일): 로드맵(섹션 3), ADR(섹션 4), 학습된 교훈(부록 A) 등 시간에 따라 형태가 바뀌는 살아있는 문서.

---

## 3. 현재와 다음 작업

> 진행 중인 작업과 앞으로 할 작업을 적습니다. 완료되면 위 Changelog 로 옮기고 이 섹션에서는 즉시 삭제합니다.

### 3.1. 진행 중 (In Progress)

*현재 없음.*

### 3.2. 단기 (Short-term, 1~2 세션 내)

- **체크박스 시각 개선 (체크 시 ✓ 마크가 보이도록)**
    - 위치: `ui/preferences_dialog.py`, `ui/confirm_remove_dialog.py` 의 `QCheckBox` 들.
    - 진단 (2026-05-28 사전 확인):
        - 두 다이얼로그의 스타일시트는 `QCheckBox::indicator` 를 직접 손대고 있지 않음 — 라벨의 색·폰트만 지정.
        - `main.py` 도 `setStyle` / `setPalette` / `setStyleSheet` 호출이 없어 Qt 가 OS 기본 스타일로 그림(Windows 11Style).
        - 그럼에도 ✓ 가 직관적이지 않은 이유는 (a) 다이얼로그 배경(`#2b2b2b`) 과 OS 가 그리는 라이트 톤 체크박스 indicator 의 부조화, (b) Windows 11 다크 모드에서 Qt 의 부분 적응으로 ✓ 색이 배경과 대비가 약한 경우의 조합으로 추정.
    - 정책: 가장 단순한 방향 — 두 다이얼로그의 스타일시트에 `QCheckBox::indicator` 의 `width` / `height` 만 키워(예: 18×18) ✓ 가 잘 보이게 하고, 색·배경은 손대지 않음. ✓ 마크는 Qt 기본 렌더 그대로 둠.
    - 그래도 부족하면 두 번째 단계: `QApplication.setStyle("Fusion")` 을 `main.py` 에서 호출 — Fusion 은 OS 와 무관하게 일관된 위젯 렌더링을 보장하고, 다크 팔레트와 잘 어울린다는 평가가 보편적. 단, 다른 위젯(버튼·진행률 바)의 외양이 미세하게 달라질 수 있어 회귀 점검 필요. macOS 호환성 과제와 시너지 — Fusion 으로 통일하면 두 OS 의 렌더 차이도 줄어듦.
    - 라디오 버튼은 현재 코드베이스에 없음(확인됨) — 같이 다룰 필요 없음.

- **파일명 확장자를 제목 라벨에 표시**
    - 위치: `ui/download_item_widget.py` `_apply_title_elide` · `update_title` · 새 `update_ext`, `ui/main_window.py` `_on_format_selected`.
    - 표시 형식: 제목 끝에 확장자 — 폭이 넉넉할 때 `"긴 영상 제목.mp4"`, 폭이 좁아 제목이 잘릴 때 `"긴 영상 제… .mp4"` (확장자는 절대 잘리지 않음).
    - elide 정책:
        - 모드는 `ElideRight` 이지만 Qt 의 기본 줄임표 `…` (U+2026 단일 문자) 사용 + 줄임표와 `.` 사이에 공백 1칸 — 즉 `"… .mp4"`. 점 4개(`....`) 가 연달아 보이는 시각 충돌 회피.
        - 직접 elide: 확장자 + 구분 공백의 폭만큼 가용 폭에서 미리 빼고, 제목만 `QFontMetrics.elidedText(ElideRight)` 로 자른 뒤, 결과 뒤에 `" .mp4"` 를 다시 붙임. 잘림이 발생하지 않으면 공백 없이 `".mp4"` 만 붙임 (자연스러운 케이스).
    - 확장자 스타일: HTML rich text 로 부분 색만 다르게 — 확장자 색 `#ffd060`, 굵기는 제목과 동일(이미 bold). `lbl_title.setText("<span>...</span>")` 사용. 제목에 `<` / `>` / `&` 가 포함된 경우 대비 `html.escape` 로 escape.
    - 표시 시점(가드): 화질 선택 전에는 확장자 비표시. 위젯 인스턴스에 `_ext_known: bool` 플래그를 두고, `update_ext` 가 한 번이라도 호출되어야 elide 결과에 확장자를 끼움. `MainWindow._on_format_selected` 가 `item.ext = fmt.ext` 직후 `widget.update_ext(fmt.ext)` 호출.
    - `update_ext` 는 내부적으로 `_apply_title_elide` 를 재호출하여 라벨을 다시 그림. 폭 변경(resize) 시에도 기존 `resizeEvent` 경로가 그대로 elide 를 다시 적용하므로 별도 작업 없음.

- **메타 행에 코덱·포맷·비트레이트 추가**
    - 위치: `ui/download_item_widget.py` `lbl_meta`, `core/info_fetcher.py` `FormatInfo`, `ui/format_select_dialog.py`, `ui/main_window.py` `_on_format_selected`.
    - 현재 `"업로더 • 재생시간"` 한 줄 → `"업로더 • 재생시간 • H.264 MP4 • AAC 192kbps"` 형태로 확장. 오디오 전용 항목은 `"아티스트 • 3:42 • MP3 320kbps"`.
    - `FormatInfo` 에 `vcodec` / `acodec` / `abr` / `tbr` 필드 추가 — yt-dlp raw format dict 에서 그대로 가져옴.
    - 표시 시점: 위젯 생성 직후에는 업로더·재생시간만, 사용자가 `FormatSelectDialog` 에서 화질 확정한 직후(`_on_format_selected`) 코덱·비트레이트까지 채워 메타 라벨 재갱신.
    - 통합 포맷(`bestvideo+bestaudio/best`) 정책: 선택 시점에 어떤 코덱이 채택될지 미확정이라 코덱 자리는 빈 값 또는 `"자동"`. ffprobe 호출 같은 추가 비용은 도입하지 않음 (이번 단기 과제 범위 밖).
    - 코덱 표기 정규화: yt-dlp 의 `vcodec` 은 `"avc1.640028"` 같은 raw 코덱 문자열이라 사람 친화 이름(`H.264`, `VP9`, `AV1`, `AAC`, `Opus`, `MP3` 등) 으로 매핑하는 작은 헬퍼 필요. 매핑 출처: yt-dlp wiki / MDN.

- **macOS 지원 정식화 (실행 환경만)**
    - 동기: 사용자가 Windows 에서 개발하고, macOS 에서는 실행만 함. README/CLAUDE 에 명시되어 있던 "Windows 우선, macOS 일부 기능 미동작" 정책을 "Windows 개발 / macOS 실행 양쪽 정식 지원" 으로 격상. macOS 작업/문서 환경(zsh 등) 보강은 불필요.
    - 진단 (2026-05-28 사전 확인):
        - `utils/file_utils.py` `open_folder()`: `subprocess.run(["explorer", ...])` 가 Windows 전용. macOS 에서 `FileNotFoundError` 로 "📂 열기" 버튼이 깨짐. 가장 큰 회귀 지점.
        - `main.py` 의 폰트 `QFont("맑은 고딕", 10)`: macOS 에 해당 폰트가 없어 시스템 폴백으로 그려짐. 의도된 모양이 아닐 수 있음.
        - `requirements.txt` 의 `psutil` 은 크로스플랫폼 — 문제 없음.
        - yt-dlp + ffmpeg + Node.js 는 macOS 도 정식 지원 (Homebrew 로 설치 가능).
        - `core/downloader.py` 의 `windowsfilenames: True` 는 macOS 에서도 동작 — 다소 보수적이지만 의도된 정책으로 유지.
    - 정책:
        1. `open_folder()` 플랫폼 분기. `sys.platform` 으로 `"win32"` / `"darwin"` / 기타(linux) 갈래. macOS: `subprocess.run(["open", "-R", path])` (파일 선택) / `subprocess.run(["open", path])` (폴더). Linux: `subprocess.run(["xdg-open", path])` — 부수효과 없이 같이 처리.
        2. `main.py` 폰트 fallback 체인. `QFont("맑은 고딕, Apple SD Gothic Neo, sans-serif", 10)` — Qt 가 매칭 가능한 첫 폰트로 그림. macOS 는 Apple SD Gothic Neo 로 자동 fallback.
        3. README.md 의 "요구 사항" 절에서 "Windows 환경에서 검증 / macOS·Linux 는 일부 기능이 동작하지 않을 수 있다" 라는 단서 제거. macOS 실행 가이드(`brew install ffmpeg node`) 한 줄 추가.
        4. **개발 환경 관련 문서(CLAUDE.md "5. 개발 환경", "8.4. 터미널 명령")는 손대지 않음** — 사용자가 macOS 에서 개발하지 않으므로 Windows + PowerShell 규약을 그대로 유지.
    - 검증 절차: Windows 에서 위 1~3 수정 → push → macOS 에서 pull → `python main.py` 로 실행 → "📂 열기" 버튼, 한글 폰트, 다운로드 정상 동작 확인. 사용자가 macOS 결과를 알려주는 식으로 한 사이클 돌림.
    - 보류 (이번 과제 범위 밖):
        - NFC 정규화 vs macOS APFS 의 fs-level NFD 반환 — 앱 내부는 `normalize_info_dict` 로 NFC 통일이라 OK 추정. 실측 후 문제 있으면 추가 과제.
        - `.gitattributes` (LF/CRLF) — 단일 OS 작업이라 불필요.

### 3.3. 중기 (Mid-term, 다음 마일스톤)

- **포맷 선택 UX 개선**
  - "최고 화질 (자동·효율 우선)" 과 "최고 호환 (MP4/H.264)" 분리 (ADR-002 후보)

### 3.4. 장기 (Long-term, 백로그)

- **자동 업데이트 검증**
  - `utils/updater.py` 가 yt-dlp 신버전 감지 시 안전하게 갱신하는지 확인
- **다국어 지원**
  - i18n 도입 (한국어·영어 기본)
- **플레이리스트 일괄 다운로드**
  - 한 URL 로 N 개 항목 추가
- **테마·스타일 옵션**
  - 라이트·다크·시스템 자동 전환

---

## 4. 아키텍처 결정 기록 (ADR)

> 중요한 설계 결정을 한 항목씩 기록합니다. 한번 작성된 ADR 은 **수정하지 않고** 새 ADR 로 대체합니다 (Superseded 표시).
> 참고: [ADR — Architectural Decision Records](https://adr.github.io/)

### 4.1. ADR-001: 썸네일 처리 — UI 미리보기와 파일 임베드의 분리

- **상태**: Accepted
- **날짜**: 2026-05-17
- **관련 커밋**: `fix(ui): worker lifecycle...`, `feat(downloader): embed thumbnail...`
- **관련 이슈**: WORKLOG 6번 (해결됨)

#### 맥락 (Context)

"썸네일이 안 보인다" 는 동일한 문구가 두 개의 전혀 다른 대상을 가리키고 있었음:

1. **UI 미리보기 썸네일** — `DownloadItemWidget.lbl_thumb` QLabel 에 표시되는 작업 화면 내 미리보기
2. **파일 임베드 썸네일** — 다운로드된 mp4/mp3 에 메타데이터로 박혀 Windows 탐색기·플레이어 아이콘으로 노출되는 이미지

용어 혼동으로 진단·해결이 수 차례 지연됨. 두 대상은 코드 위치, 라이브러리, 스레드 모델이 완전히 다름.

#### 결정 (Decision)

두 썸네일을 **명시적으로 구분**하여 코드와 문서에 반영한다.

**UI 미리보기 (PySide6 영역)**

- `QPixmap` / `QImage` 는 **반드시 GUI 스레드에서만** 생성한다.
- 워커 스레드(`ThumbnailWorker`) 는 raw bytes 만 시그널로 전달하고, 위젯이 GUI 스레드에서 `QPixmap.loadFromData()` 로 변환한다.
- 워커 시그널은 `Qt.QueuedConnection` 을 명시한다.
- 워커는 `item_id` 를 함께 전달해 위젯 재사용 시 시그널 오염을 방지한다.
- `_thumb_workers` 는 dict 구조로 관리하고 cancel 메서드를 제공한다.

**파일 임베드 (yt-dlp/FFmpeg 영역)**

- yt-dlp 옵션 `writethumbnail=True`, `embedthumbnail=True` 를 설정한다.
- postprocessor 체인을 다음 순서로 구성한다:
  1. `FFmpegThumbnailsConvertor` (webp → jpg 변환)
  2. `EmbedThumbnail` (파일에 임베드)
  3. `FFmpegMetadata` (제목·업로더 등 메타데이터)
- MP3 는 `-id3v2_version 3 -write_id3v1 1` 로 Windows 탐색기 호환을 보장한다.
- FFmpeg / FFprobe 가 PATH 에 있어야 한다.

#### 결과 (Consequences)

**긍정**

- 워커 스레드에서 QPixmap 을 만들던 잠재적 크래시·표시 누락이 사라짐
- 다운로드 파일이 탐색기·음악 플레이어에서 썸네일을 정상 표시
- 두 대상이 코드·문서·대화에서 분리되어 디버깅 비용 감소

**부정**

- FFmpeg 의존이 명시적으로 필요 (사용자 환경 안내 필요)
- postprocessor 체인이 길어져 다운로드 후처리 시간이 약간 증가

#### 대안 검토

- **A안 — 워커에서 QPixmap 생성 후 emit**: PySide6 규약 위반. 채택 불가.
- **B안 — `info["thumbnail"]` 신뢰 안 하고 자체 선택 로직(`_pick_thumbnail`)**: 진단 결과 yt-dlp 가 이미 maxresdefault 를 정확히 반환함. 불필요한 복잡도. 채택 안 함.
- **C안(채택)**: 위 결정 참조.

---

### 4.2. ADR-002: (예약됨) 포맷 선택 — "최고 화질" 의미 분리

- **상태**: Proposed
- **날짜**: TBD

현재 "최고 화질" 은 yt-dlp 의 `bestvideo+bestaudio/best` 로 동작하며, YouTube 의 VP9/AV1 우선 정책에 따라 H.264 1080p 보다 파일이 작아질 수 있음. 사용자 혼란 방지를 위해 "최고 화질 (자동·효율 우선)" 과 "최고 호환 (MP4/H.264)" 를 분리할지 결정 필요. 추후 작성.

---

### 4.3. ADR-003: 다운로드 워커 오케스트레이션을 `DownloadManager` 로 분리

- **상태**: Accepted
- **날짜**: 2026-05-28
- **관련 커밋**: `feat(ui): 동시성 제어 큐 매니저 도입 + MainWindow 분할` (`954152f`)

#### 맥락 (Context)

환경설정 슬라이더의 `max_concurrent` 값을 실제 동시 다운로드 수 제어로 승격시키는 작업("동시성 제어 구현") 을 시작하며 `MainWindow` 의 현재 책임 부담을 확인. `MainWindow` 는 이미 ① UI 구성, ② 항목 라이프사이클(추가·제거·일괄정리), ③ 다운로드 워커 오케스트레이션, ④ 썸네일 워커 관리, ⑤ 앱 차원 부수 동작(업데이트 체크·환경설정) 다섯 책임을 짊어진 약 500 줄짜리 클래스였음. 큐 매니저 정책(`_dispatch_next` / `_refresh_waiting_labels` / `_start_worker`) 을 ③ 에 추가하면 ③ 의 무게가 한 단계 더 커지고, 다음 단기 항목인 "다운로드 항목 메타데이터 표시 결손" 이 ② 를 키울 예정이라 분할 시점을 더 늦추기 어려운 상황.

사용자가 1차 코드 제시(부분 발췌) 의 가독성 문제를 지적한 것이 직접적 계기. 변경이 일곱 함수에 흩어져 부분 발췌의 이점이 사라졌고, 변경 지점이 묻혀 보였음. 단순 형식 문제가 아니라 분할이 늦었다는 신호로 해석.

#### 결정 (Decision)

다섯 책임 중 ③ 만 떼어내는 **최소 분할** 채택. 신규 패키지 `controllers/` 디렉터리에 `DownloadManager` (`QObject` 서브클래스) 를 신설하고, `MainWindow` 는 매니저에 위임만 수행.

**경계 (boundary):**

- 매니저가 책임지는 것: `DownloadWorker` 의 생성·연결·종료, `dl_workers` dict 보유, 동시성 한도 적용 (`_dispatch_next`), WAITING 순번 라벨 갱신 (`_refresh_waiting_labels`).
- 매니저가 책임지지 않는 것: `InfoWorker` (항목 라이프사이클에 묶임), `ThumbnailWorker` (큐 정책과 무관), 다이얼로그, 위젯 자체의 생성·파괴.
- `items` / `widgets` dict 는 `MainWindow` 가 단일 소유자. 매니저는 참조만 받아 읽기·순회. `ItemRegistry` 같은 추가 추상은 도입하지 않음 (이 규모에 과설계).

**시그널 정책:**

- 진행률·속도·ETA·병합 (`progress` / `speed` / `eta` / `merging`): 워커→위젯 **직접 연결** (매니저 미경유). 라이프사이클이 아니라 흐름이므로 매니저가 중계해 비용을 N 배로 늘릴 이유가 없음.
- 라이프사이클 (`finished` / `error` / `cancelled`): 워커→매니저→`MainWindow` 의 두 단 경로. 매니저가 받아 자체 시그널 (`item_done` / `item_error` / `item_cancelled`) 로 재발사. 이 경로에서 매니저가 `_dispatch_next` 를 호출해 슬롯 한 칸 풀림을 즉시 다음 항목 출발로 이어줌.

**큐 자료구조 부재:**

별도 `Queue` / `deque` 를 두지 않고 `self.items` 의 dict 순서(=삽입 순서) 를 큐로 사용. 대기 중 항목 = `status == WAITING` 인 항목. 단일 출처 원칙 유지 — 두 자료구조를 동기화하는 비용과 그 동기화가 어긋날 위험을 회피.

#### 결과 (Consequences)

- `MainWindow` 는 약 500 줄 → 약 400 줄로 감소. 워커 시그널 연결 잡음이 매니저로 이동하여 `MainWindow` 의 가독성 개선.
- 매니저는 UI 에 직접 의존하지 않음 (`widgets` 를 호출할 때는 인터페이스 메서드만 사용). 향후 단위 테스트 가능성 열림 — `widgets` 자리에 mock 을 주입하면 큐 정책만 검증 가능.
- `CLAUDE.md` 의 "폴더 구조" 섹션에 `controllers/` 디렉터리 추가 갱신 필요 (별도 `docs(claude)` 커밋으로 따라감).
- 다음에 ② 항목 라이프사이클이 커지면 (예: 항목 메타데이터 표시 확장, 항목 정렬·필터링) `ItemRegistry` 같은 추가 분할이 자연스러운 후보. 지금은 미루지만, 매니저 분리가 그 분할의 패턴을 미리 만든 셈.
- 분할이 한 커밋에 기능 추가 (`feat`) 와 묶인 점은 정직성 비용. 두 커밋으로 끊는 (a) 안과 한 커밋으로 가는 (b) 안 사이에서 응답 비용을 이유로 (b) 채택. 검증 시나리오에 "분할 회귀" (시나리오 ⑥, 새 동작이 거의 개입하지 않는 가장 단순한 시나리오 — 영상 1 개 추가 후 완료까지) 를 별도로 둬 분할 부분의 무죄 추정을 확보하는 절차로 부분 보완.

#### 대안 (Alternatives considered)

- **A. 전체 파일 통째 제시 + 분할 없음**: 변경 추적은 쉬워지지만 `MainWindow` 가 계속 비대해짐. 다음 작업에서 같은 고민을 한 번 더 하게 됨.
- **B. 다섯 책임 모두 분할 (controllers/items/workers/ui 등 전면 재배치)**: 이 규모에 과분할. 매니저 외 책임들은 분량이 작아 빼낸 후 한 파일이 다섯 줄짜리 메서드 세 개만 갖는 식이 됨.
- **C. 큐 매니저만 `MainWindow` 안의 별도 메서드 그룹으로 둠 (분할 없음)**: 1차 응답의 형태였음. 변경 가독성이 떨어지고 향후 단위 테스트 가능성이 닫힘.
- **D. refactor 와 feat 두 커밋으로 분리**: 정직하지만 응답을 두 번 끊는 비용이 두 커밋의 청결함을 능가한다고 판단해 단일 feat 로 묶음. 시나리오 ⑥ 으로 분할 회귀 검증을 따로 둠으로써 부분 보완.

---

### 4.4. ADR-004: `process_ie_result` 우회 폐기, NFC 보존을 PostProcessor 정공법으로

- **상태**: Accepted
- **날짜**: 2026-05-28
- **관련 커밋**: `fix(downloader): YouTube 토큰 만료 회귀 …` (`316c642`)
- **대체 관계**: 2026-05-18 의 `fix(downloader)` "NFC 메타데이터를 yt-dlp 의 정상 경로로 흘려보내는 구조로 재구성" 결정을 **부분 번복** (process_ie_result 사용 부분). ADR-001 의 후처리 체인 결정은 유효, 본 ADR 이 한 단계(`pre_process` 의 NFC PP) 를 추가하는 형태로 보강.

#### 맥락 (Context)

2026-05-18 에 NFC 메타 보존을 위해 본 다운로드 호출을 `ydl.download([url])` → `ydl.process_ie_result(probed, download=True)` 로 교체. probe 에서 받아 NFC 화한 info dict 를 재추출 없이 후처리 체인에 흘리는 우회로 사용. SoundCloud 의 NFD 한글 메타가 NFC 로 보존되는 것을 검증.

2026-05-28 mp3 메타 정리 작업의 검증 단계에서 같은 코드가 YouTube 영상 다운로드 시 `HTTP Error 403: Forbidden` 으로 실패하는 회귀가 발견됨. 통제 실험:

- yt-dlp CLI 단독 호출 (`yt-dlp -x --audio-format mp3 ...`) — 성공
- 같은 venv 에서 Python API `ydl.download([url])` 단독 호출 — 성공
- 같은 venv 에서 Python API `ydl.process_ie_result(probed, download=True)` — 실패 (403)

원인 해석: probe 단계에서 yt-dlp 가 가져온 format URL(googlevideo 의 `videoplayback?...`) 의 nsig/sig 토큰에 만료 시점이 있고, 두 번째 `process_ie_result` 호출 시점에 그 토큰이 더는 유효하지 않거나, yt-dlp 가 download 단계에서 토큰을 새로 발급받는 흐름이 `process_ie_result` 경로에서는 우회됨. YouTube 의 토큰 정책이 5월 사이 더 엄격해진 것으로 보이며, SoundCloud · 다른 사이트는 같은 문제가 없어 약 열흘 동안 잠복.

#### 결정 (Decision)

`process_ie_result` 우회를 폐기하고 NFC 보존을 **`pre_process` 단계의 커스텀 PostProcessor** 로 달성.

**구조:**

- `core/downloader.py` 모듈 최상위에 `_NFCNormalizePP(PostProcessor)` 정의. `run(info)` 에서 info dict 의 모든 문자열 값을 재귀적으로 `unicodedata.normalize("NFC", ...)`. 동시에 `info["meta_comment"] = info.get("description") or ""` 사전 주입 — `FFmpegMetadataPP` 의 `webpage_url → comment` 자동 매핑 차단 (이전엔 별도 단기 항목이었으나 같은 PP 안에서 비용 0 으로 해결).
- `ydl.add_post_processor(_NFCNormalizePP(), when="pre_process")` 로 등록. `pre_process` 의 정의는 yt-dlp README 의 "after video extraction" — `extract_info` 직후, 파일명 결정·다운로드·모든 일반 PP 보다 앞.
- 본 다운로드는 `ydl.download([url])` 로 복귀. probe 단계 삭제.

**경계 (boundary):**

- NFC 정규화의 단일 출처는 `_NFCNormalizePP`. 호출자(워커·매니저) 는 NFC 를 신경 쓰지 않음.
- `utils.file_utils` 의 `normalize_unicode` / `normalize_info_dict` / `sanitize_filename` 은 그대로 보존되지만 `core/downloader.py` 는 더 이상 사용하지 않음. 다른 호출자 (예: `core/info_fetcher.py` 의 InfoWorker 경로) 가 여전히 필요로 할 수 있어 file_utils 자체에는 유지.
- 파일명 sanitize 는 yt-dlp 의 `windowsfilenames: True` + `trim_file_name: 200` 에 위임. Windows 금지 문자 처리와 길이 제한이 yt-dlp 의 outtmpl 처리 단계에서 일어남.

**부수 결정:**

- `_BASE_OPTS` 의 `js_runtimes: {"node": {}}` / `remote_components: ["ejs:github"]` 두 줄 제거. node 단일 고정이 deno/bun 자동 선택을 가로막던 점을 자동 탐지에 맡겨 해소. yt-dlp 가 사용 가능한 런타임을 알아서 고른다 (CLI 동작에서 deno 가 선택됨을 확인).

#### 결과 (Consequences)

**긍정**

- YouTube 토큰 흐름이 yt-dlp 의 정상 경로를 따라 처리되어 403 회귀 해소.
- NFC 보존은 한 PP 하나의 책임으로 응집. 메타 통제 관련 모든 가공이 같은 자리에서 일어나 추적 비용 감소.
- SoundCloud `comment` 자동 매핑 문제도 같은 PP 가 `meta_comment` 사전 주입으로 해결 — 별도 코드 경로 불필요.
- JS 런타임 환경 변화에 둔감 (node 만 박혀 있던 고정이 풀림).
- 코드 라인 수가 줄어듦 (55 insertions / 111 deletions).

**부정**

- 2026-05-18 의 결정에 대한 신뢰가 약화됨. probe-then-process 패턴 자체가 일반적으로 안전하다고 가정했으나 YouTube 의 토큰 정책이 그 가정을 깨뜨릴 수 있음을 학습. 다른 사이트에서도 같은 가정이 깨질 가능성 — 후속 회귀 시 비슷한 진단을 빠르게 할 수 있도록 부록 A 에 함정 기록.
- 파일명 sanitize 를 외부(yt-dlp) 에 위임하면서 `sanitize_filename` 의 엄밀한 동작 명세 (200자 제한, `download` fallback 등) 가 약간 다른 메커니즘으로 대체됨. yt-dlp 의 `windowsfilenames` 가 우리 sanitize 와 비트 단위로 같은 결과를 보장하지는 않으나, Windows 안전성은 동등.

#### 대안 검토 (Alternatives considered)

- **A. `process_ie_result` 유지하되 download 직전에 토큰만 새로 받기**: yt-dlp 의 사적 API 호출 필요. 깨지기 쉬운 길.
- **B. `extract_info(url, download=True)` 한 번 호출 — probe 없이**: NFC 정규화할 틈이 사라짐. 길 C 보다 약함.
- **C. `MetadataParserPP` 의 INTERPRET 액션으로 title NFC 강제**: 소스 검토 결과 INTERPRET 는 "info dict 의 기존 값을 정규식으로 파싱해 같거나 다른 키에 박는" 변환이지 "임의 외부 값을 info dict 에 박는" 도구가 아님. NFC 값을 외부에서 주입할 길이 없어 채택 불가.
- **D(채택). `pre_process` 단계 커스텀 PostProcessor**: yt-dlp README 가 공식적으로 권장하는 임베딩 패턴 (`ydl.add_post_processor(MyCustomPP(), when='pre_process')`). 정공법.

#### 관련 (See also)

- ADR-001 (썸네일 처리 — 후처리 체인). 본 ADR 이 그 체인의 가장 앞 단계에 `_NFCNormalizePP` 를 추가.
- 부록 A "학습된 교훈" 의 `yt-dlp` 항목 — `process_ie_result` 토큰 만료 함정과 `pre_process` 권장 패턴.

---

## 5. 부록 A. 학습된 교훈 (Lessons)

> 같은 실수를 반복하지 않기 위한 메모. `CLAUDE.md` "9. 알려진 함정" 이 영구 제약만 담는다면, 본 부록은 디버깅 사례에서 얻은 구체적 함정과 회피책을 주제별로 누적한다.

### 5.1. PowerShell · Windows 환경

- `>` 리다이렉트는 기본적으로 UTF-16 LE BOM 으로 파일을 만든다. UTF-8 이 필요하면 `Out-File -Encoding utf8` 또는 `Set-Content -Encoding utf8` 을 명시한다.
- `git diff` 가 멈추고 `:` 이 보이면 less 페이저다. `q` 로 종료, `Space` 로 한 페이지, `G` 로 끝으로 이동. 페이저 없이 보려면 `git --no-pager diff`.
- 빈 파일의 Git SHA 는 `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`.
- PowerShell `git commit -m "..."` 에서 큰따옴표 안에 큰따옴표를 넣으려고 `""` 로 이스케이프하면 빈 문자열로 해석되어 인자가 끊긴다. 큰따옴표 안에는 작은따옴표를 쓰거나, 헤더 한 줄로만 커밋하고 본문은 WORKLOG 로 빼는 게 안전하다.

### 5.2. Python · PySide6

- 타입 힌트(`self.x: dict = {}`) 는 어노테이션일 뿐, 변수를 자동 생성하지 않는 위치도 있다. `__init__` 에서 명시적으로 초기화한다.
- `QPixmap` · `QImage` 는 GUI 스레드 전용. 워커 스레드에서 만들면 표시 누락·크래시가 발생한다.
- 시그널·슬롯은 스레드를 넘을 때 `Qt.QueuedConnection` 을 명시하면 안전하다.
- `QLabel.setScaledContents(True)` 는 0×0 라벨에서 빈 화면을 만들 수 있다. 직접 `scaled()` 호출이 안전하다.
- **다크 테마 앱은 `QApplication.setStyle("Fusion")` 을 먼저 깐다.** Fusion 은 OS 와 무관하게 Qt 자체 렌더링이라 Windows / macOS 에서 일관된 룩을 준다. 체크박스·라디오버튼 같은 indicator 위젯의 체크 마크가 Qt 내부에서 그려지므로 SVG / 이미지 자산 없이도 채워진다. `QCheckBox::indicator` 를 직접 스타일링하면 ✓ 마크 렌더링이 꺼지는데, Fusion 위임은 그 함정을 피한다. (참조: 2026-05-29 `fix(ui)` Fusion 적용)


### 5.3. yt-dlp

- 2025년부터 EJS (Embedded JavaScript) 를 사용. Node.js / Deno / Bun 중 하나가 PATH 에 있어야 함. 참고: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- `info["thumbnail"]` 은 보통 정확하지만, `info["thumbnails"]` 리스트에서 직접 선별할 수도 있다. 영상에 따라 maxresdefault 가 아닌 후보가 반환될 가능성이 이론상 존재하므로, 향후 문제 재현 시 `_pick_thumbnail` 같은 안전망 도입을 검토.
- `bestvideo+bestaudio/best` 는 코덱 효율 우선이라 H.264 보다 파일이 작을 수 있다.
- `postprocess_hook` 은 ffmpeg 머지만이 아니라 **모든 후처리기** 의 started/finished 를 발사한다. `d["postprocessor"]` 값으로 단계를 구분해야 한다. 2026.3.17 기준 ADR-001 체인의 순서는 `ThumbnailsConvertor` → `Merger` → `Metadata` → `EmbedThumbnail` → `MoveFiles`. 또한 postprocess 후크에는 **퍼센트 정보가 없다** (`status` / `postprocessor` / `info_dict` / `_default_template` 4개 키만 제공). 머지·임베드 단계에 퍼센트 진행률 표시는 현 구조로 불가.
- `ExtractAudio` 로 m4a→mp3 재인코딩하면 ffmpeg 가 기본 `-map_metadata 0` 으로 원본 ftyp 박스 필드(`major_brand` 등) 를 ID3 의 TXXX 로 옮겨 박는다. MP3 에는 원리상 없어야 할 메타가 남는다. `-map_metadata -1` 로 끊을 수는 있으나 그러면 같은 ffmpeg 호출에서 FFmpegMetadataPP 가 박는 `-metadata title=…` 까지 함께 무효화되어 ID3 TIT2 가 사라진다. 선별 제거가 필요하면 `meta_<key>` info dict 주입 또는 별도 ffmpeg 호출 경로를 써야 한다.
- 기본 retry/timeout 은 짧다. 실서비스 GUI 에서는 `socket_timeout`, `retries`, `fragment_retries='infinite'`, `file_access_retries`, `retry_sleep_functions` 를 명시해 일시적 stall 을 내부에서 흡수시켜야 한다.
- HLS 는 `total_bytes` / `total_bytes_estimate` 가 둘 다 없어 yt-dlp 내부 ETA 산식 (`(total - downloaded) / speed`) 이 성립하지 않는다. 진행률은 프래그먼트 기준으로 별도 산정돼 정상 표시되지만 ETA 만 공란·placeholder 가 된다. 우리는 `_eta_str` placeholder 감지 + `pct` × `elapsed` 추정으로 우회 (`~M:SS` 표기).
- **`ydl.download([url])` 은 내부에서 `extract_info` 를 다시 돌린다.** 우리가 호출 전에 가공한 info dict 가 있어도 무시되고 원본 NFD 메타가 그대로 후처리 체인에 흘러간다. 사전 정규화한 dict 를 유지하려면 `ydl.process_ie_result(info, download=True)` 를 써야 한다. yt-dlp 내부에서도 광범위하게 쓰이는 경로라 안정적.
- **`FFmpegMetadataPP` 는 info dict 의 `title` / `artist` / `description` 등을 직접 읽어 `-metadata` 인자로 변환한다.** 즉 메타 내용을 통제하려면 ffmpeg 인자를 우회로 박는 것보다 info dict 자체를 정규화한 뒤 `process_ie_result` 로 흘리는 것이 단순하고 견고하다. 사용자 정의 키는 `meta_<name>` 또는 `meta_<idx>_<name>` 형태로 info dict 에 박으면 우선 적용된다.
- **`process_ie_result(probed, download=True)` 우회는 YouTube 에서 깨질 수 있다.** probe 단계에서 받은 format URL 의 nsig/sig 토큰이 download 시점에 만료된 상태로 사용되어 `HTTP Error 403: Forbidden` 이 난다. CLI 단독 호출과 `ydl.download([url])` 은 같은 환경에서 정상이지만 `process_ie_result` 경로만 실패하는 비대칭으로 진단. 다른 사이트(SoundCloud 등) 에서는 토큰 정책이 느슨해 같은 패턴이 동작하지만, YouTube 처럼 엄격한 사이트에선 깨진다. NFC 정규화·메타 가공 같은 사전 처리는 **`pre_process` 단계의 커스텀 PostProcessor 로 옮기는 것이 정공법** (아래 항목 참조). 위 두 줄("`ydl.download([url])` 은 내부에서 `extract_info` 를 다시 돌린다…", "`FFmpegMetadataPP` 는 info dict 의 `title` / `artist` …") 은 그 시점에 진실이었고 본 항목과 함께 읽으면 시간순 학습 경로가 됨. (출처: 2026-05-28 ADR-004)
- **`pre_process` PostProcessor 가 info dict 사전 가공의 정공법.** yt-dlp README 의 임베딩 예시 그대로: `ydl.add_post_processor(MyCustomPP(), when="pre_process")`. `pre_process` 는 "after video extraction" — `extract_info` 직후, 파일명 결정·다운로드·일반 후처리 모두에 앞섬. NFC 정규화, `meta_<key>` 사전 주입, 사용자 정의 메타 가공은 이 단계에서 일어나는 것이 가장 깨끗. info dict 의 기존 키를 임의 외부 값으로 바꿔야 하는 작업은 `MetadataParserPP` 의 INTERPRET 액션으로는 불가 (INTERPRET 는 info dict 의 기존 값을 정규식으로 재해석할 뿐) — 커스텀 PP 가 정답. (출처: 2026-05-28 ADR-004)
- **yt-dlp 병렬 다운로드 제한**: yt-dlp 는 단일 프로세스 내 병렬 다운로드를 공식 지원하지 않는다. 사실상 안전 구간은 1~3개, 상한은 약 5개. 슬라이더·SpinBox 등 UI 에서 더 큰 값을 허용하더라도 위험 구간(노랑·빨강) 을 시각적으로 명시해야 사용자가 IP 차단·rate limit 위험을 인지할 수 있다. metube 기본값 3, youtube-dl-gui 한 자리 수가 업계 관행. (출처: 2026-05-27 동시 다운로드 수 UI 논의)

### 5.4. 유니코드·파일명

- 유니코드 정규화는 **클라우드·OS·소스 사이트 경계에서 깨진다**. SoundCloud 의 한글 메타는 NFD(자모 분리, U+1100~U+11FF) 로 들어오는 경우가 있다. macOS 경유 클라우드 동기화도 마찬가지. 우리 앱은 **info dict 진입 지점에서 NFC 로 통일**하는 것을 원칙으로 한다 (`unicodedata.normalize('NFC', ...)`).
- **콘솔 렌더링은 NFD 를 NFC 처럼 그려낼 수 있다.** `chcp 65001` 로 cmd.exe 를 UTF-8 로 바꾸면 한글이 멀쩡히 "기쁨" 으로 보이지만, 실제로는 `ㄱ + ㅣ + ㅃ + ㅡ + ㅁ` 5개 jamo 일 수 있다. 진단할 때는 ffprobe 출력 모양에 속지 말고 실제 코드포인트를 봐야 한다 (`python -c "import sys; print([hex(ord(c)) for c in open(sys.argv[1]).read()])"` 또는 ID3 값을 파일로 떠서 hex dump).
- ID3v2.3 의 텍스트 인코딩은 UTF-16 (BOM 포함) 이 호환성 가장 높다. yt-dlp + ffmpeg 기본 동작이 이를 따르므로 우리는 별도 옵션을 줄 필요 없으나, 값으로 넘어가는 문자열은 NFC 여야 한다.
- **ffprobe JSON 출력 자체도 NFD 를 NFC 처럼 보여줄 수 있다.** `chcp 65001` + ffprobe JSON 으로 한글이 깨끗하게 보이더라도, 콘솔 폰트의 자모 결합 렌더링 결과일 뿐 데이터는 NFD 일 수 있다. 2026-05-18 디버깅 중 이 함정에 두 번 빠졌다. **NFC/NFD 판정은 반드시 파일 원본 바이트에서**: m4a 는 `©nam` atom 의 데이터 영역, mp3 는 `TIT2` 프레임의 텍스트 영역을 직접 hex 로 봐야 한다. NFC 한글 한 글자는 UTF-8 3바이트(`0xea·0xeb·0xec` 시작), NFD 는 자모별 3바이트씩 2~3개(`0xe1 0x84 …` 패턴) 다.
- **표시 레이어는 모두 정직하지 않다.** Windows 탐색기 속성창은 NFD 를 분리해서 보여주고(정직), VS Code 터미널은 결합해서 그리고(NFC 처럼 보임), ffprobe JSON 도 결합해서 그린다. 같은 데이터가 어디서는 깨져 보이고 어디서는 멀쩡해 보이는 게 정상이다. 표시 어긋남으로 데이터를 추론하지 말 것.

### 5.5. Git

- `.gitignore` 는 **이미 추적 중인 파일에는 영향 없음**. 빼려면 `git rm --cached <path>`.
- 의미 단위로 커밋을 나누려면 `git add -p` 로 hunk 단위 스테이징.
- Conventional Commits 권장: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`. 참고: https://www.conventionalcommits.org/

### 5.6. 협업 · 커뮤니케이션

- **용어가 같다고 대상도 같지는 않다.** "썸네일" 처럼 일상어가 두 개 이상의 기술 객체를 가리킬 때, 먼저 어느 대상인지 확정한다.
- 진단 코드(print, 임시 파일 저장) 는 가설 검증 후 즉시 제거하고 커밋에 섞지 않는다.
- 가설은 한 번에 하나씩 검증한다. 동시에 여러 패치를 적용하면 원인 추적이 어려워진다.
- **단일 질문 원칙(다이얼로그 설계)**: 확인 다이얼로그는 "하나의 질문 + 부가 옵션(체크박스)" 구조가 사용자 인지 부담이 가장 낮다. 두 개의 결정을 Yes/No 로 강제 묶으면 사용자가 "예" 의 의미를 매번 재해석해야 한다. (출처: 2026-05-27 "삭제·취소 확인 다이얼로그 통일" 작업)
- **버튼 라벨은 동작을 진실하게 묘사해야 한다**: "전체 취소" 라는 라벨이 실제로는 "진행 중인 다운로드만 취소" 였기 때문에 사용자가 "목록 전체 삭제" 로 오해. 라벨과 동작이 어긋나면 UX 부채가 누적되므로, 새 동작을 추가하기 전에 라벨부터 재검토할 것. (출처: 2026-05-27 "전체 취소 → 목록 비우기" 리네이밍)
