# 스물한 번째 계획 — Vimeo 공개 영상 지원
상태: active | 시작: 2026-11-11 | 근거: PRD F12 (D067~D070, Q076~Q080)

목표: Vimeo 공개 영상 링크를 붙여 넣으면 다른 사이트처럼 화질 선택 → 다운로드가 된다. 비공개·로그인·도메인 제한 영상은 지금처럼 오류로 끝나고 앱은 정상이다.
구조:
- 바뀜: `requirements.txt`(3줄), `THIRD_PARTY_LICENSES`(절 추가), `ui/add_link_dialog.py`(`extract_urls` 가 주소 바꾸기 함수를 거침), `docs/REFERENCE.md` R§2·R§4, `README.md`(지원 안내가 있으면), `docs/PROGRESS.md`, `CHANGELOG.md`
- 생김: 없음 (테스트는 `tests/test_add_links.py`·`tests/test_third_party_licenses.py` 에 추가·기존 검사 활용)
- 진단 근거 (2026-11-11 실측, Q076): `vimeo.com/1084537` 은 curl_cffi 가 있어도 로그인 필요 / `player.vimeo.com/video/1084537` 은 curl_cffi 있으면 형식 13개·미디어 수신, 없으면 401 / PyInstaller 6.22.3 onedir 은 yt-dlp 훅이 `curl_cffi`·`curl_cffi.libs` 를 자동 수집
전역 제약:
- [U] 주소 바꾸기는 `vimeo.com/숫자` 꼴만 (D068). 해시가 붙은 링크·showcase·channels·다른 사이트는 그대로
- [AI] 꼴 판정은 `^https?://(www\.)?vimeo\.com/(\d+)/?([?#].*)?$`. 뒤의 `?`·`#` 는 버리고 `https://player.vimeo.com/video/{숫자}` 로 쓴다 (공유 링크의 `?share=copy` 등은 영상 선택에 쓰이지 않음). 바꾼 뒤 같은 주소는 하나만 남긴다
- [AI] 바꾸기는 `extract_urls` 안에서 한다 — 대화창·끌어다 놓기·클립보드가 모두 이 함수를 거치므로 한 곳이면 된다. 재시도는 항목에 저장된 (바뀐) 주소를 그대로 쓴다
- [U] 런타임 의존성은 `curl-cffi==0.17.0`·`cffi==2.1.1`·`pycparser==3.11` 만 추가. yt-dlp·certifi 핀 그대로 (D002, D069)
- [AI] `AVD.spec` 은 고치지 않는다 — yt-dlp 훅이 curl_cffi 를 수집한다(시험 빌드 확인). 작업 4 에서 빠지면 그때 고친다
- `pip install`·PyInstaller 릴리스 빌드·`git push` 는 실행 전 확인 (D032). `gaindb/` 무수정 (D015)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. 의존성 추가와 라이선스 고지 — `requirements.txt`, `THIRD_PARTY_LICENSES`
  - 실패하는 테스트 먼저: `requirements.txt` 에 3줄 추가 → `tests/test_third_party_licenses.py::test_every_requirement_has_a_section` 실패 (curl-cffi·cffi·pycparser 절 없음)
  - 절 추가: curl_cffi(MIT), cffi(MIT-0), pycparser(BSD-3-Clause) 전문. `curl_cffi.libs\libcurl-impersonate-*.dll` 에 함께 들어간 구성요소(curl, BoringSSL, nghttp2 등)는 curl_cffi·curl-impersonate 저장소의 라이선스 목록으로 확인해 같은 절 아래 고지
  - venv 설치 (실행 전 확인): `venv\Scripts\python -m pip install -r requirements.txt`
  - 확인: 위 테스트·전체 pytest 통과, `venv\Scripts\python -m pip check` → 문제 없음, `venv\Scripts\python -m yt_dlp --list-impersonate-targets` → Chrome 등 `curl_cffi` (unavailable 없음), `venv\Scripts\pip-audit -r requirements.txt` → 보고가 yt-dlp 핀만(D002), `git diff requirements.txt` → 추가 3줄 + certifi 한 줄 (D071)
  - 결과: 2026-11-11 — certifi 충돌(curl-cffi 0.17.0 은 `certifi>=2026.10.19`) → certifi 2026.10.23 (D071). 절 3개 + dll 구성요소 10개 원문(curl 8.23.0·curl-impersonate 2.3.1·BoringSSL main·zlib 1.3.1·brotli 1.2.1·zstd 1.5.7·c-ares 1.34.9·nghttp2 1.63.0·ngtcp2 1.20.0·nghttp3 1.15.0). pytest 274 통과, pip check 통과, pip-audit 은 yt-dlp 2026.3.17 핀 2건뿐. `pip install -r` 이 venv yt-dlp 를 핀으로 내려 위장이 꺼짐(2026.3.17 은 curl_cffi `<0.15`) → venv 를 2026.10.26 으로 되돌려 위장 대상 unavailable 0
  - 관찰: 표본 1084537 이 같은 날 오후부터 임베드도 401(위장 사용 확인, 다른 공개 영상 76979871·22439234 는 성공) → 작업 5 표본을 76979871 로
- [x] 2. Vimeo 주소 바꾸기 — `ui/add_link_dialog.py > extract_urls` (+ 같은 모듈의 작은 함수)
  - 실패하는 테스트 먼저 (`tests/test_add_links.py::test_extract_urls` 매개변수 추가):
    - `https://vimeo.com/1084537` → `https://player.vimeo.com/video/1084537`
    - `http://www.vimeo.com/1084537/`·`https://vimeo.com/1084537?share=copy` → 같은 player 주소
    - `https://vimeo.com/1084537/abcdef1234`(해시)·`https://vimeo.com/showcase/123`·`https://vimeo.com/channels/staffpicks/1` → 그대로
    - `https://player.vimeo.com/video/1084537` → 그대로, `https://www.youtube.com/watch?v=x` → 그대로
    - `https://vimeo.com/1084537` 와 `https://player.vimeo.com/video/1084537` 를 함께 붙여 넣음 → 하나만
  - 확인: 위 테스트·전체 pytest·ruff 통과
  - 결과: 2026-11-11 — 매개변수 9개 추가(표본 번호 76979871), 구현 전 4건 실패 → `_embed_url` 추가 후 pytest 283 통과, ruff 통과
- [x] 3. 문서 — `docs/REFERENCE.md` R§2 외부 사양(Vimeo 는 임베드 주소 + TLS 위장, curl_cffi 허용 범위 `>=0.10,<0.18`), R§4 함정 T 번호 하나(`vimeo.com/ID` 는 위장해도 로그인 필요, 위장 없으면 임베드 401), `README.md` 에 사이트·설치 안내가 있으면 한 줄
  - 확인: `grep -n "player.vimeo.com" docs/REFERENCE.md` → R§2·R§4 에 있음, README 설치 절차가 `requirements.txt` 하나로 그대로 맞음
  - 결과: 2026-11-11 — R§2 Vimeo 한 줄(`player.vimeo.com`), R§4 T28(Vimeo 로그인·401)·T29(`pip install -r` 이 yt-dlp 를 핀으로 내려 위장 꺼짐). README 설치 절은 `pip install -r requirements.txt` 하나라 그대로
- [x] 4. exe 빌드 확인 (빌드는 실행 전 확인) — `AVD.spec` 그대로
  - 확인: PyInstaller 빌드 성공, `dist\AVD\_internal\curl_cffi\`·`_internal\curl_cffi.libs\*.dll` 존재, 배포 폴더 크기 증가 약 5~6 MB | 실기기(기계): `dist\AVD\AVD.exe` 기동 → 창 제목 "AV Downloader"
  - 결과: 2026-11-11 — `pyinstaller AVD.spec` 성공(spec 무수정), `_internal\curl_cffi\`·`curl_cffi-0.17.0.dist-info`·`curl_cffi.libs\libcurl-impersonate-*.dll`(4,113,920 B) 있음, 배포 폴더 244.5 MB(이전 243 MB 안팎), 번들 yt-dlp 2026.10.26, `dist\AVD\THIRD_PARTY_LICENSES` 에 curl-cffi 절. `AVD.exe` 7초 만에 창 제목 "AV Downloader"
- [ ] 5. 인수 확인 — PRD F12 인수 기준을 모두 실행
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과, `git diff b2f4dce -- requirements.txt`(계획 시작 전 커밋 기준) 추가 3줄 + certifi 한 줄
  - 실기기 (소스 실행과 exe 각각):
    - `https://vimeo.com/76979871` 붙여넣기 → 화질 선택 창이 뜸 → 받은 파일 ▶ 재생됨
    - 받을 수 없는 Vimeo 링크(해시가 틀린 `https://vimeo.com/1084537/0000000000`, 없는 번호 `https://vimeo.com/1`) → 오류 표시, 다른 항목 추가·다운로드 계속 정상
    - YouTube 단일 링크 하나 → 지금처럼 완료 (회귀)

## 자가 검토
- PRD 기능 누락: 없음 (F12. F1 의 링크 추가 경로가 바뀌므로 작업 5 에 YouTube 회귀 확인)
- 테스트로 옮기지 않은 인수 기준: Vimeo 실제 다운로드·오류 표시·exe → 인터넷·GUI·빌드가 필요해 실기기 확인. "로그인 필요·비공개" 표본은 공개 표본을 찾기 어려워 받을 수 없는 링크(틀린 해시·없는 번호)로 대신한다 — 오류 경로는 같다
- 순서 의존: 2 는 1 과 독립(테스트만), 3 은 1·2 뒤, 4 는 1 뒤, 5 는 모두 뒤
- 범위 밖: 미등록(해시) 링크 지원 (D067 에서 버림), 쿠키·로그인, macOS 확인, 릴리스
