# PROGRESS — AV_Downloader (AVD)

## 상태
- 단계: 8 구현 · 계획: `docs/plans/2026-10-29-ruff-defaults.md` active (3/5)
- 갱신: 2026-10-29 · 마지막 커밋: `596dcc9 fix(playlist): PlaylistProbeWorker 결과 시그널을 probe_ready 로 개명` (origin/main 보다 12커밋 앞섬, push 안 함)

## 다음 할 일
1. 계획 작업 4 — `pyproject.toml` 규칙 고정 해제, `ignore = ["BLE001", "S110"]`

## 미해결
- (다음 계획 후보) Vimeo: 후보 4개가 DRM·로그인·TLS 지문 차단 — 위장 의존성 `curl_cffi` 추가 검토
- (기록, AVD 밖) Naver TV: 후보 5개 모두 yt-dlp 2026.10.26 추출기 `KeyError('result')` — 상류 수정 대기
- (정보) mp3 에 yt-dlp 가 UTF-8 ID3v1 을 붙인다(`FFmpegMetadataPP`·`EmbedThumbnail` 의 `-write_id3v1 1`). 탐색기는 ID3v2 를 읽어 한글 정상 (2026-10-28 눈 확인) — 구형 플레이어에서만 문제 가능
- (정보) `theme`·`language` 설정 키는 기본값만 있고 쓰이지 않음 — 단서: `utils/config_manager.py > DEFAULT_CONFIG`

## 확인 대기 (사람만 확인 가능)
- `docs/VERIFY_2026-07-09.md` 미확인 번호: 1-C(선택), 2-C 수동 재시도 버튼, 2-D 비공개 영상 — 기대 결과: 절차서대로
<!-- head:end — 이 줄 위(40줄 이내)만 자동 주입된다. 갱신은 이 위만 고친다. -->

## 완료 기록
<!-- 한 줄씩: YYYY-MM-DD 무엇을 (커밋 hash). 50줄을 넘으면 docs/history/로 옮긴다. -->
- 2026-10-28 metarche 이관 착수 — 기존 문서 legacy 이동, PRD 초안 (8e494a2)
- 2026-10-28 PRD 승인 (3a6f5f8)
- 2026-10-28 문서 체계 승인 — CLAUDE.md·PROGRESS·REFERENCE·settings·훅 (301d5b3)
- 2026-10-28 Python 3.15 대응 의존성 상향 (b57ba9f), pytest·ruff 개발 도구 (1d0d6d5)
- 2026-10-28 본체 라이선스 MIT 전환 (79ff953), README 현행화 (932f8ef)
- 2026-10-28 특성 테스트 — 다운로드 워커 파싱 54개 (c361f58), 파일 유틸 23개 (f42d487)
- 2026-10-28 2026-07-09 작업분 실기 검증 대리 판정 기록 (f0abd36)
- 2026-10-28 첫 계획(기반 다지기) 완료 — 인수 확인 통과 (2d292bb)
