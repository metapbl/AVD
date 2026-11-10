# 보안 정책 — AV_Downloader (AVD)

상태: approved (2026-10-29) | 수준: 기본 | 갱신: 2026-11-11
<!-- PRD와 함께 승인한다. 바꾸려면 PRD 변경 절차(discover.md §7)를 따른다. -->
<!-- 작성 기준은 metarche references/security.md. 해당 없는 칸은 지운다. 항목 끝에 출처 [U]·[X]·[AI]와 근거 D###. -->

## 1. 범위
- 수준과 이유: 기본 — 로컬 단일 사용자 데스크톱 앱. 서버·계정·민감 데이터가 없고, 바깥으로 나가는 연결만 있다 (D043) [U]
- 서비스 지역·적용 규제: GitHub 무료 공개(지역 제한 없음). 지켜야 할 규제로 아는 것 없음 — 개인정보·결제·계정을 다루지 않는다 (D044) [U]
- 이 정책이 다루지 않는 것:
  - 다운로드한 콘텐츠의 저작권·약관 준수 — 사용자 책임 (README 면책, D012) [X]
  - yt-dlp·ffmpeg·Node.js 내부 동작 — 상류 프로젝트의 보안에 맡긴다. 이 앱은 버전 갱신 경로만 다룬다 [AI]
  - `AVD.exe` 코드 서명 — 하지 않는다. Windows SmartScreen 경고가 뜰 수 있다 [AI]

## 2. 구성요소와 신뢰 경계
| 구성요소 | 배포 위치 | 인터넷 노출 | 들어오는 입력 | 이 경계의 통제 |
|---|---|---|---|---|
| AVD 앱 (PySide6, exe 또는 소스) | 사용자 PC | 아니오 (듣는 포트 없음, 바깥 연결만) | 사용자가 붙여 넣은 URL, 클립보드 | URL 은 `http://`·`https://` 로 시작해야 받는다 (`ui/add_link_dialog.py`) [X] |
| yt-dlp (번들, `_internal\yt_dlp\` 평문) | 사용자 PC | 바깥 연결 | 사이트 응답(정보·영상·자막) | 신뢰하지 않음 — 파일 이름은 정리해서 쓴다(`utils/file_utils.py > sanitize_filename`), info dict 가공은 `pre_process` 로만 (D006) [X] |
| 썸네일 받기 (`workers/thumbnail_worker.py`) | 사용자 PC | 바깥 연결 | 사이트가 준 이미지 URL·bytes | 시간 제한 요청, bytes 만 넘기고 GUI 스레드에서 Qt 가 해석 (D013) [X] |
| ffmpeg/ffprobe·Node.js | 사용자 PC (PATH, 별도 설치) | - | yt-dlp 가 넘기는 인자 | 인자 배열로 실행 (yt-dlp) [X]. Node.js 는 YouTube 의 JS 챌린지를 yt-dlp EJS 로 실행 [X] R§2 |
| yt-dlp 업데이트 | PyPI (`pypi.org`), GitHub API(버전 확인) | 바깥 연결 | wheel 파일, 버전 JSON | TLS + PyPI JSON 의 sha256 대조 뒤 교체, 실패하면 옛 폴더 복원 (D038, D047) [X][U]. 소스 실행은 `pip install -U yt-dlp` [X] |
| curl_cffi (번들, TLS 위장) | 사용자 PC | 바깥 연결 | 사이트 응답 (yt-dlp 경유) | yt-dlp 가 Vimeo 등 요청에 브라우저 TLS 지문으로 접속. 인증서 검증은 끄지 않는다. 런타임 의존성 `==` 고정 (D069, D070) [U] |
| GitHub Release (배포) | github.com/metapbl/AVD | 공개 | - | 태그와 같은 커밋의 소스 zip 첨부 (D040) [X] |

## 3. 데이터 분류
| 데이터 | 등급 | 저장 위치 | 저장 보호 | 전송 | 로그·화면 | 보존 기간 | 규제 |
|---|---|---|---|---|---|---|---|
| 설정 (`config.json`: 저장 경로·동시 수·정규화 등) | 내부 | 앱 폴더 (exe 옆 / `main.py` 옆, D039) | 평문, 운영체제 파일 권한 | 전송 안 함 | 제한 없음 | 사용자가 폴더를 지울 때까지 | - |
| 다운로드한 영상·오디오와 태그 | 공개 (사이트에 공개된 콘텐츠) | 사용자가 정한 저장 경로 | 평문 | 사이트 → 앱 (사이트가 주는 TLS) | 제한 없음 | 사용자가 지울 때까지 | - |
| 입력 URL·목록 | 내부 | 메모리만 (저장 안 함) | - | 해당 사이트로만 | 화면 표시 | 앱 종료까지 | - |

- 인증정보·고위험 데이터는 다루지 않는다. 쿠키(로그인) 지원은 로드맵(H03)이며, 들어오면 PRD §2.4 반목표("쿠키를 복사·저장·로그에 남김")에 따라 이 정책을 먼저 바꾼다 [X]
- 앱 로그 파일 없음 (D030) [X]

## 4. 클라이언트 규칙
- 비밀값(API 키·토큰)을 코드·빌드에 넣지 않는다. 지금 넣은 것 없음 [X]
- 외부 명령은 인자 배열로 실행하고 `shell=True` 를 쓰지 않는다 [AI] — 유일한 예외였던 `utils/updater.py > AppUpdater`(검증 없이 exe 를 받아 배치 실행, 호출처 없음)는 지운다 (D046) [U]
- 원격 코드 교체(yt-dlp wheel)는 받은 파일의 sha256 을 PyPI 값과 대조한 뒤에만 한다. 대조 실패·교체 실패 때는 옛 폴더를 그대로 둔다 (D038, D047) [X]
- 앱 자체 업데이트(AVD exe 교체)는 하지 않는다. 필요해지면 무결성 검증을 포함해 새로 설계한다 (D046) [U]
- 사이트가 준 문자열(제목·채널명)은 파일 이름에 쓰기 전에 정리한다 [X]. Qt 위젯에는 `PlainText` 로 넣거나, RichText 면 `html.escape` 뒤에 넣는다 [AI] — `ui/download_item_widget.py`·`ui/format_select_dialog.py`(제목·채널명)·`ui/playlist_select_dialog.py`(플레이리스트 제목) 는 지킴 [X]

## 5. 서버 규칙
- 해당 없음 — 서버 구성요소가 없다 (D043) [U]

## 6. 암호화
| 용도 | 알고리즘·라이브러리 | 키 위치 | 보호 대상 | 교체 |
|---|---|---|---|---|
| 전송 | TLS (requests·yt-dlp, 인증서는 `certifi`) | - | PyPI·GitHub·사이트 통신 | `certifi` 갱신 = 의존성 갱신 [X] |
| 무결성 | SHA-256 (`hashlib`) | 기대값은 PyPI JSON | yt-dlp wheel | - (D047) [X] |

## 7. 비밀값
| 이름 | 쓰는 곳 | 보관 (개발 / 운영) | 노출 시 교체 방법 |
|---|---|---|---|
| GitHub 토큰 (`gh` 로그인) | 릴리스 게시 (개발 PC 만) | 개발: Windows 자격 증명(keyring) / 운영: 없음 | `gh auth refresh` 또는 GitHub 설정에서 토큰 폐기 [X] |

- 앱 자체에는 비밀값이 없다 [X]

## 8. 의존성
- 취약점 검사 명령: `venv\Scripts\pip-audit -r requirements.txt` — 릴리스 전 실행 (D045) [U]. 도입(설치·RELEASE.md 반영)은 계획 작업
- lock 파일: `requirements.txt` 가 모든 런타임 의존성을 `==` 로 고정한다. 단 yt-dlp 핀은 일부러 낮게 두고 기동 때 자동 업데이트 (D002) [X]

## 9. 사고 대응
- 연락·결정할 사람: 저장소 소유자 metapbl. 신고 창구는 GitHub Issues [AI]
- 절차: security.md §7 기본 절차를 따른다. 배포본에 문제가 있으면 해당 Release 를 내리거나 고친 버전을 새로 게시하고 노트에 적는다 [AI]

## 10. Claude Code 적용 (docs 단계에서 채움)
- deny 규칙: `Read(.env)`, `Read(.env.*)`, `Read(!.env.example)`, `Read(*.pem)`, `Read(*.key)` (metarche U2) [X]
- security-guidance 플러그인: 미사용 — 기본 수준, 웹·서버 코드 없음 (D048) [U]
- 편집 때 보안 검사: 별도 없음 — `ruff check` 기본 규칙만 (D031) [AI]
