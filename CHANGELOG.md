# Changelog

이 파일은 AV_Downloader 의 시간 역순 변경 이력을 누적합니다. [Keep a Changelog](https://keepachangelog.com/) 형식을 참고합니다.

각 항목 헤더 끝의 7자리 해시는 GitHub 저장소 `metapbl/AVD` 의 해당 커밋을 가리킵니다. 검증 절차·코드 진단 같은 상세는 git 커밋 메시지에 위임합니다.

로드맵·ADR·학습된 교훈은 [`WORKLOG.md`](./WORKLOG.md) 참고.

---

## 작성 규칙

- 최신이 위. 한 번 적은 줄은 지우지 않음 (오기 정정은 새 줄로 추가).
- 헤더 형식: `- **`type(scope)`** `7자리해시`: 한 줄 제목.` 해시 없으면 배지 생략.
- 본문 분량은 항목 성격에 따라:
    - **단순 항목** (chore/docs/짧은 fix): 헤더 한 줄로 끝. 본문 없음.
    - **일반 항목** (feat/fix 중간 규모): 본문 1~3줄. "무엇·왜" 만.
    - **결정 항목** (ADR 동반·이전 결정 번복·합의 과정 결정적): 본문 최대 8줄. 검증 절차·코드 진단은 git 커밋 메시지에 위임.
- "한도가 있으니 채우자" 는 금지. 1줄로 끝낼 수 있으면 1줄로 끝낸다.
- ADR 동반·번복은 헤더 끝에 `**(ADR-NNN)**` / `**(YYYY-MM-DD `해시` 부분 번복)**` 명시.
- 날짜 헤더는 `## YYYY-MM-DD`. 같은 날 여러 항목은 한 헤더 아래 묶음.
- 분류가 헷갈리는 항목은 사용자에게 확인 받고 작성.

---

## 2026-06-02

- **`feat(playlist)`** `e27f3fb`: 플레이리스트 일괄 다운로드 + 워커 QThread 시그널 섀도잉 크래시 해소. **(ADR-006)**
    - 한 URL 로 플레이리스트 N 개 항목 일괄 추가. `controllers/playlist_flow.py` 상태머신이 `PlaylistProbeWorker`(`extract_flat`, 상한 500)→`PlaylistSelectDialog`(체크박스·전체선택/해제·영상/음원 단일 선택)→선택 항목 큐 투입을 단일 소유. 항목별 화질 다이얼로그 생략, 다이얼로그 선택을 전체 적용. 음원 비트레이트는 `core/downloader.py` 단일 출처 위임.
    - 정보추출 동시성을 다운로드 `max_concurrent` 공유 게이트(`_info_pending`/`_info_running`)로 제한 — 단일·플레이리스트 항목 한 경로. 플레이리스트 항목은 목록 하단 삽입(추가 순서 보존), 단일 항목은 상단 유지.
    - 크래시 본수정: `DownloadWorker`/`InfoWorker`/`ThumbnailWorker` 가 QThread 내장 `finished` 를 동명 커스텀 Signal 로 가려, run() 종료 직전 워커가 GC 되며 "Destroyed while thread is still running" 발생. 결과 시그널을 `download_finished`/`info_ready`/`thumb_ready` 로 개명하고 객체·dict 정리를 QThread 내장 `finished` 에 연결. 동시 2 + 60 항목 MP3 완주 검증.
    - 알려진 잔여 버그(단기 과제로 이관): 동시 부하 시 리스트 썸네일 일부 누락(결과 파일은 정상), 403 시 수동 재시도 필요(자동 백오프 미구현).

## 2026-05-30

- **`docs(claude)`** `517b518`: 작업 흐름 7 에 메타 커밋 CHANGELOG 흡수 예외 명시.
- **`docs(adr)`** `6036984`: ADR-005 오디오 후처리 정책 재검토 추가 (Proposed).
- **`docs`** `329bfe0`: 단기 1번 완료 — 세 커밋(c8e66b1, 12a53c7, 9e64f02) 을 CHANGELOG 흡수, WORKLOG 섹션 3.2 항목 제거.

- **`feat(ui)`** `c8e66b1`: 다운로드 항목 메타 행에 컨테이너·코덱·비트레이트 추가.
  - `FormatInfo` 에 `vcodec`/`acodec`/`abr`/`tbr` 필드 신설. `_select_best_format` 이 고른 video/audio 포맷의 raw 값을 위젯에 전달, 코덱 표기 정규화 헬퍼(`avc1.* → H.264`, `mp4a.* → AAC` 등) 거쳐 "1920x1080 • MP4 • H.264 • Opus 160kbps" 형태로 표기. 오디오 전용 항목은 "MP3 192kbps" 단독.

- **`feat(ui)`** `12a53c7`: "자동" 선택 시 예측 메타 표시.
  - `format_id` 가 비어 있을 때(통합 포맷 `bv*+ba/b` 정책) `_predict_auto_meta` 가 정책 기준 가장 가능성 높은 컨테이너/코덱 조합(MP4+H.264+Opus) 을 예측해 "... • 자동" 접미사와 함께 표시. 사용자가 다운로드 전에 무엇이 받아질지 가늠 가능.

- **`feat(worker)`** `9e64f02`: 다운로드 완료 시 코덱·비트레이트 사후 갱신.
  - `DownloadWorker.codec_info_resolved` 시그널 신설, progress hook 의 `finished` 와 postprocess hook 의 각 단계 `finished` 에서 `info_dict` 의 `vcodec`/`acodec`/`ext`/`abr`/`tbr` 추출해 emit. `DownloadItemWidget.update_format_meta_resolved` 가 받아 실제 값으로 덮어쓰고 `_fmt_format_id` 비워 "자동" 분기에서 빠져나옴. `is_audio` 항목은 사후 갱신 거부 (MP3 비트레이트는 `MP3_BITRATE_KBPS` 단일 출처).

### 2026-05-29

- **`feat(ui)`** `be39920`: 제목 라벨 우측에 파일 확장자 표시 + 두 거짓 라벨 정정.
    - RichText 모드의 제목 라벨에 `#ffd060` 색으로 `.ext` 부착. 폭이 좁아 잘릴 때 확장자는 잘리지 않고 제목만 `ElideRight`, 잘림 시 줄임표 뒤 공백 1칸으로 점 4개 시각 충돌 회피.
    - 동반 정정: (1) `_parse_formats` 의 비디오 라벨이 yt-dlp raw ext (webm 등) 를 보여 주는데 실제 머지는 항상 mp4 인 거짓 라벨 → "1080p MP4" 로 통일. (2) yt-dlp 후처리의 m4a 자동 리네이밍(SoundCloud 등) 대응 — `_on_download_done` 에서 `Path(path).suffix` 로 실제 확장자를 읽어 위젯·항목에 동기화.

- **`docs(worklog)`**: WORKLOG 분량 감량 — ADR/LESSONS 본문을 별도 파일로 분리.
  - WORKLOG.md 의 섹션 4 (ADR) 본문을 신규 `ADR.md` 로 이관, 부록 A (학습된 교훈) 본문을 신규 `LESSONS.md` 로 이관. WORKLOG 섹션 4·5 는 한 줄 요약 + 안정 앵커 링크로 압축한 인덱스만 보유.
  - 압축 강도: ADR 은 결정/이유/결과/대안/관련 다섯 섹션 구조 유지하되 각 섹션 산문을 핵심 문장만 (A1 강도, 약 1/2 분량). LESSONS 는 시간순 번복으로 폐기된 항목을 `[역사적]` 표시로 보존하고 중복 진술 정리 (L1 강도, 약 80% 분량).
  - 안정 앵커 도입: 각 ADR 본문 첫 줄에 `<a id="adr-NNN"></a>`, LESSONS 각 그룹 첫 줄에 `<a id="lessons-그룹키"></a>` 명시. 2026-05-28 `docs(readme)` 의 "한글 헤더 앵커 안정성 미확인" 보류 사항 해소.
  - 두 파일 본문 첫 단락에 작성 규약 명시 — 항목당 분량(ADR 30 줄, LESSON 5 줄), 출처 표기, `[역사적]` 표시 정책, 디버깅 사연은 CHANGELOG 의 영역이라는 경계.
  - WORKLOG 의 잔재였던 Changelog 본문 텍스트도 함께 제거 (이전 분리 작업의 미완료 잔재). 현 WORKLOG 섹션 2 는 "별도 파일 안내" 한 문단만 보유.
  - CLAUDE.md: 섹션 4 폴더 구조에 `ADR.md`/`LESSONS.md` 두 줄 추가, 섹션 11.1 의 로딩 정책에 "기본 두 파일 + 작업 종류별 추가 로딩" 안내와 "자동 펼침 규칙" 한 문단 추가.

- **`docs`** `cc833a7`: `CLAUDE.md` 의 헤더·폴더 트리·작업 흐름·새 세션 안내 네 자리에 `CHANGELOG.md` 분리 사실 환기.

- **`docs`** `237ec76`: Changelog 를 `WORKLOG.md` 섹션 2 에서 `CHANGELOG.md` 로 분리.
    - 어제 약 580줄까지 자란 섹션 2 가 WORKLOG 의 다른 섹션(로드맵·ADR·교훈) 을 묻고 있던 문제 해소. 새 파일 상단에 작성 규칙(단순/일반/결정 3단 분량 한도, 분류 헷갈리면 사용자 확인) 명시.

- **`fix(ui)`** `00af8eb`: Fusion 스타일 적용으로 체크박스 렌더링 통일.
    - 커스텀 `QCheckBox::indicator` 가 체크 마크 글리프를 지정하지 않아 "파란 사각형" 만 보이던 문제를 `app.setStyle("Fusion")` 위임으로 해소. 두 다이얼로그(`preferences_dialog` / `confirm_remove_dialog`) 의 체크박스가 픽셀 단위로 일치.

- **`fix(worker)`** `b362f69`: fragment 다운로드 진행률 출렁임 제거.
    - DASH/HLS fragment 에서 raw pct (현재 fragment 내 진행률) 를 `((index - 1) + raw/100) / count * 100` 로 재계산해 구조적 단조 증가 보장. `_pct_floor` 보조 방어선으로 경계 케이스도 차단.

- **`fix(worker)`** `7e7a659`: ETA 막판 수렴 보장, 갱신 주기 단축, 추정 표기 한국어화.
    - EMA 에 비대칭 단조 하향 규칙 추가(raw 가 작으면 즉시 채택), finished 진입 시 ETA 명시 클리어, 스로틀 2초 → 0.5초. 추정 표지 `~` → `약 `. `d6168fd` 후속 보정.

- **`fix(worker)`** `d6168fd`: ETA 라벨 출렁임 안정화 — 소스 고정 + 시간 기반 EMA.
    - yt-dlp ETA 와 폴백 추정이 progress 콜백마다 번갈아 들어와 라벨이 분 단위로 튀던 현상을, 다운로드 시작 시 한 번 고른 소스를 끝까지 유지 + 콜백 빈도와 무관한 시정수 기반 EMA(`1 - exp(-dt / tau)`) 로 해소.

- **`fix(ui)`** `2c5ac0b`: 진행률·속도·ETA·크기 라벨 갱신을 DOWNLOADING 상태로 제한.

- **`docs(claude)`** `e49a381`: 새 세션 URL 을 blob 경로에서 raw.githubusercontent.com 으로 전환.

- **`docs(claude)`** `68922f3`: CLAUDE.md 준수 원칙을 "9 알려진 함정" 맨 앞에 명시.

## 2026-05-28

- **`docs(readme)`** `fa3beb3`: CLAUDE.md / WORKLOG.md 링크와 `controllers/` 구조, 최신 기능 요약 추가.
    - Python 버전 표기를 "3.10 이상 (3.13/3.14 권장)" 으로, OS 표기를 "Windows 11 개발·검증, macOS/Linux 제한적" 으로 명시.

- **`feat(ui)`** `725da69`: 다운로드 항목에 "현재 / 전체 크기" 표시.
    - `lbl_size` 신설, 같은 단위면 "48.20 / 128.50 MiB" 처럼 앞 단위 생략. 워커는 이전부터 emit 하고 있었으나 받는 슬롯이 없어 무시되던 상태였음.

- **`fix(info_fetcher)`** `9699ebc`: 썸네일 URL 선정 로직 안전화.
    - `info["thumbnail"]` 단일 필드 대신 `info["thumbnails"]` 배열에서 `(preference, width*height, 인덱스)` 점수로 best 직접 선택. YouTube `maxresdefault.jpg` 404 회귀 방어.

- **`chore`** `f179ffd`: `run.bat` 제거 — VS Code 통합 터미널 워크플로와 중복.

- **`fix(downloader)`** `1c06bfd`: mp3 컨테이너 잔재 메타 선별 제거.
    - ExtractAudio 단계에 `-metadata major_brand= / minor_version= / compatible_brands=` 빈 값 주입으로 ftyp 박스 잔재가 ID3 TXXX 로 복제되는 경로 차단. 2026-05-18 의 `-map_metadata -1` 부작용(TIT2 통째 소실) 없이 선별 제거 달성.

- **`fix(downloader)`** `316c642`: YouTube 토큰 만료 회귀 — `process_ie_result` 우회를 PostProcessor 정공법으로 대체. **(ADR-004, 2026-05-18 `bcef5d0` 부분 번복)**
    - 2026-05-18 의 NFC 보존 결정(`ydl.download` → `process_ie_result` 우회) 이 YouTube 토큰 정책 강화와 충돌해 `HTTP 403` 회귀. probe 단계에서 받은 format URL 의 nsig/sig 토큰이 download 시점엔 무효.
    - 처방: `ydl.download([url])` 복귀로 토큰 흐름 정상화. NFC 보존은 신규 `_NFCNormalizePP` (when="pre_process") 가 info dict 의 모든 문자열을 재귀적으로 NFC 화. ID3 TIT2 / m4a `©nam` / 파일명까지 NFC 보장.
    - 같은 PP 가 `meta_comment` 사전 주입으로 SoundCloud comment 가 URL 로 덮어쓰이던 문제도 해소. `js_runtimes` 명시 고정 제거(자동 탐지에 위임). 파일명 sanitize 도 yt-dlp 의 `windowsfilenames` + `trim_file_name` 에 위임.

- **`docs(claude/worklog)`** `3e23995` `0724ab6`: 두 문서의 형식 규칙 재정의.
    - 헤더 번호 체계(1, 1.1, 깊이 2), 코드 제시 규칙 단순화(함수 2개 이하 → 함수 단위, 그 외 → 파일 전체, 300줄 한도 폐지), 단기 항목 ✅ 누적 정책을 "완료 시 즉시 삭제" 로 변경. ADR-003 신설.

- **`feat(ui)`** `954152f`: 동시성 제어 큐 매니저 도입 + `MainWindow` 분할. **(ADR-003)**
    - `MainWindow` 의 워커 오케스트레이션을 신규 `controllers/download_manager.py` 의 `DownloadManager` 로 이관. 환경설정 슬라이더의 `max_concurrent` 가 실제 동시 다운로드 한도로 승격.
    - 정책 P: WAITING 항목은 `lbl_status` 에 "대기 중 (N번째)" 순번 표시(진행 중 항목은 카운트 제외). 정책 Y: WAITING 의 취소 버튼 숨김(진행 중이 아니므로 거짓말), 큐에서 빼기는 ✕ 단일 경로. 정책 A: 재시도도 큐 규칙 준수 — 슬롯 차 있으면 잠시 WAITING.
    - 별도 큐 자료구조 없음. `status == WAITING` 인 것이 곧 대기열이라는 단일 출처 원칙.
    - 합의 과정: 부분 발췌 가독성 문제로 분할 vs 전체 파일 두 안 중 분할 채택. refactor + feat 두 커밋 대신 응답 비용 고려해 단일 feat 커밋 채택.

- **`feat(ui)`** `8074e43`: 항목 레이아웃 단순화 — 80px 욱여넣기 + 제목 엘라이드.
    - 행별 `setFixedHeight` 로 결정론적 배치(26+16+16+16 + 간격 6 = 80). 진행률 바 두께 6→16, 위젯 전체 `setFixedHeight(96)`. 긴 제목은 `QFontMetrics.elidedText(ElideRight)` 로 라벨 폭에 맞춰 직접 잘라 표시.

- **`chore`** `019a420`: GitHub 저장소 이전 (`ggoyong2-ctrl/AV_Downloader` → `metapbl/AVD`), 로컬 폴더명 `AVD` 로 변경.

- **`docs(worklog)`** `acd1d4d`: 2026-05-27 의 환경설정 항목을 최종 구현(`cab59c5`)에 맞춰 정정 — 단색 3:3:4 컬러 바 사양이 그라데이션 + `ConcurrentSlider` 로 재설계됨을 명기.

## 2026-05-27

- **`feat(ui)`** `cab59c5`: 환경설정 다이얼로그 정비 — 동시 다운로드 슬라이더 + last_chosen_ext.
    - SpinBox → `ConcurrentSlider` (1~10, 기본 2, 트랙에 위치 안내 점 8개). 슬라이더 위 그라데이션 바(녹/노/빨 5-stop) + "권장/주의/비권장" 라벨. "기본 저장 형식" 콤보 제거 — `FormatSelectDialog` 의 `last_chosen_ext` 로 흡수.
    - 본 단계 슬라이더는 placebo. 실제 동시성 제어는 후속 `954152f` 에서 도입. (1차 푸시 `dd1113d` 후 같은 세션에서 재설계되어 `cab59c5` 로 재푸시.)

- **`feat(ui)`** `2860017`: 삭제·취소 확인 다이얼로그 통일 + "전체 취소" → "목록 비우기" 재정의.
    - 신규 `ui/confirm_remove_dialog.py` 가 개별 ✕ 와 일괄 정리를 공유. 본질 질문은 "목록에서 제거" 하나로 고정, 디스크 삭제는 옵셔널 체크박스로 분리. 기본 포커스 "닫기" 로 엔터 사고 방어.
    - "전체 취소" 라는 단어가 사용자 멘탈 모델("화면 청소") 과 어긋났던 점, Yes/No 가 두 개의 서로 다른 질문을 욱여넣고 있던 점을 해소. 시스템 정리 경로는 `skip_confirm=True` 로 다이얼로그 우회.

- **`fix(ui)`** `0945aed`: 취소·에러 상태 진입 시 진행률 바를 0 으로 초기화 — 멈춘 막대가 "재시도" 라벨과 모순되던 점 해소.

- **`feat(ux)`** `e15280b`: 취소·재시작·삭제 동선 정비 (잔여물 정리 + 자식 프로세스 종료 + 재시도 + 조건부 파일 삭제).
    - yt-dlp 두 후크가 알려준 모든 경로를 `_touched_files` 에 누적, 취소·에러 시 `.part`/`.ytdl` 형제와 함께 일괄 삭제. 추측 경로는 안 씀 — 명시적으로 알려준 경로만 신뢰.
    - 워커 진입 시 자식 PID 스냅샷, 종료 시 차분만 `terminate()` → 5초 → `kill()`. 동시 다운로드 환경에서 남의 자식 안 잡는 게 핵심 (psutil).
    - `postprocess_hook` 도 wrap 해서 머지·임베드·MoveFiles 단계 취소 가능. 버튼 라벨이 `item.status` 단일 출처로 "취소"↔"재시도" 토글. `psutil==6.1.0` 추가.

## 2026-05-25

- **`fix(ui)`** `194ae91`: 영상 길이가 항상 `0:00` 으로 표시되던 버그 해결.
    - `update_meta(uploader, duration)` 신설. 위젯 생성 시점엔 InfoWorker 가 끝나기 전이라 `_build_ui` 가 `0:00` 으로 박고, 이후 `lbl_meta` 를 다시 그릴 경로가 없어 굳어 있었음.

## 2026-05-18

- **`fix(downloader)`** `6c37016`: HLS(SoundCloud 등) 출처에서 남은시간 "Unknown" 해결.
    - `_eta_str` 이 비었거나 unknown placeholder 일 때 `_percent_str` 기반 `pct` 와 측정 `elapsed` 로 ETA 직접 추정해 `~M:SS` 형식으로 emit. HLS 는 `total_bytes` 가 없어 yt-dlp 내부 ETA 산식이 성립하지 않는 게 원인.

- **`fix(downloader)`** `93578c3`: `fragment_retries` 에 `'infinite'` 문자열 대신 `float('inf')` 사용 — CLI 는 변환하지만 ydl_opts 직접 구성 시는 변환 안 됨.

- **`fix(downloader)`** `f32eb27`: yt-dlp retry/timeout 강화 — `Read timed out` 회복력.
    - `_BASE_OPTS` 에 `socket_timeout=30`, `retries=10`, `fragment_retries='infinite'`, `file_access_retries=5`, 지수 백오프(30s 캡) 추가.

- **`fix(downloader)`** `bcef5d0`: NFC 메타데이터를 yt-dlp 의 정상 경로로 흘려보내는 구조로 재구성. **(2026-05-28 `316c642` 부분 번복)**
    - 본 다운로드를 `ydl.download` → `process_ie_result(probed, download=True)` 로 교체. `FFmpegMetadataPP` 가 info dict 의 `title`/`artist` 를 그대로 `-metadata` 로 변환하므로 NFC dict 가 후처리 체인에 그대로 흘러감.
    - mp3 분기의 `-map_metadata -1` 제거 — m4a ftyp 잔재를 끊는 본래 목적은 달성했으나 같은 ffmpeg 호출의 `-metadata title=…` 까지 무효화해 TIT2 가 통째로 사라지던 부작용.

- **`fix(downloader)`** (해시 없음, 중간 단계): 모든 오디오 추출에 NFC 메타 우회로 확장 시도 — `if ext == "mp3"` → `if is_audio`. m4a 는 ffmpeg 호출 단계 분리로 미적용, 이후 `bcef5d0` 으로 근본 해결.

- **`fix(downloader)`** (해시 없음, 1차 시도): 유니코드 NFC 정규화 + MP3 컨테이너 잔재 메타 제거 첫 시도. `normalize_unicode` / `normalize_info_dict` 헬퍼 도입, mp3 한정 `-map_metadata -1` + `-metadata title=…` 우회로. 이후 `bcef5d0` 으로 대체.

- **`docs(claude)`** `fa3e60e`: 코드 제시 규칙을 변경 규모 기준으로 재정의 + 터미널 명령 동반 제시 규칙 신설 + VS Code 통합 터미널 명시.

- **`docs(worklog)`** `7f3a3ba`: 사이드 메모 세 건(파일명·ID3 NFC / MP3 major_brand / Read timed out) 단기 섹션에 기록. 학습된 교훈에 `yt-dlp` / `유니코드·파일명` 카테고리 추가.

## 2026-05-17

- **`docs(claude)`** `6f1899b`: "새 세션 시작 방법" 섹션을 환경별(claude.ai 웹 / Claude Code) 안내로 개정. 웹 채팅은 raw URL 던지기 방식.

- **`fix(ui)`** `05aa94f`: 다운로드 진행률을 "N.N% 다운로드 중" 형식 상태 라벨에 표시.
    - postprocess 후크에서 `Merger` 만 머지로 인식하도록 좁힘 — 기존엔 `ThumbnailsConvertor` 의 `started` 에서도 머지 시그널이 발사돼 라벨이 잠기던 UX 버그. `update_progress` 가드로 DOWNLOADING 상태에서만 갱신.

- **`docs(claude)`** `7f78c71`: 코드 제시 규칙에 300줄 기준과 변경 지점 명시 규칙 추가. (이후 `0724ab6` 가 한도 폐지.)

- **`fix(utils)`** `6cb671e`: `format_duration` float/None 안전 처리 + `strip_ansi` 헬퍼 추가.

- **`fix(ui)`** `10cebbf`: yt-dlp 진행률 메시지의 ANSI 컬러 코드 제거 — 출구 단계 방어선.

- **`docs(claude)`** `58d867e`: Claude 협업 규약 3줄 추가 (소스 코드 참조 / 코드 들여쓰기 / 코드 제시 전 확인).

- **`feat(downloader)`** `e4f168c`: 다운로드 파일에 썸네일·메타데이터 임베드 추가. **(ADR-001)**
    - `EmbedThumbnail` + `FFmpegMetadata` + `FFmpegThumbnailsConvertor` (webp→jpg) 후처리기 체인. MP3 는 `-id3v2_version 3 -write_id3v1 1` 강제 (Windows 탐색기·구형 음악 플레이어 호환).

- **`fix(ui)`** `596e012`: 워커 라이프사이클, 스레드 안전성, 취소 가드 정비. **(ADR-001)**
    - 썸네일 워커의 QPixmap 생성을 워커 스레드 → GUI 스레드로 이동, `ThumbnailWorker` 에 `item_id` 추가(늦은 시그널 오배달 방지), `_thumb_workers` list → dict + `cancel()`. `DownloadWorker` 의 취소 예외를 `isinstance(DownloadCancelled)` 로 판정.

- **`chore`** `3e35f67`: `.vscode/` 를 `.gitignore` 에 추가.

- **`docs`** `5a3ca58`: 작업 로그 시스템을 Keep a Changelog + ADR 형식으로 재구조화. `CLAUDE.md` 신규 + `WORKLOG.md` 분리. 협업 모델을 Opus 4.7 단일 체계로 명시.

- **`docs`** `a6edd68`: Node.js 요구사항을 README 에 명시 (yt-dlp EJS 메커니즘).

- **`chore`** `9afd196`: 레포 URL 수정, README 본격 작성, `requirements.txt` UTF-8 정상화 (PowerShell `>` 의 UTF-16 LE BOM 사고 복구).

- **`feat`** `f05478e`: 최초 푸시 (yt-dlp 기반 미디어 다운로더). 초기 골격은 Claude Sonnet 4.6 작업.
