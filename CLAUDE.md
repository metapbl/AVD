# AV_Downloader — Claude 컨텍스트 파일

> 이 파일은 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하기 위한 컨텍스트 파일입니다.
> Claude Code 는 자동으로 읽으며, claude.ai 웹 채팅에서는 첫 메시지에 본 파일과 `WORKLOG.md` 의 raw URL 을 던져 Claude 가 직접 가져오게 한다 (자세한 방법은 본 파일 맨 아래 "11. 새 세션 시작 방법" 참조).

---

## 1. 프로젝트 정체성

- **이름**: AV_Downloader
- **성격**: yt-dlp 기반 영상·오디오 다운로더 (PySide6 GUI, 다크 테마)
- **리포지토리**: https://github.com/metapbl/AVD
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\AVD`
- **라이선스**: MIT

## 2. 협업 모델

- **초기 골격**: Claude Sonnet 4.6 (2026년 봄)
- **현재 협업**: Claude Opus 4.7 단독 (2026-05-17 이후)
- **작업 방식**: 1인 개발자 + AI 페어 프로그래밍

## 3. 기술 스택

- **언어**: Python 3.10 이상 (개발 환경은 3.13/3.14)
- **GUI**: PySide6 6.11.x
- **다운로드 엔진**: yt-dlp 2026.3.17
- **미디어 처리**: ffmpeg (PATH 등록 필수, ffprobe 동봉)
- **YouTube JS 챌린지 해결**: Node.js (yt-dlp EJS 메커니즘, 사실상 필수)

전체 의존성은 `requirements.txt` 참조.

## 4. 폴더 구조

    AV_Downloader/
    ├── main.py                     # 진입점
    ├── CLAUDE.md                   # 이 파일
    ├── WORKLOG.md                  # 작업 로그 (Changelog + ADR)
    ├── README.md                   # 외부 사용자용 안내
    ├── requirements.txt
    ├── .gitignore
    ├── core/
    │   ├── downloader.py           # yt-dlp 다운로드 실행
    │   └── info_fetcher.py         # 영상 정보 추출
    ├── models/
    │   └── download_item.py        # 데이터 클래스, 상태 Enum
    ├── controllers/
    │   ├── __init__.py             # 패키지 마커
    │   └── download_manager.py     # 다운로드 워커 오케스트레이션 + 동시성 제어 큐
    ├── ui/
    │   ├── main_window.py          # 메인 윈도우
    │   ├── download_item_widget.py # 목록 항목 위젯
    │   ├── add_link_dialog.py      # URL 입력 다이얼로그
    │   ├── format_select_dialog.py # 화질 선택 다이얼로그
    │   ├── confirm_remove_dialog.py# 제거·삭제 확인 다이얼로그
    │   └── preferences_dialog.py   # 환경설정 다이얼로그
    ├── utils/
    │   ├── config_manager.py       # 설정 JSON 영속화
    │   ├── file_utils.py           # 파일명·경로 유틸
    │   └── updater.py              # yt-dlp/앱 자체 업데이트
    └── workers/
        ├── download_worker.py      # 다운로드 백그라운드 스레드
        ├── info_worker.py          # 정보 추출 백그라운드 스레드
        └── thumbnail_worker.py     # 썸네일 다운로드 백그라운드 스레드


## 5. 개발 환경

- **OS**: Windows 11
- **셸**: VS Code 통합 터미널 (PowerShell 프로파일). 명령 제시 시 PowerShell 문법 기본. 워크스페이스 루트가 cwd 로 열려 있다고 가정하므로 `cd` 는 필요할 때만.
- **에디터**: VS Code (Ruff + Pylance 권장, Sourcery 사용 안 함)
- **가상환경**: `venv\Scripts\activate`

## 6. 코딩 컨벤션

- **들여쓰기**: 4 칸 스페이스
- **명명**: snake_case (변수·함수), PascalCase (클래스), UPPER_SNAKE_CASE (상수)
- **타입 힌트**: 가능한 한 사용. 단 `self.x: list` 만 쓰면 속성이 생성되지 않으므로 `self.x: list = []` 형식 필수
- **Qt 시그널·슬롯**: 워커 → 메인 연결은 `Qt.ConnectionType.QueuedConnection` 명시
- **워커 스레드 금지 사항**: QPixmap / QImage 생성 절대 금지. raw bytes 만 전달하고 GUI 스레드에서 변환

## 7. 작업 흐름

- 의미 단위가 끝날 때마다 즉시 커밋. 미커밋 변경이 쌓이지 않도록 한다.
- 커밋 메시지는 [Conventional Commits](https://www.conventionalcommits.org/) 형식 따름:
  - `feat:` 새 기능
  - `fix:` 버그 수정
  - `chore:` 빌드·설정 등 잡일
  - `docs:` 문서 변경
  - `refactor:` 리팩토링 (동작 변경 없음)
- 큰 결정(아키텍처·라이브러리 선택·중대 버그 해결)은 `WORKLOG.md` 의 ADR 섹션에 기록.

## 8. Claude 응답 규칙

### 8.1. 소스 코드 참조

사용자가 코드 수정을 요청하면, Claude 는 본 `CLAUDE.md` 의 "리포지토리" 경로에서 해당 파일을 직접 가져와 현재 상태를 확인한 뒤 패치를 설계한다. 사용자에게 파일 내용을 붙여달라고 요청하지 않는다. 단, 사용자가 로컬에서만 수정하고 아직 push 하지 않은 변경분이 있을 가능성이 있을 때는 그 사실을 짧게 환기한다.

### 8.2. 코드 제시

코드를 제시할 때는 해당 파일에서의 들여쓰기 수준(모듈 최상위 / 클래스 메서드 / 중첩 블록)을 그대로 맞춰서 제시한다. 부분 발췌도 그대로 붙여넣어 동작하는 상태가 기본값이다. 변경의 형태에 따라 두 가지 제시 단위를 쓴다.

1. 변경이 **함수 2개 이하 안에서만 일어나고**, 모듈 최상위(import·상수·dataclass·자유 함수)를 건드리지 않을 때 — 변경된 각 함수를 **개별 코드 블록으로 함수 단위 발췌**한다.
2. 그 외 — **파일 전체**를 보낸다. 즉 함수 3개 이상 변경, 최상위 변경, 새 함수 추가, 함수 시그니처 변경 등이 한 가지라도 포함되면 파일 전체.

어느 경우든 코드 블록 바깥에 **변경 지점을 한 문장으로 명시**한다.

### 8.3. 코드 제시 전 확인

코드 블록을 보내기 전에 "코드를 보내드릴까요?" 라고 한 박자 묻고, 사용자의 동의를 받은 뒤 다음 응답에서 코드를 제시한다. 설계·진단·합의는 코드보다 앞에 오며, 코드는 결정된 사양의 산출물로 등장한다.

### 8.4. 터미널 명령

파일을 수정·추가·삭제하는 코드를 제시할 때는, 사용자가 그 변경을 디스크에 반영하고 커밋·push 하기까지 필요한 **터미널 명령을 같은 응답 안에 함께 제시**한다. 기본 흐름은 ① `git add <변경 파일들>` ② `git status` ③ `git commit -m "<Conventional Commits>"` ④ `git push`. 환경은 **VS Code 통합 터미널 (PowerShell)**, cwd=워크스페이스 루트 가정(`cd` 생략). 커밋 본문이 여러 줄이면 `-m` 을 여러 번 쓴다. 신규 파일·디렉터리는 `New-Item -ItemType {Directory|File} -Force` 로 빈 파일/디렉터리를 만든 뒤 본문은 사용자가 VS Code 에 붙여 넣는다 — `-Force` 는 기존 디렉터리는 보존하지만 기존 파일은 빈 파일로 덮어쓰므로 한 줄 경고를 곁들인다. 예외: 코드 제시가 없는 순수 설계·진단 응답, 또는 사용자가 "명령 빼고 코드만" 요청한 경우.

### 8.5. 마크다운 파일 전송

마크다운 파일 본문에 코드 펜스가 들어 있을 수 있으므로, 파일을 감싸는 바깥 펜스는 안쪽 펜스보다 백틱을 하나 더 사용한다 (안쪽 ``` → 바깥 ````). 안쪽이 여러 깊이면 가장 깊은 것보다 하나 더 많게.

### 8.6. 리스트 들여쓰기

마크다운 불릿은 `-` + 공백 1칸으로 시작하고, 하위 불릿은 부모 줄 기준 **2칸 들여쓰기** 로 통일한다. 1칸·3칸 들여쓰기, `-` 뒤 공백 누락은 사용하지 않는다.

### 8.7. 번호 체계

`##` / `###` 헤더에 1, 1.1 형식 번호를 붙인다(깊이 2까지). 예외: Changelog 날짜 헤더, 단기 목록 항목, ADR 고유 번호(ADR-001 등). 참조 빈도가 높은 규칙은 `-` 대신 `1.` 순서 있는 리스트로 작성한다.

## 9. 알려진 함정 (영구 제약)

> 이 섹션은 새 세션에서 즉시 알아야 할 **영구적 제약** 만 요약한다. 디버깅 맥락과 사례별 함정(NFC 판정·콘솔 렌더링 함정·yt-dlp 후처리 체인 등)은 `WORKLOG.md` 부록 A "학습된 교훈" 에 누적한다.

- **CLAUDE.md 의 모든 규칙을 답변마다 의식적으로 점검하고 철저히 준수한다.**
- **PowerShell `>` 리다이렉션은 UTF-16 LE BOM 으로 파일을 씀**. `pip freeze > requirements.txt` 시 git 이 "Binary files differ" 로 인식. 대안: `pip freeze | Out-File -Encoding utf8 requirements.txt`.
- **PySide6 의 QPixmap 은 GUI 스레드 전용**. 워커 스레드에서 만들면 `isNull()=False` 로 모든 검사를 통과하지만 paint engine 에서 빈 텍스처로 렌더링됨. 워커는 bytes 까지만, 변환은 GUI 스레드에서.
- **"썸네일" 이라는 용어는 두 가지 다른 대상을 가리킬 수 있음**: ① 앱 UI 의 QLabel 미리보기, ② 다운로드된 파일에 임베드된 메타데이터 이미지(Windows 탐색기 아이콘·앨범 아트). 디버깅 시 어느 쪽인지 반드시 명시.
- **yt-dlp 의 EJS (External JS Runtime) 의존**. YouTube 다운로드는 2025년부터 Node.js / Deno / Bun 중 하나 필수. `js_runtimes`, `remote_components` 옵션 사용. 참고: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- **`.gitignore` 는 이미 추적 중인 파일에 효과 없음**. `git rm --cached <파일>` 로 인덱스에서 빼야 함.
- **GitHub `blob/` 경로를 `crawler` 로 가져오면 한국어 산문이 통째로 누락됨**. blob 은 GitHub 의 HTML 페이지라 도구가 markdown 으로 변환하는데, 변환 단계에서 CJK 텍스트 노드가 공백으로 치환된다. 헤더 번호·영문 키워드·코드 식별자·URL 은 남지만 그 사이의 한국어 본문은 사라진다. 새 세션 시작 URL·문서 본문 재확인은 항상 `raw.githubusercontent.com` 경로(`raw=false` 기본 모드)로 한다 — 11.1 참조.
- **`crawler` `raw=true` 모드는 호출당 최대 10000 바이트** — 첫 청크 크기를 파일 전체 크기로 오인하지 말 것. 빈 응답이 나올 때까지 offset 을 10000 씩 늘려 끝까지 읽고, 빈 응답은 같은 offset 재호출로 교차 검증(일시적 빈 응답 사례 다수). 단 마크다운·텍스트 파일을 한 번에 가져오는 게 목적이라면 `raw=true` 를 쓰지 말고 `raw.githubusercontent.com` URL 을 기본 모드로 호출한다 (위 항목 참조).
- **`crawler` `raw=true` 모드는 같은 호스트·URL 시퀀스 안에서 누적 출력이 약 28KB 를 넘으면 "끝"으로 잘못 보고함**. 60KB 짜리 `WORKLOG.md` 를 `raw=true` 로 읽다가 28KB 부근에서 "Offset N is at or beyond end of body" 가 떠도 실제 끝이 아닐 수 있음. 호스트를 갈아타면(`raw.githubusercontent.com` → `github.com/.../raw/...` 또는 `cdn.jsdelivr.net/gh/...`) 새 누적 윈도가 열림. GitHub API 의 `contents` 엔드포인트로 `size` 필드를 먼저 확인하면 진짜 끝을 알 수 있음. 단 이 함정은 `raw=true` 를 명시한 경우에만 발생하므로, 마크다운을 통째로 받을 때는 11.1 의 raw URL + 기본 모드 절차를 따른다.

## 10. 현재 상태와 다음 작업

세부 진행 사항은 `WORKLOG.md` 참조. 다음 작업의 우선순위는 그 파일의 "3. 현재와 다음" 섹션에 정리되어 있음.

## 11. 새 세션 시작 방법

환경에 따라 두 가지 방식을 쓴다.

### 11.1. claude.ai 웹 채팅 (현재 주력)

새 세션의 첫 메시지에 본 파일과 `WORKLOG.md` 의 `raw.githubusercontent.com` URL 두 개를 던지고, 다음 한 줄을 덧붙인다. Claude 가 `crawler` 도구로 즉시 최신 상태를 가져온다 (붙여넣기 스냅샷이 아니라 진짜 HEAD).

> 프로젝트 컨텍스트: https://raw.githubusercontent.com/metapbl/AVD/main/CLAUDE.md
>
> 최신 작업 로그: https://raw.githubusercontent.com/metapbl/AVD/main/WORKLOG.md
>
> 위 두 문서를 먼저 읽어주십시오.

URL 선택 근거: `raw.githubusercontent.com` 경로는 응답 Content-Type 이 `text/plain` 이라 `crawler` 가 기본 모드(`raw=false`)로 호출되어도 HTML→markdown 변환을 거치지 않고 본문을 그대로 통과시킨다. 결과로 (a) 한국어 산문이 100% 보존되고, (b) 한 호출에 파일 전체가 들어오며, (c) `raw=true` 모드의 28KB 누적 함정도 적용되지 않는다. `WORKLOG.md` 가 60KB·100KB 로 커져도 한 번에 끝난다. 대안으로 `https://cdn.jsdelivr.net/gh/metapbl/AVD@main/CLAUDE.md` 형태도 동일하게 동작하나 CDN 캐싱이 push 직후 수 분 지연될 수 있어 `raw.githubusercontent.com` 을 기본으로 둔다. `github.com/.../blob/...` URL 은 사용하지 않는다 — 9 의 blob 한국어 누락 항목 참조.

사람이 브라우저로 문서를 열어볼 때는 평소처럼 `https://github.com/metapbl/AVD/blob/main/...` URL 을 쓰면 된다 — 위 raw URL 은 Claude 의 도구 호출 전용이다.

그 뒤 작업 지시는 다음 셋 중 하나로:

- "WORKLOG.md 섹션 3 첫 번째 항목을 이어가 주세요" — 로드맵 우선 항목 진행
- "ADR-NNN 의 후속 작업을 진행해 주세요" — 특정 결정의 후속
- "[구체적 작업 지시]" — 명확한 작업이 있는 경우

로컬에 push 하지 않은 변경분이 있다면 그 사실을 첫 메시지에 같이 알린다 (Claude 가 GitHub 에서 가져오는 것은 main 시점이므로).

### 11.2. Claude Code (터미널 도구)

자동으로 본 파일을 읽으므로 별도 안내 불필요. 작업 지시만 한 줄로 시작한다.
