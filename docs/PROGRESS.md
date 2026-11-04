# PROGRESS — AV_Downloader (AVD)

## 상태
- 단계: 7 계획 대기 · 열한 번째 계획 `docs/plans/2026-11-04-release.md` done. active 계획 없음
- 갱신: 2026-11-04 · v1.1.0 게시(태그 `e67600b`, Latest): 항목별 임시 폴더(D056), 같은 이름 번호 보관(D054), 일부 화질 오류 수정(D055), 닫기 확인·종료 정리(D057). 미릴리스: README 배포 방침 문구 정정(D058), 미사용 `get_unique_path` 삭제 (앱 동작 변경 없음). OPEN 미결 0

## 다음 할 일
1. (그 뒤 후보) Vimeo `curl_cffi` 검토 — 새 의존성 → PRD §2.6 제약·범위 확인부터. 진입점 `core/info_fetcher.py > InfoFetcher`

## 미해결
- (실기 미확인) D041 "끝나지 않은 항목이 있으면 재시작 대신 안내" 분기 — `ui/main_window.py > _restart_after_update`
- (판단 필요) Qt/PySide6 LGPL 소스 제공을 공식 서버 링크로 갈음 (`THIRD_PARTY_LICENSES`) — 직접 첨부가 필요한지 법률 검토 안 함
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
- 2026-10-29 두 번째 계획: PlaylistProbeWorker 시그널 `probe_ready` 개명·정리 연결 교체 (596dcc9), 인수 확인 (961d0fe)
- 2026-10-29 세 번째 계획: ruff 0.17 기본 규칙 채택 — import 정리 (133f01b), 자동 수정 (3c61718), 수동 정리 (4555bbb), 규칙 고정 해제 D037 (04d130b), 인수 확인 (1492bc8)
- 2026-10-29 네 번째 계획 승인 D038~D040 (8f4ac46)
- 2026-10-29 PyInstaller onedir 빌드 `AVD.spec` (3caf25d), exe 옆 config.json D039 (391ec31)
- 2026-10-29 exe 용 yt-dlp wheel 교체 (f0adf1b), UpdateWorker frozen 분기·T17 (0ac4c9b)
- 2026-10-29 루트 THIRD_PARTY_LICENSES·NOTICE (9579289), `build.ps1` (b1066c8, a4ce4b0)
- 2026-10-29 exe 실기기 확인 통과 (3922d92), 업데이트 뒤 자동 재시작 D041 (cb15588, c59b48e)
- 2026-11-02 다섯 번째 계획(보안 정책 후속): AppUpdater 삭제 D046 (fe68393), 제목·채널명 PlainText (fd67868), pip-audit D045·OPEN O19 (6cd8bac), 업데이트 시그널 QueuedConnection D013 (45d99f7), 인수 확인 (747f214)
- 2026-11-02 여섯 번째 계획: 완료 항목 "▶ 재생" 버튼 D049 (de9bbcd), 인수 확인 (732d62e)
- 2026-11-02 일곱 번째 계획: certifi·urllib3 핀 상향 D050·O19 해결 (3391c06), `chore(release): v1.0.2` (26a52c8), **v1.0.2 게시** 태그 26a52c8, 인수 확인 (b912bc3)
- 2026-11-02 여덟 번째 계획: 확장자 표시 정직화 D051·D053 (3fd3249), 병합 진행률 병합기 D052 (9f7f3c2)·표시 (0a2fca7), 실기기 실패 원인 `pp_key` 수정 (389a1b4), 게이지 100% (69b15b6), 인수 확인 통과
- 2026-11-03 후처리 단계 표시 (544ce5d), 오류 원문 ANSI 제거 (21a85d3), 함정 T19~T22·PRD §2.2 완료 표시 (a3c5f8e)
- 2026-11-04 후처리 이름표를 실제 pp_key 로 수정·아홉 번째 계획 인수 확인 완료, 실제 다운로드 라벨 기록으로 검증 (fb7ecc1)
- 2026-11-04 열 번째 계획 done: 일부 화질 오류 수정 (d6f2c62), 항목별 임시 폴더·번호 보관 (5e47a75, 23f6639), 임시 폴더 청소 (835187f), 조각 포맷 취소 찌꺼기 (78ad746), 창 닫기 확인·종료 정리 (dd0a069)
- 2026-11-04 열한 번째 계획 done: v1.1.0 게시 (e67600b, 기록 5f1334b)
