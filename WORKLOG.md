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

- **플레이리스트 리스트 썸네일 누락 — 동시 부하 시 UI 미리보기 일부 실패**
    - 동기: 60 항목 일괄 다운로드 시 약 15 개의 리스트 썸네일(UI 미리보기) 이 비었음. 단, 결과 파일의 임베드 썸네일은 정상 — ADR-001 의 두 대상 분리상 UI 경로만의 문제.
    - 진단 (2026-06-02): `workers/thumbnail_worker.py` `TIMEOUT_SEC = 10` 가 동시 다발 요청과 충돌 추정. 게이트 없이 60 항목이 거의 동시에 썸네일 GET 을 던져 일부가 10 초 안에 응답 못 받고 `failed` 로 빠짐 (약 25% 실패율이 동시 폭주·일시 거절 패턴과 부합).
    - 정책 (택일, 코드 단계 결정): (가) 썸네일 워커도 InfoWorker 식 경량 동시성 게이트에 태움, (나) `failed` 시 1 회 지연 재시도, (다) 둘 다.
    - 검증: 60+ 항목 플레이리스트 추가 → 리스트 썸네일 누락 0~소수 확인. 결과 파일 임베드는 회귀 없음 (분리 경로).
    - 보류: 게이트 크기 산정 — 다운로드 `max_concurrent` 공유 여부 vs 썸네일 전용 고정값.

- **다운로드 자동 재시도·백오프 — 일시적 오류의 무인 회복**
    - 동기: 플레이리스트 다운로드 중 일부 항목에 `HTTP Error 403: Forbidden` 팝업, 재시도 버튼을 누르면 바로 성공. 60 항목을 수동 재시도하는 부담이 큼.
    - 진단: YouTube 403 은 대부분 일시적(세션 토큰 만료·순간 거절). 영구 오류(비공개·삭제·지역차단) 와 구분 필요.
    - 정책 (코드 단계 결정): `DownloadWorker`/`DownloadManager` 에서 일시적 오류(403·타임아웃·일시 네트워크) 한정 지수 백오프(예: 2→5→10 초) 최대 3 회 자동 재시도, 최종 실패 시에만 ERROR 팝업 1 회. 영구 오류는 즉시 ERROR.
    - 검증: 403 빈발 플레이리스트 추가 → 자동 회복으로 수동 재시도 없이 대부분 완주, 영구 오류 항목은 즉시 ERROR 표시.
    - 보류: 재시도 대상 오류 분류 기준(메시지 패턴 vs yt-dlp 예외 타입), 백오프 파라미터의 설정 노출 여부.

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

- **병합 중 항목의 동시성 슬롯 점유 해제**
    - 동기: `max_concurrent` 한도 안에 병합(MERGING) 단계 항목까지 들어가 있어, 큰 파일 병합이 길어지면 다음 WAITING 항목이 출발하지 못함. 병합은 다운로드가 아니므로 다운로드 슬롯에서 빼는 것이 사용자 직관과도 일치.
    - 진단: `controllers/download_manager.py` `active_count()` 가 `w.isRunning()` 만 카운트. `DownloadWorker.run()` 은 `Downloader.download()` 를 동기 호출하고, yt-dlp 는 다운로드 직후 같은 호출 안에서 후처리(병합·메타·썸네일 임베드) 까지 마친 뒤 리턴 → MERGING 동안 `isRunning()` = True 가 계속 유지되어 슬롯을 잡고 있음.
    - 정책:
        1. `active_count()` 의 활성 기준을 `isRunning() and items[id].status != MERGING` 으로 변경. WAITING 라벨 재계산은 기존 `_refresh_waiting_labels()` 가 status 기준이라 별도 수정 불필요.
        2. 워커 `merging` 시그널 수신 경로에 매니저의 `_dispatch_next()` 호출 추가. 현재는 `lambda: widget.update_status(MERGING)` 만 연결되어 있으므로 매니저 슬롯을 하나 더 붙이는 방식 (위젯 직결은 유지, 매니저는 라이프사이클 한정 원칙 — ADR-003 정합).
        3. 병합 동시 실행에는 별도 한도를 두지 않는다. 디스크 I/O 포화가 실측에서 관찰되면 `max_concurrent_merge` 도입을 ADR 로 검토.
    - 검증: 슬라이더 2, 큰 영상 3개 연속 추가 → 첫 두 개가 병합 단계에 진입한 순간 세 번째 항목이 즉시 DOWNLOADING 으로 출발하는지 확인. 동시에 진행 중인 두 항목의 라벨이 "병합 중" 유지되는지도 확인 (상태 전이가 슬롯 회수의 부작용으로 흔들리지 않을 것).
    - 보류: 위 한도 분리(`max_concurrent_merge`) 는 실측 후 결정.

- **병합 단계 진행률 표시**
    - 동기: 큰 파일은 병합에 수십 초~수 분이 걸리는데 현재 UI 는 "병합 중" 라벨만 뜨고 진행률이 없어 사용자가 멈춘 것으로 오인.
    - 진단: yt-dlp `postprocessor_hook` 은 `started`/`finished` 두 신호만 전달, 퍼센트 정보 없음. `FFmpegMerger` 가 내부에서 호출하는 ffmpeg 의 stdout 도 yt-dlp 가 잡아먹어 외부 노출 없음. 우회로는 ffmpeg `-progress pipe:1 -nostats` 출력을 직접 가로채는 커스텀 PostProcessor 로 `FFmpegMerger` 를 대체하는 것.
    - 정책:
        1. 커스텀 머지 PostProcessor 추가 (`core/downloader.py` 또는 신규 모듈). `requested_formats` 가 2개 이상일 때만 활성, 단일 progressive 경로는 기존 흐름 유지.
        2. `subprocess.Popen(..., stdout=PIPE, stderr=DEVNULL)` 로 ffmpeg 직접 기동, 라인 파싱(`out_time_ms=`, `progress=continue|end`) → `out_time_ms / (info["duration"] * 1e6) * 100` 으로 퍼센트 환산.
        3. `DownloadWorker` 에 새 시그널 `merge_progress(float)` 추가, 위젯 직결.
        4. 위젯 표시 방식 — 기존 진행률 바 재활용 (라벨만 "병합" 으로 전환) vs 별도 라벨. 코드 작성 단계에서 결정.
    - 검증: 4K 60fps 영상(병합에 30초 이상 걸리는 표본) 다운로드 → 병합 단계 진입 후 퍼센트가 0 → 100 으로 카운트업, 종료 직후 DONE 전이 확인. 단일 progressive 경로(병합 없음) 가 회귀하지 않는지도 확인.
    - 보류: 진행률 표시 UI(바 재활용 vs 별도), `duration` 이 누락된 라이브/스트림 경우의 폴백(시간 표시만, 퍼센트 생략).

- **확장자 표시 정직화 — 미확정 시 숨김, 메타데이터 확보 후 갱신**
    - 동기: SoundCloud 같은 오디오 전용 소스를 "최고 화질 (자동 선택)" 으로 받으면 실제 결과는 m4a 인데, 화질 선택 직후부터 다운로드 완료 직전까지 제목 옆에 노란 ".mp4" 가 거짓으로 표시되다가 완료 시점에야 ".m4a" 로 바뀐다. 표시가 진실이 되는 시점이 너무 늦다.
    - 진단:
        1. `core/info_fetcher.py` `_parse_formats()` 가 통합 포맷("bestvideo+bestaudio/best") 행에 무조건 `ext="mp4"` 를 박는다 — 비디오 소스에서는 진실이지만 오디오 전용 소스에서는 거짓.
        2. `DownloadWorker.codec_info_resolved` 는 후처리 단계마다 `(vcodec, acodec, ext, abr, tbr)` 를 emit 하며 ext 가 함께 들어오지만, 위젯 `update_format_meta_resolved` 는 메타 라벨만 갱신할 뿐 제목 옆 노란 ext 라벨(`update_ext` 경로) 은 건드리지 않는다.
        3. 결과적으로 ext 의 진실은 `_on_worker_finished(path)` 시점의 실제 파일 경로에서야 반영된다.
    - 정책:
        1. `info_fetcher._parse_formats()` 의 통합 포맷 행에서 `ext=""` 로 변경 (미확정 표식). 비디오 구체 행("1080p MP4") 은 그대로 `ext="mp4"` 유지 — 머지 정책으로 진실 보장.
        2. `DownloadItemWidget.update_ext("")` 호출 시 `_ext_known=False` 로 자연스럽게 처리되도록 기존 가드 활용 (`update_ext` 가 이미 `lstrip(".")` 후 빈 값이면 미확정으로 다룬다). 제목 옆 노란 ".mp4" 가 표시되지 않는다.
        3. `DownloadItemWidget.update_format_meta_resolved` 에 ext 반영 로직 추가 — `ext` 가 의미 있는 값이면 `self._ext` 갱신 + `_apply_title_elide()` 호출. `_fmt_ext` 단일 출처도 같이 갱신해 메타 라벨의 컨테이너 표기도 진실로.
        4. (선택) 다이얼로그 측 표시 — 통합 포맷 행의 라벨 "최고 화질 (자동 선택)" 은 비디오/오디오 어느 쪽에도 거짓이 아니므로 그대로 유지. 화질 선택 후 위젯에는 ext 가 비어 있다가 다운로드 개시 후 채워지는 흐름.
    - 검증:
        1. SoundCloud URL 추가 → "최고 화질 자동 선택" 행 선택 → 다운로드 개시 전까지 제목 옆 노란 ext 라벨 비어 있음 → 다운로드 진행 중 ".m4a" 로 채워짐 → 완료까지 유지.
        2. YouTube URL 의 "1080p MP4" 명시적 선택 → 화질 선택 직후부터 ".mp4" 표시 (현재 동작 유지, 회귀 없음).
        3. YouTube URL 의 "최고 화질 자동 선택" → 다운로드 개시 전까지 ext 비어 있음 → 진행 중 ".mp4" 로 채워짐 → 완료까지 유지.
    - 보류: 다이얼로그의 통합 포맷 행 라벨을 소스에 따라 동적으로 바꾸는 것 ("최고 화질" vs "최고 음질") 은 별도 항목으로 분리 가능 — 본 항목은 표시 정직화에 집중.

- **모듈 분할 — 큰 파일의 응집도 점검과 헬퍼 추출**
    - 동기: `ui/download_item_widget.py` ~900줄, `workers/download_worker.py` ~750줄, `ui/main_window.py` ~700줄. 줄 수 자체보다 응집도 저하와 향후 분할 비용 증가가 우려.
    - 진단:
        1. `ui/download_item_widget.py` 모듈 최상위 `humanize_codec` / `format_bitrate` / `format_codec_segment` / `_VCODEC_PREFIX_MAP` / `_ACODEC_PREFIX_MAP` / `AUTO_FORMAT_ID` 6개 심볼은 표시 포맷 헬퍼로 위젯 본질이 아니며 `format_select_dialog` 도 이미 import 중. 응집도 다른 곳에 박혀 있다.
        2. `workers/download_worker.py` 모듈 최상위 `_normalize_token` / `_split_size_str` / `_normalize_size_str` / `_is_unknown_size` / `_parse_eta_secs` / `_format_eta_secs` / `_extract_codec_info` + `_UNKNOWN_TOKENS` 는 순수 문자열 파싱 유틸로 Qt 의존 없음. 워커 클래스와 분리 가능.
        3. 두 분할 모두 외부 결합 N≤2, 내부 상태 공유 없음 → 시기 민감도 낮음. 지금 하든 미루든 비용 거의 동일하나 의식이 또렷할 때 처리.
        4. `ui/main_window.py` 는 책임 6갈래(UI 구성·항목 추가 흐름·썸네일 라이프사이클·다운로드 위임·제거 흐름·업데이터) 가 같은 dict 4개(items / widgets / info_workers / _thumb_workers) 를 공유하는 시그널 라우팅 허브. 분할은 dict 소유권 재배치 + 별도 컨트롤러 신설이 필요한 재설계 수준. ADR-003 직후라 책임 경계가 안정화 중이므로 본 항목에선 제외.
    - 정책:
        1. `ui/codec_format.py` 신규 — download_item_widget 의 코덱 헬퍼 6개 심볼 이동. download_item_widget·format_select_dialog 둘 다 새 모듈에서 import. 동작 변경 없음.
        2. `workers/progress_parsing.py` 신규 — download_worker 의 모듈 최상위 유틸 8개 + `_UNKNOWN_TOKENS` 이동. 워커는 import 만. 동작 변경 없음.
        3. 워커의 ETA 평활화 메서드(`_decide_eta_source` / `_emit_eta` / `_maybe_emit_eta` / `_do_emit_eta`) 는 인스턴스 상태와 강결합이라 분할 보류.
        4. main_window 분할·stylesheet 모듈화·file_utils 의 psutil 그룹 분리는 본 항목 범위 밖. 중기/장기 항목으로 별도 관리.
    - 검증: 분할 후 `python main.py` 정상 기동 + 화질 선택·다운로드·재시도·취소·환경설정 동선 회귀 없음 + import 순환 없음.
    - 보류:
        1. main_window 분할 — ADR-003 의 후속 책임 안정화 후 별도 ADR 로 검토 (다음 마일스톤 이후).
        2. stylesheet 의 모듈/리소스 분리 — 장기 항목 "테마·스타일 옵션" 진입 시 함께 처리.
        3. file_utils 의 psutil 그룹(`snapshot_child_pids` / `terminate_pids`) 분리 — 양이 더 자라거나 프로세스 관리 유틸이 추가될 때.


### 3.3. 중기 (Mid-term, 다음 마일스톤)

- **포맷 선택 UX 개선** — "최고 화질 (자동·효율 우선)" 과 "최고 호환 (MP4/H.264)" 분리. 더불어 사용자가 비디오·오디오 컨테이너 (mp4/webm/mkv, mp3/m4a/opus 등) 를 직접 고를 수 있도록 다이얼로그 확장. ADR-002 의 결정과 함께 진행.

### 3.4. 장기 (Long-term, 백로그)

- **자동 업데이트 검증** — `utils/updater.py` 가 yt-dlp 신버전 감지 시 안전 갱신 확인.
- **다국어 지원** — i18n 도입 (한국어·영어 기본).
- **테마·스타일 옵션** — 라이트·다크·시스템 자동 전환.

---

## 4. ADR 인덱스

> 본문은 `ADR.md`. 항목 한 줄로 결정의 핵심을 알 수 있도록 요약하고, 펼침이 필요할 때만 raw URL 로 본문 로딩.

- **ADR-001** 썸네일 처리 — UI 미리보기와 파일 임베드의 분리 (Accepted, 2026-05-17) — UI 미리보기는 PySide6 GUI 스레드 전용, 파일 임베드는 yt-dlp/FFmpeg postprocessor 체인. 두 대상을 코드·문서·대화에서 명시 분리. → [ADR.md#adr-001](./ADR.md#adr-001)
- **ADR-002** 포맷 선택 — "최고 화질" 의미 분리 (Proposed, TBD) — `bestvideo+bestaudio/best` 의 VP9/AV1 우선이 사용자 기대(H.264 1080p) 와 어긋날 수 있어 "자동·효율 우선" 과 "최고 호환 MP4/H.264" 분리 검토. → [ADR.md#adr-002](./ADR.md#adr-002)
- **ADR-003** 다운로드 워커 오케스트레이션을 `DownloadManager` 로 분리 (Accepted, 2026-05-28) — `MainWindow` 의 다섯 책임 중 ③ 만 `controllers/` 로 떼어냄. 진행 시그널은 워커→위젯 직결, 라이프사이클만 매니저 경유. 큐는 `items` dict 삽입 순서. → [ADR.md#adr-003](./ADR.md#adr-003)
- **ADR-004** `process_ie_result` 우회 폐기, NFC 보존을 PostProcessor 정공법으로 (Accepted, 2026-05-28) — YouTube 토큰 만료 회귀(403) 해결. `ydl.download([url])` 복귀 + `_NFCNormalizePP(when="pre_process")`. `js_runtimes`/`remote_components` 고정 제거. 2026-05-18 결정 부분 번복. → [ADR.md#adr-004](./ADR.md#adr-004)
- **ADR-005** 오디오 후처리 정책 — 원본 보존 vs 비트레이트 통일 (Proposed, TBD) — `FFmpegExtractAudio` 의 192 kbps 일괄 적용이 고음질 원본을 다운컨버트하는 문제. 네 갈래 검토 (환경설정 노출 / 컨테이너만 변경 / 다이얼로그 드롭다운 / 조건부 확인). → [ADR.md#adr-005](./ADR.md#adr-005)
- **ADR-006** 플레이리스트 일괄 다운로드 — 글로벌 포맷 선택과 워커 시그널 규율 (Accepted, 2026-06-02) — 한 URL → 상한 500 경량 목록(`extract_flat`) → 체크박스 선택 다이얼로그 → 영상/음원 단일 선택 전체 적용. 정보추출은 다운로드 `max_concurrent` 공유 게이트. 워커 커스텀 시그널이 QThread 내장 `finished` 를 가리던 크래시를 시그널 개명(`download_finished`/`info_ready`/`thumb_ready`)으로 해소. → [ADR.md#adr-006](./ADR.md#adr-006)

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
- QThread 내장 시그널(`finished`/`started`) 은 같은 이름 커스텀 Signal 로 가리지 말 것 — 스레드 생존 중 GC 크래시 (ADR-006)

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
