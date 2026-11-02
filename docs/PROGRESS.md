# PROGRESS — AV_Downloader (AVD)

## 상태
- 단계: 8 구현 · 아홉 번째 계획 `docs/plans/2026-11-03-postprocess-stage-ansi.md` active (2/4)
- 갱신: 2026-11-03 · 아홉 번째 계획(후처리 단계 표시·오류 ANSI 제거·문서 정리, Q059) 승인. **v1.0.2 뒤 미릴리스 변경 있음** (fix·feat 5건). OPEN 미결 0

## 다음 할 일
3. 계획 작업 3 문서 정리 — 재료:
  - REFERENCE R§4 함정 T19: PyInstaller exe 아이콘 리소스는 번호 1 이라 Qt(`IDI_ICON1`)가 못 찾음 → 새 폴더 첫 실행 작업표시줄 기본 아이콘. 대책 `main.py > set_window_class_icon`
  - REFERENCE R§4 함정 T20: 소스 실행 업데이트 리허설에 `version.py` 문자열만 바꾸면 pip 가 dist-info 를 보고 '이미 최신' — 실제 옛 버전 `pip install yt-dlp==…` 필요 (2026-11-02 작업 4). T11 보강: 리포 로컬 `user.name` 이 비어 전역 `METAPBL` 로 커밋됨 → 2026-11-02 로컬 설정 재고정
  - REFERENCE R§4 함정 T21: 릴리스 전 `pip install -r requirements.txt` 는 venv yt-dlp 를 핀(2026.3.17)으로 내려 배포본에 옛 yt-dlp 가 실린다 → 올릴 패키지만 지정해 설치 (2026-11-02 일곱 번째 계획 작업 1)
  - REFERENCE R§4 함정 T22: yt-dlp PostProcessor 하위 클래스는 `pp_key()` 가 클래스 이름에서 만들어져 hook 의 `postprocessor` 이름·`postprocessor_args` 키가 바뀐다 → `pp_key` 를 부모 값으로 고정. 또 하위 클래스의 `run` 은 메타클래스가 다시 감싸 started/finished 가 두 번 나간다 (여덟 번째 계획 작업 4 실기기 실패, 389a1b4)
  - PRD §2.2 [그 뒤] 줄의 병합 진행률·확장자 정직화를 완료로 표시 (여덟 번째 계획 자가 검토)
4. 계획 작업 4 인수 확인 (실기기 5개)
5. (다음 계획 후보, 사용자 제안) 저장 폴더에 같은 이름 파일이 있으면 yt-dlp 가 "이미 받음"으로 건너뛰어 화질과 관계없이 완료 처리 → 임시 이름으로 받고 끝에 이름 정하기 등 정책 결정 필요 (PRD F1 동작 변경). 단서 `utils/file_utils.py > get_unique_path`(있으나 다운로드 경로에 안 쓰임?), `core/downloader.py > Downloader.download`
6. (다음 계획 후보) 일부 YouTube 영상 720p 만 "Requested format is not available" (LXb3EKWsInQ, EkRmp25XkZc — 480·1080 은 됨). 정보 추출 때 보인 포맷 136 을 다운로드 요청에선 못 받는 것으로 보임, 이번 계획 변경과 무관(포맷 선택 단계 오류). 단서 `core/info_fetcher.py > _parse_formats` (`f"{id}+bestaudio/best"`)
7. (판단 필요) README "비영리 무료 공개" 문단·PRD §2·D012 "비영리" 표현을 NOTICE 새 문구("license 에 제한을 더하지 않음")와 맞출지
8. (그 뒤 후보) Vimeo `curl_cffi` 검토 — 새 의존성 → PRD §2.6 제약·범위 확인부터. 진입점 `core/info_fetcher.py > InfoFetcher`

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
