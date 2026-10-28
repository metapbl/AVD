# PROGRESS — AV_Downloader (AVD)

## 상태
- 단계: 8 구현 · 계획: `docs/plans/2026-10-28-foundation.md` 작업 8/9 (1~8 완료)
- 갱신: 2026-10-28 · 마지막 커밋: `f42d487 test: 파일 유틸 특성 테스트 추가`

## 다음 할 일
1. 작업 9 인수 확인 — 자동 하네스 결과(D036) + 사용자 눈 확인 1건 받기

## 미해결
- (다음 계획 후보, 눈 확인으로 확정) mp3 에 UTF-8 한글 ID3v1 이 붙는다 — T7 재발 의심. 원인은 yt-dlp 자체(`postprocessor/ffmpeg.py > FFmpegMetadataPP` 의 `-write_id3v1 1`, `embedthumbnail.py` 도 같음). 앱의 37855ee 는 앱 쪽 인자만 뺐다
- (다음 계획 후보) `workers/playlist_probe_worker.py > PlaylistProbeWorker.finished = Signal(object)` 가 QThread 내장 `finished` 를 가리고 `controllers/playlist_flow.py` 가 `deleteLater` 를 거기 연결 — T2 규칙 위반. 하네스에선 크래시 없음
- (기록, AVD 밖) Vimeo: 후보 4개가 DRM·로그인·TLS 지문 차단(yt-dlp 위장 의존성 `curl_cffi` 필요). `curl_cffi` 추가는 다음 계획 후보
- (기록, AVD 밖) Naver TV: 후보 5개 모두 yt-dlp 2026.10.26 추출기 `KeyError('result')` — 상류 수정 대기
- (다음 계획 후보) ruff 0.17 기본 규칙으로는 앱 코드 64건 (blind-except 21·import 순서 19·try-except-pass 9 등, 26건 자동 수정 가능) — 단서: D035
- (정보) `theme`·`language` 설정 키는 기본값만 있고 쓰이지 않음 — 단서: `utils/config_manager.py > DEFAULT_CONFIG`

## 확인 대기 (사람만 확인 가능)
- 눈 확인 1건 (D036): `C:\Users\Administrator\Videos\AVD_verify\youtube_single\` 의 mp4 — 기대 결과: PRD §1 판정 3항 (탐색기 아이콘이 영상 썸네일, 속성 > 자세히 제목이 원제와 같고 깨짐 없음, 파일명 자모 분리 없음). 함께 `youtube_playlist\` 의 한글 mp3 속성 > 자세히 제목 — 기대 결과: 한글 정상 (ID3v1 판정)
- sendvid 표본 URL — 사용자가 안전한 URL 제공 시 하네스로 확인
- `docs/VERIFY_2026-07-09.md` 미확인 번호: 1-C(선택), 2-C 수동 재시도 버튼, 2-D 비공개 영상
<!-- head:end — 이 줄 위(40줄 이내)만 자동 주입된다. 갱신은 이 위만 고친다. -->

## 완료 기록
<!-- 한 줄씩: YYYY-MM-DD 무엇을 (커밋 hash). 50줄을 넘으면 docs/history/로 옮긴다. -->
- 2026-10-28 metarche 이관 착수 — 기존 문서 legacy 이동, PRD 초안 (8e494a2)
- 2026-10-28 PRD 승인 (3a6f5f8)
- 2026-10-28 문서 체계 승인 — CLAUDE.md·PROGRESS·REFERENCE·settings·훅
