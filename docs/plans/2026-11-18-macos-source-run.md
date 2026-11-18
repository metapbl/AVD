# 스물아홉 번째 계획 — macOS 소스 실행 정식화
상태: done (2026-11-18, macOS 실기 미확인) | 시작: 2026-11-18 | 근거: 사용자 "3안을 처리하고 1안으로"(PRD §2.2 macOS 실행 정식화) → 범위 "소스 실행만"(2026-11-18 사용자 선택)

목표: macOS 에서 `python main.py` 로 띄운 AVD 가 Windows 와 같은 기능으로 동작한다 — 완료 항목의 📂 가 Finder 에서 파일을 선택해 열고, 한글 UI 가 macOS 기본 한글 글꼴로 보인다.
구조:
- 생김: `tests/test_open_folder.py`
- 바뀜:
  - `utils/file_utils.py > open_folder` — `sys.platform == "darwin"` 이면 `open -R <파일>` / `open <폴더>`
  - `main.py` — 기본 글꼴: macOS 는 "Apple SD Gothic Neo", 그 외 "맑은 고딕"
  - `README.md > 요구 사항` 운영체제 문구, `docs/PRD.md` 실행 환경 줄
전역 제약:
- .app 빌드·배포는 하지 않는다 (범위 밖: config.json 위치, Finder 실행 PATH, spec·.icns, 미서명 안내)
- Windows 동작은 그대로 — 기존 explorer 경로·테스트를 바꾸지 않는다
- 이 Windows 기기에서는 macOS 를 실행할 수 없다. 자동 확인은 `sys.platform`·`subprocess.run` 을 가로채는 테스트로, 실제 동작은 작업 4 실기로

## 작업
- [x] 0. PRD 변경·승인 — §2.2 "macOS 실행 정식화" 를 "소스 실행"으로 좁히고 .app 배포는 로드맵에 남김, 실행 환경 줄(152행) 갱신. 결정 D081 기록 (`/metarche discover`)
  - 확인: 2026-11-18 사용자 "승인" (Q092, D081, F16)
- [x] 1. 테스트 먼저 — `tests/test_open_folder.py`
  - darwin + 파일 → `["open", "-R", path]` | darwin + 폴더 → `["open", path]` | win32 + 파일 → `["explorer", "/select,", path]`(현행 고정) | 없는 경로 → 호출 없음
  - 확인: 구현 전 darwin 2건 빨강, win32·없는 경로 초록
  - 2026-11-18: 2 failed(darwin), 2 passed
- [x] 2. 구현 — `open_folder` 분기, `main.py` 글꼴 한 줄
  - 확인: 작업 1 초록, 전체 테스트 통과, ruff 통과
  - 2026-11-18: 337 passed, ruff All checks passed
- [x] 3. 문서 — README 운영체제 문구(macOS 소스 실행 지원, .app 없음), CHANGELOG, PROGRESS
- [ ] 4. 사용자 실기 확인 (macOS, 소스 실행) — 보류: 2026-11-18 사용자 "실기기 확인은 현재 어렵습니다". PROGRESS 확인 대기로 옮김
  - 영상 1건·mp3 1건 받기 → 완료 항목 📂 → Finder 에서 그 파일이 선택된 채 열림 | ▶ 재생 → 기본 앱으로 열림 | UI 한글이 Apple SD Gothic Neo 로 보임(네모·대체 글꼴 아님) | 저장 파일명 한글이 Finder 에서 정상
- [x] 5. 커밋 (`feat(macos): ...`, 작성자 확인)

## 자가 검토
- 하지 않는 것: .app 빌드·배포, Linux 분기(`xdg-open`), 글꼴 설정 UI
- 위험:
  - 글꼴 이름이 없으면 Qt 가 대체 글꼴을 고른다 — 깨지지는 않고 모양만 다르다. 작업 4 에서 확인
  - Windows 기기에서 macOS 동작을 볼 수 없다 — 실기 전까지 "자동 확인만" 으로 기록
