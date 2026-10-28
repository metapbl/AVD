# PROGRESS — AV_Downloader (AVD)

## 상태
- 단계: 8 구현 · 계획: `docs/plans/2026-10-28-foundation.md` 작업 1/9
- 갱신: 2026-10-28 · 마지막 커밋: `3a6f5f8 docs: approve PRD`

## 다음 할 일
1. 작업 2 — 기동 실기 확인 (사용자), 이어서 작업 3 개발 도구 (`requirements-dev.txt`, `pyproject.toml`)

## 미해결
- README 낡은 절: config 위치(실제는 앱 폴더), 끊긴 `WORKLOG.md` 링크·디렉터리 구조 — 단서: Q011, Q012 → 작업 5
- ruff 없음(venv 재생성으로 삭제) → `.py` 편집 시 검사 훅이 "검사 도구 없음". gaindb 제외 설정도 없음 — 작업 3 에서 해소
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
