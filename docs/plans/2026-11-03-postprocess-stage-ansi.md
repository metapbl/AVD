# 아홉 번째 계획 — 후처리 단계 표시 · 오류 원문 ANSI 제거 · 문서 정리
상태: active | 시작: 2026-11-03 | 근거: PRD F1, F4 (Q059)

목표: (1) 다운로드·병합이 끝난 뒤 후처리(MP3 변환·태그 기록·썸네일 임베드)가 파일을 다시 쓰는 동안 상태 라벨이 "병합 중 100%"·"100.0% 다운로드 중" 에 멈춰 있지 않고 지금 단계를 보여 준다. (2) 오류 창 원문에 `[0;31mERROR:[0m` 같은 ANSI 색 코드가 보이지 않는다. (3) 여덟 번째 계획에서 미룬 문서 정리(PRD §2.2 완료 표시, 함정 T19~T22)를 반영한다.
구조:
- 바뀜: `workers/download_worker.py`(새 시그널 `postprocess_stage`, `_on_postprocess`, `run` 의 오류 문자열), `workers/info_worker.py`·`workers/playlist_probe_worker.py`(오류 문자열), `controllers/download_manager.py`(시그널 연결), `ui/download_item_widget.py`(새 `update_postprocess_stage`), `docs/REFERENCE.md` R§4, `docs/PRD.md` §2.2·§8, `CHANGELOG.md`
- 생김: `tests/test_postprocess_stage.py`, `tests/test_error_ansi.py`
전역 제약:
- [AI] 단계 라벨은 후처리 hook 의 `status == "started"` 일 때 `postprocessor` 이름으로만 고른다. 이름표: `FFmpegExtractAudio` → "MP3 변환 중", `FFmpegMetadata` → "태그 기록 중", `FFmpegThumbnailsConvertor`·`EmbedThumbnail` → "썸네일 넣는 중". 표에 없는 이름(`Merger`·`MoveFiles`·NFC `pre_process` 등)은 보내지 않는다. `Merger` 는 기존 `merging`·`merge_progress` 그대로
- [AI] 위젯은 라벨만 바꾸고 진행률 바는 그대로 둔다(100 근처). 상태가 DOWNLOADING·MERGING 이 아니면 늦게 온 값은 버린다. `DownloadStatus` 와 슬롯 해제 시점(D005)은 바꾸지 않는다
- [AI] ANSI 제거는 워커가 오류 문자열을 만들 때 기존 `utils.file_utils.strip_ansi` 를 한 번 거친다. 재시도 판단 `_is_transient_error` 도 지운 문자열로 한다
- 워커→위젯 연결은 `Qt.ConnectionType.QueuedConnection` 명시, 새 Signal 이름에 `finished`/`started` 금지 (D013, R§4 T2)
- `requirements.txt` yt-dlp 핀 그대로 (D002), `gaindb/` 무수정 (D015)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. 후처리 단계 라벨 — `workers/download_worker.py > _on_postprocess`, `controllers/download_manager.py`, `ui/download_item_widget.py > update_postprocess_stage`
  - 실패하는 테스트 먼저 (`tests/test_postprocess_stage.py`):
    - 워커: `{"status": "started", "postprocessor": "FFmpegMetadata"}` → `postprocess_stage("태그 기록 중")` 한 번 / `EmbedThumbnail`·`FFmpegThumbnailsConvertor` → "썸네일 넣는 중" / `FFmpegExtractAudio` → "MP3 변환 중" / 같은 이름의 `finished`·`Merger`·`MoveFiles` → 발사 없음
    - 위젯: MERGING 상태에서 `update_merge_progress(100, …)` 뒤 `update_postprocess_stage("태그 기록 중")` → 라벨 "태그 기록 중", 바 값 그대로 / DOWNLOADING 상태에서도 바뀜 / DONE·ERROR·CANCELLED 뒤 늦게 온 값은 무시
    - `DownloadWorker` 가 `finished`/`started` 를 가리지 않음 (기존 `test_worker_signals` 통과)
  - 확인: `venv\Scripts\python -m pytest tests/test_postprocess_stage.py` 통과 → 전체 pytest 통과 → ruff 통과
  - 결과 (2026-11-03): 테스트 먼저 12개 실패 확인(속성 없음) → 구현 뒤 새 테스트 12 통과, 전체 pytest 143 통과, ruff 통과, `gaindb/`·`requirements.txt` diff 없음. 이름표는 워커 모듈 상수 `_PP_STAGE_LABELS`. 실제 hook 이름 확인은 작업 4 실기기
- [x] 2. 오류 원문 ANSI 제거 — `workers/download_worker.py > run`, `workers/info_worker.py`, `workers/playlist_probe_worker.py`
  - 실패하는 테스트 먼저 (`tests/test_error_ansi.py`): 각 워커의 yt-dlp 호출이 `"\x1b[0;31mERROR:\x1b[0m [youtube] x: Private video"` 를 담은 예외를 던지게 바꿔 두고 실행 → `error` 시그널 문자열에 `\x1b` 가 없고 `"ERROR: [youtube] x: Private video"` 를 담음. 다운로드 워커는 ANSI 가 섞인 일시적 오류 문구도 재시도로 판정
  - 확인: `venv\Scripts\python -m pytest tests/test_error_ansi.py` 통과 → 전체 pytest 통과 → ruff 통과
  - 결과 (2026-11-03): 테스트 먼저 4개 실패 확인(원문에 `\x1b` 남음) → 세 워커의 `str(e)` 를 `strip_ansi(str(e))` 로 바꾼 뒤 새 테스트 4 통과, 전체 pytest 147 통과, ruff 통과, `gaindb/`·`requirements.txt` diff 없음. 재시도 판정은 지운 문자열로 (503 → 재시도 3회 확인)
- [x] 3. 문서 정리 — `docs/REFERENCE.md` R§4, `docs/PRD.md` §2.2·§8
  - REFERENCE R§4 표에 T19(exe 아이콘 리소스 번호), T20(소스 실행 업데이트 리허설은 실제 옛 yt-dlp 설치), T21(릴리스 전 `-r requirements.txt` 가 yt-dlp 를 핀으로 내림), T22(PostProcessor 하위 클래스의 `pp_key`·`run` 재포장) 추가, T11 에 리포 로컬 `user.name` 비었던 사례 보강 (재료: PROGRESS 다음 할 일 3)
  - PRD §2.2 [그 뒤] 줄의 병합 진행률·확장자 정직화에 "여덟 번째 계획에서 완료 (D051~D053)" 표시, §8 변경 이력 한 줄
  - 확인: `Select-String -Path docs/REFERENCE.md -Pattern '^\| T(19|20|21|22) '` → 4줄, `Select-String -Path docs/PRD.md -Pattern 'D051'` → §2.2·§8 에 1줄 이상
  - 결과 (2026-11-03): T19~T22 4줄(근거 c21cbbb·2026-11-02·3391c06·389a1b4), T11 보강, PRD `D051` 27·124행 확인
- [ ] 4. 인수 확인
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과, `git diff -- gaindb/ requirements.txt` 비어 있음 | 실기기 (소스 실행):
    - 1 YouTube 1080p 병합 영상 → "병합 중 N%" 가 100% 에 이른 뒤 "태그 기록 중" → "썸네일 넣는 중" → 완료, 파일 재생됨
    - 2 YouTube MP3 받기 → "100.0% 다운로드 중" 뒤 "MP3 변환 중" → "태그 기록 중" → "썸네일 넣는 중" → (정규화 켜졌으면 정규화) → 완료
    - 3 후처리 단계("태그 기록 중" 등)에서 취소 → "취소됨", 저장 폴더에 임시 파일·ffmpeg 프로세스가 남지 않음
    - 4 비공개·삭제된 영상 URL 로 정보 추출 실패, 그리고 다운로드 오류 하나 → 오류 창 원문에 `[0;31m` 같은 코드가 없음
    - 5 동시 2개 이상에서 한 항목이 병합에 들어가면 다음 대기 항목이 바로 출발 (D005 유지)

## 자가 검토
- PRD 기능 누락: 없음. 720p 포맷 오류는 원인 진단이 먼저라 넣지 않음, 같은 이름 파일 건너뜀은 F1 동작 변경이라 discover 로 분리 (Q059)
- 테스트로 옮기지 않은 인수 기준: 실제 사이트 다운로드의 단계 순서·취소 뒤 남은 파일·오류 창 표시 → 실기기 (네트워크·사이트 응답이 테스트 환경에 없음). hook 이름→라벨, ANSI 제거는 단위 테스트로 덮는다
- 순서 의존: 4 는 1~3 뒤. 1·2·3 은 서로 독립
