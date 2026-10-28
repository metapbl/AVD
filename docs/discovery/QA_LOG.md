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
