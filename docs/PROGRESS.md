# PROGRESS — AV_Downloader (AVD)

## 상태
- 단계: 7 계획 대기 · 계획: 없음 (첫 계획 작성 예정)
- 갱신: 2026-10-28 · 마지막 커밋: `3a6f5f8 docs: approve PRD`

## 다음 할 일
1. 첫 계획 `docs/plans/2026-10-28-*.md` 작성 — 순서 F11 venv·의존성 상향 → F8 MIT·README → F9 pytest 특성 테스트 → F10 실기 검증 (PRD §3, D022)

## 미해결
- 이 PC 의 `venv/` 가 깨짐 (`C:\Python314` 없음), 현 requirements 는 Python 3.15 에 설치 불가 — 단서: Q027, Q030 → F11
- README 낡은 절: config 위치(실제는 앱 폴더), Python 하한(실제 3.12), 끊긴 `CLAUDE.md`·`WORKLOG.md` 링크 — 단서: Q011, Q012, Q032 → F8·F11
- 검사 훅의 ruff 는 옛 venv 에 남은 단독 실행 파일(0.15.15)로 동작 중. venv 재생성(F11) 때 사라지므로 `requirements-dev.txt`(pytest·ruff) 필요. `gaindb/` 제외 설정(`ruff.toml`)이 아직 없어 gaindb 파일을 고치면 경고가 남 — F11 에서 함께
- (정보) `theme`·`language` 설정 키는 기본값만 있고 쓰이지 않음 — 단서: `utils/config_manager.py > DEFAULT_CONFIG`

## 확인 대기 (사람만 확인 가능)
- `docs/VERIFY_2026-07-09.md` 항목 — 기대 결과: 절차서 번호별 통과 (F10)
- 표본 8건 (YouTube 단일·플레이리스트, SoundCloud, Vimeo, sendvid, Naver TV, Bandcamp, Dailymotion) — 기대 결과: 완료 후 재생 가능. 성공 기준 장면은 PRD §1 판정 3항 (D033, D034)
<!-- head:end — 이 줄 위(40줄 이내)만 자동 주입된다. 갱신은 이 위만 고친다. -->

## 완료 기록
<!-- 한 줄씩: YYYY-MM-DD 무엇을 (커밋 hash). 50줄을 넘으면 docs/history/로 옮긴다. -->
- 2026-10-28 metarche 이관 착수 — 기존 문서 legacy 이동, PRD 초안 (8e494a2)
- 2026-10-28 PRD 승인 (3a6f5f8)
- 2026-10-28 문서 체계 승인 — CLAUDE.md·PROGRESS·REFERENCE·settings·훅
