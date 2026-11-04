# 열다섯 번째 계획 — 라이트 테마와 테마 전환
상태: done (2026-11-04) | 시작: 2026-11-04 | 근거: 사용자 요청 Q075, 결정 D065

목표: Paper 를 라이트 테마로 추가하고, 기본은 Windows 색 모드를 따르며, 환경설정에서 다크·라이트로 고정할 수 있게 한다.
구조:
- 생김: `assets/icons/check_light.svg`·`radio_light.svg`
- 바뀜: `ui/theme.py`, `ui/*.py` QSS 색 이름화, `main.py`, `AVD.spec`, `utils/config_manager.py`, `tests/test_theme.py`
전역 제약:
- 새 의존성 없음. 다크 화면은 이전과 화소까지 같아야 한다 (새 설정 그룹이 들어간 환경설정 제외)

## 작업
- [x] 1. 색표와 `@이름` 치환, 창 코드의 색 이름화
  - 확인: 캡처 비교 — 메인·화질 선택·플레이리스트·제거 확인·링크 추가 동일
- [x] 2. Windows 따라가기·실행 중 전환 — `apply_theme`, `refresh_theme`, `_on_theme_changed`
  - 확인: `tests/test_theme.py` 통과 · 진짜 MainWindow 에서 색 모드 변경과 고정 전환 확인
- [x] 3. 환경설정 "화면 테마" (Windows 설정 따르기 / 다크 / 라이트)
  - 확인: `tests/test_theme.py` 통과
- [x] 4. 인수 확인
  - 확인: `venv\Scripts\python -m pytest` 통과 · `venv\Scripts\ruff.exe check` 통과 · 라이트 화면 캡처 확인
  - 결과: 2026-11-04 통과. 실제 Windows 설정 변경·제목 표시줄 색·exe 표시는 사람 확인 대기

## 자가 검토
- 테스트로 옮기지 않은 인수 기준: 실제 Windows 설정 변경, 제목 표시줄 색 → 사람 확인
- 범위 밖: Windows 색 모드가 바뀔 때 이미 열려 있는 다이얼로그 다시 칠하기 (다음에 열 때 반영)
