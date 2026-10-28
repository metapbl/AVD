# 두 번째 계획 — PlaylistProbeWorker 결과 시그널 개명 (T2 위반 해소)
상태: active | 시작: 2026-10-28 | 근거: PRD F2 (D007, D013), R§4 T2

목표: `PlaylistProbeWorker` 가 QThread 내장 `finished` 를 가리지 않게 하고, 워커 정리(`deleteLater`)를 스레드가 실제로 끝난 뒤인 내장 `finished` 에만 연결한다. 같은 위반이 다시 들어오면 테스트가 잡는다.
구조:
- 바뀜: `workers/playlist_probe_worker.py`(결과 시그널 `finished` → `probe_ready`, 독스트링), `controllers/playlist_flow.py > PlaylistFlow.start`(연결 정리, 클래스 독스트링의 정리 체인 서술), `CHANGELOG.md`
- 생김: `tests/test_worker_signals.py`
전역 제약:
- 이름은 같은 폴더 관례(`info_ready`, `thumb_ready`)를 따라 `probe_ready`
- 성공·실패 핸들러(`_on_probe_done`, `_on_probe_error`)의 동작은 바꾸지 않는다. 연결만 바꾼다
- 결과 시그널 연결은 `QueuedConnection` 유지 (D013)
- `gaindb/` 무수정, yt-dlp 핀 유지 (D015, D002)
- 커밋 작성자 `metapbl` 확인, `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. 결과 시그널 개명과 정리 연결 교체 — `workers/playlist_probe_worker.py > PlaylistProbeWorker`, `controllers/playlist_flow.py > PlaylistFlow.start`
  - 먼저 실패하는 테스트: `tests/test_worker_signals.py` — `workers/` 의 모든 QThread 서브클래스가 클래스 본문에 `finished`·`started` 를 정의하지 않음, `PlaylistProbeWorker` 에 `probe_ready` 가 있음
  - 연결 결과: `probe_ready`→`_on_probe_done`, `error`→`_on_probe_error` (둘 다 Queued), 내장 `finished`→`deleteLater` 하나. 이벤트 루프가 없는 워커라 효과 없는 `quit` 연결과, 스레드 종료 전에 걸리던 `error`→`deleteLater` 는 뺀다
  - 확인: 수정 전 `venv\Scripts\python -m pytest tests/test_worker_signals.py` → 실패 1건 이상, 수정 후 → 통과 | `venv\Scripts\ruff.exe check workers controllers tests` → 새 위반 없음
- [ ] 2. 인수 확인 — F2 흐름이 그대로 동작하는지
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과
  - 실기기: (a) YouTube 플레이리스트 URL 추가 → 선택 다이얼로그가 뜨고, 확인·취소 모두 크래시나 콘솔의 `QThread: Destroyed while thread is still running` 없음 (b) 플레이리스트가 아닌 깨진 URL → 상태줄에 "플레이리스트를 가져오지 못했습니다" 류 메시지, 크래시 없음

## 자가 검토
- PRD 기능 누락: 없음 (F2 동작 보존만, 새 기능 없음)
- 테스트로 옮기지 않은 인수 기준: F2 다이얼로그 표시·종료 → GUI 이벤트 루프와 네트워크가 필요해 실기기 확인으로 대체 (pytest-qt 미도입)
- 순서 의존: 2는 1 뒤
