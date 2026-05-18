# AV_Downloader 작업 로그

> 이 문서는 AV_Downloader 의 작업 진척, 결정 사항, 잔여 과제를 추적합니다.
> 프로젝트의 변하지 않는 정보(기술 스택·폴더 구조·코딩 컨벤션 등)는 `CLAUDE.md` 에 별도로 관리하며, 이 파일은 시간과 함께 자라는 정보만 담습니다.

**최종 업데이트**: 2026-05-18

---

## 문서 구조

이 파일은 네 섹션으로 구성됩니다.

- **섹션 1 — 빠른 안내**: 새 세션 시작 시 어떻게 이 문서를 활용할지.
- **섹션 2 — Changelog**: 시간 역순으로 모든 의미 있는 변경 사항을 누적.
- **섹션 3 — 현재와 다음**: 진행 중인 작업과 단기·중기·장기 로드맵.
- **섹션 4 — ADR (결정 기록)**: 아키텍처·중대 버그 해결 등 큰 결정의 맥락과 결과.

각 섹션은 서로 다른 시간 척도를 가집니다. 섹션 2 는 한 번 적은 줄을 절대 지우지 않고 누적됩니다. 섹션 3 은 유동적이며 항목이 완료되면 섹션 2 로 옮깁니다. 섹션 4 는 큰 결정이 있을 때만 새 항목이 추가됩니다.

---

## 1. 빠른 안내

### 1.1. 새 세션 시작 방법

`CLAUDE.md` 의 "새 세션 시작 방법" 섹션을 따른다. 환경별(claude.ai 웹 채팅 / Claude Code) 절차가 거기에 정리되어 있다.

### 1.2. 작업 완료 시 갱신 규칙

- 의미 단위가 끝나 커밋이 발생하면 → 섹션 2 (Changelog) 의 맨 위에 한 줄 추가
- 큰 결정(아키텍처·중대 버그 해결)이 있으면 → 섹션 4 (ADR) 에 새 항목 추가
- 새 할 일이 생기면 → 섹션 3 (현재와 다음) 의 적절한 위치에 추가
- 섹션 3 의 항목이 완료되면 → 섹션 2 로 이동하며 섹션 3 에서는 제거 또는 ✅ 표시

---

## 2. Changelog (시간 역순)

> [Keep a Changelog](https://keepachangelog.com/) 형식을 참고하여, 최신 변경이 위로 오도록 누적. 한 번 적은 줄은 절대 지우지 않음.

### 2026-05-18

- **`fix(downloader)`**: NFC 메타데이터를 yt-dlp 의 정상 경로로 흘려보내는 구조로 재구성.
  - `core/downloader.py`: 본 다운로드 호출을 `ydl.download([url])` 에서 `ydl.process_ie_result(probed, download=True)` 로 교체. yt-dlp 의 `FFmpegMetadataPP` 가 info dict 의 `title`/`artist` 를 그대로 `-metadata` 인자로 변환하므로, 재추출 없이 우리 NFC dict 를 그대로 후처리 체인에 넘기면 NFC 가 보장된다
  - `core/downloader.py`: mp3 분기에서 `-map_metadata -1` 제거. 이 옵션이 m4a ftyp 잔재(`major_brand` 등) 를 끊는 본래 목적은 달성했으나, FFmpegMetadataPP 가 같은 ffmpeg 호출에서 박는 `-metadata title=…` 까지 함께 무효화해 ID3 TIT2 가 통째로 사라지는 부작용이 확인됨. NFC title 보존이 우선이므로 제거. major_brand 잔재는 무해한 메타 노이즈로 수용
  - 검증: m4a 의 `©nam` atom, mp3 의 TIT2 프레임 모두 NFC UTF-8 (`0xea·0xeb·0xec` 계열) / UTF-16 LE (`0x45 0xc5` 계열) 단일 코드포인트로 박힘. 자모 분리(`0xe1 0x84`) 흔적 없음
  - 관련: 부록 A "학습된 교훈" 의 `yt-dlp` / `유니코드·파일명` 항목 갱신

- **`fix(downloader)`**: 모든 오디오 추출에 NFC 메타 우회로 확장 (중간 단계, 후속 패치로 대체됨).
  - `if ext == "mp3"` 조건을 `if is_audio` 로 넓혀 m4a/wav/aac 에서도 `-metadata title=NFC값` 강제 주입을 시도. mp3 는 우연히 동작했으나 m4a 는 ffmpeg 호출 단계 분리로 인해 미적용. 이후 `process_ie_result` 경로로 근본 해결됨

- **`fix(downloader)`**: 유니코드 NFC 정규화 + MP3 컨테이너 잔재 메타 제거 1차 시도.
  - `utils/file_utils.py`: `normalize_unicode`, `normalize_info_dict` 헬퍼 추가. `sanitize_filename` 도입부에서도 NFC 적용
  - `core/info_fetcher.py`: `extract_info` 직후 info dict 전체에 NFC 적용
  - `core/downloader.py`: 사전 `extract_info(download=False)` 호출 → NFC 화 → `outtmpl` 의 title 자리를 NFC 고정 문자열로 박음. mp3 한정 `-map_metadata -1` + `-metadata title=…` 우회로 도입 (이후 `process_ie_result` 로 대체)

- **`docs(claude)`**: 코드 제시 규칙을 변경 규모 기준으로 재정의 + 터미널 명령 동반 제시 규칙 신설 + VS Code 통합 터미널 명시.

- **`docs(worklog)`**: 사이드 메모 세 건(파일명·ID3 NFC 정규화 / MP3 major_brand 잔재 / Read timed out 회복력) 단기 섹션에 기록. 학습된 교훈에 `yt-dlp` / `유니코드·파일명` 카테고리 추가.

### 2026-05-17

- **`docs(claude)`**: "새 세션 시작 방법" 섹션을 환경별 안내로 개정.
  - claude.ai 웹 채팅 / Claude Code 두 환경 분리
  - 웹 채팅에서는 본문 통째 붙여넣기 대신 GitHub raw URL 던지는 방식 채택 (Claude 가 `crawler` 로 직접 가져옴 — 진짜 HEAD 반영)
  - 로컬 미푸시 변경분 환기 규칙 명문화

- **`fix(ui)`**: 다운로드 진행률을 "N.N% 다운로드 중" 형식으로 상태 라벨에 표시.
  - `workers/download_worker.py`: postprocess 후크에서 `Merger` 후처리기만 머지로 인식하도록 좁힘. 기존엔 `ThumbnailsConvertor` 등 모든 후처리기의 `started`에서 `merging` 시그널이 발사되어, 영상 스트림 종료 직후 라벨이 "병합 중"으로 잠기고 오디오 스트림 다운로드 동안에도 그대로 고정되는 UX 버그가 있었음
  - `workers/download_worker.py`: `_output_path` 갱신을 모든 후처리기의 `finished`에서 수행하도록 변경. 체인 마지막 단계(`MoveFiles`)의 최종 경로를 반영
  - `ui/download_item_widget.py`: `update_progress` 가드 추가 — 상태가 `DOWNLOADING`일 때만 상태 라벨을 "N.N% 다운로드 중"으로 갱신
  - `ui/download_item_widget.py`: `update_status` 가 `self.item.status` 를 단일 출처로 갱신하도록 정리. `MERGING` 분기를 "병합 중" 라벨로 통일하고 ETA 자리에 박던 "병합 중..." 표기 제거
  - 진단으로 확인된 후처리 체인 순서: `ThumbnailsConvertor` → `Merger` → `Metadata` → `EmbedThumbnail` → `MoveFiles` (yt-dlp 2026.3.17 기준)

- **`docs(claude)`**: 코드 제시 규칙에 300줄 기준과 변경 지점 명시 규칙 추가.
  - 약 300줄 미만 파일은 통째로 제시, 그 이상은 함수 단위 부분 발췌
  - 파일 전체를 보낼 때는 코드 블록 바깥에 변경 지점을 한 문장으로 명시

- **`fix(utils)`**: `format_duration` float/None 안전 처리 + `strip_ansi` 헬퍼 추가.

- **`fix(ui)`**: yt-dlp 진행률 메시지의 ANSI 컬러 코드 제거.

- **`docs(claude)`**: Claude 협업 규약 3줄 추가 (소스 코드 참조 / 코드 들여쓰기 / 코드 제시 전 확인).

- **`feat(downloader)`**: 다운로드 파일에 썸네일·메타데이터 임베드 추가.
  - `EmbedThumbnail`, `FFmpegMetadata`, `FFmpegThumbnailsConvertor` (webp→jpg) 후처리기 체인 추가
  - `writethumbnail`, `embedthumbnail` 플래그 활성화
  - MP3 의 경우 `-id3v2_version 3 -write_id3v1 1` 강제 (Windows 탐색기·구형 음악 플레이어 호환)
  - 관련: ADR-001

- **`fix(ui)`**: 워커 라이프사이클, 스레드 안전성, 취소 가드 정비.
  - 썸네일 워커: QPixmap 생성을 워커 스레드 → GUI 스레드로 이동, raw bytes 만 시그널로 전달
  - `ThumbnailWorker` 시그니처에 `item_id` 추가 — 늦은 시그널이 엉뚱한 위젯에 꽂히는 사고 방지
  - `_thumb_workers` 를 list → dict 로 전환, `cancel()` 메서드 추가
  - `_on_cancel_all`: 활성 워커 사전 체크 + 확인 다이얼로그 (실수 방지)
  - `DownloadWorker`: 취소 예외를 문자열 매칭 대신 `isinstance(DownloadCancelled)` 로 판정
  - 관련: ADR-001

- **`chore`**: `.vscode/` 를 `.gitignore` 에 추가.
  - VS Code 워크스페이스 설정이 레포로 들어가는 것을 방지

- **`docs`**: 작업 로그 시스템을 Keep a Changelog + ADR 형식으로 재구조화.
  - `CLAUDE.md` 신규 작성 — 변하지 않는 프로젝트 컨텍스트
  - `WORKLOG.md` 재구조화 — Changelog 와 ADR 분리
  - 협업 모델을 Opus 4.7 단일 체계로 명시 (2026-05-17 부)

- **`docs`**: Node.js 요구사항을 README 에 명시 (yt-dlp EJS 메커니즘 설명).

- **`chore`**: 레포 URL 수정, README 본격 작성, `requirements.txt` UTF-8 정상화.
  - `utils/updater.py` 의 `GITHUB_REPO` 플레이스홀더를 `ggoyong2-ctrl/AV_Downloader` 로
  - PowerShell `>` 리다이렉션이 UTF-16 LE BOM 으로 만든 `requirements.txt` 를 UTF-8 로 재작성

- **`feat`**: 최초 푸시 (Initial commit: yt-dlp based media downloader).
  - 초기 골격은 Claude Sonnet 4.6 작업
  - `config.json` 은 gitignore 처리 (사용자별 개인 경로 포함)

---

## 3. 현재 및 다음 작업 (Current & Next)

> 진행 중인 작업과 앞으로 할 작업을 적습니다. 완료되면 위 **Changelog**로 옮기고 이 섹션에서는 삭제합니다.

### 🔵 진행 중 (In Progress)

*현재 없음.*

### 🟡 단기 (Short‑term, 1~2 세션 내)

- [x] **테스트 영상 다양화 검증** ✅ (2026-05-17 완료, ffprobe로 1·2·3 모두 확인)
  - 커스텀 썸네일이 있는 영상으로 임베드 정상 동작 확인
  - 4K/8K 영상에서 `bestvideo+bestaudio` 동작 확인 (VP9/AV1 코덱)
  - MP3 추출 시 ID3v2.3 태그가 Windows 탐색기에서 정상 표시되는지 확인
- [x] **파일명·ID3 태그 유니코드 NFC 정규화** ✅ (2026-05-18 완료, `process_ie_result` 경로로 m4a/mp3 양쪽 데이터 NFC 확정)
- [ ] **`_pick_thumbnail` 흔적 정리**
  - `core/info_fetcher.py`에서 의미 없는 공백/정렬 변경분 검토 후 정리 커밋
- [ ] **README.md 업데이트**
  - CLAUDE.md 존재 및 사용법 한 줄 추가
  - WORKLOG.md 구조 변경 사실 한 줄 추가
- [ ] **다운로드 항목 메타데이터 표시 결손**
  - 파일 크기, 해상도, 비디오 코덱/포맷, 오디오 코덱/비트레이트 등이 UI에 표시되지 않음
  - `DownloadWorker.file_size` 시그널은 정의돼 있으나 위젯 슬롯 연결이 없을 가능성 — `main_window.py` 라우팅 확인 필요
  - 해상도/코덱/비트레이트는 `FormatInfo` 에 있을 가능성이 높으나 위젯이 받지 않음 — 데이터 흐름 설계 필요
  - 발견: 2026-05-17 검증 중
- [ ] **영상 길이가 항상 `0:00` 으로 표시되는 버그**
  - `DownloadItemWidget._build_ui()` 에서 `format_duration(self.item.duration)` 을 라벨에 박는데, 위젯 생성 시점엔 `item.duration` 이 아직 0 (InfoWorker 완료 전)
  - `_on_info_fetched` 에서 `item.duration` 은 갱신되나, `lbl_meta` 라벨 텍스트를 다시 갱신하는 경로가 없음
  - 해결책 후보: `update_title` 과 같은 패턴의 `update_meta(uploader, duration)` 메서드 추가
  - 발견: 2026-05-17 (사용자 지적 — "그전부터의 구조였습니다")
- [ ] **MP3 컨테이너 잔재 메타의 *선별적* 제거 (`major_brand` 등)**
  - 1차 시도(`-map_metadata -1`) 는 ID3 TIT2 까지 함께 날리는 부작용으로 철회됨
  - FFmpegMetadataPP 의 `meta_<key>` info dict 주입 경로 또는 후처리 후 별도 ffmpeg 호출로 `major_brand` / `minor_version` / `compatible_brands` 세 키만 표적 제거
  - 우선순위 낮음 (잔재는 디코더 동작에 무해, ffprobe 에서만 보이는 메타 노이즈)
  - 발견: 2026-05-18
- [ ] **SoundCloud 출처의 `comment` 가 트랙 URL 로 자동 채워짐**
  - yt-dlp 의 `FFmpegMetadataPP` 가 `webpage_url` 을 `comment` 로 매핑. 원본 트랙 설명을 잃음
  - `parse_metadata` 또는 `info["comment"]` 사전 주입으로 회피 가능
  - 우선순위 낮음
  - 발견: 2026-05-18 (NFC 검증 중 부수 발견)
- [ ] **`Read timed out` 회복력 — yt-dlp 재시도/타임아웃 옵션 강화**
  - 증상: 응답 지연이 누적되면 작업이 에러로 취소됨. 재시도하면 통과하기도 함 (일시적 네트워크 stall)
  - 원인 가설: yt-dlp 기본 `socket_timeout` 이 짧고(20s), `retries`/`fragment_retries`/`file_access_retries` 를 우리 쪽에서 명시하지 않아 한 번의 stall 이 `urllib3.ReadTimeoutError → DownloadError` 로 그대로 전파됨 (yt-dlp #15833, #14571 동일 증상)
  - 처방: `workers/download_worker.py` 의 ydl_opts 에 추가:
    - `socket_timeout=30`
    - `retries=10`
    - `fragment_retries='infinite'`
    - `file_access_retries=5`
    - `retry_sleep_functions={'http': lambda n: min(2**n, 30), 'fragment': lambda n: min(2**n, 30)}`
  - 발견: 2026-05-17 (사용자 사이드 메모)

### 🟢 중기 (Mid‑term, 다음 마일스톤)

- [ ] **취소 시 부분 파일 정리**
  - `_on_cancel`/`_on_cancel_all` 에서 .part, .ytdl 임시 파일 자동 삭제
- [ ] **네트워크 재시도 로직**
  - `workers/download_worker.py` 에서 일시적 오류(타임아웃, 503 등)는 N회 자동 재시도
- [ ] **포맷 선택 UX 개선**
  - "최고 화질 (자동)"과 "최고 호환 (MP4/H.264)" 분리 (ADR‑002 후보)
- [ ] **다운로드 큐 동시성 제어**
  - 동시 다운로드 N개 제한 설정 (Preferences 항목 추가)

### 🟣 장기 (Long‑term, 백로그)

- [ ] **자동 업데이트 검증**
  - `utils/updater.py` 가 yt‑dlp 신버전 감지 시 안전하게 갱신하는지 확인
- [ ] **다국어 지원**
  - i18n 도입 (한국어/영어 기본)
- [ ] **플레이리스트 일괄 다운로드**
  - 한 URL로 N개 항목 추가
- [ ] **테마/스타일 옵션**
  - 라이트/다크/시스템 자동 전환

---

## 4. 아키텍처 결정 기록 (ADR)

> 중요한 설계 결정을 한 항목씩 기록합니다. 한번 작성된 ADR은 **수정하지 않고** 새 ADR로 대체합니다 (Superseded 표시).
> 참고: [ADR — Architectural Decision Records](https://adr.github.io/)

### ADR‑001: 썸네일 처리 — UI 미리보기와 파일 임베드의 분리

- **상태**: Accepted
- **날짜**: 2026-05-17
- **관련 커밋**: `fix(ui): worker lifecycle...`, `feat(downloader): embed thumbnail...`
- **관련 이슈**: WORKLOG 6번 (해결됨)

#### 맥락 (Context)

"썸네일이 안 보인다"는 동일한 문구가 두 개의 전혀 다른 대상을 가리키고 있었음:

1. **UI 미리보기 썸네일** — `DownloadItemWidget.lbl_thumb` QLabel에 표시되는 작업 화면 내 미리보기
2. **파일 임베드 썸네일** — 다운로드된 mp4/mp3에 메타데이터로 박혀 Windows 탐색기·플레이어 아이콘으로 노출되는 이미지

용어 혼동으로 진단·해결이 수 차례 지연됨. 두 대상은 코드 위치, 라이브러리, 스레드 모델이 완전히 다름.

#### 결정 (Decision)

두 썸네일을 **명시적으로 구분**하여 코드와 문서에 반영한다.

**UI 미리보기 (PySide6 영역)**
- `QPixmap`/`QImage`는 **반드시 GUI 스레드에서만** 생성한다.
- 워커 스레드(`ThumbnailWorker`)는 raw bytes만 시그널로 전달하고, 위젯이 GUI 스레드에서 `QPixmap.loadFromData()`로 변환한다.
- 워커 시그널은 `Qt.QueuedConnection`을 명시한다.
- 워커는 `item_id`를 함께 전달해 위젯 재사용 시 시그널 오염을 방지한다.
- `_thumb_workers`는 dict 구조로 관리하고 cancel 메서드를 제공한다.

**파일 임베드 (yt‑dlp/FFmpeg 영역)**
- yt‑dlp 옵션 `writethumbnail=True`, `embedthumbnail=True`를 설정한다.
- postprocessor 체인을 다음 순서로 구성한다:
  1. `FFmpegThumbnailsConvertor` (webp → jpg 변환)
  2. `EmbedThumbnail` (파일에 임베드)
  3. `FFmpegMetadata` (제목·업로더 등 메타데이터)
- MP3는 `-id3v2_version 3 -write_id3v1 1`로 Windows 탐색기 호환을 보장한다.
- FFmpeg/FFprobe가 PATH에 있어야 한다.

#### 결과 (Consequences)

**긍정**
- 워커 스레드에서 QPixmap을 만들던 잠재적 크래시/표시 누락이 사라짐
- 다운로드 파일이 탐색기·음악 플레이어에서 썸네일을 정상 표시
- 두 대상이 코드·문서·대화에서 분리되어 디버깅 비용 감소

**부정**
- FFmpeg 의존이 명시적으로 필요 (사용자 환경 안내 필요)
- postprocessor 체인이 길어져 다운로드 후처리 시간이 약간 증가

#### 대안 검토

- **A안 — 워커에서 QPixmap 생성 후 emit**: PySide6 규약 위반. 채택 불가.
- **B안 — `info["thumbnail"]` 신뢰 안 하고 자체 선택 로직(`_pick_thumbnail`)**: 진단 결과 yt‑dlp가 이미 maxresdefault를 정확히 반환함. 불필요한 복잡도. 채택 안 함.
- **C안(채택)**: 위 결정 참조.

---

### ADR‑002: (예약됨) 포맷 선택 — "최고 화질" 의미 분리

- **상태**: Proposed
- **날짜**: TBD

현재 "최고 화질"은 yt‑dlp의 `bestvideo+bestaudio/best`로 동작하며, YouTube의 VP9/AV1 우선 정책에 따라 H.264 1080p보다 파일이 작아질 수 있음. 사용자 혼란 방지를 위해 "최고 화질 (자동 · 효율 우선)"과 "최고 호환 (MP4/H.264)"를 분리할지 결정 필요. 추후 작성.

---

## 부록 A. 학습된 교훈 (Lessons)

> 같은 실수를 반복하지 않기 위한 메모. 주제별로 누적합니다.

### PowerShell · Windows 환경

- `>` 리다이렉트는 기본적으로 UTF‑16 LE BOM으로 파일을 만든다. UTF‑8이 필요하면 `Out-File -Encoding utf8` 또는 `Set-Content -Encoding utf8`을 명시한다.
- `git diff`가 멈추고 `:`이 보이면 less 페이저다. `q`로 종료, `Space`로 한 페이지, `G`로 끝으로 이동. 페이저 없이 보려면 `git --no-pager diff`.
- 빈 파일의 Git SHA는 `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`.
- PowerShell `git commit -m "..."` 에서 큰따옴표 안에 큰따옴표를 넣으려고 `""` 로 이스케이프하면 빈 문자열로 해석되어 인자가 끊긴다. 큰따옴표 안에는 작은따옴표를 쓰거나, 헤더 한 줄로만 커밋하고 본문은 WORKLOG 로 빼는 게 안전하다.

### Python · PySide6

- 타입 힌트(`self.x: dict = {}`)는 어노테이션일 뿐, 변수를 자동 생성하지 않는 위치도 있다. `__init__`에서 명시적으로 초기화한다.
- `QPixmap`·`QImage`는 GUI 스레드 전용. 워커 스레드에서 만들면 표시 누락·크래시가 발생한다.
- 시그널‑슬롯은 스레드를 넘을 때 `Qt.QueuedConnection`을 명시하면 안전하다.
- `QLabel.setScaledContents(True)`는 0×0 라벨에서 빈 화면을 만들 수 있다. 직접 `scaled()` 호출이 안전하다.

### yt‑dlp

- 2025년부터 EJS(Embedded JavaScript)를 사용. Node.js/Deno/Bun 중 하나가 PATH에 있어야 함. 참고: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- `info["thumbnail"]`은 보통 정확하지만, `info["thumbnails"]` 리스트에서 직접 선별할 수도 있다.
- `bestvideo+bestaudio/best`는 코덱 효율 우선이라 H.264보다 파일이 작을 수 있다.
- `postprocess_hook` 은 ffmpeg 머지만이 아니라 **모든 후처리기**의 started/finished 를 발사한다. `d["postprocessor"]` 값으로 단계를 구분해야 한다. 2026.3.17 기준 ADR-001 체인의 순서는 `ThumbnailsConvertor` → `Merger` → `Metadata` → `EmbedThumbnail` → `MoveFiles`. 또한 postprocess 후크에는 **퍼센트 정보가 없다** (`status`/`postprocessor`/`info_dict`/`_default_template` 4개 키만 제공). 머지·임베드 단계에 퍼센트 진행률 표시는 현 구조로 불가.
- `ExtractAudio` 로 m4a→mp3 재인코딩하면 ffmpeg 가 기본 `-map_metadata 0` 으로 원본 ftyp 박스 필드(`major_brand` 등)를 ID3 의 TXXX 로 옮겨 박는다. MP3 에는 원리상 없어야 할 메타가 남는다. `-map_metadata -1` 로 끊을 수는 있으나 그러면 같은 ffmpeg 호출에서 FFmpegMetadataPP 가 박는 `-metadata title=…` 까지 함께 무효화되어 ID3 TIT2 가 사라진다. 선별 제거가 필요하면 `meta_<key>` info dict 주입 또는 별도 ffmpeg 호출 경로를 써야 한다.
- 기본 retry/timeout 은 짧다. 실서비스 GUI 에서는 `socket_timeout`, `retries`, `fragment_retries='infinite'`, `file_access_retries`, `retry_sleep_functions` 를 명시해 일시적 stall 을 내부에서 흡수시켜야 한다.
- **`ydl.download([url])` 은 내부에서 `extract_info` 를 다시 돌린다.** 우리가 호출 전에 가공한 info dict 가 있어도 무시되고 원본 NFD 메타가 그대로 후처리 체인에 흘러간다. 사전 정규화한 dict 를 유지하려면 `ydl.process_ie_result(info, download=True)` 를 써야 한다. yt-dlp 내부에서도 광범위하게 쓰이는 경로라 안정적.
- **`FFmpegMetadataPP` 는 info dict 의 `title`/`artist`/`description` 등을 직접 읽어 `-metadata` 인자로 변환한다.** 즉 메타 내용을 통제하려면 ffmpeg 인자를 우회로 박는 것보다 info dict 자체를 정규화한 뒤 `process_ie_result` 로 흘리는 것이 단순하고 견고하다. 사용자 정의 키는 `meta_<name>` 또는 `meta_<idx>_<name>` 형태로 info dict 에 박으면 우선 적용된다.

### 유니코드·파일명

- 유니코드 정규화는 **클라우드·OS·소스 사이트 경계에서 깨진다**. SoundCloud 의 한글 메타는 NFD(자모 분리, U+1100~U+11FF) 로 들어오는 경우가 있다. macOS 경유 클라우드 동기화도 마찬가지. 우리 앱은 **info dict 진입 지점에서 NFC 로 통일**하는 것을 원칙으로 한다 (`unicodedata.normalize('NFC', ...)`).
- **콘솔 렌더링은 NFD 를 NFC 처럼 그려낼 수 있다.** `chcp 65001` 로 cmd.exe 를 UTF-8 로 바꾸면 한글이 멀쩡히 "기쁨" 으로 보이지만, 실제로는 `ㄱ + ㅣ + ㅃ + ㅡ + ㅁ` 5개 jamo 일 수 있다. 진단할 때는 ffprobe 출력 모양에 속지 말고 실제 코드포인트를 봐야 한다 (`python -c "import sys; print([hex(ord(c)) for c in open(sys.argv[1]).read()])"` 또는 ID3 값을 파일로 떠서 hex dump).
- ID3v2.3 의 텍스트 인코딩은 UTF-16 (BOM 포함) 이 호환성 가장 높다. yt-dlp + ffmpeg 기본 동작이 이를 따르므로 우리는 별도 옵션을 줄 필요 없으나, 값으로 넘어가는 문자열은 NFC 여야 한다.
- **ffprobe JSON 출력 자체도 NFD 를 NFC 처럼 보여줄 수 있다.** `chcp 65001` + ffprobe JSON 으로 한글이 깨끗하게 보이더라도, 콘솔 폰트의 자모 결합 렌더링 결과일 뿐 데이터는 NFD 일 수 있다. 2026-05-18 디버깅 중 이 함정에 두 번 빠졌다. **NFC/NFD 판정은 반드시 파일 원본 바이트에서**: m4a 는 `©nam` atom 의 데이터 영역, mp3 는 `TIT2` 프레임의 텍스트 영역을 직접 hex 로 봐야 한다. NFC 한글 한 글자는 UTF-8 3바이트(`0xea·0xeb·0xec` 시작), NFD 는 자모별 3바이트씩 2~3개(`0xe1 0x84 …` 패턴)다.
- **표시 레이어는 모두 정직하지 않다.** Windows 탐색기 속성창은 NFD 를 분리해서 보여주고(정직), VS Code 터미널은 결합해서 그리고(NFC 처럼 보임), ffprobe JSON 도 결합해서 그린다. 같은 데이터가 어디서는 깨져 보이고 어디서는 멀쩡해 보이는 게 정상이다. 표시 어긋남으로 데이터를 추론하지 말 것.

### Git

- `.gitignore`는 **이미 추적 중인 파일에는 영향 없음**. 빼려면 `git rm --cached <path>`.
- 의미 단위로 커밋을 나누려면 `git add -p`로 hunk 단위 스테이징.
- Conventional Commits 권장: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`. 참고: https://www.conventionalcommits.org/

### 협업 · 커뮤니케이션

- **용어가 같다고 대상도 같지는 않다.** "썸네일"처럼 일상어가 두 개 이상의 기술 객체를 가리킬 때, 먼저 어느 대상인지 확정한다.
- 진단 코드(print, 임시 파일 저장)는 가설 검증 후 즉시 제거하고 커밋에 섞지 않는다.
- 가설은 한 번에 하나씩 검증한다. 동시에 여러 패치를 적용하면 원인 추적이 어려워진다.
