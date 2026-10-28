# 첫 계획 — 기반 다지기 (venv·라이선스·특성 테스트·실기 검증)
상태: active | 시작: 2026-10-28 | 근거: PRD F11, F8, F9, F10 (D017, D022, D023, D025~D029, D033, D034)

목표: 이 PC 에서 Python 3.15 로 앱이 돌고, 본체 라이선스가 MIT 로 정리되고, 순수 함수의 현재 동작이 pytest 로 고정되며, 밀린 실기 검증과 표본 8건 확인으로 앱이 깨지지 않았음을 확인한다.
구조:
- 바뀜: `requirements.txt`(PySide6 계열 4개·numpy·scipy 판), `README.md`(Python 하한·config 위치·문서 절·라이선스 절), `LICENSE`(MIT 전문), `NOTICE`(본체 MIT 서술)
- 생김: `requirements-dev.txt`(pytest·ruff), `pyproject.toml`(ruff `extend-exclude = ["gaindb", "docs", "venv"]`, pytest `pythonpath = ["."]`, `testpaths = ["tests"]` 만), `tests/test_download_worker_parsing.py`, `tests/test_file_utils.py`
- 다시 만듦: `venv/` (git 밖)
전역 제약:
- 앱 코드(`*.py` 기존 파일)와 `gaindb/` 는 고치지 않는다 (D015, D023). `git diff -- gaindb/` 는 계획 내내 비어 있어야 한다
- yt-dlp 핀 2026.3.17 유지 (D002)
- 커밋마다 작성자 `metapbl` 확인, `CHANGELOG.md` 맨 위 항목 (D014, D020)
- `pip install`·venv 삭제·`git push` 는 실행 전 확인 (D032)

## 작업
- [x] 1. venv 재생성과 의존성 상향 (F11) — `requirements.txt`, `README.md > 요구 사항`
  - 깨진 `venv/` 삭제(확인 후) → `py -3.15 -m venv venv` → `requirements.txt` 의 `PySide6`·`PySide6_Addons`·`PySide6_Essentials`·`shiboken6` 6.11.1→6.12.0, `numpy` 2.5.1→2.5.4, `scipy` 1.18.0→1.18.1 → `venv\Scripts\python -m pip install -r requirements.txt`. README 의 "Python 3.10 이상 (3.13/3.14 권장)" → "Python 3.12 이상 (3.15 에서 개발)"
  - 확인: `venv\Scripts\python -m pip check` → `No broken requirements found.` / `venv\Scripts\python -c "import PySide6, numpy, scipy, yt_dlp, gaindb; print(PySide6.__version__)"` → `6.12.0` / `git diff --stat requirements.txt` → 6줄 변경
  - 결과: 2026-10-28 통과 — `pip check` → No broken requirements found. / Python 3.15.1, PySide6 6.12.0, numpy 2.5.4, scipy 1.18.1, yt-dlp 2026.03.17 / `import main` 성공 / requirements.txt 12줄(6±)
  - 커밋: `chore(deps): Python 3.15 대응 — PySide6 6.12.0·numpy 2.5.4·scipy 1.18.1 (D027)`
- [ ] 2. 기동 실기 확인 (F11 인수 기준 2) — 코드 변경 없음, 커밋 없음
  - 실기기: 사용자가 `venv\Scripts\python main.py` 실행 → 메인 창이 뜨고 yt-dlp 업데이트 모달이 떠서 완료 후 닫힘. 종료 뒤 내가 `venv\Scripts\python -m pip show yt-dlp` → 버전이 2026.3.17 보다 높음
  - 실패하면 첫 계획 미완 (D033): PROGRESS 미해결에 기록하고 의존성 되돌림을 사용자와 정한다
- [x] 3. 개발 도구 마련 — `requirements-dev.txt`, `pyproject.toml`
  - 내용: `-r requirements.txt` + `pytest`·`ruff` 판 고정(설치 시점 최신, ruff 는 0.15.x). `pyproject.toml` 은 위 구조의 키만
  - 확인: `venv\Scripts\python -m pip install -r requirements-dev.txt` 후 `venv\Scripts\ruff.exe check .` → `All checks passed!` (gaindb 제외 반영) / `venv\Scripts\ruff.exe check --force-exclude gaindb/api.py` → 출력 없음 / `venv\Scripts\python -m pytest` → `no tests ran` (종료 코드 5)
  - 계획 변경 (D035): ruff 0.17.3 채택, 0.17 기본 규칙 확장으로 64건이 걸려 `[tool.ruff.lint] select = ["E4","E7","E9","F"]` 고정
  - 결과: 2026-10-28 통과 — 설치 성공 / `ruff check .` → All checks passed! / gaindb/api.py → 검사 제외 / `pytest` → 종료 코드 5 (테스트 없음) / 검사 훅이 F401 을 돌려줌(exit 2)
  - 커밋: `chore(dev): pytest·ruff 개발 의존성과 pyproject 설정 추가`
- [x] 4. 본체 라이선스 MIT 전환 (F8 기준 1~3) — `LICENSE`, `NOTICE`, `README.md > 라이선스·면책`
  - `LICENSE` 를 MIT 전문 + `Copyright (c) 2026 META PUBLIC` 으로. `NOTICE`·README 의 본체 라이선스 서술을 MIT 로, 무보증 문구는 "MIT 및 LGPL-2.1 양쪽의 무보증 조항"으로. 서드파티 고지의 Apache-2.0(requests 등)은 유지
  - 확인: `Select-String -Path LICENSE -Pattern "MIT License","META PUBLIC"` → 2건 / `Select-String -Path NOTICE,README.md -Pattern "Apache"` → 서드파티 고지·변경 이력 문장 외 0건 (결과를 줄 단위로 보인다) / `git diff --stat -- gaindb/` → 출력 없음
  - 결과: 2026-10-28 통과 — LICENSE 1행 `MIT License`·3행 `Copyright (c) 2026 META PUBLIC` / LICENSE·NOTICE·README 의 "Apache" 는 NOTICE 47행 서드파티(requests 등) 고지 1건뿐 / `git diff --stat -- gaindb/` 출력 없음
  - 커밋: `chore: 본체 라이선스 Apache-2.0 → MIT 전환 (D017)`
- [x] 5. README 정합 (F8 기준 4) — `README.md > 머리 인용·실행·디렉터리 구조·문서`
  - config 위치를 "앱 폴더의 `config.json`" 으로. `WORKLOG.md` 언급·링크를 지우고 문서 절을 `CLAUDE.md`·`docs/PRD.md`·`docs/PROGRESS.md`·`docs/REFERENCE.md`·`CHANGELOG.md` 안내로 바꾼다. 디렉터리 구조 블록을 실제 구조로(`controllers/playlist_flow.py`, `gaindb/`, `docs/` 등). ADR-003 링크는 `docs/legacy/ADR.md` 로
  - 확인: `Select-String -Path README.md -Pattern "WORKLOG.md","사용자 설정 폴더"` → 0건 / README 의 상대 링크 대상이 모두 존재 (`Select-String` 으로 `](` 링크 추출 → 각각 `Test-Path` True)
  - 결과: 2026-10-28 통과 — "WORKLOG.md"·"사용자 설정 폴더" 0건 / 상대 링크 14개 모두 존재 / 디렉터리 구조에 playlist·update 모듈·gaindb·docs·개발 도구 파일 반영
  - 커밋: `docs(readme): config 위치·문서 안내·디렉터리 구조를 현행에 맞춤`
- [x] 6. 다운로드 워커 파싱 함수 특성 테스트 (F9) — `tests/test_download_worker_parsing.py`
  - 대상: `workers/download_worker.py > _is_transient_error, _parse_eta_secs, _format_eta_secs, _normalize_size_str, _split_size_str, _is_unknown_size`. 기대값은 현 코드 출력에서 얻는다. `_is_transient_error` 는 REFERENCE T3·T4 의 경계(403·429 일시, 400/401/404/410 영구, 포장된 `Unable to download webpage: HTTP Error 404`)를 반드시 포함
  - 확인: `venv\Scripts\python -m pytest tests/test_download_worker_parsing.py` → 전부 통과 / 변이 확인: `_is_transient_error` 의 반환을 임시로 뒤집으면 실패 → 원복 후 `git diff -- workers/` 출력 없음
  - 결과: 2026-10-28 통과 — 54 passed / 변이(`_is_transient_error` 일시 패턴 반환 True→False) 시 7 failed / 원복 후 `git diff -- workers/` 출력 없음 / `ruff check tests` 통과
  - 커밋: `test: 다운로드 워커 파싱 함수 특성 테스트 추가`
- [x] 7. 파일 유틸 특성 테스트 (F9) — `tests/test_file_utils.py`
  - 대상: `utils/file_utils.py > sanitize_filename, normalize_unicode, get_unique_path, format_duration`. NFD 한글 입력 → NFC 출력(T9), Windows 금지 문자, 중복 파일명(`tmp_path`), `None`·0·시간 경계
  - 확인: `venv\Scripts\python -m pytest` → 전부 통과 / 변이 확인 1회 후 `git diff -- utils/` 출력 없음
  - 결과: 2026-10-28 통과 — 전체 77 passed (이 파일 23) / 변이(`sanitize_filename` 의 NFC 정규화 제거) 시 1 failed / 원복 후 `git diff -- utils/` 출력 없음 / `ruff check tests` 통과
  - 커밋: `test: 파일 유틸 특성 테스트 추가`
- [ ] 8. 2026-07-09 실기 검증 마무리 (F10) — `docs/VERIFY_2026-07-09.md`, `docs/PROGRESS.md`
  - 사용자가 절차서대로 확인하고 번호별 통과/실패를 알려 준다. 통과는 확인 대기에서 지우고, 실패는 고치지 않고 미해결 + 다음 계획 후보로 기록. 알려 주지 않은 번호는 확인 대기에 남긴다
  - 실기기: 절차서 각 번호 → 절차서의 기대 결과
  - 커밋: `docs: 2026-07-09 작업분 실기 검증 결과 기록`
- [ ] 9. 인수 확인 — PRD 성공 기준과 F8~F11 인수 기준 전부
  - 확인: `venv\Scripts\python -m pytest` 통과 / `venv\Scripts\ruff.exe check .` 통과 / 작업 4·5 의 `Select-String` 재실행 / `git diff 301d5b3 -- gaindb/` 출력 없음 / `git log 301d5b3.. --format="%an <%ae>"` 가 모두 `metapbl <ggoyong2@gmail.com>`
  - 실기기: 성공 기준 장면(YouTube 단일) → PRD §1 판정 3항 모두 / 표본 8건(YouTube 단일·플레이리스트, SoundCloud, Vimeo, sendvid, Naver TV, Bandcamp, Dailymotion) → 완료 후 재생 가능. 판정은 D033 (성공 기준·작업 2 실패만 미완, 나머지는 기록, 원인 불명은 보류)
  - 커밋: `docs: 첫 계획 인수 확인 결과 기록` (PROGRESS·계획 상태 done)

## 자가 검토
- PRD 기능 누락: 없음 (F8 → 4·5, F9 → 6·7, F10 → 8·9, F11 → 1·2·3)
- 테스트로 옮기지 않은 인수 기준: F11 기준 2(기동·업데이트 모달), F10 전부, 성공 기준 → GUI·네트워크·탐색기 표시는 자동화 불가라 실기 (D026, D032)
- 순서 의존: 2 는 1 뒤(새 venv), 3 은 1 뒤, 6·7 은 3 뒤(pytest·pythonpath), 9 는 전부 뒤. 4·5·8 은 1 뒤면 순서 무관
- 특성 테스트 원칙: 이 계획은 기존 함수를 고치지 않으므로 6·7 자체가 특성 테스트다 (plan.md §2)
