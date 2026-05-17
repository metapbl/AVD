# AV_Downloader — Claude 컨텍스트 파일

> 이 파일은 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하기 위한 컨텍스트 파일입니다.
> Claude Code 는 자동으로 읽으며, claude.ai 웹 채팅에서는 첫 메시지로 본문을 붙여넣어 사용합니다.

---

## 프로젝트 정체성

- **이름**: AV_Downloader
- **성격**: yt-dlp 기반 영상·오디오 다운로더 (PySide6 GUI, 다크 테마)
- **리포지토리**: https://github.com/ggoyong2-ctrl/AV_Downloader
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\AV_Downloader`
- **라이선스**: MIT

## 협업 모델

- **초기 골격**: Claude Sonnet 4.6 (2026년 봄)
- **현재 협업**: Claude Opus 4.7 단독 (2026-05-17 이후)
- **작업 방식**: 1인 개발자 + AI 페어 프로그래밍

## 기술 스택

- **언어**: Python 3.10 이상 (개발 환경은 3.13/3.14)
- **GUI**: PySide6 6.11.x
- **다운로드 엔진**: yt-dlp 2026.3.17
- **미디어 처리**: ffmpeg (PATH 등록 필수, ffprobe 동봉)
- **YouTube JS 챌린지 해결**: Node.js (yt-dlp EJS 메커니즘, 사실상 필수)

전체 의존성은 `requirements.txt` 참조.

## 폴더 구조

    AV_Downloader/
    ├── main.py                     # 진입점
    ├── CLAUDE.md                   # 이 파일
    ├── WORKLOG.md                  # 작업 로그 (Changelog + ADR)
    ├── README.md                   # 외부 사용자용 안내
    ├── requirements.txt
    ├── run.bat
    ├── .gitignore
    ├── core/
    │   ├── downloader.py           # yt-dlp 다운로드 실행
    │   └── info_fetcher.py         # 영상 정보 추출
    ├── models/
    │   └── download_item.py        # 데이터 클래스, 상태 Enum
    ├── ui/
    │   ├── main_window.py          # 메인 윈도우
    │   ├── download_item_widget.py # 목록 항목 위젯
    │   ├── add_link_dialog.py      # URL 입력 다이얼로그
    │   ├── format_select_dialog.py # 화질 선택 다이얼로그
    │   └── preferences_dialog.py   # 환경설정 다이얼로그
    ├── utils/
    │   ├── config_manager.py       # 설정 JSON 영속화
    │   ├── file_utils.py           # 파일명·경로 유틸
    │   └── updater.py              # yt-dlp/앱 자체 업데이트
    └── workers/
        ├── download_worker.py      # 다운로드 백그라운드 스레드
        ├── info_worker.py          # 정보 추출 백그라운드 스레드
        └── thumbnail_worker.py     # 썸네일 다운로드 백그라운드 스레드


## 개발 환경

- **OS**: Windows 11
- **셸**: PowerShell
- **에디터**: VS Code (Ruff + Pylance 권장, Sourcery 사용 안 함)
- **가상환경**: `venv\Scripts\activate`

## 코딩 컨벤션

- **들여쓰기**: 4 칸 스페이스
- **명명**: snake_case (변수·함수), PascalCase (클래스), UPPER_SNAKE_CASE (상수)
- **타입 힌트**: 가능한 한 사용. 단 `self.x: list` 만 쓰면 속성이 생성되지 않으므로 `self.x: list = []` 형식 필수
- **Qt 시그널·슬롯**: 워커 → 메인 연결은 `Qt.ConnectionType.QueuedConnection` 명시
- **워커 스레드 금지 사항**: QPixmap / QImage 생성 절대 금지. raw bytes 만 전달하고 GUI 스레드에서 변환

## 작업 흐름

- 의미 단위가 끝날 때마다 즉시 커밋. 미커밋 변경이 쌓이지 않도록 한다.
- 커밋 메시지는 [Conventional Commits](https://www.conventionalcommits.org/) 형식 따름:
  - `feat:` 새 기능
  - `fix:` 버그 수정
  - `chore:` 빌드·설정 등 잡일
  - `docs:` 문서 변경
  - `refactor:` 리팩토링 (동작 변경 없음)
- 큰 결정(아키텍처·라이브러리 선택·중대 버그 해결)은 `WORKLOG.md` 의 ADR 섹션에 기록.

## 알려진 함정

- **PowerShell `>` 리다이렉션은 UTF-16 LE BOM 으로 파일을 씀**. `pip freeze > requirements.txt` 시 git 이 "Binary files differ" 로 인식. 대안: `pip freeze | Out-File -Encoding utf8 requirements.txt`.
- **PySide6 의 QPixmap 은 GUI 스레드 전용**. 워커 스레드에서 만들면 `isNull()=False` 로 모든 검사를 통과하지만 paint engine 에서 빈 텍스처로 렌더링됨. 워커는 bytes 까지만, 변환은 GUI 스레드에서.
- **yt-dlp 의 `info["thumbnail"]` 은 항상 maxresdefault 를 가리키지 않을 수 있음**. 영상에 따라 다른 후보가 반환될 가능성 있음. 현재는 정상 동작 중이나 향후 문제 발생 시 `_pick_thumbnail` 같은 안전망 도입 검토.
- **"썸네일" 이라는 용어는 두 가지 다른 대상을 가리킬 수 있음**: ① 앱 UI 의 QLabel 미리보기, ② 다운로드된 파일에 임베드된 메타데이터 이미지(Windows 탐색기 아이콘·앨범 아트). 디버깅 시 어느 쪽인지 반드시 명시.
- **yt-dlp 의 EJS (External JS Runtime) 의존**. YouTube 다운로드는 2025년부터 Node.js / Deno / Bun 중 하나 필수. `js_runtimes`, `remote_components` 옵션 사용. 참고: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- **`.gitignore` 는 이미 추적 중인 파일에 효과 없음**. `git rm --cached <파일>` 로 인덱스에서 빼야 함.

## 현재 상태와 다음 작업

세부 진행 사항은 `WORKLOG.md` 참조. 다음 작업의 우선순위는 그 파일의 "현재와 다음" 섹션에 정리되어 있음.

## 새 세션 시작 방법

새 Claude 세션의 첫 메시지로 이 파일 본문을 통째로 붙여넣고, 다음 한 줄을 덧붙입니다:

> `WORKLOG.md` 의 "현재와 다음" 섹션에서 첫 번째 항목을 이어가 주세요.

또는 특정 작업을 지정:

> `WORKLOG.md` 의 ADR-XXX 결정을 검토하고, 관련된 후속 작업을 진행해 주세요.
