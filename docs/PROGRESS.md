# PROGRESS — AV_Downloader (AVD)

## 상태
- 단계: 8 구현 · 계획: `docs/plans/2026-10-28-foundation.md` 작업 6/9 (1·3·4·5·6·7 완료, 2 확인 대기)
- 갱신: 2026-10-28 · 마지막 커밋: `c361f58 test: 다운로드 워커 파싱 함수 특성 테스트 추가`

## 다음 할 일
1. 작업 2 기동 결과와 작업 8 실기 검증 결과 받기 (사용자 확인) → 작업 9 인수 확인

## 미해결
- (다음 계획 후보) ruff 0.17 기본 규칙으로는 앱 코드 64건 (blind-except 21·import 순서 19·try-except-pass 9 등, 26건 자동 수정 가능) — 단서: D035
- (정보) `theme`·`language` 설정 키는 기본값만 있고 쓰이지 않음 — 단서: `utils/config_manager.py > DEFAULT_CONFIG`

## 확인 대기 (사람만 확인 가능)
- 작업 2 기동: `venv\Scripts\python main.py` — 기대 결과: 메인 창 표시, yt-dlp 업데이트 모달이 떠서 완료 후 닫힘
- `docs/VERIFY_2026-07-09.md` 항목 — 기대 결과: 절차서 번호별 통과 (F10)
- 표본 8건 (YouTube 단일·플레이리스트, SoundCloud, Vimeo, sendvid, Naver TV, Bandcamp, Dailymotion) — 기대 결과: 완료 후 재생 가능. 성공 기준 장면은 PRD §1 판정 3항 (D033, D034)
<!-- head:end — 이 줄 위(40줄 이내)만 자동 주입된다. 갱신은 이 위만 고친다. -->

## 완료 기록
<!-- 한 줄씩: YYYY-MM-DD 무엇을 (커밋 hash). 50줄을 넘으면 docs/history/로 옮긴다. -->
- 2026-10-28 metarche 이관 착수 — 기존 문서 legacy 이동, PRD 초안 (8e494a2)
- 2026-10-28 PRD 승인 (3a6f5f8)
- 2026-10-28 문서 체계 승인 — CLAUDE.md·PROGRESS·REFERENCE·settings·훅
