# 다섯 번째 계획 — 보안 정책 후속
상태: active | 시작: 2026-11-02 | 근거: SECURITY_POLICY §4·§6, PRD §2.6 (D045, D046)

목표: 보안 정책(2026-10-29 승인)이 "계획 작업"으로 미룬 세 가지를 끝낸다. 쓰이지 않는 위험한 앱 자체 업데이트 코드가 사라지고, 사이트가 준 제목이 형식 선택 창에서 서식으로 해석되지 않으며, 릴리스 전에 의존성 취약점 검사를 한다.
구조:
- 바뀜: `utils/updater.py`(`AppUpdater`·`APP_API_URL`·`GITHUB_REPO` 삭제), `ui/format_select_dialog.py > FormatSelectDialog`(제목 `QLabel` PlainText), `requirements-dev.txt`(pip-audit 핀), `docs/RELEASE.md`(취약점 검사 절), `CHANGELOG.md`
- 생김: `tests/test_format_select_dialog.py`
- (선택, 작업 4) `ui/main_window.py > _run_ytdlp_update`
전역 제약:
- `gaindb/` 무수정, `requirements.txt` 의 yt-dlp 핀 유지 (D015, D002)
- [AI] pip-audit 가 취약점을 보고해도 이 계획에서 의존성 버전을 올리지 않는다. 결과를 OPEN 에 질문으로 넣고 그 판단은 따로 한다 (yt-dlp 핀은 D002 로 올리면 안 되기 때문)
- [AI] `pip install pip-audit` 는 실행 전 확인 (D032)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. `AppUpdater` 삭제 (D046) — `utils/updater.py > AppUpdater`, `APP_API_URL`, `GITHUB_REPO`
  - 호출처 없음 확인됨 (2026-11-02 grep). `GITHUB_REPO` 는 `APP_API_URL` 에만 쓰여 함께 지운다. `subprocess`·`requests` import 는 `YtdlpUpdater`·`install_ytdlp_wheel` 이 계속 쓴다
  - 확인: `git grep -n "AppUpdater\|APP_API_URL\|GITHUB_REPO\|shell=True" -- "*.py" ":!gaindb" ":!docs"` → 출력 없음 | 전체 pytest 통과 | ruff 통과
  - 결과 (2026-11-02): grep 출력 없음(종료 1), pytest 96 통과, ruff 통과. 88줄 삭제
- [x] 2. 형식 선택 창 제목 PlainText (SECURITY_POLICY §4) — `ui/format_select_dialog.py > FormatSelectDialog.__init__`
  - 실패하는 테스트 먼저: 제목이 `<b>굵게</b>` 인 `VideoInfo` 로 창을 만들고 `QLabel#videoTitle` 의 `textFormat() == PlainText`, `text()` 가 원문 그대로
  - SECURITY_POLICY §4 의 "고칠 작업 후보 [X]" 문구를 "지킴 [X]" 로 바꾼다 (사실 갱신, 정책 내용은 그대로)
  - 확인: `venv\Scripts\python -m pytest tests/test_format_select_dialog.py` 통과 → 전체 pytest 통과
  - 범위 추가 (2026-11-02 사용자 승인): 같은 창의 업로더 줄 `lbl_meta`, `ui/playlist_select_dialog.py` 의 플레이리스트 제목 라벨도 AutoText 였음 → 함께 PlainText
  - 결과 (2026-11-02): 테스트 2건 먼저 실패 확인 → 구현 뒤 pytest 98 통과, ruff 통과. SECURITY_POLICY §4 문구를 "지킴" 으로
- [x] 3. pip-audit 도입 (D045) — `requirements-dev.txt`, `docs/RELEASE.md`
  - 설치 뒤 버전을 `requirements-dev.txt` 에 핀. Python 3.15 에서 설치·실행이 안 되면 여기서 멈추고 OPEN 에 질문
  - RELEASE.md 에 "3. 빌드" 앞 절로 `venv\Scripts\pip-audit -r requirements.txt` 추가: 취약점이 나오면 게시 전에 판단 (yt-dlp 는 기동 시 자동 업데이트로 최신이 되므로 핀 버전 보고는 기록만)
  - 확인: `venv\Scripts\pip-audit -r requirements.txt` 실행 완료 (종료 코드와 보고 내용을 계획 결과에 기록, 취약점이 있으면 OPEN 에 질문)
  - 결과 (2026-11-02): pip-audit 2.10.1 이 Python 3.15.1 에 설치·실행됨. 종료 코드 1 — 3개 패키지 14건(중복 ID 포함): certifi 2026.4.22 → 2026.10.18, urllib3 2.7.0 → 2.8.0, yt-dlp 2026.3.17(핀, D002 의도) → 2026.7.4. 버전은 올리지 않고 OPEN O19. RELEASE.md 는 절 번호를 바꾸지 않으려고 "3. 빌드" 첫 줄로 넣음
- [ ] 4. (선택) D013 위반 정리 — `ui/main_window.py > _run_ytdlp_update`
  - `worker.done.connect(_on_done)` 에 `Qt.ConnectionType.QueuedConnection` 명시. PROGRESS 미해결의 기존 항목
  - 확인: 전체 pytest 통과 | 실기기: 소스 실행에서 yt-dlp 업데이트 질문 → 예 → 완료 문구 표시 (업데이트할 버전이 없으면 `version.py` 를 옛 값으로 바꿔서)
- [ ] 5. 인수 확인
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과 · `venv\Scripts\ruff.exe check` 통과 | 실기기: 소스 실행으로 YouTube 영상 하나 링크 추가 → 형식 선택 창에 제목이 보이고 다운로드 완료

## 자가 검토
- PRD 기능 누락: 없음 (기능 추가 없음, 보안 정책 후속만)
- 테스트로 옮기지 않은 인수 기준: 작업 1 은 삭제라 grep 으로 확인 / 작업 3 은 도구 도입이라 실행 결과로 확인 / 작업 4 는 시그널 연결 방식이라 실기기로 확인
- 순서 의존: 없음 (서로 다른 파일). 5 는 마지막
