# 일곱 번째 계획 — 의존성 보안 핀 올림·v1.0.2 릴리스
상태: active | 시작: 2026-11-02 | 근거: OPEN O19, Q056, SECURITY_POLICY §6, PRD §2.6 (D040, D045)

목표: pip-audit 가 보고한 certifi·urllib3 취약점을 핀 상향으로 없애고, 그 빌드를 v1.0.2 로 게시한다. 끝나면 `pip-audit -r requirements.txt` 가 yt-dlp(D002 의도된 옛 핀) 말고는 보고하지 않고, GitHub Release v1.0.2 에 zip 2개가 있다.
구조:
- 바뀜: `requirements.txt`(`certifi==2026.10.18`, `urllib3==2.8.0`), `utils/updater.py > APP_VERSION`(`1.0.2`), `CHANGELOG.md`, `docs/discovery/OPEN.md`(O19 해결), `QA_LOG.md`·`DECISIONS.md`(답·결정 기록)
- 생김: 태그 `v1.0.2`, GitHub Release `AVD v1.0.2`
- 앱 동작 코드 변경 없음
전역 제약:
- `requirements.txt` 의 yt-dlp 핀은 올리지 않는다 (D002)
- [AI] 이번 계획에서는 certifi·urllib3 두 줄만 올린다. requests 등 다른 핀은 pip 가 요구하지 않는 한 그대로
- [X] requests 2.34.2 의 요구 범위 `urllib3<3,>=1.26`, `certifi>=2023.5.7` — 새 버전 모두 허용 (2026-11-02 venv 메타데이터 확인)
- venv 안 `pip install` 은 실행 전 확인 (D032)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. 핀 올림 — `requirements.txt`
  - 두 줄을 고치고 `venv\Scripts\python -m pip install certifi==2026.10.18 urllib3==2.8.0` (실행 전 확인)
  - `-r requirements.txt` 로 설치하지 않는다: venv 의 yt-dlp 2026.10.26 이 핀 2026.3.17 로 내려가 배포본에 옛 yt-dlp 가 실린다 (RELEASE §3, 2026-11-02 발견)
  - 확인: `venv\Scripts\python -m pip check` → "No broken requirements found." | `venv\Scripts\pip-audit -r requirements.txt` → 보고가 yt-dlp 만 남음 | 전체 pytest 통과
  - 1차 (2026-11-02): 두 패키지만 설치(venv yt-dlp 2026.10.26 유지 확인). `pip check` 통과, pip-audit 종료 1 — 보고는 yt-dlp 2026.3.17(핀, D002) 9건뿐, pytest 104 통과, ruff 통과. 실기기 대기
  - 실기기: 소스 실행으로 YouTube 영상 하나 링크 추가 → 정보·썸네일(UI 미리보기)이 뜨고 다운로드 완료 (certifi·urllib3 는 HTTPS 요청 경로에 쓰이므로). 통과하면 O19 를 해결로 옮기고 QA_LOG·DECISIONS 에 기록
  - 결과: 2026-11-02 통과 — 사용자 "정상" (정보·썸네일 표시, 다운로드 완료). O19 해결 → D050
- [x] 2. 버전 올리기·CHANGELOG (RELEASE §1·§2) — `utils/updater.py > APP_VERSION` → `1.0.2`, `CHANGELOG.md`
  - [U] v1.0.2 에는 v1.0.1 이후 미릴리스 변경(보안 정책 후속, 완료 항목 폴더 열기·재생 버튼)도 함께 실린다
  - 확인: `git rev-list --count main..origin/main` → 0 | `gh release list --repo metapbl/AVD` 에 v1.0.2 없음 | 커밋 `chore(release): v1.0.2` 작성자 `metapbl <ggoyong2@gmail.com>`
  - 결과: 2026-11-02 — origin 대비 behind 0, 릴리스·태그는 v1.0.0·v1.0.1 뿐. `APP_VERSION` 1.0.2
- [ ] 3. 빌드·exe 실기기 확인 (RELEASE §3·§4) — `.\build.ps1`
  - 확인: `pip-audit -r requirements.txt` 보고가 yt-dlp 만 | `release\AVD-v1.0.2-win64.zip`·`AVD-v1.0.2-src.zip` 생김 | 번들 yt-dlp 버전 기록 | 실기기: 리포 밖 새 폴더에 푼 `AVD.exe` 로 RELEASE §4 의 1~3 → 모두 기대대로 (하나라도 아니면 4 로 가지 않는다)
- [ ] 4. 태그·push·GitHub Release (RELEASE §5·§6) — 각 명령 실행 전 확인 (D040)
  - 노트 파일은 스크래치패드에 쓰고 내용을 먼저 보여 준다
  - 확인: `gh release view v1.0.2 --repo metapbl/AVD --json assets` → zip 2개
- [ ] 5. 인수 확인
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과 · `venv\Scripts\ruff.exe check` 통과 · 작업 1 의 소스 실행 확인과 작업 3 의 exe 확인 결과가 기록됨 · 작업 4 의 assets 2개

## 자가 검토
- PRD 기능 누락: 없음 (기능 추가 없음, 보안 후속과 릴리스)
- 테스트로 옮기지 않은 인수 기준: HTTPS 요청 동작·exe 동작 → 네트워크·빌드 산출물이 필요해 실기기 확인으로 대체
- 순서 의존: 1 → 2 → 3 → 4 → 5 (2 는 1 의 핀이 커밋된 뒤여야 빌드에 실린다)
