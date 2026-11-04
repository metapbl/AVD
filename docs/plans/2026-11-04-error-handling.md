# 열세 번째 계획 — 2차 오류 처리 정리
상태: done (2026-11-04) | 시작: 2026-11-04 | 근거: 사용자 요청 Q072, 결정 D061, D062

목표: 오류가 작업을 막지 않고 항목에 사유와 함께 남게 하고, 시작 시 버전 확인이 창을 멈추지 않게 한다. 끝나면 실패 항목은 목록에 남아 "자세히"와 "재시도"를 쓸 수 있고, 자동으로 뜨는 오류 창이 없다.
구조:
- 생김: `workers/update_check_worker.py`, `tests/test_error_handling.py`
- 바뀜: `ui/main_window.py`, `ui/download_item_widget.py`, `docs/PRD.md` F4·§8
전역 제약:
- 새 의존성 없음. 재현 테스트 먼저. 워커→메인 연결은 `QueuedConnection` 명시 (D013)
- QThread 에 `finished`/`started` 이름의 커스텀 Signal 금지 (R§4 T2)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. 오류 사유 보존·자동 창 제거 — `item.error_msg`, 상태 라벨 요약, "자세히" 버튼 (D061)
  - 확인: `tests/test_error_handling.py` 수정 전 실패, 수정 후 통과
- [x] 2. 정보 가져오기 실패 항목 유지 — 단일 영상은 재시도 때 화질 선택, 플레이리스트 항목은 고른 형태 유지 (D061)
  - 확인: `tests/test_error_handling.py` 통과
- [x] 3. 버전 확인 워커 — `UpdateCheckWorker`, 종료 때 대기 (D062)
  - 확인: `tests/test_error_handling.py` 통과 · `tests/test_app_shutdown.py` 통과
- [x] 4. 인수 확인
  - 확인: `venv\Scripts\python -m pytest` 통과 · `venv\Scripts\ruff.exe check` 통과 · 사용자 실기 확인 항목 전달
  - 결과: 2026-11-04 — pytest 213·ruff 통과. 진짜 MainWindow 로 오류 항목 화면·버전 확인 워커 왕복·종료 확인. 실제 네트워크 오류 화면은 사람 확인 대기

## 자가 검토
- 테스트로 옮기지 않은 인수 기준: 실제 네트워크 오류·봇 차단 때의 화면 → 사람 확인
- 범위 밖: 정보 가져오는 중 "취소" 버튼 동작, 3차 편의 기능, 라이선스 안내 보강
