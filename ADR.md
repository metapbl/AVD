# AV_Downloader — 아키텍처 결정 기록 (ADR)

> 이 파일은 프로젝트의 중요한 설계 결정을 항목별로 누적합니다.
> 일상적 변경 이력은 `CHANGELOG.md`, 진행 중 작업과 인덱스는 `WORKLOG.md` 가 담당합니다.

## 작성 규약

- 한 항목 본문은 **30 줄 이내** (코드 펜스·표 포함, 헤더 제외).
- 구조: **결정 / 이유 / 결과 / 대안 / 관련** 다섯 섹션을 유지하되 각 섹션 2~4 문장으로 압축.
- 헤더 직후 줄에 `<a id="adr-NNN"></a>` 명시 앵커를 박는다 (한글 슬러그 불안정성 회피).
- 한 번 작성된 ADR 은 **수정하지 않는다**. 결정이 바뀌면 새 ADR 로 대체하고 양쪽 상태를 `Superseded by ADR-NNN` / `Supersedes ADR-NNN` 으로 명기.
- 사용자 합의 과정·시행착오 메타 서술은 적지 않는다 (그건 `CHANGELOG.md` 의 영역).

---

### ADR-001: 썸네일 처리 — UI 미리보기와 파일 임베드의 분리

<a id="adr-001"></a>

- **상태**: Accepted
- **날짜**: 2026-05-17

**결정**

"썸네일" 이라는 같은 단어가 두 대상을 가리키고 있었음 — ① UI 미리보기 (`DownloadItemWidget.lbl_thumb`), ② 파일 임베드 (탐색기·플레이어 아이콘). 두 대상을 코드·문서·대화에서 명시적으로 분리한다.

UI 미리보기는 PySide6 영역: `QPixmap` / `QImage` 는 GUI 스레드 전용, `ThumbnailWorker` 는 raw bytes 만 emit, 시그널은 `Qt.QueuedConnection`, `item_id` 동반, `_thumb_workers` 는 dict + cancel 제공.

파일 임베드는 yt-dlp/FFmpeg 영역: `writethumbnail=True` + `embedthumbnail=True`, postprocessor 체인 `FFmpegThumbnailsConvertor → EmbedThumbnail → FFmpegMetadata` 순. MP3 는 `-id3v2_version 3 -write_id3v1 1` 로 Windows 호환 보장. FFmpeg/FFprobe PATH 필수.

**이유**

용어 혼동으로 진단·해결이 수 차례 지연됨. 두 대상은 코드 위치·라이브러리·스레드 모델이 완전히 다르므로 분리가 진단 비용을 결정.

**결과**

워커 스레드 QPixmap 으로 인한 잠재 크래시·표시 누락 해소. 다운로드 파일이 탐색기·음악 플레이어에서 썸네일 정상 표시. FFmpeg 의존이 명시적으로 필요해짐.

**대안**

A. 워커에서 QPixmap 생성 후 emit — PySide6 규약 위반. B. `info["thumbnail"]` 신뢰 안 하고 자체 선택 로직 — yt-dlp 가 이미 maxresdefault 반환, 불필요한 복잡도. C(채택): 위 결정.

**관련**

ADR-004 가 본 체인 앞에 `_NFCNormalizePP` 추가로 보강.

---

### ADR-002: (예약됨) 포맷 선택 — "최고 화질" 의미 분리

<a id="adr-002"></a>

- **상태**: Proposed
- **날짜**: TBD

**결정**

현재 "최고 화질" 은 yt-dlp 의 `bestvideo+bestaudio/best` 로 동작 → YouTube 의 VP9/AV1 우선 정책에 따라 H.264 1080p 보다 파일이 작아질 수 있음. 사용자 혼란 방지를 위해 "최고 화질 (자동·효율 우선)" 과 "최고 호환 (MP4/H.264)" 분리 검토. 결정 시 본 ADR 갱신.

---

### ADR-003: 다운로드 워커 오케스트레이션을 `DownloadManager` 로 분리

<a id="adr-003"></a>

- **상태**: Accepted
- **날짜**: 2026-05-28
- **관련 커밋**: `954152f`

**결정**

`MainWindow` 의 다섯 책임 (UI 구성·항목 라이프사이클·다운로드 워커 오케스트레이션·썸네일 워커·앱 부수 동작) 중 ③ 만 떼어내는 **최소 분할**. 신규 `controllers/download_manager.py` 의 `DownloadManager` (QObject) 가 `DownloadWorker` 생성·연결·종료, `dl_workers` dict, 동시성 한도 적용, WAITING 순번 라벨 갱신을 책임짐.

`items` / `widgets` dict 는 `MainWindow` 단일 소유, 매니저는 참조만 받아 읽기·순회. 진행률·속도·ETA·병합 시그널은 워커→위젯 **직접 연결** (매니저 미경유). 라이프사이클 시그널만 워커→매니저→`MainWindow` 두 단 경로. 큐 자료구조는 `self.items` dict 의 삽입 순서를 그대로 사용 (별도 `Queue`/`deque` 두지 않음 — 단일 출처).

**이유**

큐 매니저 정책을 `MainWindow` 에 추가하면 한 클래스가 500 줄을 넘고 다음 작업이 더 키울 예정. 가독성·테스트 가능성·다음 분할의 패턴 확보가 동시에 필요.

**결과**

`MainWindow` 약 500 → 400 줄로 감소. 매니저는 UI 직접 의존 없어 단위 테스트 가능성 확보. `widgets` 자리에 mock 주입 가능. 분할이 한 커밋에 feat 와 묶인 점은 정직성 비용.

**대안**

A. 분할 없이 통째 — 비대화 지속. B. 다섯 책임 전면 재배치 — 과분할. C. `MainWindow` 안 메서드 그룹화 — 변경 가독성 떨어지고 테스트 가능성 닫힘. D. refactor·feat 두 커밋 분리 — 응답 비용으로 단일 feat 채택, 분할 회귀는 검증 시나리오 ⑥ (영상 1개 추가 후 완료) 로 별도 확보.

---

### ADR-004: `process_ie_result` 우회 폐기, NFC 보존을 PostProcessor 정공법으로

<a id="adr-004"></a>

- **상태**: Accepted
- **날짜**: 2026-05-28
- **관련 커밋**: `316c642`
- **대체 관계**: 2026-05-18 의 `fix(downloader)` "NFC 메타데이터를 yt-dlp 의 정상 경로로 흘려보내는 구조로 재구성" 결정의 `process_ie_result` 사용 부분을 **번복**. ADR-001 의 후처리 체인 결정은 유효 — 본 ADR 이 `pre_process` PP 한 단계 추가로 보강.

**결정**

`process_ie_result(probed, download=True)` 우회 폐기, 본 다운로드는 `ydl.download([url])` 로 복귀. NFC 정규화는 `core/downloader.py` 모듈 최상위에 신설한 `_NFCNormalizePP(PostProcessor)` 가 `when="pre_process"` 단계에서 수행. `pre_process` = `extract_info` 직후, 파일명 결정·다운로드·일반 PP 모두에 앞섬. 같은 PP 가 `info["meta_comment"] = info.get("description") or ""` 도 사전 주입 — `FFmpegMetadataPP` 의 `webpage_url → comment` 자동 매핑 차단.

부수 결정: `_BASE_OPTS` 의 `js_runtimes` / `remote_components` 두 줄 제거 — node 고정이 deno/bun 자동 선택을 막던 점을 자동 탐지에 맡김. 파일명 sanitize 는 yt-dlp 의 `windowsfilenames: True` + `trim_file_name: 200` 에 위임.

**이유**

probe 에서 받은 format URL 의 nsig/sig 토큰이 두 번째 호출 시점에 만료 → YouTube 에서 `HTTP Error 403: Forbidden` 회귀. CLI 단독 호출과 `ydl.download` 은 정상이지만 `process_ie_result` 만 실패하는 비대칭으로 진단. SoundCloud 등은 토큰 정책이 느슨해 잠복.

**결과**

403 해소, NFC 보존을 한 PP 하나의 책임으로 응집. SoundCloud `comment` 자동 매핑도 같은 PP 가 해결. JS 런타임 환경 변화에 둔감. 파일명 sanitize 가 외부 위임으로 바뀌었으나 Windows 안전성은 동등.

**대안**

A. `process_ie_result` 유지 + 토큰만 재발급 — 사적 API 호출 필요, 깨지기 쉬움. B. `extract_info(url, download=True)` 한 번 — NFC 정규화 틈 사라짐. C. `MetadataParserPP` INTERPRET 액션으로 NFC 강제 — INTERPRET 는 기존 값 재해석 도구지 외부 값 주입 불가. D(채택): `pre_process` 커스텀 PP. yt-dlp README 권장 임베딩 패턴.

**관련**

ADR-001 (후처리 체인). LESSONS yt-dlp 항목의 `process_ie_result` 함정.
