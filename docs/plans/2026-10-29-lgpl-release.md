# 네 번째 계획 — LGPL 배포 산출물과 첫 릴리스
상태: active | 시작: 2026-10-29 | 근거: PRD §2.2 [두 번째 계획] 항목, §2.6, F7 (D011, D022, D038, D039, D040)

목표: Windows 사용자가 GitHub Release 의 zip 을 풀어 `AVD.exe` 로 바로 쓴다. `gaindb/` 는 평문 `.py` 로 교체할 수 있고, 릴리스에 소스 zip 과 의존성 라이선스 전문이 함께 있다. exe 에서도 yt-dlp 자동 업데이트가 동작한다.
구조:
- 생김: `AVD.spec`(PyInstaller onedir), `build.ps1`(빌드→라이선스 동봉→zip 2개), `THIRD_PARTY_LICENSES`(루트, 본체 의존성 전문), `docs/RELEASE.md`(릴리스 절차서), `tests/test_frozen_paths.py`, `tests/test_ytdlp_wheel.py`, `tests/test_third_party_licenses.py`
- 바뀜: `requirements-dev.txt`(pyinstaller), `utils/config_manager.py > CONFIG_PATH`, `utils/updater.py`(wheel 설치 함수 추가), `workers/update_worker.py > UpdateWorker.run`(frozen 분기), `NOTICE`, `README.md`, `.gitignore`(`release/`), `utils/updater.py > APP_VERSION`(작업 9), `CHANGELOG.md`
전역 제약:
- `gaindb/` 무수정, `requirements.txt` 의 yt-dlp 핀 유지 (D015, D002)
- 소스 실행(`venv\Scripts\python main.py`) 동작은 바뀌지 않는다. 새 분기는 모두 `getattr(sys, "frozen", False)` 일 때만 탄다
- onedir 만 (onefile 금지, D011). `gaindb`·`yt_dlp` 는 `module_collection_mode="py"` 로 `_internal\` 아래 평문 `.py` (D038)
- [AI] 대상은 Windows x64 하나. macOS 는 H04 로 보류 그대로
- [AI] ffmpeg/ffprobe·Node.js 는 동봉하지 않는다 (NOTICE 기존 방침). README 에 별도 설치 안내
- [AI] 빌드는 지금 venv 그대로 쓴다. 번들된 yt-dlp 버전은 릴리스 노트에 적는다
- [AI] 시험 빌드(`dist\`·`build\` 만 씀)는 확인 없이, 릴리스 빌드·태그·`git push`·`gh release` 는 각각 실행 전 확인 (D032, D040)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. PyInstaller 도입과 최소 onedir 빌드 — `requirements-dev.txt`, `AVD.spec`
  - `pip install pyinstaller` 는 실행 전 확인 (D032). 설치 뒤 버전을 `requirements-dev.txt` 에 핀
  - spec: `windowed`, onedir, `module_collection_mode={"gaindb": "py", "yt_dlp": "py"}`, `gaindb/` 의 `LICENSE`·`NOTICE`·`THIRD_PARTY_LICENSES` 를 datas 로 같은 폴더에
  - Python 3.15·PySide6 6.12 를 지원하는 PyInstaller 가 없으면 여기서 멈추고 OPEN 에 질문을 넣는다
  - 확인: `venv\Scripts\pyinstaller AVD.spec --noconfirm` 성공 | `dist\AVD\_internal\gaindb\api.py`·`gaindb\LICENSE`·`yt_dlp\version.py` 가 평문으로 존재 | `AVD.exe` 기동 → 메인 창 표시
  - 결과 (2026-10-29): PyInstaller 6.22.3·Python 3.15.1 빌드 성공(경고는 선택 의존성 `curl_cffi`·`yt_dlp_ejs`·urllib3 emscripten, `scipy.special._cdflib` 숨은 import 없음 — 정규화 동작은 작업 7 에서 확인). 평문 파일 모두 존재(`yt_dlp` .py 1041개, 2026.10.26), 배포 폴더 239 MB. exe 기동 8초 만에 창 제목 "AV Downloader". `config.json` 은 아직 `_internal\` 에 생김 → 작업 2. `*.spec` 무시 규칙에 `!AVD.spec` 예외 추가
- [x] 2. exe 옆 config.json (D039) — `utils/config_manager.py > CONFIG_PATH`
  - 실패하는 테스트 먼저: `sys.frozen=True`·`sys.executable` 을 임시 경로로 바꾸고 모듈 reload → `CONFIG_PATH == exe 폴더/config.json` / 바꾸지 않으면 지금 경로(리포 루트) 그대로
  - 확인: `venv\Scripts\python -m pytest tests/test_frozen_paths.py` 통과 → 전체 pytest 통과
  - 결과 (2026-10-29): frozen 테스트 먼저 실패 확인 → 구현 뒤 pytest 85 통과, ruff 통과. 시험 빌드 기동 → `dist\AVD\config.json` 생김, `_internal\config.json` 없음
- [x] 3. yt-dlp wheel 설치 함수 (D038) — `utils/updater.py > install_ytdlp_wheel(dest_dir, on_line)`
  - PyPI JSON(`https://pypi.org/pypi/yt-dlp/json`)의 `py3-none-any` wheel URL·sha256 → 받기 → sha256 대조 → 임시 폴더에 `yt_dlp/` 만 풀기 → `dest_dir\yt_dlp` 를 `yt_dlp.old` 로 옮기고 새 폴더로 바꾼 뒤 옛 폴더 삭제. 바꾸는 도중 실패하면 옛 폴더를 되돌린다
  - 실패하는 테스트 먼저 (네트워크는 가짜 응답, 가짜 wheel zip): 정상 → 새 `version.py` 로 교체됨 / sha256 불일치 → 실패 반환, 기존 폴더 그대로 / 교체 중 예외 → 기존 폴더 복원
  - 확인: `venv\Scripts\python -m pytest tests/test_ytdlp_wheel.py` 통과 → 전체 pytest 통과
  - 결과 (2026-10-29): 3건 먼저 실패 확인 → 구현 뒤 pytest 88 통과, ruff 통과. 실제 PyPI 로 임시 폴더에 시험 → `yt_dlp-2026.10.26-py3-none-any.whl` 받아 sha256 통과·교체, 찌꺼기 없음
- [x] 4. UpdateWorker frozen 분기 — `workers/update_worker.py > UpdateWorker.run`
  - frozen 이면 pip 대신 작업 3 함수 호출(`dest_dir = Path(yt_dlp.__file__).parent.parent`), 진행 줄은 `progress_text` 로, 완료 문구 "다시 시작하면 적용됩니다". 소스 실행 경로는 손대지 않는다
  - REFERENCE 함정 대장에 "동결 빌드의 `sys.executable` 은 AVD.exe — `-m pip` 이 앱을 다시 띄운다" 추가
  - 실패하는 테스트 먼저: frozen + 작업 3 함수를 가짜로 → `run()` 직접 호출 시 `done(True, …)`, subprocess 미호출
  - 확인: pytest 통과 | 시험 빌드 후 실기기 확인은 작업 7
  - 결과 (2026-10-29): `tests/test_update_worker.py` 2건 먼저 실패 확인 → 구현 뒤 pytest 90 통과, ruff 통과. REFERENCE R§4 T17 추가. 시험 빌드·기동 정상 (업데이트 실제 동작은 작업 7)
- [x] 5. 루트 THIRD_PARTY_LICENSES 와 NOTICE — `THIRD_PARTY_LICENSES`, `NOTICE`
  - `requirements.txt` 의 각 패키지 + Python(PSF) + PyInstaller 부트로더(GPL 예외)의 라이선스 전문. 원문은 venv 의 `*.dist-info` 라이선스 파일에서 옮긴다 (Qt/PySide6 는 LGPLv3 전문, 참조하는 GPLv3 전문 포함)
  - NOTICE 에 THIRD_PARTY_LICENSES 위치와 배포본 안의 `gaindb` 위치(`_internal\gaindb\`) 한 줄
  - 실패하는 테스트 먼저: `requirements.txt` 의 모든 패키지 이름이 THIRD_PARTY_LICENSES 의 절 제목에 있다
  - 확인: `venv\Scripts\python -m pytest tests/test_third_party_licenses.py` 통과
  - 결과 (2026-10-29): 2건 먼저 실패 확인 → 생성 뒤 pytest 92 통과, ruff 통과. 13절 220 KB — requirements 11개(PySide6 계열 4개는 한 절) + Python(기본 설치 `LICENSE.txt`) + PyInstaller(`COPYING.txt`) + setuptools(빌드 때 런타임 훅이 실음). PySide6 wheel 에 LGPL 전문이 없어 사용자 GaindB 리포의 `licenses/qt/LGPL-3.0.txt`·`GPL-3.0.txt` 를 옮김. `dist` 에 메타데이터만 실린 pluggy 는 코드가 없어 제외. 생성 스크립트는 리포에 넣지 않음 (1회용)
- [x] 6. 빌드 스크립트 — `build.ps1`, `.gitignore`
  - pyinstaller → `LICENSE`·`NOTICE`·`THIRD_PARTY_LICENSES`·`README.md` 를 `dist\AVD\` 에 복사 → `release\AVD-v{APP_VERSION}-win64.zip` 와 `git archive` 로 `release\AVD-v{APP_VERSION}-src.zip`
  - 확인: `.\build.ps1` → zip 2개 생성 | exe zip 목록에 `AVD.exe`·`LICENSE`·`NOTICE`·`THIRD_PARTY_LICENSES`·`_internal\gaindb\api.py`·`_internal\gaindb\LICENSE` 존재 | src zip 에 `gaindb\`·`main.py` 존재
  - 결과 (2026-10-29, `b1066c8`): 커밋 안 된 변경이 있으면 멈춤 확인(소스 zip 이 exe 와 같은 커밋이어야 해서 추가). `AVD-v1.0.0-win64.zip` 100.0 MB·1394항목, 필수 8개 모두 있음 / `AVD-v1.0.0-src.zip` 0.3 MB·96항목, `gaindb/api.py`·`main.py`·`LICENSE`·`AVD.spec` 있음. 두 zip 모두 `config.json` 없음
- [x] 7. exe 실기기 확인 (작업 6 의 zip 을 리포 밖 새 폴더에 풀어서)
  - 실기기: 단일 YouTube 다운로드 → 완료·재생 가능 | MP3 + 음량 정규화 → 완료, 태그 기록 | 환경설정 저장 → exe 옆에 `config.json` 생김
  - 실기기 (교체 가능성): `_internal\gaindb\api.py` 공개 함수 첫 줄에 표시 파일을 쓰는 한 줄을 넣고 정규화 실행 → 그 파일이 생김 (평문 수정이 반영됨)
  - 실기기 (업데이트 리허설): `_internal\yt_dlp\version.py` 의 `__version__` 을 옛 값으로 바꾸고 기동 → 업데이트 질문 → 예 → 완료 문구 → 다시 시작 → 질문 없음, 버전이 최신
  - 판정: Claude 가 할 수 있는 것은 D036 처럼 대리 확인하고, 창 표시·탐색기는 사용자 눈 확인
  - 결과 (2026-10-29, `a4ce4b0` 빌드를 scratchpad 에 풀어서): 사용자 — 업데이트 질문·예·완료, AVD 창 중복 없음, 다시 켜면 질문 없음, mp4(VP9+Opus)·mp3(192k, "음량 −3.0dB") 완료. Claude 대리 — `yt_dlp\version.py` 2026.03.17→2026.10.26·`yt_dlp.old` 없음(실행 중 폴더 이름 바꾸기 성공), `config.json` exe 옆, `REPLACED_MARKER.txt` 생김, 두 파일 ffmpeg 전체 디코딩 오류 0, mp3 표지(mjpeg)·제목·아티스트·NFC 파일명 정상, MP3Gain 태그 `status ok`·volume 88.3(목표 89, −3.0dB 적용 뒤 값과 맞음). 업데이트 뒤 자동 재시작 요청 → Q049
- [ ] 8. 업데이트 뒤 자동 재시작 (D041) — `utils/updater.py > restart_command`, `ui/main_window.py > _run_ytdlp_update`
  - 실패하는 테스트 먼저: `restart_command()` — frozen 이면 `[AVD.exe, *argv[1:]]`, 소스면 `[python, *argv]`
  - 성공한 업데이트의 "닫기" 뒤: 끝나지 않은 항목이 없으면 새 프로세스를 띄우고 `QApplication.quit()`, 있으면 안내만. 완료 문구를 "닫기를 누르면 앱을 다시 시작합니다" 로
  - 확인: pytest 통과 | 실기기 (scratchpad 의 새 빌드, `version.py` 를 옛 값으로): 업데이트 → 닫기 → 앱이 꺼졌다 다시 뜨고 질문 없음, AVD 프로세스 1개
- [ ] 9. 배포본 안내와 릴리스 절차서 — `README.md > 설치`, `docs/RELEASE.md`
  - README: zip 풀기 → ffmpeg·Node.js 설치 → `AVD.exe`, `gaindb` 교체 위치, 설정 파일 위치
  - RELEASE.md: 버전 올리기 → CHANGELOG → `build.ps1` → 실기기 최소 항목(작업 7 의 첫 줄) → 태그·push → `gh release create` 에 zip 2개
  - 확인: 두 문서에 적힌 경로를 `Test-Path` 로 작업 6 산출물에 대조 → 전부 True
- [ ] 10. 첫 릴리스 게시 (D040) — `utils/updater.py > APP_VERSION`, `CHANGELOG.md`
  - `gh release list --repo metapbl/AVD` 와 원격 태그로 기존 번호 확인 → 버전 제안 → 사용자 확인 → `APP_VERSION` 갱신·커밋
  - RELEASE.md 절차대로: 릴리스 빌드(확인) → 태그 → `git push` 와 태그 push(확인) → `gh release create`(확인), 노트에 번들 yt-dlp 버전·ffmpeg 별도 설치 안내
  - 확인: `gh release view v{버전} --repo metapbl/AVD --json assets` → zip 2개 | 받은 exe zip 을 새 폴더에 풀어 기동 → 메인 창
- [ ] 11. 인수 확인
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과 | `ruff check` 통과 | `git diff 90d1a0e.. -- gaindb/` 비어 있음 | 소스 실행 `venv\Scripts\python main.py` 기동 정상
  - 실기기: 성공 기준 장면(YouTube 단일)을 릴리스에서 받은 exe 로 → PRD §1 판정 3항

## 자가 검토
- PRD 기능 누락: 없음 — §2.2 항목의 onedir 빌드(1·6), `gaindb/` 평문 배치(1·7), THIRD_PARTY_LICENSES(5), 릴리스 절차(9·10). F7 은 exe 에서도 동작하도록(3·4), 업데이트 뒤 재시작(8)
- 테스트로 옮기지 않은 인수 기준: exe 기동·교체 가능성·업데이트 리허설(7·8)과 게시(10)는 동결 빌드·GitHub 가 있어야 해서 자동 테스트가 안 된다 → 실기기 확인으로 대체. 경로 판별·wheel 교체·워커 분기·라이선스 목록은 테스트(2~5)
- 순서 의존: 2~5 는 1 뒤(빌드가 되는지 먼저 확인), 6 은 5 뒤, 7 은 2~6 뒤, 8 은 4·7 뒤, 9 는 6·8 뒤, 10 은 7~9 뒤, 11 은 마지막
- 알림 (고치지 않음): `utils/updater.py > YtdlpUpdater.update`(pip 직접 호출)와 `AppUpdater`(onefile exe 교체 가정)는 호출처가 없다. onedir 에선 `AppUpdater` 가 맞지 않으므로 앱 자체 업데이트를 쓰게 될 때 다시 본다
- PRD 본문: §5 "배포 형태 … (미착수)" 표기는 완료 뒤 갱신이 필요하다 — PRD 변경 절차(/metarche discover)로 처리할지 작업 11 에서 묻는다
