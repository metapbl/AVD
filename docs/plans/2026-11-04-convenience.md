# 열네 번째 계획 — 3차 편의 기능
상태: active | 시작: 2026-11-04 | 근거: 사용자 요청 Q073, 결정 D063

목표: 자주 쓰는 동작을 줄인다. 끝나면 링크를 여러 방법으로 넣을 수 있고, 목록 상황과 저장 위치가 한눈에 보이며, 화질을 열로 비교할 수 있다.
구조:
- 생김: `tests/test_list_summary.py`, `tests/test_add_links.py`, `tests/test_format_columns.py`, `tests/test_playlist_banner.py`
- 바뀜: `ui/main_window.py`, `ui/add_link_dialog.py`, `ui/format_select_dialog.py`, `ui/download_item_widget.py`, `controllers/playlist_flow.py`, `docs/PRD.md`, `README.md`
전역 제약:
- 새 의존성 없음. 재현 테스트 먼저. 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. 상태 요약·완료 지우기·저장 폴더 표시 (12, 14, 15번)
  - 확인: `tests/test_list_summary.py` 수정 전 실패, 수정 후 통과
- [ ] 2. Ctrl+V·끌어다 놓기·여러 줄 붙여넣기, 화질 창 차례대로 (16번, D063)
  - 확인: `tests/test_add_links.py` 수정 전 실패, 수정 후 통과
- [ ] 3. 화질 목록 열 정렬 (17번)
  - 확인: `tests/test_format_columns.py` 수정 전 실패, 수정 후 통과 · `tests/test_dialog_enter.py` 통과
- [ ] 4. 플레이리스트 확인 표시 (18번)
  - 확인: `tests/test_playlist_banner.py` 수정 전 실패, 수정 후 통과
- [ ] 5. 인수 확인
  - 확인: `venv\Scripts\python -m pytest` 통과 · `venv\Scripts\ruff.exe check` 통과 · 실제 클래스 캡처 확인 · 사용자 실기 확인 항목 전달

## 자가 검토
- 테스트로 옮기지 않은 인수 기준: 브라우저에서 실제로 끌어다 놓기, 실제 플레이리스트 응답 시간 → 사람 확인
- 범위 밖: 정보 가져오는 중 "취소" 버튼 동작, 플레이리스트 확인 취소 버튼, 라이선스 안내 보강
