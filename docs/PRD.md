# PRD — AV_Downloader (AVD)

상태: approved (2026-10-28) | 단계: 6 문서 | 갱신: 2026-10-28
<!-- 상태가 approved (YYYY-MM-DD)가 되기 전에는 코드·뼈대·의존성 설치를 하지 않는다. -->
<!-- 모든 항목 끝에 출처를 단다: [U] 사용자 · [X] 기존 코드·문서 · [AI] AI 기본값. 근거 결정은 (D###). -->

## 1. 목적
- 해결할 문제: yt-dlp 의 영상·오디오 다운로드를 명령줄 없이 GUI 로 — 화질 선택, 동시 다운로드, 한글 파일명·태그 보존, MP3 음량 정규화까지 한 번에. [X] README
- 사용자 (누가, 몇 명, 어떤 기기): 개발자 본인(Windows 11 주 사용, macOS 실행), 그리고 GitHub 무료 공개로 받는 불특정 사용자. [X] CLAUDE §2, README (D012, D028)
- 성공 기준 (관찰 가능한 장면 하나): YouTube URL 붙여넣기 → 화질 선택 → 한글 제목 그대로인 파일이 저장 폴더에 생기고, 탐색기에서 썸네일·한글 태그가 정상으로 보인다 [U] (D021)
  - '정상' 판정: 탐색기 아이콘이 기본 아이콘이 아닌 영상 썸네일 / 파일 속성 > 자세히의 제목이 원제와 같고 한글 깨짐(□·?) 없음 / 파일명 한글이 자모 분리 없이 보임 [U] (D034)
- 기한과 수명 (언제까지, 다 쓰면 폐기/유지): 기한 없음, 계속 유지 [AI→U 확인 Q021]

## 2. 범위
### 2.1 필수 (현재 구현됨)
- 단일 URL 영상/오디오 다운로드, 포맷 선택 다이얼로그 [X]
- 플레이리스트 일괄 다운로드 (D007) [X]
- 동시 다운로드 + 대기열, 진행률·속도·ETA [X]
- 취소·재시도·자동 재시도 (D008), 파일 동시 삭제, 부분 파일 정리 [X]
- 메타데이터·썸네일 임베드 (D004), 한글 NFC 정규화 (D006) [X]
- MP3 음량 정규화 (D009) [X]
- yt-dlp 자동 업데이트 (D002), 클립보드 URL 감지 [X]
### 2.2 있으면 좋음 (로드맵, 순서는 D022)
- [첫 계획] venv 재생성·의존성 상향(F11) → MIT 전환 반영·README 정합(F8) → pytest 특성 테스트(F9) → 2026-07-09 실기 검증·표본 사이트(F10) [U]
- [두 번째 계획] LGPL 배포 산출물 — onedir 빌드, `gaindb/` 평문 배치, THIRD_PARTY_LICENSES, 릴리스 절차 [U]
- [그 뒤] 병합 단계 진행률 표시, 확장자 표시 정직화, macOS 실행 정식화 [X] WORKLOG 3.2
- 포맷 선택 UX — "최고 화질" vs "최고 호환" 분리 (ADR-002 Proposed) [X]
- 오디오 비트레이트 정책 (ADR-005 Proposed) [X]
- 쿠키(브라우저 로그인) 지원, 다국어, 테마 전환 [X] WORKLOG 3.4
### 2.3 이번에는 안 함
- 다운로드 일시정지/재개 — URL 토큰 만료로 사실상 재시작이 되어 보류 [X] WORKLOG 3.3
### 2.4 반목표 (절대 그렇게 되면 안 되는 동작)
- DRM 우회·유료/인증 전용 콘텐츠 무단 접근 (D012) [X]
- 쿠키 도입 시 앱이 쿠키를 복사·저장·로그에 남김 [X] WORKLOG 3.4
- 음량 정규화 실패가 다운로드 실패로 번짐 (D009) [X]
### 2.5 나중을 위해 구조만 준비
- `theme`·`language` 설정 키 (기본값만 존재) [X] config_manager
### 2.6 제약 (법·라이선스·비용·개인정보)
- 본체 MIT, `gaindb/` LGPL-2.1-or-later, 배포 onedir + 소스 첨부 (D017, D011) [U]
- 비영리 무료 (D012) [X]

## 3. 기능
<!-- F1~F7 은 현행 동작이 기준 (D024). 인수 기준은 계획에서 손대는 작업에만. -->
### F1 단일 URL 다운로드 — 정보 추출 → 포맷 선택 → 다운로드 → 병합/후처리 → 완료 [X]
### F2 플레이리스트 일괄 다운로드 (D007) [X]
### F3 대기열·동시성 제어 — 병합·정규화 단계는 슬롯 해제 (D005) [X]
### F4 오류 처리 — 자동 재시도, 봇 차단 안내, 취소 시 자식 프로세스 정리 (D008) [X]
### F5 MP3 음량 정규화 (D009) [X]
### F6 환경설정 — 저장 경로, 동시 수, 자동 업데이트, 음량 정규화 [X]
### F7 yt-dlp 자동 업데이트 (D002) [X]

### F8 [첫 계획 A] MIT 전환 반영·README 정합 (D017, D025)
- 인수 기준:
  - Given 루트 `LICENSE` / When 연다 / Then MIT 전문과 "Copyright (c) 2026 META PUBLIC"
  - Given 루트 `NOTICE`·README `## 라이선스`·`## 면책` 절 / When 읽는다 / Then 본체 MIT·`gaindb/` LGPL 로 표기. 본체 라이선스로서의 "Apache" 표기 없음 (서드파티 고지의 requests 등 Apache-2.0 표기는 유지)
  - Given 변경 후 / When `git diff -- gaindb/` / Then 비어 있음
  - Given README `## 실행`·`## 문서` 절 / When 읽는다 / Then config 위치는 "앱 폴더의 `config.json`", 루트 `CLAUDE.md`·`WORKLOG.md` 링크 없음 (`grep -n "CLAUDE.md\|WORKLOG.md" README.md` 결과가 존재하는 파일만 가리킴)
- 확인 방법: 자동 (grep·git diff)
### F9 [첫 계획 B] pytest 특성 테스트 (D023, D025)
- 인수 기준:
  - Given 테스트 추가 / When `pytest` / Then 다음 함수의 현재 동작 고정 테스트 전부 통과 — `workers/download_worker.py`: `_is_transient_error`, `_parse_eta_secs`, `_format_eta_secs`, `_normalize_size_str`, `_split_size_str`, `_is_unknown_size` / `utils/file_utils.py`: `sanitize_filename`, `normalize_unicode`, `get_unique_path`, `format_duration`
  - 기대값은 특성 테스트 원칙대로 현 코드의 출력에서 얻는다 (PRD 가 정하지 않음)
  - Given F9 커밋 / When 그 커밋의 diff 를 본다 / Then 기존 `.py` 무수정, pytest 는 개발용 의존성 파일로 분리, `requirements.txt` 변경 없음 (상향은 앞선 F11 커밋)
  - Given 대상 함수 동작을 일부러 바꾼다 / When `pytest` / Then 해당 테스트 실패 (한 번 확인 후 원복)
- 확인 방법: 자동
### F10 [첫 계획 C] 2026-07-09 실기 검증 마무리 (D025)
- 인수 기준:
  - Given `docs/VERIFY_2026-07-09.md` / When 사용자가 통과·실패 번호를 알려 준다 / Then 결과 기록, 확인 대기에서 제거
  - Given 실패 항목 / When 기록한다 / Then 고치지 않고 미해결 + 다음 계획 후보
- 마무리: 성공 기준 장면(D021) + 표본 8개 사이트 실기 (D026): YouTube 단일·플레이리스트, SoundCloud, Vimeo, sendvid, Naver TV, Bandcamp, Dailymotion
- 완료 조건 (D033): 성공 기준 장면·F11 기동 확인 실패 = 첫 계획 미완(의존성 상향 되돌림 검토). 나머지 표본 실패 = 기록 후 다음 계획 후보, 원인 판정 불가 = '보류' [U]
- 확인 방법: 실기 (사용자, 절차서 번호별 통과/실패)

### F11 [첫 계획 D, 맨 앞] venv 재생성·의존성 상향 (D027, D028)
- 인수 기준 (D029):
  - Given 깨진 `venv/` / When 설치된 Python 3.15.1(`py -3.15`) 로 재생성 후 `pip install -r requirements.txt` / Then 오류 없이 설치, `pip check` 통과
  - Given 새 venv / When `python main.py` / Then 메인 창이 뜨고, yt-dlp 저버전 핀 때문에 업데이트 진행 모달이 떠서 완료 후 닫힘
  - Given `requirements.txt` diff / When 본다 / Then 바뀐 줄은 정확히 `PySide6`·`PySide6_Addons`·`PySide6_Essentials`·`shiboken6` 6.11.1→6.12.0, `numpy` 2.5.1→2.5.4, `scipy` 1.18.0→1.18.1 뿐 (yt-dlp 등 불변)
  - Given README 요구 사항 / When 읽는다 / Then "Python 3.12 이상" 으로 표기
- 확인 방법: 자동(설치·pip check) + 실기(기동, 성공 기준 장면은 F10 마무리에서)

## 4. 기술 결정
| 항목 | 선택 | 버린 안 (이유) | 근거 |
|---|---|---|---|
| GUI | PySide6 6.12.0 (3.15 대응) | 6.11.1 유지 + Python 3.14 | D001, D027 |
| 다운로드 엔진 | yt-dlp (저버전 핀 + 자동 업데이트) | 핀 최신화 | D002 |
| 미디어 처리 | ffmpeg/ffprobe (PATH) | - | D003 |
| 오케스트레이션 | DownloadManager | MainWindow 허브 | D005 |
| 음량 정규화 | 벤더링 GaindB | - | D009 |
| 배포 | PyInstaller onedir | onefile | D011 |
| 본체 라이선스 | MIT (`gaindb/` 는 LGPL) | Apache-2.0 (단순함 우선) | D017 |

## 5. 비기능 요구
- 실행 환경 (OS, 언어 버전, 네트워크): Windows 11 정식, macOS 는 실행만 되고 폴더 열기·폰트 미분기(정식화는 로드맵), Python ≥3.12 (개발 3.15), 인터넷 필수 (D028) [X]
- 성능 (시작 시간, 반응 속도, 자원): 별도 목표 없음. 참고 — yt-dlp 단일 프로세스 병렬은 1~3개가 경험상 안정 (기본 2) [X] LESSONS
- 배포 형태: PyInstaller onedir exe (미착수) (D011) [X]
- 로그 (위치, 형식, 상세 모드): 앱 로그 체계 없음, 지금은 도입 안 함 [U] (D030)

## 6. 검증과 운영
- 자동 테스트 대상 / 실기기 확인 대상과 결과 전달 방식: pytest — Qt 무관 순수 함수 특성 테스트 (D023). GUI·사이트는 실기 — 절차서 번호별 통과/실패를 채팅으로 (D026, D032) [U]
- 전체 테스트 명령과 걸리는 시간: `pytest` (F9 에서 신설, 수 초 예상) [AI]
- 편집 때 자동 검사 (확장자별 린터·타입 검사 명령): `.py` → `ruff check` (`gaindb/` 제외) 훅 (D031) [U]. VS Code 저장 시 Ruff fixAll 은 기존대로 [X]
- 위험한 명령 (실행 전 확인 대상): `git push`, `gh release`, PyInstaller 릴리스 빌드, `pip install`/업그레이드, venv 삭제 (D032) [U]
- 버전 관리 (커밋 단위, 메시지 형식): Conventional Commits, 의미 단위 즉시 커밋, 작성자 고정 (D014) [X]

## 7. 미결
→ `docs/discovery/OPEN.md` (2026-10-28 기준 미결 0개)

## 8. 변경 이력
| 날짜 | 변경 | 근거 |
|---|---|---|
| 2026-10-28 | adopt 역추출 초안 | Q001~Q013 |
| 2026-10-28 | 본체 라이선스 MIT 전환 결정 | D017 |
| 2026-10-28 | 무맥락 검사 반영 (판정 기준·완료 조건 명시) | Q034, D033, D034 |
| 2026-10-28 | 단계 1~4 질의응답 반영 (성공 기준, 계획 순서, 인수 기준, 표본 사이트, Python 3.15·의존성 상향, 검증 운영) | D021~D032 |
