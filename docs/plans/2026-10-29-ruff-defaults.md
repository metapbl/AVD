# 세 번째 계획 — ruff 0.17 기본 규칙 채택과 위반 정리
상태: active | 시작: 2026-10-29 | 근거: D035 (고정 규칙의 후속), D037, PRD §5 비기능

목표: `pyproject.toml` 의 규칙 고정(`select = ["E4","E7","E9","F"]`)을 풀고 ruff 0.17 기본 규칙으로 앱 코드가 `All checks passed!` 가 된다. 앱 동작은 바뀌지 않는다.
구조:
- 바뀜: 앱 코드 20개 파일(import 순서·기계적 정리), `pyproject.toml`(`select` 제거, `ignore` 2개), `docs/discovery/DECISIONS.md`(D037), `CHANGELOG.md`
- 생김: 없음
전역 제약:
- 동작을 바꾸는 수정은 하지 않는다. `--unsafe-fixes` 는 쓰지 않는다
- 예외 처리는 그대로 둔다. `BLE001`(blind-except 21건)·`S110`(try-except-pass 9건)은 고치지 않고 규칙에서 뺀다 — 워커가 yt-dlp 의 온갖 예외를 받아 `error` 시그널로 넘기는 경계와, 정리 단계에서 실패를 삼키는 자리라 의도된 코드다. 좁히면 워커 스레드에서 예외가 새어 조용히 멈출 위험이 생긴다 (D037 로 기록)
- 작업 1~3 동안 `pyproject.toml` 은 그대로 둔다(편집 훅이 기존 규칙으로 돈다). 기본 규칙 검사는 `--isolated` 로 따로 돌린다
- `gaindb/` 무수정, yt-dlp 핀 유지 (D015, D002)
- 커밋 작성자 `metapbl` 확인, `CHANGELOG.md` 맨 위 항목 (D014, D020)

기본 규칙 검사 명령 (아래 "기본 검사"):
`venv\Scripts\ruff.exe check --isolated --exclude gaindb,docs,venv --statistics .`

## 작업
- [ ] 1. import 순서 정리 (`I001` 19건, 자동) — 앱 코드 전반
  - `venv\Scripts\ruff.exe check --isolated --exclude gaindb,docs,venv --select I --fix .`
  - 확인: 기본 검사 → `I001` 없음, 64→45 | `venv\Scripts\python -m pytest` 통과 | `venv\Scripts\python -c "import main"` 오류 없음
- [ ] 2. 안전 자동 수정 7건 — `workers/download_worker.py`(`PLR1730` 진행률 0~100 고정 2건, `SIM114` ETA 분기 1건), `ui/download_item_widget.py`(`PLR1730` 2건), `utils/file_utils.py`(`PYI041`), `ui/main_window.py`(`PIE790`)
  - `--select PLR1730,SIM114,PYI041,PIE790 --fix` (unsafe 아님)
  - 확인: 기본 검사 → 해당 규칙 없음, 45→38 | pytest 통과 | `git diff` 를 눈으로 보고 `if x<0: x=0` → `max(x,0)` 같은 같은 뜻 변환만인지 확인
- [ ] 3. 수동 정리 8건 — 동작 불변
  - `ui/main_window.py` `ISC004` 3건: 오류 안내 튜플 안의 이어 붙인 문자열을 괄호로 감싼다 (글자 그대로)
  - `utils/file_utils.py > open_folder` `PLW1510` 2건: `check=False` 명시 (탐색기는 성공해도 1 을 돌려줄 수 있어 지금처럼 검사 안 함)
  - `ui/download_item_widget.py` `RUF046`: 불필요한 `int()` 제거 / `utils/file_utils.py` `RUF059`: 안 쓰는 `gone` → `_gone` / `ui/main_window.py` `SIM102`: 중첩 `if` 합치기
  - 확인: 기본 검사 → `BLE001`·`S110` 30건만 남음 | pytest 통과
- [ ] 4. 규칙 고정 해제 — `pyproject.toml`, `DECISIONS.md`
  - `select` 줄 제거, `ignore = ["BLE001", "S110"]` 와 이유 주석 (D037, 승인 때 기록됨)
  - 확인: `venv\Scripts\ruff.exe check --force-exclude .` → `All checks passed!`
- [ ] 5. 인수 확인
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과 | `ruff check` 통과 | `git diff e4ecca5.. -- gaindb/` 비어 있음
  - 실기기: 앱 실행 → 단일 YouTube 영상 하나 다운로드 완료(진행률·ETA 표시 정상), 완료 항목 "폴더 열기"로 탐색기 열림

## 자가 검토
- PRD 기능 누락: 없음 (동작 불변 정리, 새 기능 없음)
- 테스트로 옮기지 않은 인수 기준: 작업 2·3 의 UI·진행률 코드(`download_item_widget` 폭 계산, 조각 진행률 고정, 탐색기 열기)는 특성 테스트가 없다 → 새 특성 테스트 대신 같은 뜻 변환임을 diff 로 확인하고 실기기 다운로드 1건으로 대체 (기계적 변환에 GUI 테스트 도구를 들이는 비용이 더 큼)
- 순서 의존: 4는 1~3 뒤 (먼저 바꾸면 편집 훅이 남은 위반으로 계속 실패), 5는 마지막
