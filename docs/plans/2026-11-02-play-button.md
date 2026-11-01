# 여섯 번째 계획 — 완료 항목 "▶ 재생" 버튼
상태: active | 시작: 2026-11-02 | 근거: PRD F1 (D049)

목표: 다운로드가 끝난 항목에서 "▶ 재생" 을 누르면 받은 파일이 OS 기본 앱(동영상 플레이어·음악 앱)으로 열린다.
구조:
- 바뀜: `utils/file_utils.py`(`open_file` 추가, `open_folder` 옆), `ui/download_item_widget.py > DownloadItemWidget`(`btn_play`·`play_requested` 시그널·상태별 표시·스타일), `ui/main_window.py`(시그널 연결·`_on_play_file`), `CHANGELOG.md`
- 생김: `tests/test_play_button.py`
전역 제약:
- 버튼은 세로 버튼 줄(`btn_layout`, `QVBoxLayout`)에서 "📂 열기" 와 "✕" 사이, 60px 고정. 표시 규칙은 `btn_open` 과 같다 (DONE 에서만 보임) (D049)
- [AI] 파일 열기는 `QDesktopServices.openUrl(QUrl.fromLocalFile(path))` — Qt 에 이미 있고 macOS 에서도 동작. `os.startfile` 은 Windows 전용이라 쓰지 않는다
- [AI] 파일이 없으면 아무 일도 하지 않는다 — `open_folder` 와 같은 방식 (D049)
- [AI] 스타일은 `btnOpen` 과 구분되게 `btnPlay` 를 따로 둔다 (색은 기존 팔레트 안에서)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. "▶ 재생" 버튼 — `utils/file_utils.py > open_file`, `ui/download_item_widget.py > DownloadItemWidget`, `ui/main_window.py > _on_play_file`
  - 실패하는 테스트 먼저 (`tests/test_play_button.py`):
    - `open_file`: 있는 파일 → `QDesktopServices.openUrl` 이 그 파일 URL 로 한 번 호출 / 없는 경로 → 호출 없음 (openUrl 은 가짜로 바꿈)
    - 위젯: DONE → `btn_play` 보임, 버튼 줄 순서가 열기 → 재생 → ✕ / WAITING·DOWNLOADING·ERROR·CANCELLED → 숨김 / 클릭 → `play_requested(item_id)`
    - 높이: DONE 상태로 띄운 위젯에서 세 버튼이 겹치지 않고 위젯(96px) 안에 들어간다
  - 확인: `venv\Scripts\python -m pytest tests/test_play_button.py` 통과 → 전체 pytest 통과 → ruff 통과
  - 결과 (2026-11-02): 테스트 먼저 실패 확인(`open_file` 없음 ImportError) → 구현 뒤 새 테스트 6 통과, 전체 pytest 104 통과, ruff 통과. DONE 버튼 세로 위치 열기 8~30·재생 35~57·✕ 62~84 (위젯 96, 아래 여백 8). 색은 기존 팔레트 초록 `#2e7d32`·hover `#4caf50`. 숨김 처리는 상태 분기마다 넣지 않고 `update_status` 에 한 줄(`status == DONE`)
- [ ] 2. 인수 확인
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과 | 실기기 (소스 실행): 1 영상 하나 받기 → 완료 항목에 "📂 열기 / ▶ 재생 / ✕" 가 세로로 잘리지 않고 보인다 · 2 "▶ 재생" → 기본 플레이어에서 재생 · 3 MP3 로 받은 항목의 "▶ 재생" → 기본 음악 앱에서 재생 · 4 진행 중 항목에는 "▶ 재생" 이 없다

## 자가 검토
- PRD 기능 누락: 없음. 완료 항목 동작이 바뀌므로 마칠 때 PRD F1 에 한 줄 추가를 제안한다 (execute.md §wrap 5)
- 테스트로 옮기지 않은 인수 기준: 실제 플레이어가 뜨는지·눈으로 보이는 배치 → 실기기 (OS 기본 앱 연결은 테스트 환경에서 볼 수 없음)
- 순서 의존: 2 는 1 뒤
