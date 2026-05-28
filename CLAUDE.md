# AV_Downloader — Claude 컨텍스트 파일

> 이 파일은 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하기 위한 컨텍스트 파일입니다.
> Claude Code 는 자동으로 읽으며, claude.ai 웹 채팅에서는 첫 메시지에 본 파일과 `WORKLOG.md` 의 GitHub raw URL 을 던져 Claude 가 직접 가져오게 한다 (자세한 방법은 본 파일 맨 아래 "새 세션 시작 방법" 참조).

---

## 프로젝트 정체성

- **이름**: AV_Downloader
- **성격**: yt-dlp 기반 영상·오디오 다운로더 (PySide6 GUI, 다크 테마)
- **리포지토리**: https://github.com/metapbl/AVD
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\AVD`
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
- **셸**: VS Code 통합 터미널 (PowerShell 프로파일). 명령 제시 시 PowerShell 문법 기본. 워크스페이스 루트가 cwd 로 열려 있다고 가정하므로 `cd` 는 필요할 때만.
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
- **Claude 의 소스 코드 참조 규칙**: 사용자가 코드 수정을 요청하면, Claude 는 본 `CLAUDE.md` 의 "리포지토리" 경로에서 해당 파일을 직접 가져와 현재 상태를 확인한 뒤 패치를 설계한다. 사용자에게 파일 내용을 붙여달라고 요청하지 않는다. 단, 사용자가 로컬에서만 수정하고 아직 push 하지 않은 변경분이 있을 가능성이 있을 때는 그 사실을 짧게 환기한다.
- **Claude 의 코드 제시 규칙**: 코드를 제시할 때는 해당 파일에서의 들여쓰기 수준(모듈 최상위 / 클래스 메서드 / 중첩 블록)을 그대로 맞춰서 제시한다. 부분 발췌도 그대로 붙여넣어 동작하는 상태가 기본값이다. 제시 단위는 변경의 규모와 파일 크기를 함께 본다.
  - 변경이 **한 함수/메서드 안에 머무는 경미한 수정**(시그니처 유지, 한두 군데 손봄)이면 — 파일 크기와 무관하게 **해당 함수(또는 메서드) 단위로 부분 발췌**한다.
  - 변경이 **여러 함수에 걸치거나, 모듈 최상위(import·상수·dataclass) 를 건드리거나, 새 함수를 추가**하는 등 파일의 골격에 영향을 줄 때는 — 약 300줄 미만이면 **파일 전체**, 그보다 크면 **변경된 함수들을 묶어 부분 발췌**한다.
  - **한 줄짜리 수정**은 코드 블록 없이 인라인 지시로 끝낼 수 있다.
  - 어느 경우든 코드 블록 바깥에 **변경 지점을 한 문장으로 명시**한다.
- **Claude 의 코드 제시 전 확인 규칙**: 코드 블록을 보내기 전에 "코드를 보내드릴까요?" 라고 한 박자 묻고, 사용자의 동의를 받은 뒤 다음 응답에서 코드를 제시한다. 설계·진단·합의는 코드보다 앞에 오며, 코드는 결정된 사양의 산출물로 등장한다. 단, 한 줄짜리 수정 같은 사소한 변경은 본 규칙의 예외로 둘 수 있다.
- **Claude 의 터미널 명령 제시 규칙**: 파일을 수정·추가·삭제하는 코드를 제시할 때는, 사용자가 그 변경을 디스크에 반영하고 커밋·push 하기까지 필요한 **터미널 명령을 같은 응답 안에 함께 제시**한다. 사용자가 별도로 "커밋 명령 주세요" 라고 다시 묻지 않아도 되도록 한다. 기본 흐름은 ① `git add <변경 파일들>` ② `git status` (다른 것이 끼지 않았는지 확인) ③ `git commit -m "<Conventional Commits 메시지>"` ④ `git push`. 명령은 **VS Code 통합 터미널 (PowerShell)** 기준으로 작성하고, 워크스페이스 루트가 cwd 로 열려 있다고 가정해 `cd` 는 생략한다. PowerShell 의 큰따옴표 중첩 함정을 피해 커밋 본문이 여러 줄이면 `-m` 을 여러 번 쓴다. 예외: 코드 제시가 없는 순수 설계·진단 응답, 또는 사용자가 명시적으로 "명령 빼고 코드만" 요청한 경우.

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

환경에 따라 두 가지 방식을 쓴다.

### claude.ai 웹 채팅 (현재 주력)

새 세션의 첫 메시지에 본 파일과 `WORKLOG.md` 의 raw URL 두 개를 던지고, 다음 한 줄을 덧붙인다. Claude 가 `crawler` 도구로 즉시 최신 상태를 가져온다 (붙여넣기 스냅샷이 아니라 진짜 HEAD).

> 프로젝트 컨텍스트: https://raw.githubusercontent.com/metapbl/AVD/main/CLAUDE.md
>
> 최신 작업 로그: https://raw.githubusercontent.com/metapbl/AVD/main/WORKLOG.md
>
> 위 두 문서를 먼저 읽어주십시오.

그 뒤 작업 지시는 다음 셋 중 하나로:

- "WORKLOG.md 섹션 3 첫 번째 항목을 이어가 주세요" — 로드맵 우선 항목 진행
- "ADR-NNN 의 후속 작업을 진행해 주세요" — 특정 결정의 후속
- "[구체적 작업 지시]" — 명확한 작업이 있는 경우

로컬에 push 하지 않은 변경분이 있다면 그 사실을 첫 메시지에 같이 알린다 (Claude 가 GitHub raw 에서 가져오는 것은 main 시점이므로).

### Claude Code (터미널 도구)

자동으로 본 파일을 읽으므로 별도 안내 불필요. 작업 지시만 한 줄로 시작한다.
