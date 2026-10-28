# ADOPT_MAP — 기존 문서 → 새 위치 (adopt 되짚기용, 2026-10-28)

상태: adopt 완료 — legacy 이동 승인 (Q018)

## 1. 매핑
| # | 기존 | 새 위치 |
|---|---|---|
| 1 | CLAUDE.md §1 정체성·라이선스 | PRD §1·§2.6, D010~D012 |
| 2 | CLAUDE.md §3 기술 스택 | PRD §4·§5, D001~D003, D016 |
| 3 | CLAUDE.md §4 폴더 구조 (낡음) | REFERENCE R§1 — 실제 구조로 새로 작성 |
| 4 | CLAUDE.md §5 개발 환경 | REFERENCE R§5 |
| 5 | CLAUDE.md §6 코딩 컨벤션 | 새 CLAUDE.md 프로젝트 규칙, D013 |
| 6 | CLAUDE.md §7 작업 흐름 | PRD §6, D014, 새 CLAUDE.md |
| 7 | CLAUDE.md §9 함정 (PowerShell `>`·QPixmap·썸네일 용어·EJS·gitignore) | REFERENCE R§4 |
| 8 | WORKLOG §3.1 진행 중 | PROGRESS 다음 할 일·확인 대기 |
| 9 | WORKLOG §3.2~3.4 로드맵 | PRD §2.2·2.3 + PROGRESS 다음 할 일 |
| 10 | WORKLOG §4 ADR 인덱스 / ADR.md 본문 | DECISIONS D004~D011 (본문은 legacy 에서 ADR-NNN 으로 참조) |
| 11 | WORKLOG §5 교훈 인덱스 / LESSONS.md 본문 | REFERENCE R§4 함정 대장 |
| 12 | docs/VERIFY_2026-07-09.md | PROGRESS 확인 대기 (문서는 제자리) |
| 13 | CHANGELOG.md | 루트 유지, 계속 씀 (D020) |
| 14 | README.md | 루트 유지 (외부 사용자용), 낡은 절은 구현 단계 수정 후보 |

## 2. 버림 (전역 지침과 중복 또는 웹 채팅 전용)
| # | 기존 | 이유 |
|---|---|---|
| B1 | CLAUDE.md §8.1 환경별 파일 참조 (웹 채팅 raw URL) | Claude Code 는 작업 트리 직접 읽음 |
| B2 | CLAUDE.md §8.2 코드 제시 단위 (함수/파일 전체) | 채팅에 코드 붙여넣기 전용 |
| B3 | CLAUDE.md §8.3 "코드를 보내드릴까요?" | 채팅 전용. 관문은 metarche 가 대신 |
| B4 | CLAUDE.md §8.4 터미널 명령 함께 제시 | Claude Code 가 직접 실행 |
| B5 | CLAUDE.md §8.5 마크다운 바깥 펜스 | 채팅 전송 전용 |
| B6 | CLAUDE.md §9 crawler 함정 3건 (blob 한국어 누락·raw 10KB·28KB) | 웹 채팅 도구 전용 |
| B7 | CLAUDE.md §11 새 세션 시작 방법 | 웹 채팅 전용 / Claude Code 자동 |
| B8 | WORKLOG §1·§2 문서 운용 규칙 | metarche 문서 체계로 대체 |
| B9 | CLAUDE.md §2 협업 모델 (모델 이력) | 역사 정보, 결과물에 영향 없음 |

## 3. 판단 보류 → 해결 (Q017)
- CLAUDE.md §8.6·§8.7 서식 규칙 → 새 CLAUDE.md (D018)
- LESSONS 협업 그룹 → REFERENCE UI·작업 원칙 (D019)

## 4. legacy 이동안 (승인 대기)
- `docs/legacy/` 로 `git mv`: CLAUDE.md, WORKLOG.md, ADR.md, LESSONS.md
- 제자리: README.md, CHANGELOG.md, LICENSE, NOTICE, docs/VERIFY_2026-07-09.md
