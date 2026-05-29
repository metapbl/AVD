# AV_Downloader 작업 로그

> 이 문서는 AV_Downloader 의 진행 중 작업·로드맵·결정 인덱스를 추적합니다.
> 프로젝트의 변하지 않는 정보(기술 스택·폴더 구조·코딩 컨벤션 등)는 `CLAUDE.md`, 시간 역순 변경 이력은 `CHANGELOG.md`, ADR 본문은 `ADR.md`, 학습된 교훈 본문은 `LESSONS.md` 가 담당합니다.

## 문서 구조

이 파일은 다섯 섹션으로 구성됩니다.

- **1 빠른 안내** — 새 세션 시작·갱신 규칙
- **2 Changelog 안내** — 본문은 `CHANGELOG.md`
- **3 현재와 다음** — 진행 중 작업과 단기·중기·장기 로드맵
- **4 ADR 인덱스** — 본문은 `ADR.md`
- **5 학습된 교훈 인덱스** — 본문은 `LESSONS.md`

각 섹션은 서로 다른 시간 척도를 가집니다. `CHANGELOG.md` 는 append-only 누적, 섹션 3 은 유동적이며 완료 시 즉시 삭제(✅ 마커 남기지 않음), 섹션 4·5 는 인덱스만 갱신하고 본문은 각각 `ADR.md` / `LESSONS.md` 에 추가합니다.

---

## 1. 빠른 안내

### 1.1. 새 세션 시작 방법

`CLAUDE.md` 의 "11. 새 세션 시작 방법" 섹션을 따른다. 기본 로딩은 `CLAUDE.md` + `WORKLOG.md` 두 파일, 특정 ADR / 교훈 후속 작업 시 `ADR.md` / `LESSONS.md` 의 raw URL 을 추가로 전달한다.

### 1.2. 작업 완료 시 갱신 규칙

- 의미 단위가 끝나 커밋이 발생하면 → `CHANGELOG.md` 의 맨 위에 항목 추가
- 큰 결정(아키텍처·중대 버그 해결)이 있으면 → `ADR.md` 에 새 ADR 본문 추가 + 본 파일 섹션 4 인덱스 한 줄 추가
- 디버깅에서 얻은 교훈이 있으면 → `LESSONS.md` 의 해당 그룹에 추가 + 본 파일 섹션 5 인덱스의 한 줄 요약 갱신
- 새 할 일이 생기면 → 섹션 3 의 적절한 위치에 추가
- 섹션 3 의 항목이 완료되면 → `CHANGELOG.md` 의 해당 커밋 항목에 흡수하고 섹션 3 에서는 즉시 삭제

---

## 2. Changelog

시간 역순 변경 이력은 별도 파일 `CHANGELOG.md` 에서 관리합니다. 새 항목은 그쪽에 추가하십시오.

이 문서(WORKLOG) 는 "지금 무엇을 하고 있고, 왜 그렇게 하기로 했는가" 에, CHANGELOG 는 "무엇이 바뀌었는가" 에 집중합니다.

---

## 3. 현재와 다음

> 진행 중인 작업과 앞으로 할 작업을 적습니다. 완료되면 위 Changelog 로 옮기고 이 섹션에서는 즉시 삭제합니다.

### 3.1. 진행 중 (In Progress)

*현재 없음.*

### 3.2. 단기 (Short-term, 1~2 세션 내)

- **체크박스 시각 개선 (체크 시 ✓ 마크가 보이도록)**
    - 위치: `ui/preferences_dialog.py`, `ui/confirm_remove_dialog.py` 의 `QCheckBox` 들.
    - 진단 (2026-05-28): 두 다이얼로그 스타일시트는 `QCheckBox::indicator` 미손, 라벨 색·폰트만 지정. `main.py` 도 `setStyle`/`setPalette`/`setStyleSheet` 호출 없음 → OS 기본 (Windows 11 Style) 렌더. ✓ 가 직관적이지 않은 이유는 다이얼로그 다크 배경(`#2b2b2b`) 과 OS 라이트 톤 indicator 의 부조화로 추정.
    - 정책: 1단계 — 두 다이얼로그 스타일시트의 `QCheckBox::indicator` 에 `width`/`height` 만 18×18 로 키움, 색·배경 미손. 2단계 (부족 시) — `main.py` 에서 `QApplication.setStyle("Fusion")`. Fusion 은 OS 무관 일관 렌더, 다크 팔레트 친화. macOS 호환성 과제와 시너지. 라디오 버튼은 코드베이스 부재 (확인됨).

- **메타 행에 코덱·포맷·비트레이트 추가**
    - 위치: `ui/download_item_widget.py` `lbl_meta`, `core/info_fetcher.py` `FormatInfo`, `ui/format_select_dialog.py`, `ui/main_window.py` `_on_format_selected`.
    - 표시: `"업로더 • 재생시간"` → `"업로더 • 재생시간 • H.264 MP4 • AAC 192kbps"`. 오디오 전용: `"아티스트 • 3:42 • MP3 320kbps"`.
    - `FormatInfo` 에 `vcodec`/`acodec`/`abr`/`tbr` 필드 추가 (yt-dlp raw dict 그대로).
    - 갱신 시점: 위젯 생성 직후엔 업로더·재생시간만, `_on_format_selected` 직후 코덱·비트레이트 채워 메타 라벨 재갱신.
    - 통합 포맷 (`bestvideo+bestaudio/best`) 정책: 선택 시점에 코덱 미확정 → 빈 값 또는 `"자동"`. ffprobe 호출 같은 추가 비용 미도입.
    - 코덱 표기 정규화: yt-dlp `vcodec` 의 `"avc1.640028"` raw 문자열 → 사람 친화 이름(`H.264`, `VP9`, `AV1`, `AAC`, `Opus`, `MP3`) 매핑 헬퍼.

- **macOS 지원 정식화 (실행 환경만)**
    - 동기: 사용자가 Windows 에서 개발, macOS 에서는 실행만. README/CLAUDE 의 "Windows 우선, macOS 일부 미동작" 정책을 "Windows 개발 / macOS 실행 양쪽 정식 지원" 으로 격상.
    - 진단 (2026-05-28): `utils/file_utils.py` `open_folder()` 의 `subprocess.run(["explorer", ...])` 가 Windows 전용 → macOS 에서 "📂 열기" 깨짐. `main.py` 의 `QFont("맑은 고딕", 10)` 은 macOS 폴백. yt-dlp·ffmpeg·Node.js 는 Homebrew 로 정식 지원. `windowsfilenames: True` 는 macOS 에서도 동작 (보수적 정책 유지).
    - 정책:
        1. `open_folder()` 플랫폼 분기. `sys.platform` 으로 `"win32"`/`"darwin"`/기타 갈래. macOS: `open -R <path>` (파일 선택) / `open <path>` (폴더). Linux: `xdg-open <path>`.
        2. `main.py` 폰트 fallback 체인: `QFont("맑은 고딕, Apple SD Gothic Neo, sans-serif", 10)`.
        3. README 의 운영체제 단서 제거, macOS 실행 가이드 (`brew install ffmpeg node`) 한 줄 추가.
        4. CLAUDE.md "5. 개발 환경", "8.4. 터미널 명령" 미수정 — 개발은 Windows + PowerShell 유지.
    - 검증: Windows 수정 → push → macOS pull → `python main.py` → 📂 열기·한글 폰트·다운로드 확인.
    - 보류: NFC vs APFS NFD (실측 후 필요 시), `.gitattributes` (단일 OS 작업이라 불필요).

### 3.3. 중기 (Mid-term, 다음 마일스톤)

- **포맷 선택 UX 개선** — "최고 화질 (자동·효율 우선)" 과 "최고 호환 (MP4/H.264)" 분리. 더불어 사용자가 비디오·오디오 컨테이너 (mp4/webm/mkv, mp3/m4a/opus 등) 를 직접 고를 수 있도록 다이얼로그 확장. ADR-002 의 결정과 함께 진행.

### 3.4. 장기 (Long-term, 백로그)

- **자동 업데이트 검증** — `utils/updater.py` 가 yt-dlp 신버전 감지 시 안전 갱신 확인.
- **다국어 지원** — i18n 도입 (한국어·영어 기본).
- **플레이리스트 일괄 다운로드** — 한 URL 로 N 개 항목 추가.
- **테마·스타일 옵션** — 라이트·다크·시스템 자동 전환.

---

## 4. ADR 인덱스

> 본문은 `ADR.md`. 항목 한 줄로 결정의 핵심을 알 수 있도록 요약하고, 펼침이 필요할 때만 raw URL 로 본문 로딩.

- **ADR-001** 썸네일 처리 — UI 미리보기와 파일 임베드의 분리 (Accepted, 2026-05-17) — UI 미리보기는 PySide6 GUI 스레드 전용, 파일 임베드는 yt-dlp/FFmpeg postprocessor 체인. 두 대상을 코드·문서·대화에서 명시 분리. → [ADR.md#adr-001](./ADR.md#adr-001)
- **ADR-002** 포맷 선택 — "최고 화질" 의미 분리 (Proposed, TBD) — `bestvideo+bestaudio/best` 의 VP9/AV1 우선이 사용자 기대(H.264 1080p) 와 어긋날 수 있어 "자동·효율 우선" 과 "최고 호환 MP4/H.264" 분리 검토. → [ADR.md#adr-002](./ADR.md#adr-002)
- **ADR-003** 다운로드 워커 오케스트레이션을 `DownloadManager` 로 분리 (Accepted, 2026-05-28) — `MainWindow` 의 다섯 책임 중 ③ 만 `controllers/` 로 떼어냄. 진행 시그널은 워커→위젯 직결, 라이프사이클만 매니저 경유. 큐는 `items` dict 삽입 순서. → [ADR.md#adr-003](./ADR.md#adr-003)
- **ADR-004** `process_ie_result` 우회 폐기, NFC 보존을 PostProcessor 정공법으로 (Accepted, 2026-05-28) — YouTube 토큰 만료 회귀(403) 해결. `ydl.download([url])` 복귀 + `_NFCNormalizePP(when="pre_process")`. `js_runtimes`/`remote_components` 고정 제거. 2026-05-18 결정 부분 번복. → [ADR.md#adr-004](./ADR.md#adr-004)

---

## 5. 학습된 교훈 인덱스

> 본문은 `LESSONS.md`. 그룹 단위로 무엇이 들어 있는지 한눈에 보고, 펼침이 필요할 때만 본문 로딩. `[역사적]` 표시는 시간순 번복 항목.

### 5.1. PowerShell · Windows 환경 → [LESSONS.md#lessons-powershell](./LESSONS.md#lessons-powershell)

- `>` 리다이렉트의 UTF-16 LE BOM 함정, `Out-File -Encoding utf8` 대안
- `git diff` less 페이저 탈출, `--no-pager` 옵션
- 빈 파일 Git SHA
- 큰따옴표 안 큰따옴표 이스케이프 함정

### 5.2. Python · PySide6 → [LESSONS.md#lessons-pyside6](./LESSONS.md#lessons-pyside6)

- 타입 힌트는 변수 자동 생성 아님, `__init__` 명시 초기화
- `QPixmap`/`QImage` GUI 스레드 전용
- 스레드 횡단 시그널의 `Qt.QueuedConnection`
- `setScaledContents(True)` + 0×0 라벨 함정
- 다크 테마는 `setStyle("Fusion")` 우선 — indicator ✓ 렌더링 보장

### 5.3. yt-dlp → [LESSONS.md#lessons-yt-dlp](./LESSONS.md#lessons-yt-dlp)

- EJS 의존 (Node.js/Deno/Bun), node 고정 금지
- `info["thumbnail"]` vs `info["thumbnails"]` 배열, `_pick_thumbnail` 안전망
- `bestvideo+bestaudio/best` 의 코덱 효율 우선 함정 (ADR-002)
- `postprocess_hook` 의 단계 구분, 퍼센트 키 부재
- `ExtractAudio` 의 ftyp 박스 잔재 메타와 `-map_metadata -1` 부작용
- retry/timeout 명시 필요
- HLS 의 `total_bytes` 부재 → ETA 우회
- **`pre_process` 커스텀 PostProcessor 가 정공법** ← 현 권장 (ADR-004)
- `FFmpegMetadataPP` 의 info dict 직접 참조
- 단일 프로세스 병렬 다운로드 미지원, 안전 1~3개
- [역사적] `ydl.download([url])` 의 `extract_info` 재실행 함정 → 폐기
- [역사적] `process_ie_result` 우회의 YouTube 토큰 만료 → 폐기 (ADR-004)

### 5.4. 유니코드 · 파일명 → [LESSONS.md#lessons-unicode](./LESSONS.md#lessons-unicode)

- 클라우드·OS·소스 사이트 경계의 NFD 침투, info dict 진입 NFC 통일
- 콘솔/터미널/ffprobe JSON 의 결합 렌더링 — 판정은 파일 원본 바이트로
- 표시 레이어의 비정직성 (탐색기 분리 / VS Code 결합)
- ID3v2.3 의 UTF-16 BOM 기본, 값은 NFC 여야 함

### 5.5. Git → [LESSONS.md#lessons-git](./LESSONS.md#lessons-git)

- `.gitignore` 는 이미 추적 파일에 무효, `git rm --cached`
- `git add -p` 의 hunk 단위 스테이징
- Conventional Commits 약속
- `--amend` 후 push 거부 = 형제 분기 신호, `git log --graph --all` 우선

### 5.6. 협업 · 커뮤니케이션 → [LESSONS.md#lessons-collab](./LESSONS.md#lessons-collab)

- 용어가 같다고 대상도 같지 않다 (ADR-001)
- 진단 코드 즉시 제거, 커밋 비혼입
- 가설은 하나씩 검증
- 단일 질문 원칙 (다이얼로그)
- 버튼 라벨은 동작을 진실하게 묘사
