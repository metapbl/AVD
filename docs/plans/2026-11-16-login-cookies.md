# 스물일곱 번째 계획 — 로그인 쿠키 사용 (F15)
상태: in-progress | 시작: 2026-11-16 | 근거: 사용자 "1안 진행"(PRD §2.2 쿠키 지원) → Q088~Q090, D078·D079

목표: 환경설정에서 브라우저나 cookies.txt 를 고르면, 본인 계정이 볼 수 있는 영상(연령 제한·봇 확인 등)을 받을 수 있다.
구조:
- 생김: `tests/test_cookies.py`
- 바뀜:
  - `core/downloader.py` — `cookie_opts(config) -> dict`(`JS_CHALLENGE_OPTS` 옆), cookiefile 되쓰기 막기, `Downloader.download` 가 쿠키 옵션을 받음
  - `core/info_fetcher.py > InfoFetcher.fetch`, `workers/playlist_probe_worker.py` — 같은 쿠키 옵션을 받음
  - `workers/info_worker.py`·`workers/download_worker.py`·`controllers/download_manager.py`·`controllers/playlist_flow.py`·`ui/main_window.py` — 워커를 만들 때 설정에서 쿠키 옵션을 만들어 넘김
  - `ui/preferences_dialog.py` — "로그인 쿠키" 구역
  - `ui/main_window.py > _friendly_error` — 쿠키 읽기 실패 안내, "추후 지원 예정" 문구 교체
  - `utils/config_manager.py > DEFAULT_CONFIG` — `cookie_source`("none"|"browser"|"file", 기본 "none")·`cookie_browser`(기본 "firefox")·`cookie_file`(기본 "")
전역 제약:
- 앱 코드는 쿠키 값을 읽거나 옮기지 않는다. 출처만 yt-dlp 옵션(`cookiesfrombrowser`·`cookiefile`)으로 넘긴다 (D079)
- 사용자 cookies.txt 를 고치지 않는다 — yt-dlp 는 `close()` 때 `save_cookies()` 로 cookiefile 에 다시 쓴다(2026.10.26 `YoutubeDL.py` 1054·1064행 확인). 막는 방법은 작업 2 에서 정하고 테스트로 고정한다
- 브라우저 목록은 `yt_dlp.cookies.SUPPORTED_BROWSERS` 를 그대로 쓴다 (직접 목록을 만들지 않음)
- UI 미리보기 썸네일 받기(`workers/thumbnail_worker.py`)에는 쿠키를 쓰지 않는다 (D079)
- 색은 `ui/theme.py` 이름으로 (D065). 워커→메인 연결은 QueuedConnection (D013)
- yt-dlp 핀은 올리지 않는다 (D002)

## 작업
- [x] 0. PRD·보안 정책 승인 — 상태 `changing` → `approved (날짜)`, OPEN 재확인 1건(D079 [AI] 부분) 사용자 확인
  - 확인: 2026-11-16 사용자 "승인" (AI 기본값 포함)
- [ ] 1. 테스트 먼저 — `tests/test_cookies.py`
  - `cookie_opts`: "none" → `{}` | "browser"+firefox → `{"cookiesfrombrowser": ("firefox",)}` | "file"+경로 → `{"cookiefile": 경로}` | "file"+빈 경로 → `{}`
  - 세 경로(정보·플레이리스트·다운로드)가 만드는 yt-dlp 옵션에 쿠키 옵션이 들어간다 (`yt_dlp.YoutubeDL` 을 가로채 확인, 네트워크 없음)
  - 실제 `YoutubeDL` 을 임시 cookies.txt 로 열고 쿠키를 불러온 뒤 닫는다 → 파일 내용·수정 시각 그대로
  - `_friendly_error`: 쿠키 읽기 실패 원문(DPAPI 복호화 실패, 쿠키 DB 복사 실패, 파일 없음·Netscape 형식 아님) → "로그인 쿠키를 읽지 못했습니다" + 대처 | 봇 감지 안내에 "추후 지원 예정" 없음
  - 환경설정: 세 선택 저장·다시 열기 유지, `config.json` 에 쿠키 값 없음(출처 키만)
  - 확인: 새 테스트가 실패(빨강)하는 것을 본다
- [ ] 2. 구현 core·워커 — `cookie_opts`, cookiefile 보호, 세 경로 연결
  - 확인: 작업 1 의 core 테스트 통과, 전체 pytest 통과, ruff 통과
- [ ] 3. 구현 UI — 환경설정 구역(라디오 셋 + 브라우저 콤보 + 파일 고르기), 오류 안내 문구
  - 확인: 작업 1 전부 통과, 전체 pytest·ruff 통과. 캡처로 환경설정 창 확인 (다크·라이트)
- [ ] 4. 사용자 실기 확인 (Windows, 소스 실행)
  - 로그인된 Firefox → 연령 제한 YouTube 영상 받기 | cookies.txt(브라우저 확장으로 내보냄) → 같은 영상 받기, 파일 수정 시각 그대로 | Chrome 을 고름 → 실패 시 안내 문구 | "사용 안 함" → 지금과 같음
- [ ] 5. 문서 — README(로그인 쿠키 사용법, DRM 우회 금지 방침 문단에 D078 해석 한 줄), CHANGELOG, PROGRESS, REFERENCE 함정 대장(yt-dlp 의 cookiefile 되쓰기), PRD F15 완료 표시
- [ ] 6. 커밋 (`feat(cookies): ...`, 작성자 확인)

## 자가 검토
- PRD 기능 누락: F15 인수 기준 6개 = 작업 1(자동 5) + 작업 4(실기: Firefox·cookies.txt 실제 받기)
- 테스트로 옮기지 않은 인수 기준: 실제 로그인 상태로 연령 제한 영상이 받아지는지 → 작업 4
- 하지 않는 것: 쿠키 내보내기 기능, 사이트별 쿠키 켜기/끄기, 브라우저 프로필 선택, Chrome 앱 전용 암호화 우회, exe 빌드 확인(릴리스 계획에서)
- 위험:
  - Windows Chrome·Edge 는 대부분 읽기에 실패한다 — 안내 문구로 Firefox·cookies.txt 를 권한다
  - yt-dlp 자동 업데이트로 cookiefile 처리 방식이 바뀌면 보호가 깨질 수 있다 — 작업 1 의 무변경 테스트가 실제 yt-dlp 로 돌아서 잡는다 (단, 소스 실행 환경의 yt-dlp 기준)
  - 쿠키를 켜면 계정 단위로 사이트 제재를 받을 수 있다 — README 에 한 줄 안내
