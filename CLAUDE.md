<!-- metarche -->
# AV_Downloader (AVD)

yt-dlp 기반 영상·오디오 다운로더 (PySide6 다크 테마 GUI). 본인과 GitHub 무료 공개 사용자용. 상세는 `docs/PRD.md`.

## 구조
- `main.py` — 진입점 (QApplication, Fusion 스타일, 폰트)
- `core/` — yt-dlp 호출 (`Downloader`, `InfoFetcher`)
- `controllers/` — 워커 라이프사이클·대기열 (`DownloadManager`, `PlaylistFlow`)
- `workers/` — QThread 워커 (다운로드·정보·썸네일·플레이리스트·업데이트)
- `ui/` — 메인 창·위젯·다이얼로그 / `models/` — `DownloadItem`, `DownloadStatus`
- `utils/` — 설정(`config.json`, 앱 폴더)·파일명·업데이터
- `gaindb/` — 벤더링 서브패키지, **LGPL-2.1-or-later, 상류 무수정**
- `docs/legacy/` — 이관 전 문서 (참고용, 고치지 않는다)

## 명령
- 실행: `venv\Scripts\python main.py`
- venv 생성: `py -3.15 -m venv venv` → `venv\Scripts\python -m pip install -r requirements.txt` (설치는 실행 전 확인)
- 전체 테스트: `venv\Scripts\python -m pytest` (F9 이후, 작업마다 실행)
- 편집 때 자동 검사: `.claude/hooks/check.ps1`이 실행 (`venv\Scripts\ruff.exe check --force-exclude`)
- 외부 도구: ffmpeg/ffprobe·Node.js 가 PATH 에 있어야 한다 (R§2)

## 이 프로젝트의 규칙
- 워커 스레드에서 QPixmap/QImage 를 만들지 않는다. bytes 만 넘기고 GUI 스레드에서 변환 (D013, R§4 T1)
- 워커→메인 시그널 연결은 `Qt.ConnectionType.QueuedConnection` 명시 (D013)
- QThread 서브클래스에 `finished`/`started` 이름의 커스텀 Signal 금지 (R§4 T2)
- 속성 타입 힌트는 값까지: `self.x: list = []` (힌트만 쓰면 속성이 안 생긴다)
- `gaindb/` 는 고치지 않는다. 본체는 `gaindb.api` 공개 함수만 호출 (D015, D017)
- "썸네일"은 UI 미리보기와 파일 임베드 중 어느 쪽인지 밝힌다 (D004)
- info dict 가공은 `pre_process` PostProcessor 로, NFC 정규화는 진입점에서 (D006, R§4 T5)
- `requirements.txt` 의 yt-dlp 핀을 올리지 않는다 — 기동 시 자동 업데이트 리허설 장치 (D002)
- 커밋: Conventional Commits, 작성자 `metapbl <ggoyong2@gmail.com>`. 커밋 후 `git log -1 --format="%an <%ae>"` 확인 (D014, R§4 T11)
- 의미 단위 커밋마다 `CHANGELOG.md` 맨 위에 항목 추가 (D020)
- 문서 서식: 불릿 `- ` 뒤 하위는 2칸 들여쓰기, `##`/`###` 헤더에 1, 1.1 번호 (D018)
- PowerShell `>` 는 UTF-16 으로 쓴다. 파일 출력은 `Out-File -Encoding utf8` (R§4 T12)

## 문서 지도
- `docs/PRD.md` — 무엇을 왜 (승인본. 바꾸려면 /metarche discover)
- `docs/PROGRESS.md` — 상태·다음 할 일 (머리는 세션 시작 때 자동 주입)
- `docs/REFERENCE.md` — 구조·외부 사양·함정 대장·UI 원칙. 필요한 절만 검색해 읽는다
- `docs/plans/` — 작업 계획 (체크박스)
- `docs/discovery/` — DECISIONS 는 결정 확인용, QA_LOG 는 검색만
- `CHANGELOG.md` — 외부 공개용 변경 이력, `README.md` — 사용자 안내

## 작업 기록
- 작업을 끝내면 계획 파일의 체크박스를 갱신한다. 세션을 마칠 때 docs/PROGRESS.md 머리 부분을 갱신하고 /metarche wrap을 제안한다.
- 관련 없는 작업으로 넘어갈 때는 /clear를 제안한다.
- 새 결정은 `docs/discovery/DECISIONS.md`에, 반복된 실수의 원인은 REFERENCE 함정 대장에 적는다.
- PRD 변경 중(`상태: changing`)에는 docs/ 밖을 수정하지 않는다 (훅이 막는다).

## 압축 시 보존
- 압축할 때는 진행 중인 계획 파일 경로, 수정한 파일 목록, 확인 명령을 보존한다.
