# 스물다섯 번째 계획 — 프로그램 정보 (창 제목 버전 · 정보 창)
상태: 진행 중 (사용자 화면 확인 대기) | 시작: 2026-11-12 | 근거: 사용자 요청 "프로그램의 버전이나 정보가 없는 것이 불만" → 2안(창 제목) + 3안(별도 정보 창) 선택

목표: 지금 쓰는 앱 버전과 구성요소 버전을 앱 안에서 볼 수 있게 한다.
구조:
- 생김: `ui/about_dialog.py`(`AboutDialog`, `REPO_URL`), `tests/test_about_dialog.py`
- 바뀜: `ui/main_window.py` — 창 제목, 도구 모음 "ⓘ 정보" 버튼, `_on_about`
전역 제약:
- 버전은 한 곳에서 읽는다: 앱 `utils/updater.py > APP_VERSION`, yt-dlp 는 지금 불러온 모듈(`yt_dlp.version`), GaindB 는 `gaindb.__version__`(상류가 공개한 값, 읽기만 — D015)
- 색은 `ui/theme.py` 이름으로 (D065). Enter 는 "닫기" (D060)

## 작업
- [x] 1. 테스트 먼저 — `tests/test_about_dialog.py` 5개: 창 제목 `AV Downloader {버전}` | 정보 창에 앱·yt-dlp·GaindB 버전, MIT·THIRD_PARTY_LICENSES, 저장소 링크(브라우저로 열림) | 기본 버튼 "닫기" | 버전 글자 선택 가능 | 도구 모음 버튼이 창을 연다
- [x] 2. 구현 — `AboutDialog`, 창 제목, "ⓘ 정보" 버튼("⚙ 설정" 오른쪽, 같은 모양)
  - 확인: pytest 305 통과, ruff 통과. 캡처로 창·도구 모음 확인 (다크)
- [x] 3. 문서 — PRD F14, D077, CHANGELOG, PROGRESS
- [ ] 4. 사용자 화면 확인 — 정보 버튼 → 창 내용 | 링크 클릭 → 브라우저 | 라이트 테마에서 글자 색 | Enter·Esc 로 닫힘
- [x] 5. 커밋

## 자가 검토
- PRD 기능 누락: F14 인수 기준 = 작업 1 의 테스트 + 작업 4
- 테스트로 옮기지 않은 인수 기준: 링크가 실제 브라우저를 여는지, 라이트 테마 색 → 눈 확인
- 하지 않는 것: 최신 앱 버전 확인 버튼, 라이선스 전문 보기, "정보 복사" 버튼
- 위험: exe 빌드에서는 확인하지 않았다 — 다음 릴리스 실기기 확인에 "정보 창" 한 줄 추가
