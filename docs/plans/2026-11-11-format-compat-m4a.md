# 스물세 번째 계획 — 최고 호환 영상 · M4A 음원 선택지
상태: done (2026-11-11) | 시작: 2026-11-11 | 근거: 사용자 요청 "1번 2번 합쳐서 진행" (PRD §2.2 포맷 선택 UX·오디오 비트레이트 정책, OPEN H01·H02)

목표: 화질 선택 창과 플레이리스트 선택 창에 선택지 두 개를 더한다. 기존 선택지의 동작은 바꾸지 않는다.
- "최고 호환 (H.264 + AAC)" — 구형 플레이어·TV·편집기에서 열리는 MP4
- "M4A 오디오 (원본 그대로)" — 원본이 AAC 면 재인코딩 없이 담는다

사용자 결정 (2026-11-11):
- H01: 호환 항목을 **추가**한다. "최고 화질 (자동 선택)"이 첫 줄·기본값으로 남는다
- H02: **M4A 행 추가**. MP3 192kbps 는 그대로 (음량 정규화는 MP3 에만 있다, D009)
- 플레이리스트 선택 창에도 같은 선택지를 넣는다

구조:
- 바뀜: `core/info_fetcher.py > _parse_formats`, `controllers/playlist_flow.py`, `ui/playlist_select_dialog.py`, `ui/format_select_dialog.py`, `ui/main_window.py > _apply_format`, `utils/config_manager.py > DEFAULT_CONFIG`
- 안 바뀜: `gaindb/`
- 계획과 달라진 것: `core/downloader.py` 한 곳 — m4a 는 챕터를 넣지 않는다 (작업 7 에서 썸네일 임베드 실패 발견, T31)
- 문서: `docs/PRD.md`(§2.2, 새 F13), `DECISIONS.md`, `OPEN.md`(H01·H02 닫기), `CHANGELOG.md`, `README.md`

전역 제약:
- yt-dlp 핀 그대로 (D002). `gaindb/` 무수정 (D015)
- 포맷 문자열은 한 곳(`core/info_fetcher.py` 상수)에 두고 플레이리스트·창이 가져다 쓴다 — 지금은 `playlist_flow.py` 가 따로 적어 두었다
- 릴리스는 이 계획에 넣지 않는다 (끝난 뒤 따로 v1.4.0)

설계:
- 최고 호환 포맷: `bv*[vcodec^=avc1]+ba[acodec^=mp4a]/bv*[vcodec^=avc1]+ba/bv*+ba/b`, ext `mp4`
  - H.264 가 없는 사이트는 뒤 후보로 내려간다. 실제 코덱은 지금처럼 완료 뒤 메타 줄에 덮어쓴다(`codec_info_resolved`)
  - YouTube 의 H.264 는 보통 1080p 까지다. 행의 해상도 칸에 "최대 1080p 안팎" 같은 약속은 적지 않고 코덱 칸에 "H.264 / AAC" 만 적는다
- M4A 포맷: `bestaudio[ext=m4a]/bestaudio/best`, ext `m4a`
  - 원본이 AAC 가 아니면(SoundCloud Opus·MP3 등) yt-dlp 가 AAC 로 재인코딩한다. 그래서 라벨은 "재인코딩 없음"이라고 단정하지 않고 "원본 그대로" + 코덱 칸에 원본 AAC 비트레이트(있을 때)를 보인다. m4a 원본이 없으면 코덱 칸은 "AAC"
- 플레이리스트 `mode`: `video` · `video_compat` · `audio` · `audio_m4a`
- 기본 선택 행: 지금은 `last_chosen_ext` 만 기억해서 mp4 행이 둘이면 늘 첫 줄로 돌아간다. 고정 행 넷은 `last_chosen_format_id` 로 기억하고, 해상도 행(`137+bestaudio/best` 등 영상마다 다른 값)은 지금처럼 ext 로 찾는다

## 작업
- [x] 1. 문서 먼저 — PRD §2.2 두 줄 완료 표시 + F13(인수 기준) 추가, DECISIONS D072(H01)·D073(H02)·D074(플레이리스트), OPEN H01·H02 를 해결 표로
  - 확인: PRD 변경 이력 표에 한 줄 | OPEN 보류 표에 H01·H02 없음
- [x] 2. `info_fetcher` — 포맷 상수 4개(`AUTO`·`COMPAT`·`MP3`·`M4A`)와 새 행 2개. 순서: 최고 화질 → 최고 호환 → 해상도 행 → MP3 → M4A
  - 테스트 먼저: `tests/test_format_rows.py` — 가짜 formats 로 (a) 행 순서·ext·is_audio (b) M4A 행 abr 이 m4a 원본 값 (c) yt-dlp `build_format_selector` 로 호환 문자열이 avc1+mp4a 를 고르고, avc1 이 없으면 뒤 후보로 내려감 (d) M4A 문자열이 m4a 를 고르고 없으면 다른 오디오
  - `ui/download_item_widget.py > AUTO_FORMAT_ID` 는 새 상수를 가져다 쓴다 (값 불변)
- [x] 3. 화질 선택 창 — 코덱 칸(호환 "H.264 / AAC", M4A "AAC nnnkbps"), `last_chosen_format_id` 기억
  - 테스트: `tests/test_format_rows.py` 에 함께 — 호환을 고른 뒤 다시 열면 호환 행이 선택됨 | 해상도 행을 고른 뒤는 지금처럼 ext 로 | 설정 키가 없으면 첫 행
- [x] 4. `main_window._apply_format` — `is_audio = (format_id == "bestaudio/best")` 를 ext 기준으로 (M4A 플레이리스트 항목이 영상으로 표시되는 것 막기)
  - 확인: `grep "bestaudio/best"` 로 남은 비교가 없는지. 테스트: 플레이리스트 경로로 m4a 를 넣으면 위젯이 음원으로 표시
- [x] 5. 플레이리스트 — 라디오 4개, `PlaylistFlow._mode_to_format` 이 2의 상수를 쓴다
  - 테스트: mode 4개 → (format_id, ext) | 알 수 없는 mode 는 지금 동작 유지 | 기본 선택 "영상 (최고 화질)" 불변
  - 결과: 캡처로 확인 — 라디오 4개 한 줄에 들어감 ("영상 (최고 화질)"·"영상 (최고 호환)"·"MP3"·"M4A")
- [x] 6. 전체 테스트 + ruff — `venv\Scripts\python -m pytest` — 297 통과, ruff 통과
- [x] 7. 실기 확인 (인터넷 필요, ffprobe 로 판정) — 1·3·4·5 는 `Downloader` 를 직접 불러 확인, 2·6·7 은 앱 화면에서 사용자 확인
  - [x] 1. 최고 호환 — 4K 영상(LXb3EKWsInQ)에서 고르는 형식: 299(1080p `avc1`) + 140(`mp4a` 129k). 최고 화질은 701(2160p `av01`) + 251(`opus`). 실제 받기는 짧은 영상(jNQXAC9IVRw): `h264` + `aac` mp4, 제목 태그 있음. 재생은 사용자 확인
  - [x] 2. 최고 화질 → 전과 같음 — 사용자 확인: 정상 (`E:\다운로드\yt temp`)
  - [x] 3. M4A — jNQXAC9IVRw: `aac` 128k(원본 140 과 같음), 썸네일(`attached_pic`)·제목 태그 있음. 처음엔 썸네일 임베드 실패 → m4a 챕터 끄고 통과 (T31)
  - [x] 4. MP3 — `mp3` 192k, 썸네일·제목 태그 있음. 음량 정규화는 워커 단계라 여기서 안 봄(코드 무변경) — 사용자
  - [x] 5. SoundCloud(forss/flickermood) → M4A — `aac` 160k, 썸네일·제목 태그 있음. 이 곡은 AAC 원본이 있어 재인코딩 경로는 타지 않았다
  - [x] 6. 플레이리스트 → 최고 호환 / M4A 각각 완료 — 사용자 확인: 정상
  - [ ] 7. 화질 선택 창에서 최고 호환을 고른 뒤 다음 링크의 창에 최고 호환이 선택돼 있는지 — 사용자 확인: 정상
- [x] 8. CHANGELOG·REFERENCE T31·PROGRESS, 커밋 — README 는 이미 "MP3/M4A" 로 적혀 있어 그대로
- [x] 9. (추가, D075) 화질 선택 창 순서를 최고 화질 → 최고 호환 → MP3 → M4A → 해상도 행으로, 2160p·4320p 는 "4K 2160p MP4"·"8K 4320p MP4" — pytest 298 통과, 캡처로 확인

## 자가 검토
- PRD 기능 누락: F13 인수 기준 = 작업 7 의 1~6
- 테스트로 옮기지 않은 인수 기준: 작업 7 전부 (인터넷·실제 ffmpeg 필요)
- 순서 의존: 1 → 2 → (3, 4, 5) → 6 → 7 → 8
- 하지 않는 것: 환경설정에 기본 포맷 노출, MP3 320, Opus·FLAC 선택지, 해상도 행마다 호환/화질 갈래, `default_format` 설정 키 정리(쓰이는 곳 없음 — 알리기만)
- 위험:
  - M4A 행의 "원본 그대로"는 원본이 AAC 일 때만 참이다 — 라벨 문구는 작업 3 에서 사용자 확인
  - H.264 가 없는 사이트에서 "최고 호환"이 다른 코덱으로 내려간다 — 완료 뒤 메타 줄이 실제 코덱을 보인다
