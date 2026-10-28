# QA_LOG — 질의응답 원장

<!-- 추가만 한다. 고치거나 지우지 않는다. 정정은 새 항목으로 쓰고 이전 Q번호를 적는다. -->
<!-- 전체를 읽지 않는다. 필요한 Q번호나 낱말로 검색한다. -->

## 양식

### Q001 · YYYY-MM-DD · 단계 1 · [U]
Q: 질문
A: 답 (사용자 표현 그대로, 길면 요약하고 "요약" 표시)
→ D001 확정 | OPEN Q005 추가 | 없음

- 출처가 [X]인 항목은 A에 근거 파일과 위치를 적는다. 예: `src/app.py > main`
- 출처가 [AI]인 항목은 A에 "AI 기본값"과 이유를 적고 OPEN의 재확인 칸에 올린다.

---

### Q001 · 2026-10-28 · 단계 0 · [X]
Q: 무엇을 만드는가
A: yt-dlp 기반 영상·오디오 다운로더, PySide6 다크 테마 데스크톱 GUI. yt-dlp 지원 사이트 전반. 출처: `README.md > 머리`, `CLAUDE.md > 1`
→ PRD §1 초안

### Q002 · 2026-10-28 · 단계 0 · [X]
Q: 누가, 어떻게 배포하는가
A: 1인 개발자 + AI 페어. GitHub 오픈소스 비영리 무료 공개, 유료 판매 없음. 출처: `CLAUDE.md > 2`, `README.md > 배포 방침`
→ D012

### Q003 · 2026-10-28 · 단계 0 · [X]
Q: 현재 구현된 기능
A: 요약 — 영상/오디오(MP3·M4A) 다운로드와 메타데이터·썸네일 임베드, 포맷 선택 다이얼로그(직전 확장자 기억), 동시 다운로드+대기열(슬라이더), 진행률·속도·ETA(HLS 추정 `~M:SS`), 클립보드 URL 감지, yt-dlp 자동 업데이트(비동기 모달), 취소·재시도·파일 동시 삭제·부분파일 정리, NFC 정규화, 플레이리스트 일괄(상한 500), 자동 재시도(최대 3회), MP3 음량 정규화(GaindB), 봇 차단 안내. 출처: `README.md > 주요 기능`, `ADR.md`, `CHANGELOG.md`
→ PRD §3 초안

### Q004 · 2026-10-28 · 단계 0 · [X]
Q: 기술 스택과 실행 환경
A: Python ≥3.10(개발 3.13/3.14), PySide6 6.11.1, yt-dlp 2026.3.17(의도적 저버전 핀), ffmpeg/ffprobe PATH 필수, Node.js(EJS) 사실상 필수, numpy·scipy·psutil·requests. Windows 11 개발·검증, macOS 는 실행만(일부 미동작). 출처: `requirements.txt`, `CLAUDE.md > 3·5`, `README.md > 요구 사항`, `WORKLOG.md > 3.1·3.2`
→ D001~D003, D016

### Q005 · 2026-10-28 · 단계 0 · [X]
Q: 확정된 아키텍처 결정
A: ADR-001(썸네일 UI/임베드 분리), 003(DownloadManager 분리), 004(NFC PostProcessor), 006(플레이리스트), 007(세션 재시도), 008(GaindB 통합), 009·010(이중 라이선스) Accepted. ADR-002(최고 화질 의미 분리)·005(오디오 비트레이트 정책) Proposed. 출처: `ADR.md`, `WORKLOG.md > 4`
→ D004~D010, Proposed 2건은 OPEN 후보

### Q006 · 2026-10-28 · 단계 0 · [X]
Q: 라이선스·법적 제약
A: 본체 Apache-2.0(META PUBLIC), `gaindb/` LGPL-2.1-or-later. 배포물은 onedir(onefile 금지), `gaindb/` 평문 .py, 릴리스마다 소스 아카이브 첨부. DRM 우회·유료 콘텐츠 무단 접근 기능 금지. 출처: `README.md > 라이선스·배포 방침`, `ADR.md > ADR-010`, `WORKLOG.md > 3.1`
→ D010~D012

### Q007 · 2026-10-28 · 단계 0 · [X]
Q: 진행 중·다음 할 일
A: 진행 중 — LGPL 배포 산출물 정비(미착수), 2026-07-09 작업분 실기 검증(`docs/VERIFY_2026-07-09.md`). 단기 — macOS 실행 정식화, 병합 진행률 표시, 확장자 표시 정직화, 모듈 분할. 중기 — 일시정지/재개(보류), 포맷 선택 UX(ADR-002). 장기 — 쿠키 지원, 업데이트 UX 실기 검증, 다국어, 테마. 출처: `WORKLOG.md > 3`
→ PROGRESS·OPEN 후보

### Q008 · 2026-10-28 · 단계 0 · [X]
Q: 검증·도구
A: 자동 테스트 없음(tests/ 없음, pytest 미설치). 린터는 VS Code 저장 시 Ruff fixAll 만(`.vscode/settings.json`), ruff 설정 파일 없음. 검증은 사용자 실기(절차서 방식). 출처: 폴더 구조, `.vscode/settings.json`, `docs/VERIFY_2026-07-09.md`
→ PRD §6 빈칸, OPEN 후보

### Q009 · 2026-10-28 · 단계 0 · [X]
Q: 작업 방식 규칙
A: Conventional Commits, 의미 단위 즉시 커밋, 커밋 후 CHANGELOG 맨 위 추가, 큰 결정은 ADR, 작성자 `metapbl <ggoyong2@gmail.com>` 고정·push 전 확인, 워커→메인 QueuedConnection, 워커 스레드 QPixmap 금지, 타입 힌트 `self.x: list = []`, `gaindb/` 상류 무수정. 출처: `CLAUDE.md > 6·7`, `WORKLOG.md > 3.1`
→ D013~D015, 새 CLAUDE.md 후보

### Q010 · 2026-10-28 · 단계 0 · [X] · 문서≠코드
Q: WORKLOG 3.2 "병합 중 항목의 동시성 슬롯 점유 해제"는 미완인가
A: 코드는 이미 구현됨 — `controllers/download_manager.py > active_count` 가 MERGING·NORMALIZING 을 슬롯에서 제외(커밋 c5c4a3c). 로드맵 항목이 낡음.
→ 코드를 사실로 봄. PROGRESS 로 옮기지 않음

### Q011 · 2026-10-28 · 단계 0 · [X] · 문서≠코드
Q: config.json 위치
A: README 는 "사용자 설정 폴더"라 하나 코드는 앱 폴더(`utils/config_manager.py > CONFIG_PATH = 프로젝트 루트/config.json`). `theme`·`language` 키는 기본값만 있고 UI 노출 여부 미확인.
→ 코드를 사실로 봄. README 수정은 구현 단계 후보

### Q012 · 2026-10-28 · 단계 0 · [X] · 문서≠코드
Q: CLAUDE.md 폴더 구조·로컬 경로
A: CLAUDE.md §4 에 `gaindb/`, `controllers/playlist_flow.py`, `ui/playlist_select_dialog.py`, `ui/update_progress_dialog.py`, `workers/playlist_probe_worker.py`, `workers/update_worker.py`, `assets/`, `docs/` 누락. 로컬 경로 기재 `C:\Users\ggoyo_zhxlvdr\AVD` ≠ 현재 `C:\Users\Administrator\My Projects\AVD`. README "문서" 절도 WORKLOG 가 ADR·교훈 본문을 담던 시절 서술.
→ 새 CLAUDE.md·REFERENCE 는 실제 구조로 작성

### Q013 · 2026-10-28 · 단계 0 · [X]
Q: 큰 파일
A: `ui/main_window.py` 1057줄, `ui/download_item_widget.py` 929줄, `workers/download_worker.py` 867줄. 출처: `wc -l`
→ 모듈 분할 로드맵 근거 유지

### Q014 · 2026-10-28 · 단계 0 · [U]
Q: adopt 되짚기 — 추출 사실 1~6, 문서≠코드 7~9, 버림 B1~B9 중 틀린 번호
A: "모두 맞구요"
→ D001~D016 확정. ADOPT_MAP 판단 보류 3건은 미결 유지

### Q015 · 2026-10-28 · 단계 0 · [U]
Q: (사용자 질문) 본체 라이선스를 Apache-2.0 에서 MIT 로 바꿀 수 있는가
A: 답변함 — 가능. 근거: 커밋 작성자 전원 metapbl 1인(`git shortlog`), 본체에 타인 Apache 코드 없음, 의존성 제약 없음. `gaindb/` 는 LGPL 유지 필수. 대가는 명시적 특허 허여 상실(ADR-009 의 남은 유일한 근거)과 이미 배포한 Apache 판 철회 불가. 결정은 사용자 대기
→ OPEN 후보 (D010 재검토 여부)

### Q016 · 2026-10-28 · 단계 0 · [U]
Q: 본체 라이선스 — Apache-2.0 유지(추천) / MIT 전환
A: "본체 라이선스를 MIT 로 전환하겠습니다. 결정 기록과 함께 진행해 주세요."
→ D017 확정, D010 대체. 파일 변경(LICENSE·NOTICE·README, 관련 문서 서술)은 PRD 승인 후 계획 단계의 작업으로 넣는다

### Q017 · 2026-10-28 · 단계 0 · [U]
Q: 판단 보류 3건 — 서식 규칙 유지 / 협업 교훈 REFERENCE 보존 / CHANGELOG 계속 (모두 추천안)
A: "판단 보류 3건 모두 추천대로 해 주세요."
→ D018, D019, D020 확정

### Q018 · 2026-10-28 · 단계 0 · [U]
Q: [관문] 기존 문서 4개(CLAUDE·WORKLOG·ADR·LESSONS) docs/legacy/ 이동 승인
A: "승인합니다. legacy 로 옮기고 OPEN 을 만들어 진행해 주세요."
→ git mv 완료, OPEN.md 생성 (O01~O08)

### Q019 · 2026-10-28 · 단계 0 · [X]
Q: 앱 로그 체계
A: 없음. `import logging` 은 `utils/file_utils.py` 하나뿐. 출처: grep
→ OPEN O08

### Q020 · 2026-10-28 · 단계 1 · [U]
Q: 성공 기준 — 관찰 가능한 장면 하나 (추천: YouTube URL → 화질 선택 → 한글 제목 파일 저장, 탐색기에서 썸네일·한글 태그 정상)
A: "성공 기준은 추천안대로 해 주세요."
→ D021 확정, OPEN O01 해결

### Q021 · 2026-10-28 · 단계 1 · [U]
Q: [되짚기] 단계 1 목적 — 무엇(X)·누가(X)·성공 기준(U)·수명 계속 유지(AI)
A: "맞습니다. 단계 2로 진행해 주세요."
→ PRD §1 확정, 수명 재확인 해소

### Q022 · 2026-10-28 · 단계 2 · [U]
Q: 첫 계획 범위 — 1 MIT·문서 정합 / 2 pytest 특성 테스트 / 3 07-09 실기 검증 / 4 LGPL 배포 / 5 표시 개선 / 6 구조·macOS (추천: 1·2·3 → 4 → 5·6)
A: "추천대로"
→ D022, D023 확정. OPEN O02·O04 해결

### Q023 · 2026-10-28 · 단계 2 · [U]
Q: [되짚기] 단계 2 범위 — 계획 순서·pytest(U), 현 기능 필수·일시정지 제외·반목표 3·theme/language 잔존 키(X), 보류 4건(AI)
A: "맞다"
→ PRD §2 확정

### Q024 · 2026-10-28 · 단계 3 · [U]
Q: 인수 기준 범위(손대는 작업만) + 첫 계획 기준 초안 1~10
A: "네 추천대로 하되, yt-dlp 라이브러리 깃허브 사이트에서 말하는 지원되는 다른 사이트들에 대한 검증도 필요하지 않나 생각하는데 그대의 생각은 어떻습니까"
→ D024, D025 확정. 다른 사이트 검증은 OPEN O09 로 질문

### Q025 · 2026-10-28 · 단계 3 · [U]
Q: 표본 실기 점검 사이트 (O09)
A: "sendvid도 추가했으면 합니다. 추천 표본을 조금 더 늘릴수있을가요?"
→ O09 에 sendvid 포함 확정, 확장 표본안 제시 (승인 대기)

### Q026 · 2026-10-28 · 단계 3 · [X]
Q: sendvid 를 yt-dlp 가 지원하는가
A: 전용 추출기 없음 — 상류 `supportedsites.md` 에 sendvid 항목 없음, `yt_dlp/extractor/sendvid.py` 404 (2026-10-28 master 기준). generic(범용) 추출기로만 시도됨 → 동작 여부는 실기로만 판단 가능. Dailymotion·Bandcamp·Naver·Kakao·chzzk·archive.org·Vimeo·SoundCloud 는 전용 추출기 있음.
→ 표본에서 sendvid 는 "범용 추출기 경로" 대표로 둠

### Q027 · 2026-10-28 · 단계 3 · [X] · 환경
Q: 이 PC 에서 앱·테스트를 돌릴 Python 환경
A: `venv/` 가 깨져 있음 — `pyvenv.cfg` 의 `home = C:\Python314` 가 이 PC 에 없음(이전 PC `C:\Users\ggoyo_zhxlvdr\AVD` 에서 만든 venv 를 복사). PATH 의 `python` 은 MS Store 3.15.1, yt_dlp 미설치.
→ OPEN O10 (venv 재생성) — pytest 작업(F9)·실기 검증의 선행 조건

### Q028 · 2026-10-28 · 단계 3 · [U]
Q: 표본 8개 사이트안 확정 여부
A: "이대로 확정"
→ D026 확정, OPEN O09 해결

### Q029 · 2026-10-28 · 단계 3 · [U]
Q: [되짚기] 단계 3 기능 — 1~5(U), sendvid 범용 추출기(X), 테스트 대상 함수 위치(X)
A: "맞다"
→ PRD §3 확정

### Q030 · 2026-10-28 · 단계 4 · [X] · 환경
Q: 이 PC 의 Python 3.15.1 로 현 requirements 를 설치할 수 있는가
A: 불가. PyPI 확인(2026-10-28) — PySide6/shiboken6 6.11.1 은 `requires_python <3.15`, numpy 2.5.1·scipy 1.18.0 은 cp315 휠 없음(최고 cp314). 3.15 지원판은 PySide6 6.12.0, numpy 2.5.4, scipy 1.18.1. `py -0p` 결과 설치된 Python 은 3.15 하나뿐(Python install manager 경로).
→ venv 재생성 방식 안 비교 (O10)

### Q031 · 2026-10-28 · 단계 4 · [U]
Q: venv 재생성 — A안 Python 3.14 추가 설치·requirements 불변(추천) / B안 3.15 에 맞춰 의존성 상향
A: "B안 (3.15)"
→ D027 확정. 첫 계획에 F11(venv·의존성 상향) 을 맨 앞 작업으로 추가, F9 의 "requirements 불변" 은 테스트 작업 한정으로 정정. 위험: 특성 테스트 전 GUI 라이브러리 상향 → 회귀는 F10 실기·표본 사이트로 잡는다

### Q032 · 2026-10-28 · 단계 4 · [X] · 문서≠코드
Q: 지원 Python 하한
A: README·옛 CLAUDE.md 는 "3.10 이상" 이나, 현 requirements 의 numpy 2.5.x·scipy 1.18.x 가 `requires_python >=3.12` (PyPI). 실제 하한은 3.12.
→ D028 (D016 대체), README 수정은 F11

### Q033 · 2026-10-28 · 단계 4 · [U]
Q: F11 기준 1~4 + 로그 도입 안 함 / ruff check 훅(gaindb 제외) / 위험 명령 목록 / 실기 결과 채팅 전달 (모두 추천안)
A: "모두 추천대로"
→ D029~D032 확정, OPEN O05~O08 해결

### Q034 · 2026-10-28 · 단계 5 · [AI]
Q: PRD 검사(맥락 없는 서브에이전트) 지적 처리
A: 요약 — 사실로 메울 수 있는 것은 PRD 에 반영: F11 정확한 패키지·판·Python 출처, F9 대상 함수 위치·기대값은 현 코드 출력(특성 테스트), F9/F11 requirements 범위는 커밋 단위로 명시, F8 "Apache" 판정은 서드파티 고지 예외 명시·README 절 특정, F11 자동 업데이트 판정 = 진행 모달, macOS 지원 수준·동시성 수치 성격 명시, 성공 기준 '정상' 판정 [AI] 추가. 의도적이라 그대로 둔 것: F1~F7 예외 동작(현행이 기준, D024), 두 번째 계획 LGPL 인수 기준(계획 때 작성, D024), 로드맵 항목, 실기 절차의 비자동성(D026). 사용자 결정 필요: 표본 실기 통과 기준 → OPEN O11
→ OPEN O11, 재확인 1 (성공 기준 '정상' 판정)

### Q035 · 2026-10-28 · 단계 5 · [U]
Q: O11 실기 통과 기준(성공 기준·F11 기동 실패만 미완) + 성공 기준 '정상' 판정 재확인 (모두 추천안)
A: "둘 다 추천대로"
→ D033, D034 확정. OPEN 미결·재확인 0개. 참고: 원본 세션(local_2085c4aa) 은 사용자 요청으로 삭제, 이 포크 세션에서 계속

### Q036 · 2026-10-28 · 단계 5 · [U]
Q: [관문] PRD 승인
A: "승인"
→ PRD 상태 approved (2026-10-28), 단계 6 문서로

### Q037 · 2026-10-28 · 단계 6 · [U]
Q: 문서 분류 목록 (CLAUDE.md 1~4 / PROGRESS 5~7 / REFERENCE 8~12 / settings·훅 13~15)
A: "이대로 작성"
→ CLAUDE.md(52줄, draft)·PROGRESS(머리 19줄)·REFERENCE(80줄)·.claude/settings.json·hooks 3개 작성. 추가: `.gitignore` 에 `.claude/settings.local.json`

### Q038 · 2026-10-28 · 단계 6 · [U]
Q: [관문] 문서 구성 승인
A: "승인"
→ CLAUDE.md 첫 줄 `<!-- metarche -->`, 단계 7 계획으로

### Q039 · 2026-10-28 · 단계 7 · [U]
Q: [관문] 작업 계획 docs/plans/2026-10-28-foundation.md 승인
A: "승인"
→ 계획 active, 단계 8 구현
