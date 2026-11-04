# 열 번째 계획 — 일부 화질 다운로드 오류 수정 · 항목별 임시 폴더 작업
상태: active | 시작: 2026-11-04 | 근거: PRD F1 (D054, D055, D056, Q060~Q062)

목표: (1) 포맷 목록에 보인 화질을 다운로드 때도 받을 수 있어 "Requested format is not available" 이 나지 않는다. (2) 각 항목은 자기 임시 폴더에서 작업을 모두 끝낸 뒤 저장 폴더로 옮겨진다. 저장 폴더의 기존 파일은 원본으로 쓰이거나 지워지지 않고, 같은 이름이 있으면 `제목 (1).ext` 로 둘 다 남는다.
구조:
- 바뀜: `core/downloader.py`(JS 옵션 상수, `trim_file_name`), `core/info_fetcher.py`·`workers/playlist_probe_worker.py`(같은 상수 사용), `workers/download_worker.py`(임시 폴더 수명, 완료 후 이동, 잔여물 추적 코드 제거), `utils/file_utils.py`(`move_unique`, `sweep_stale_temp_dirs`), `controllers/download_manager.py`(기동 시 청소), `docs/REFERENCE.md` R§2·R§4, `docs/PROGRESS.md`, `CHANGELOG.md`
- 생김: `tests/test_js_runtime_opts.py`, `tests/test_move_unique.py`, `tests/test_item_temp_dir.py`
- 진단 근거 (2026-11-04 실측):
  - 포맷: LXb3EKWsInQ·EkRmp25XkZc 모두 정보 추출 옵션에는 포맷 136 있음(72개·53개), 다운로드 옵션에는 없음(69개·43개). yt-dlp 는 `js_runtimes` 를 빼면 Deno 만 켠다
  - 현재 방식(로컬 서버): 기존 `T.m4a`·`T.mp4` 를 원본 삼아 MP3 로 변환한 뒤 삭제, 같은 번호 조각 재사용, 최종 파일이 있으면 요청 화질과 관계없이 완료, 기존 파일 태그 덮어쓰기
  - 임시 폴더 방식(같은 조건): 위 사례 모두 새로 받고 기존 파일 유지, 2개 동시 다운로드도 `T.mp4`·`T (1).mp4` 로 분리
전역 제약:
- [AI] 임시 폴더는 `tempfile.mkdtemp(prefix=".avd_", dir=save_dir)` 로 워커가 만든다. `Downloader.download` 에는 `save_dir` 대신 이 폴더를 넘긴다
- [AI] 실행 순서는 다운로드·병합·후처리 → 음량 정규화 → 이동 → `download_finished`(최종 경로) → 임시 폴더 삭제. 항목의 슬롯 해제 시점(D005)은 바꾸지 않는다
- [AI] 이동은 `open(dst, "x")` 로 이름을 먼저 차지하고 `os.replace` 로 덮어쓴다. 다른 항목과 동시에 옮겨도 기존 파일을 덮어쓰지 않으며, 별도 Lock 이 필요 없다
- [AI] 이동이 실패하면 오류로 끝내되 임시 폴더를 지우지 않고 오류 문구에 그 경로를 넣는다. 받은 파일을 잃지 않기 위해서다
- [AI] 재시도는 지금처럼 처음부터 받는다. 자식 프로세스를 끝낸 뒤 임시 폴더를 지우고 새로 만든다 (Windows 파일 잠금, 기존 순서 유지)
- [AI] `trim_file_name` 을 200 → 180 으로 낮춘다. 임시 폴더 이름(14자)만큼 경로가 길어져 260자 제한에 먼저 닿는 것을 막는다. 180자를 넘는 제목의 파일명은 전보다 짧아진다
- [AI] 강제 종료로 남은 임시 폴더는 기동 시 현재 저장 폴더에서 수정한 지 1일이 지난 `.avd_*` 만 지운다. 실행 중인 다른 인스턴스의 작업을 지우지 않기 위해 1일을 둔다
- `requirements.txt` yt-dlp 핀 그대로 (D002), `gaindb/` 무수정 (D015)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. JS 런타임 옵션 통일 — `core/downloader.py > JS_CHALLENGE_OPTS`·`Downloader.download`, `core/info_fetcher.py > InfoFetcher.fetch`, `workers/playlist_probe_worker.py`
  - 실패하는 테스트 먼저 (`tests/test_js_runtime_opts.py`): `yt_dlp.YoutubeDL` 을 바꿔치기해 세 곳이 넘기는 옵션을 잡는다 → 세 곳의 `js_runtimes`·`remote_components` 가 같고, `node`·`deno`·`bun` 이 모두 있다
  - `_BASE_OPTS` 위의 "자동 탐지에 맡김" 주석을 실제 동작에 맞게 고친다
  - 확인: 위 테스트·전체 pytest·ruff 통과 | 실측: 두 영상을 다운로드 옵션으로 추출 → 포맷 136 있음, 720p 실제 다운로드 → "Requested format"·403 오류 없음, ffprobe 높이 720
- [x] 2. 겹치지 않는 이동 — `utils/file_utils.py > move_unique`
  - 실패하는 테스트 먼저 (`tests/test_move_unique.py`): 같은 이름 없음 → `T.mp4` / 있음 → `T (1).mp4` / 둘 있음 → `T (2).mp4` / 기존 파일 해시 그대로 / 스레드 2개 동시 이동 → 파일 2개, 내용 유지 / 이동 실패 → 차지한 빈 파일을 남기지 않고 원본 유지 / 제목에 점이 있어도 번호는 마지막 확장자 앞에 붙음 (`a.b.mp4` → `a.b (1).mp4`)
  - 확인: 위 테스트·전체 pytest·ruff 통과
- [x] 3. 항목별 임시 폴더 — `workers/download_worker.py > run`, `core/downloader.py > trim_file_name`
  - `_touched_files`·`_collect_paths_from_hook`·`_cleanup_residue`·`_safe_unlink` 를 임시 폴더 삭제로 대체한다. 취소·오류 때 추적한 경로를 지우던 코드가 기존 파일을 건드릴 여지도 함께 사라진다
  - 실패하는 테스트 먼저 (`tests/test_item_temp_dir.py`, 실제 yt-dlp·ffmpeg + 로컬 서버, 인터넷 없음):
    - 기존 `a.m4a` + MP3 요청 → `a.m4a` 해시 그대로, `a.mp3` 길이가 서버 파일과 같음
    - 기존 `av.mp4` + MP3 요청 (합쳐진 포맷만) → `av.mp4` 해시 그대로, `av.mp3` 생성
    - 기존 `av.mp4` + 같은 파일 요청 → `av.mp4` 해시·태그 그대로, `av (1).mp4` 생성, `download_finished` 가 `(1)` 경로
    - 저장 폴더에 `.avd_*` 가 남지 않음 (성공·취소·오류 모두). 취소·오류 때 기존 파일 그대로
    - 일시 오류 재시도 → 두 번째 시도가 새 임시 폴더에서 성공, 첫 임시 폴더 없음 (바꿔치기한 Downloader)
    - 이동 실패 → `error` 문구에 임시 경로, 임시 폴더와 파일 유지 (바꿔치기한 `move_unique`)
    - 음량 정규화가 이동 전 임시 파일에 적용됨 (바꿔치기한 gain 함수에 넘어온 경로)
  - 확인: 위 테스트·전체 pytest·ruff 통과
- [ ] 4. 오래된 임시 폴더 청소 — `utils/file_utils.py > sweep_stale_temp_dirs`, `controllers/download_manager.py`
  - 실패하는 테스트 먼저 (`tests/test_move_unique.py`에 추가): 수정 2일 전 `.avd_x` 삭제 / 방금 만든 `.avd_y` 유지 / `.avd_` 로 시작하지 않는 폴더·파일 유지 / 저장 폴더 없음 → 오류 없이 통과
  - 확인: 위 테스트·전체 pytest·ruff 통과
- [ ] 5. 문서 — `docs/REFERENCE.md` R§2 JS 런타임 설명·구조, R§4 함정 T23(`js_runtimes` 를 빼면 자동 탐지가 아니라 Deno 만 켜짐)·T24(같은 이름 파일이 있으면 yt-dlp 가 그 파일을 원본으로 후처리하고 삭제할 수 있음), `README.md` 에 관련 안내가 있으면 수정
  - 확인: `grep -n "T23\|T24" docs/REFERENCE.md` → 항목 있음, R§2 가 D055 와 일치
- [ ] 6. 인수 확인 — F1 변경 인수 기준을 실제 다운로드로 실행
  - Given 빈 임시 폴더 / When 같은 영상을 480p, 720p 순서로 받음 / Then `제목.mp4`(높이 480)와 `제목 (1).mp4`(높이 720)가 있고 첫 파일 해시 그대로, `(1)` 파일의 제목 태그에 번호 없음
  - Given 빈 임시 폴더 / When 같은 영상 두 화질을 동시에 받음 / Then 파일 2개, 높이가 각각 요청 화질, `.avd_*` 없음
  - Given 같은 제목의 mp4 가 있음 / When 같은 영상을 MP3 로 받음(음량 정규화 켬) / Then mp4 해시 그대로, mp3 에 정규화 적용
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과 | 실기기: 앱에서 같은 영상을 다른 화질로 두 번 받기 → 항목 둘 다 완료, 두 번째 ▶ 재생이 새 파일을 엶, 다운로드 중 취소 → 저장 폴더에 찌꺼기 없음

## 자가 검토
- PRD 기능 누락: 없음 (F1 이 대상. F2·F3·F5 는 같은 워커를 쓰므로 함께 적용되며 작업 3·6 으로 확인)
- 테스트로 옮기지 않은 인수 기준: YouTube 실제 다운로드·▶ 재생·취소 화면 → 인터넷과 GUI 가 필요해 실측·실기기 확인
- 순서 의존: 3 은 2 뒤, 4 는 2 뒤(같은 파일), 5 는 1·3 뒤, 6 은 모두 뒤. 1 은 독립
- 범위 밖: 이어받기(재시도는 지금도 처음부터), 임시 폴더 숨김 속성, 예전 저장 폴더의 임시 폴더 청소, Vimeo `curl_cffi`, README "비영리" 문구, 릴리스
