# 여덟 번째 계획 — 확장자 표시 정직화 · 병합 단계 진행률
상태: active | 시작: 2026-11-02 | 근거: PRD §2.2 [그 뒤], F1, F3 (D022, D051, D052)

목표: (1) "최고 화질 (자동 선택)" 으로 받은 항목은 제목 옆에 거짓 ".mp4" 가 뜨지 않고, 다운로드 중 확정된 확장자(예: SoundCloud ".m4a")로 채워진다. (2) 영상+음성 병합 단계에서 진행률 바가 0→100 으로 차고 상태가 "병합 중 42%" 로 보인다 (길이를 모르면 "병합 중 1:23").
구조:
- 바뀜: `ui/download_item_widget.py > DownloadItemWidget`(`update_format_meta`·`update_format_meta_resolved` 확장자 처리, 새 `update_merge_progress`), `core/downloader.py`(새 `_ProgressMergerPP`·설치 함수), `workers/download_worker.py > DownloadWorker`(병합 조각 ext 비우기 `_on_progress`, 새 시그널 `merge_progress`, `_on_postprocess`), `controllers/download_manager.py`(시그널 연결), `CHANGELOG.md`
- 생김: `tests/test_ext_display.py`, `tests/test_merge_progress.py`
전역 제약:
- 다운로드에 넘기는 `item.ext`(=`merge_output_format`)와 `FormatInfo` 통합 포맷 `ext="mp4"` 는 바꾸지 않는다. 확장자 정직화는 표시 경로(워커 시그널·위젯)만 (D051, D053)
- [AI] 병합기는 `core/downloader.py` 에 `_NFCNormalizePP` 옆 하위 클래스로 둔다. 바꿔치기는 `yt_dlp.YoutubeDL` 모듈의 `FFmpegMergerPP` 이름 하나만. 부모 `real_run_ffmpeg`·`run` 의 모양이 기대와 다르면 바꾸지 않는다 (진행률만 없음) (D052)
- [AI] ffmpeg 는 `-progress pipe:1 -nostats` 를 더해 stdout 을 줄 단위로 읽는다. stderr 는 오류 메시지용으로 따로 모으되 파이프가 가득 차 멈추지 않게 한다 (스레드 또는 임시 파일). 실패 시 오류 처리·`try_utime`·`os.rename` 은 부모와 같게
- [AI] 진행 알림은 yt-dlp 후처리 hook `{"status": "processing", "postprocessor": "Merger"}` 로 보낸다 → 기존 `_wrap_hook` 취소 검사가 병합 중에도 돈다. 취소 예외가 나면 ffmpeg 를 끝내고 다시 던진다
- 워커→위젯 연결은 `Qt.ConnectionType.QueuedConnection` 명시, 새 Signal 이름에 `finished`/`started` 금지 (D013, R§4 T2)
- `requirements.txt` yt-dlp 핀 그대로 (D002), `gaindb/` 무수정 (D015)
- 커밋 작성자 `metapbl` 확인, 의미 단위 커밋마다 `CHANGELOG.md` 맨 위 항목 (D014, D020)

## 작업
- [x] 1. 확장자 표시 정직화 — `ui/download_item_widget.py > update_format_meta, update_format_meta_resolved`, `workers/download_worker.py > _on_progress, _on_postprocess` (D053, Q058 로 범위 추가)
  - 실패하는 테스트 먼저 (`tests/test_ext_display.py`):
    - 워커: 병합 조각 파일명(`제목.f137.webm`, format_id "137")의 진행 hook → `codec_info_resolved` 의 ext 가 "" / 단일 포맷 `downloading` hook → ext "m4a" / `Merger started` → 최종 ext "mp4"
    - 통합 포맷(`AUTO_FORMAT_ID`, ext "mp4") 선택 → 제목 라벨에 ".mp4" 없음
    - 그 뒤 `update_format_meta_resolved("none", "aac", "m4a", …)` → 제목 라벨에 ".m4a"
    - 명시 포맷("1080p MP4", ext "mp4") 선택 → 바로 ".mp4" (현재 동작 유지)
    - MP3 항목 → resolved 가 "webm" 을 보내도 ".mp3" 유지
    - `InfoFetcher._parse_formats` 통합 포맷 행 `ext == "mp4"` (D051 다운로드 값 고정)
  - 확인: `venv\Scripts\python -m pytest tests/test_ext_display.py` 통과 → 전체 pytest 통과 → ruff 통과
  - 결과 (2026-11-02): 테스트 먼저 4개 실패 확인(".mp4" 표시, 조각 ext "webm", 발사 없음 2) → 구현 뒤 새 테스트 7 통과, 전체 pytest 111 통과, ruff 통과, `gaindb/`·`requirements.txt` diff 없음. 위젯은 `update_format_meta` 에서 AUTO 면 숨김, `update_format_meta_resolved` 가 `update_ext` 재사용. 워커는 `_without_merge_part_ext` 로 조각 ext 를 비우고 `downloading`·`Merger started` 에서도 발사. 실기기 확인은 작업 4
- [x] 2. 병합 진행률 병합기 — `core/downloader.py > _ProgressMergerPP`, 설치 함수
  - 실패하는 테스트 먼저 (`tests/test_merge_progress.py`):
    - 순수 함수: ffmpeg `-progress` 줄(`out_time_us=…`, `progress=continue|end`) → (퍼센트, 처리한 초). duration 없으면 퍼센트 없음, 100 넘지 않음
    - 실제 ffmpeg: lavfi 로 만든 2초 영상 전용 mp4 + 음성 전용 m4a 를 병합 → 결과 파일 존재, hook 에 `processing` 이 1번 이상, 퍼센트가 줄지 않고 마지막이 100 근처
    - 취소: hook 이 첫 `processing` 에서 `DownloadCancelled` 를 던짐 → 예외가 밖으로 나오고 ffmpeg 프로세스가 끝나 있음
    - 안전망: 부모 메서드 모양을 바꿔 둔 상태에서 설치 → `yt_dlp.YoutubeDL.FFmpegMergerPP` 가 원래 클래스 그대로
  - 확인: `venv\Scripts\python -m pytest tests/test_merge_progress.py` 통과 → 전체 pytest 통과 → ruff 통과
  - 결과 (2026-11-02): 테스트 먼저 ImportError 실패 확인 → 구현 뒤 새 테스트 10 통과(실제 ffmpeg 2개 포함), 전체 pytest 121 통과, ruff 통과(RUF012 1건 고침), `gaindb/`·`requirements.txt` diff 없음. `run` 은 오버라이드하지 않음 — `PostProcessorMetaClass` 가 하위 클래스 `run` 을 다시 감싸 `started` 가 두 번 나가 슬롯이 이중 해제되므로, duration 은 `_hook_progress` 의 `started` 에서 잡는다. stderr 는 임시 파일. 취소 시 ffmpeg kill + 반쯤 쓴 `.temp` 출력 삭제. 안전망은 `real_run_ffmpeg` 시그니처·모듈의 `FFmpegMergerPP` 정체 확인
- [x] 3. 워커·위젯 연결 — `workers/download_worker.py > _on_postprocess`, `controllers/download_manager.py`, `ui/download_item_widget.py > update_merge_progress`
  - 실패하는 테스트 먼저 (`tests/test_merge_progress.py` 에 추가):
    - 워커 `_on_postprocess` 에 Merger `processing` dict → `merge_progress(퍼센트, 초)` 발사 (퍼센트 모르면 -1). `started` 는 기존 `merging` 그대로
    - 위젯 MERGING 상태에서 `update_merge_progress(42.0, 10)` → 바 42, 라벨 "병합 중 42%" / `(-1, 83)` → 라벨 "병합 중 1:23" / DONE·CANCELLED 뒤 늦게 온 값은 무시
    - `DownloadWorker` 가 `finished`/`started` 를 가리지 않음 (기존 `test_worker_signals` 통과)
  - 확인: 위 테스트 통과 → 전체 pytest 통과 → ruff 통과
  - 결과 (2026-11-02): 테스트 먼저 6개 실패 확인(속성 없음) → 구현 뒤 `tests/test_merge_progress.py` 16 통과, 전체 pytest 127 통과, ruff 통과, `gaindb/`·`requirements.txt` diff 없음. 위젯 가드는 `item.status`(`update_status` 가 동기화) — `merging`·`merge_progress` 모두 큐 연결이라 순서 보장. 길이 모를 때 바는 그대로 두고 라벨만 시간 표시
- [ ] 4. 인수 확인
  - 확인: 전체 테스트 `venv\Scripts\python -m pytest` 통과, `git diff -- gaindb/ requirements.txt` 비어 있음 | 실기기 (소스 실행):
    - 1 4K 60fps 등 병합이 30초 넘는 YouTube 영상 → 병합 단계에서 바가 0→100, 라벨 "병합 중 N%" 증가 → 완료, 파일 재생됨
    - 2 SoundCloud "최고 화질 (자동 선택)" → 화질 선택 직후 제목 옆 확장자 없음 → 다운로드 중 ".m4a"(또는 실제 확장자) → 완료까지 유지
    - 3 YouTube "1080p MP4" 명시 선택 → 선택 직후부터 ".mp4" / "최고 화질 (자동 선택)" → 다운로드 중 ".mp4" 로 채워지고 결과 파일이 .mp4
    - 4 병합 중 취소 → 바로 "취소됨", 저장 폴더에 `.temp` 파일과 ffmpeg 프로세스가 남지 않음
    - 5 병합 없는 단일 포맷(예: MP3 받기) → 기존과 같게 완료 (회귀 없음)
    - 6 동시 2개 이상에서 한 항목이 병합에 들어가면 다음 대기 항목이 바로 출발 (D005 유지)
  - 결과: 2026-11-02 실패 — 사용자: "병합중이 안나옴. 병합중이 안나오니 병합중 취소도 불가능 / 병합에 들어가면 대기항목이 출발하는지 확인이 안됨 / 다운로드 100퍼센트에서 멈춘상태로 장시간". 2·3·5 는 답 없음 (재확인 때 함께)
  - 원인 (2026-11-02): yt-dlp 가 hook 의 `postprocessor` 이름을 클래스 이름에서 만든다(`pp_key()`) → `_ProgressMergerPP` 는 "_ProgressMerger" 라 워커의 `== "Merger"` 비교에 걸리지 않아 `merging`·`merge_progress` 가 한 번도 발사되지 않음 (작업 2 회귀, 테스트가 이름을 확인하지 않음). 재현: 스크래치 스크립트로 실제 YouTube 다운로드의 hook 을 찍어 확인. 수정: `pp_key` 를 `FFmpegMergerPP.pp_key()` 로 고정 + 회귀 테스트 `test_progress_merger_keeps_merger_key`. 수정 뒤 실제 다운로드 hook "Merger started/processing/finished", pytest 128·ruff 통과. 실기기 재확인 대기
  - 결과: 2026-11-02 재확인 — 사용자 "전체 확인" (1~6). 단 1: "병합중에서 100퍼센트가 게이지 끝부분이 약간 덜 차는데 정상작동인지?" → 결함으로 보고 고친 뒤 1 만 다시 확인. 계획 밖 발견 3건(720p "Requested format is not available", 같은 이름 파일이 있으면 화질과 관계없이 완료 처리, 오류 창 ANSI 코드)은 PROGRESS 다음 할 일 2~4 로
  - 게이지 원인·수정 (2026-11-02): 라벨은 반올림(`:.0f`)·바는 버림(`int`)이라 99.6 이 "100%" 인데 바 99, 그리고 ffmpeg 마지막 `out_time_us` 가 길이보다 조금 짧음. `_merge_progress` 가 `progress=end` 를 (100, 길이)로, 위젯 바는 `round`. 회귀 테스트 3개 먼저 실패 확인 → pytest 131·ruff 통과. 실기기 1 게이지만 재확인 대기

## 자가 검토
- PRD 기능 누락: 없음. §2.2 [그 뒤] 의 macOS 실행 정식화는 이번에 넣지 않음 (Q057). 마칠 때 PRD §2.2 [그 뒤] 줄에 두 항목 완료 표시를 제안한다
- 테스트로 옮기지 않은 인수 기준: 실제 사이트 다운로드·눈으로 보는 진행률·취소 뒤 남은 파일 → 실기기 (네트워크·사이트 응답이 테스트 환경에 없음). 병합 자체는 로컬 ffmpeg 통합 테스트로 덮는다
- 순서 의존: 3 은 2 뒤, 4 는 1~3 뒤. 1 은 독립
- 위험: yt-dlp 자동 업데이트로 `FFmpegMergerPP`·`real_run_ffmpeg` 가 바뀌면 진행률이 사라질 수 있다 → 안전망으로 병합 자체는 계속됨, 작업 2 의 실제 ffmpeg 테스트가 회귀를 잡는다 (D052)
