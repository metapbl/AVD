# 열두 번째 계획 — Graphite 테마와 1차 UX 수정
상태: active | 시작: 2026-11-04 | 근거: 사용자 요청 Q071, 결정 D059, D060

목표: 앱 전체를 Graphite 테마로 바꾸고, 키보드 실수·조용한 실패·상태 구분 문제를 고친다. 끝나면 Enter 가 각 창의 주 동작을 누르고, 실패가 사용자에게 보이며, 완료·대기·오류가 색으로 구분된다.
구조:
- 생김: `ui/theme.py`(팔레트·공통 위젯 스타일), `assets/icons/check.svg`·`radio.svg`, `tests/test_theme.py`, `tests/test_dialog_enter.py`, `tests/test_user_feedback.py`
- 바뀜: `main.py`, `AVD.spec`, `ui/*.py`
전역 제약:
- 새 의존성 없음. 테마 커밋에는 동작 변경을 섞지 않는다 (Q071)
- 버그 수정은 재현 테스트 먼저. `gaindb/` 는 고치지 않는다 (D017)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. Graphite 테마 — `ui/theme.py`, `ui/*.py` QSS 색, `main.py`, `AVD.spec`
  - 확인: `tests/test_theme.py` 통과 | 실제 클래스 캡처를 시안과 대조
- [x] 2. Enter 기본 버튼 — 화질 선택 "다운로드", 환경설정 "저장", 플레이리스트 "추가"
  - 확인: `tests/test_dialog_enter.py` 수정 전 실패, 수정 후 통과
- [x] 3. 실패 안내 — 파일 삭제 실패, 옮겨진 파일 재생·열기
  - 확인: `tests/test_user_feedback.py` 수정 전 실패, 수정 후 통과
- [ ] 4. 상태 표시 — 완료·대기·취소 색, 완료 시 작업 표시줄 알림, 항목 버튼 툴팁
  - 확인: `tests/test_user_feedback.py` 통과
- [ ] 5. 인수 확인
  - 확인: `venv\Scripts\python -m pytest` 통과 · `venv\Scripts\ruff.exe check` 통과 · 사용자 실기 확인 항목 전달

## 자가 검토
- 테스트로 옮기지 않은 인수 기준: 실제 창의 인상·마우스 오버, exe 안의 SVG 표시 → 사람 확인 또는 다음 빌드 때 확인
- 범위 밖: 오류 처리 정리(사유 보존·모달 제거·정보 실패 항목 유지), 시작 시 버전 확인 스레드, Ctrl+V·끌어다 놓기, 화질 목록 열 정렬, 라이선스 안내 보강
