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

**후기 (2026-07-10, 부분 번복)**

위 결정 중 `info["meta_comment"] = info.get("description") or ""` 부분만 번복 — `meta_comment` 를 **빈 문자열**로 변경(커밋 `d273280`). `webpage_url → comment` 자동 매핑을 차단한다는 목적은 유지되지만, description 을 넣으면 FFmpeg 가 이를 비표준 `TXXX:comment` (UTF-16) 프레임으로 써 한글 Windows '주석' 열에서 mojibake 가 됐다. 빈 값이면 comment 프레임 자체가 안 생겨(실측) 문제 소멸. 영상 URL 은 `purl` 태그가 보관하므로 정보 손실 없음. `pre_process` PP 정공법과 자동 매핑 차단 메커니즘은 그대로 유효.

---

### ADR-005: (예약됨) 오디오 후처리 정책 — 원본 보존 vs 비트레이트 통일

<a id="adr-005"></a>

- **상태**: Proposed
- **날짜**: TBD

**결정**

현재 `core/downloader.py` 는 `is_audio` (mp3/m4a/wav/aac) 모두에 대해 `FFmpegExtractAudio` 를 192 kbps 로 일괄 적용. YouTube Opus 160 kbps, SoundCloud 320 kbps MP3, Bandcamp FLAC 등 원본이 192 kbps 보다 고음질일 때 lossy→lossy 재인코딩으로 정보 손실. `MP3_BITRATE_KBPS` 가 모듈 상수라 환경설정 노출도 없음. 네 갈래 검토 — (가) 현상 유지 + 비트레이트 환경설정 노출, (나) 원본 더 고음질이면 컨테이너만 변경 권고, (다) 포맷 선택 다이얼로그에 비트레이트 드롭다운 (ADR-002 와 결합), (라) 원본 `abr > 192` 일 때만 사용자 확인. 결정 시 본 ADR 갱신.

---

### ADR-006: 플레이리스트 일괄 다운로드 — 글로벌 포맷 선택과 워커 시그널 규율

<a id="adr-006"></a>

- **상태**: Accepted
- **날짜**: 2026-06-02

**결정**

한 URL 로 플레이리스트 N 개 항목을 일괄 추가한다. 흐름은 `controllers/playlist_flow.py` 의 상태머신 단일 소유 — `PlaylistProbeWorker` (`extract_flat="in_playlist"`, 상한 500) 로 경량 목록 → `PlaylistSelectDialog` (체크박스 목록·전체선택/해제·영상/음원 단일 선택) → 선택 항목만 큐 투입. 화질은 항목별 다이얼로그 없이 다이얼로그의 단일 선택을 전체 적용 — 영상 `bestvideo+bestaudio/best`+`mp4`, 음원 `bestaudio/best`+`mp3`. 음원 비트레이트는 하드코딩하지 않고 `core/downloader.py` 단일 출처에 위임 (ADR-005 확정 시 자동 반영).

정보추출 동시성은 별도 값을 두지 않고 다운로드 `max_concurrent` 를 공유하는 게이트(`_info_pending`/`_info_running`)로 제한 — 단일 항목·플레이리스트 항목 모두 한 경로 경유.

부수 결정 (중대): 워커는 QThread 내장 시그널(`finished`/`started`)을 **같은 이름의 커스텀 Signal 로 가리지 않는다**. 결과 전달용 시그널을 별도 명명(`download_finished`/`info_ready`/`thumb_ready`) 하고, 객체·dict 정리는 QThread 내장 `finished` 에 연결해 스레드 종료 후 수행.

**이유**

`DownloadWorker.finished = Signal(str)` 가 QThread 의 인자 없는 `finished` 를 가려, `run()` 종료 직전 emit 된 결과 시그널 처리 중에 dict 에서 워커가 빠지고 GC 되어 "QThread: Destroyed while thread is still running" 크래시 발생. 동시 2 + 플레이리스트 60 항목 부하에서 3~4번째 병합 단계에 재현. 단일 항목에서는 pop 시점이 늦어 잠복했음.

**결과**

크래시 해소, 60+ 항목 MP3 일괄 다운로드 완주 검증. 정보추출이 다운로드 한도를 공유해 429/IP 차단 위험 회피. 항목별 화질 다이얼로그 제거로 일괄 UX 단순화. 플레이리스트 항목은 목록 하단 삽입(추가 순서 보존), 단일 항목은 상단 삽입(기존 동작 유지).

**대안**

A. 워커 시그널 이름 유지 + `destroyed`/플래그 우회 — 섀도잉 잔존, 새 함정. B. 정보추출 전용 동시성 값 신설 — 설정 항목 증가, 사용자 혼란. C. 항목별 체크박스 없는 단순 확인 다이얼로그 — 세밀 선택 불가. D(채택): 위 결정.

**관련**

ADR-003 (매니저 라이프사이클 분리 — 본 게이트가 같은 원칙 확장). ADR-005 (음원 비트레이트 단일 출처 위임). LESSONS PySide6 의 QThread 시그널 섀도잉 항목.

---

### ADR-007: 다운로드 자동 재시도 — yt-dlp retries 위의 세션 레벨 재시도

<a id="adr-007"></a>

- **상태**: Accepted
- **날짜**: 2026-07-09

**결정**

일시적 다운로드 오류를 무인 회복하기 위해, `DownloadWorker.run()` 이 `Downloader.download()` 호출 전체를 재시도 루프로 감싼다. 매 시도마다 `Downloader` 를 **새로 생성**(=새 `YoutubeDL` 세션, `extract_info` 재실행)해 만료 토큰을 새로 받는다. 오류는 메시지 패턴으로 분류(`_is_transient_error`): 영구 패턴 우선 검사 후 일시 패턴, 어디에도 안 걸리면 보수적으로 영구(즉시 ERROR) 취급. 일시적 오류 한정 지수 백오프(2→5→10초) 최대 3회 자동 재시도, 최종 실패 시에만 `error` 1회 emit. 재시도 진입은 `retrying(현재, 최대)` 시그널 → 위젯 "재시도 중 (N/M)" 라벨. 백오프 대기는 0.1초 단위로 취소를 폴링해 반응성 유지.

**이유**

yt-dlp 내부 `retries=10` 은 "다운로드 중 HTTP 재시도" 계층이라, YouTube 403 처럼 **시작 시점 세션/토큰 만료**로 나는 오류는 같은 세션 안에서 몇 번을 재시도해도 계속 403 이다. 실제로 사용자가 수동 재시도 버튼을 누르면 새 세션이 새 토큰을 받아 바로 성공했다 — 이는 재시도가 세션 전체를 다시 도는 계층이어야 함을 뜻한다 (ADR-004 의 토큰 만료 배경과 정합).

**결과**

플레이리스트 403 빈발 상황에서 수동 재시도 없이 대부분 완주, 영구 오류(비공개·삭제·지역차단)는 즉시 ERROR. 백오프 대기 중 취소는 ~0.1초 내 반영되어 `cancelled` 로 종료. 오프스크린 시뮬레이션으로 분류 18케이스·재시도 루프 4시나리오·취소 반응성 검증.

**대안**

A. yt-dlp `retries` 만 늘림 — 세션 내 재시도라 토큰 만료 403 에 무효. B. 예외 타입으로 분류 — yt-dlp 가 대부분 `DownloadError` 로 뭉뚱그려 불가. C. 판단 불가 오류도 재시도 — 무의미한 대기로 사용자 체감 악화, 채택 안 함. D. 백오프·횟수를 설정 노출 — 대부분 무의미한 노브라 상수 하드코딩(모듈 최상위 명시로 후일 설정화 용이). E(채택): 위 결정.

**관련**

ADR-004 (YouTube 토큰 만료 403, 세션 재시작으로 새 토큰). ADR-003 (매니저 라이프사이클). LESSONS yt-dlp 의 403 토큰 만료 항목.

---

### ADR-008: GaindB(mp3gain 독립 구현, Apache-2.0) 통합 — MP3 다운로드 후 음량 정규화

<a id="adr-008"></a>

- **상태**: Accepted (UI·클리핑·실환경 검증 완료 — 문서 잔여만 남음, WORKLOG 3 참조)
- **날짜**: 2026-07-10 (2026-07-23 UI·클리핑·api 계층, 2026-07-24 v3 최종본·Apache-2.0 반영)
- **관련 커밋**: `e1a8a26` `17c8933` `51a071f` `aea6955` `1cbb6bc` `82ca735` `5d392bd` `aac618c`

**결정**

별도 프로젝트 GaindB(mp3gain 의 클린룸 재구현, ReplayGain 무손실 게인)를 AVD 에 벤더링해, MP3 다운로드 완료 직후 트랙 모드로 음량을 목표 dB(기본 89, 조절 75.0~105.0)에 맞춘다. 적용 대상은 MP3 한정(`ext == "mp3"`). 게인은 부가 기능이라 실패해도 다운로드 자체는 성공 처리하되 실패 사실은 사용자에게 표시. 병합(MERGING)·정규화(NORMALIZING) 단계는 다운로드 슬롯을 점유하지 않도록 `active_count()` 에서 제외.

**이유**

"모든 MP3 음량을 일정하게" 라는 요구는 단순 dB 오프셋이 아니라 곡별 분석 기반 목표 라우드니스 정규화(ReplayGain 트랙 모드)를 필요로 한다. GaindB 는 무손실(global_gain 조정)이라 재인코딩 없이 붙일 수 있고, ffmpeg 는 AVD 가 이미 의존한다. AVD 본체(MIT)와 벤더링 서브패키지 `gaindb/`(Apache-2.0)는 라이선스 충돌이 없다(둘 다 permissive; Apache-2.0 준수를 위해 상류 `LICENSE`·`NOTICE`·`THIRD_PARTY_LICENSES` 를 `gaindb/` 에 동봉).

**결과**

다운로드 후처리 파이프라인에 게인 단계가 한 지점(`download()` 성공 후, `download_finished` 전)으로 응집. 슬롯 해제로 병합·정규화 중에도 다음 다운로드가 출발. numpy/scipy(BSD) 의존이 새로 추가됨. 게인 실패는 완료 라벨 공유(`완료(음량 조정 실패)`) + 상태바로 알림(팝업 없음).

**대안**

A. 단순 dB 오프셋 — 곡별 편차를 못 잡아 "일정한 음량" 요구 미충족. B. ffmpeg `loudnorm` 필터 — 재인코딩 발생(무손실 아님). C. 앨범 모드 — AVD 는 곡을 개별 처리하므로 부적합. D(채택): GaindB 트랙 모드 벤더링.

**관련**

ADR-003 (매니저 라이프사이클 — 슬롯 해제가 같은 원칙 확장). ADR-005 (오디오 후처리 정책 — 게인은 그 하류 단계). 라이선스 근거는 벤더링본 안의 `gaindb/NOTICE`·`gaindb/THIRD_PARTY_LICENSES`(독립 구현·의존성 고지, v3 부터 동봉).

**후기 (2026-07-23 갱신)**

GaindB 가 CLI·GUI·AVD 공유 순수 함수 api 계층(`gaindb/api.py`)을 도입해 벤더링본을 그 리팩터본(이후 v2 안정본)으로 교체(`aea6955`→`5d392bd`). 목표 dB→89 기준 오프셋 변환이 api 안에 캡슐화돼 GUI 는 목표 dB 만 넘긴다. 클리핑 판정은 예정대로 GaindB 본체가 해결: `analyze_file` 이 `clip_state`("none"/"possible"/"definite")를 반환하고 AVD 는 `definite` 만 클리핑으로 표시한다("설정값 강제 적용, 여부만 표시" 방침 유지). 워커는 `analyze_file`(비파괴, seed 확보) → `apply_file_track_gain`(seed 재사용 적용) 2단계로 처리하고 `normalize_done(적용dB, 클리핑)` 시그널로 위젯에 전달, 완료 라벨을 `완료 · 음량 +N.NdB`/`(클리핑)`/`완료 (음량 조정 실패)` 로 표시(`1cbb6bc`). 설정 UI 는 SpinBox 초안(다크 테마 화살표 미표시·레이아웃 깨짐)을 폐기하고, 체크박스로 펼쳐지는 접이식 컨테이너 안에 `QLineEdit`+`QDoubleValidator` 입력창과 `QSlider`(0.5dB 단위, 정수 슬라이더 ×2 스케일)를 공존시켜 상호 동기화(`82ca735`). Windows 실환경 검증 완료(2026-07-23).

**후기 (2026-07-24 — GaindB v3 최종본)**

GaindB 가 최종본(v3)에서 두 가지를 정리했다. (1) 구조: 그동안 리포 루트에 있어 AVD 벤더링 시 매번 `from apply_gain` → `from gaindb.apply_gain` 로 교정하던 `apply_gain.py` 를 upstream 이 `gaindb/` 패키지 안으로 이동 → 이제 원본을 무수정으로 벤더링(교정 패치 제거). (2) 라이선스: 전 파일 `SPDX-License-Identifier: Apache-2.0` 헤더 + docstring 문구를 "clean-room"→"독립 구현"·"ReplayGain 공개 사양의 표준 계수"로 정리하고 `LICENSE`·`NOTICE`·`THIRD_PARTY_LICENSES` 를 갖췄다. AVD 는 Apache-2.0 준수를 위해 이 3개 라이선스 파일을 `gaindb/` 에 함께 벤더링(`aac618c`). 트랙 모드 공개 API(`analyze_file`·`apply_file_track_gain`) 시그니처는 v2 와 동일해 `download_worker.py` 무수정 호환. 잔여: README 게인 기능·의존 한 줄. 세부는 WORKLOG 3.
