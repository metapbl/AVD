# REFERENCE — AV_Downloader (AVD)
<!-- 필요할 때 검색해 읽는다. 참조는 R§n, 코드 위치는 파일 > 함수. -->

## R§1 아키텍처
- 흐름: URL 입력(클립보드 감지) → `InfoWorker`(정보 추출) → 포맷 선택 다이얼로그 → `DownloadManager.enqueue` → 슬롯이 나면 `DownloadWorker` 시작 → yt-dlp 다운로드·후처리(병합·메타·썸네일 임베드) → MP3 면 `gaindb` 음량 정규화 → 완료
- 진행 시그널은 워커 → 위젯 직결, 라이프사이클(시작·종료·취소)만 매니저 경유 (D005)
- `main.py` — QApplication, Fusion 스타일, `MainWindow` 기동
- `ui/main_window.py` > `MainWindow` — UI 구성·항목 추가·썸네일·제거·업데이터의 시그널 허브 (items/widgets dict 소유)
- `controllers/download_manager.py` > `DownloadManager` — 대기열과 동시성. `active_count` 는 MERGING·NORMALIZING 을 슬롯에서 제외, `_dispatch_next` 로 다음 항목 출발
- `controllers/playlist_flow.py` > `PlaylistFlow` — 플레이리스트 경량 목록(상한 500) → 선택 다이얼로그 → 일괄 등록 (D007)
- `workers/download_worker.py` > `DownloadWorker.run` — 세션 단위 재시도 루프(`_is_transient_error`, 2→5→10초, 최대 3회), 진행률·ETA 파싱, MP3 정규화 호출 (D008, D009)
- `workers/info_worker.py` > `InfoWorker`, `thumbnail_worker.py` > `ThumbnailWorker`, `playlist_probe_worker.py` > `PlaylistProbeWorker`, `update_worker.py` > `UpdateWorker`
- `core/downloader.py` > `Downloader.download` — `YoutubeDL` 옵션 구성, `_NFCNormalizePP`(pre_process) 등록 (D006)
- `core/info_fetcher.py` > `InfoFetcher.fetch` — `VideoInfo`/`FormatInfo` 생성
- `utils/config_manager.py` > `ConfigManager` — 앱 폴더 `config.json`, `DEFAULT_CONFIG` 병합
- `utils/updater.py` > `YtdlpUpdater` — 기동 시 yt-dlp 갱신 (D002) / `AppUpdater`
- `utils/file_utils.py` — `sanitize_filename`, `normalize_unicode`, `get_unique_path`, `snapshot_child_pids`·`terminate_pids`(취소 시 ffmpeg/Node 정리)
- `gaindb/api.py` > `apply_file_track_gain`, `analyze_file` — 본체가 부르는 유일한 경계 (D017)

## R§2 외부 사양·제약
- yt-dlp (핀 2026.3.17, 기동 시 최신화): YouTube 는 JS 런타임(Node/Deno/Bun) 필요, 런타임 고정하지 않는다 (출처: https://github.com/yt-dlp/yt-dlp/wiki/EJS)
- yt-dlp 후처리 체인 (2026.3.17 기준): `ThumbnailsConvertor → Merger → Metadata → EmbedThumbnail → MoveFiles`. `postprocessor_hook` 은 started/finished 만, 퍼센트 없음
- yt-dlp `retries` 는 세션 내 HTTP 재시도일 뿐 — 토큰 만료 403 은 새 `YoutubeDL` 세션으로만 회복 (D008)
- yt-dlp 지원 사이트: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md — sendvid 는 전용 추출기 없음, 범용 추출기 (Q026, 2026-10-28)
- ffmpeg/ffprobe: 번들하지 않음, PATH 필수. 병합·변환·메타·썸네일 임베드
- PySide6 6.12.0 (LGPLv3, 동적 링크), `requires_python <3.16,>=3.10` (PyPI, Q030)
- numpy 2.5.x·scipy 1.18.x: `requires_python >=3.12` → AVD 하한 3.12 (D028)
- gaindb 0.5.1 (LGPL-2.1-or-later, 상류 https://github.com/metapbl/GainDB): 배포 시 평문 `.py`·소스 첨부 의무 (D011)

## R§3 설계 근거
<!-- 내용은 docs/discovery/DECISIONS.md에 있다. 여기는 색인만. -->
- D002 — yt-dlp 저버전 핀 유지, 기동 시 자동 업데이트로 최신화
- D004 — 썸네일: UI 미리보기(GUI 스레드)와 파일 임베드(postprocessor) 분리
- D005 — 라이프사이클은 DownloadManager, 진행 시그널은 워커→위젯 직결
- D006 — NFC 는 `pre_process` PostProcessor, `ydl.download([url])` 사용
- D007 — 플레이리스트: 상한 500 경량 목록, 단일 포맷 일괄
- D008 — 세션 단위 재시도, 일시적 오류만 2→5→10초 최대 3회
- D009 — MP3 음량 정규화(GaindB 트랙 모드 89dB), 실패해도 다운로드는 성공
- D011 — 배포 PyInstaller onedir, gaindb 평문, 릴리스마다 소스 첨부
- D013 — 워커는 bytes 까지, QueuedConnection 명시
- D015 — gaindb 상류 무수정
- D017 — 본체 MIT, gaindb LGPL (폴더 경계 이중 라이선스)
- D023 — pytest 는 Qt 무관 순수 함수 특성 테스트부터
- D027 — Python 3.15 venv, PySide6 6.12.0·numpy 2.5.4·scipy 1.18.1
- D028 — 지원 Python 하한 3.12
- D033 — 첫 계획 완료 조건 (성공 기준·F11 기동 실패만 미완)

## R§4 함정 대장
| ID | 증상 | 원인 | 대처 | 근거 |
|---|---|---|---|---|
| T1 | 썸네일 QLabel 이 빈 화면, `isNull()` 은 False | 워커 스레드에서 QPixmap 생성 | 워커는 bytes 만 emit, GUI 스레드에서 변환 | ADR-001 |
| T2 | "QThread: Destroyed while thread is still running" 크래시 | 커스텀 Signal `finished` 가 내장 시그널을 가려 run() 종료 전 GC | 결과 시그널은 `download_finished` 등으로 명명, 정리는 내장 `finished` 에 연결 | ADR-006 |
| T3 | 같은 세션 재시도가 계속 403 | YouTube 토큰 만료는 `retries`(HTTP 재시도)로 안 풀림 | 새 `YoutubeDL` 세션으로 전체 재시작 | ADR-007 |
| T4 | 404 영상을 헛재시도 | `Unable to download webpage: HTTP Error 404` 가 일시 패턴에 걸림 | 영구 4xx(400/401/404/410)를 일시 패턴보다 먼저 검사. 403·429 는 일시 | ADR-007 |
| T5 | 사전 가공한 info dict 가 무시되거나 403 회귀 | `ydl.download` 가 `extract_info` 재실행 / `process_ie_result` 우회는 토큰 만료 | `pre_process` PostProcessor 로 가공 | ADR-004 |
| T6 | 미리보기 썸네일이 영영 빔 | `maxresdefault.jpg` 가 없는 영상에서 404 | 후보 리스트 순차 폴백, 최후 `hqdefault` | 2026-07-09 |
| T7 | MP3 한글 태그가 `?뱀떊…` 로 깨짐 | `-write_id3v1 1` — ID3v1 은 인코딩 필드 없음, 한글 Windows 가 CP949 로 읽음 | ID3v1 기록 안 함 (v2.3 UTF-16 만). 단 yt-dlp 자체가 mp3 에 `-write_id3v1 1` 을 붙여 v1 은 남는다 — 탐색기는 v2 를 읽어 정상 (2026-10-28 확인) | 37855ee |
| T8 | MP3 '주석'만 깨짐 | ffmpeg 가 comment 를 비표준 `TXXX:comment` 로 씀 | `meta_comment` 를 빈 문자열로 → 프레임 미생성 | 21ccde9 |
| T9 | 한글이 자모로 분리됨 | 소스 사이트·OS 경계에서 NFD 유입 | info dict 진입점 NFC 통일. 판정은 파일 원본 바이트로 (콘솔·VS Code 는 결합해 보여 속는다) | ADR-004 |
| T10 | m4a→mp3 에 엉뚱한 TXXX(major_brand 등) | ExtractAudio 의 기본 `-map_metadata 0` | `-map_metadata -1` 은 TIT2 까지 지움 → `meta_<key>` 주입으로 선별 | LESSONS |
| T11 | 커밋 작성자가 도구 내장 주소로 바뀜 (25개 누적) | 전역 `user.email` 없음 → 도구가 자기 주소 사용 | 리포 로컬 작성자 고정 + push 전 `git log -1 --format="%an <%ae>"` | fbbccbf |
| T12 | git 이 requirements.txt 를 바이너리로 봄 | PowerShell `>` 가 UTF-16 LE BOM 으로 씀 | `Out-File -Encoding utf8` | LESSONS |
| T13 | 백업 브랜치까지 재작성됨, origin 사라짐 | `git filter-repo` 동작 | `git bundle create ..\repo.bundle --all` 로 리포 밖 백업 | fbbccbf |
| T14 | 문서 속 커밋 해시가 유령 참조 | 히스토리 재작성 | `commit-map` 으로 일괄 치환 후 `git cat-file -t` 전수 확인 | fbbccbf |
| T15 | HLS 에서 ETA 안 나옴 | `total_bytes`·`total_bytes_estimate` 모두 없음 | placeholder 감지 + 진행률×경과시간 추정 `~M:SS` | LESSONS |
| T16 | 체크박스 ✓ 가 안 그려짐 | `QCheckBox::indicator` 직접 스타일링 | `setStyle("Fusion")` 먼저, indicator 스타일링 피함 | 2026-05-29 |
| T17 | exe 에서 yt-dlp 업데이트하면 AVD.exe 가 하나 더 뜸 | 동결 빌드의 `sys.executable` 은 AVD.exe → `[sys.executable, "-m", "pip", …]` 가 앱 실행 | `sys.frozen` 이면 pip 대신 `install_ytdlp_wheel` (D038). `sys.executable` 로 하위 파이썬을 띄우는 코드는 frozen 분기 필수 | 2026-10-29 |

## R§5 환경·도구
- Windows 11, PowerShell 7 (`pwsh`), VS Code (Ruff 저장 시 fixAll, `.vscode/settings.json`)
- Python: 이 PC 에는 3.15.1 하나 (`py -0p`, Python install manager). venv 는 `py -3.15 -m venv venv`
- `.gitignore` 는 이미 추적 중인 파일에 무효 → `git rm --cached <path>`
- `git diff` 가 `:` 에서 멈추면 페이저 — `git --no-pager diff`
- 동시 다운로드는 단일 프로세스 yt-dlp 특성상 1~3개가 안정 (기본 2)

## R§6 UI·작업 원칙 (D019)
- 같은 낱말이 두 대상을 가리키면 대상부터 확정한다 ("썸네일" — ADR-001)
- 진단 코드(print·임시 파일)는 가설 검증 후 즉시 제거, 커밋에 섞지 않는다
- 가설은 한 번에 하나씩 검증한다
- 확인 다이얼로그는 질문 하나 + 부가 옵션(체크박스). 두 결정을 Yes/No 하나로 묶지 않는다
- 버튼 라벨은 실제 동작대로 쓴다 ("전체 취소"가 진행 중만 취소하던 사례)
