# AV_Downloader — 학습된 교훈 (Lessons)

> 같은 실수를 반복하지 않기 위한 메모. `CLAUDE.md` "9. 알려진 함정" 이 영구 제약만 담는다면, 본 파일은 디버깅 사례에서 얻은 구체적 함정과 회피책을 주제별로 누적합니다.

## 작성 규약

- 한 항목은 **5 줄 이내** (1~3 문장).
- 그룹 헤더 직후 줄에 `<a id="lessons-그룹키"></a>` 명시 앵커.
- 시간순 번복으로 더는 유효하지 않은 항목은 **삭제하지 않고** `[역사적]` 표시 + 현 권장 항목 링크.
- 출처는 `ADR-NNN` 또는 7자리 커밋 해시로만 표기. 디버깅 사연은 적지 않는다 (그건 `CHANGELOG.md` 의 영역).
- 새 항목 추가 시 같은 그룹 안 중복 진술을 정리하고, 그룹이 길어지면 하위 분할을 고려.

---

### PowerShell · Windows 환경

<a id="lessons-powershell"></a>

- `>` 리다이렉트는 기본 UTF-16 LE BOM. UTF-8 이 필요하면 `Out-File -Encoding utf8` 또는 `Set-Content -Encoding utf8` 명시.
- `git diff` 가 `:` 로 멈추면 less 페이저. `q` 종료 / `Space` 다음 페이지 / `G` 끝. 페이저 없이 보려면 `git --no-pager diff`.
- 빈 파일의 Git SHA 는 `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`.
- PowerShell 의 큰따옴표 안 큰따옴표는 `""` 로 이스케이프 불가 (빈 문자열 해석). 큰따옴표 안에는 작은따옴표를 쓰거나, 커밋 헤더 한 줄로만 쓰고 본문은 WORKLOG 로 빼는 게 안전.

### Python · PySide6

<a id="lessons-pyside6"></a>

- 타입 힌트 (`self.x: dict`) 만으로는 변수가 생성되지 않음. `__init__` 에서 `= {}` 로 명시 초기화.
- `QPixmap` / `QImage` 는 GUI 스레드 전용. 워커는 raw bytes 만 emit.
- 시그널·슬롯이 스레드를 넘으면 `Qt.QueuedConnection` 명시.
- `QLabel.setScaledContents(True)` 는 0×0 라벨에서 빈 화면을 만들 수 있음. 직접 `scaled()` 호출이 안전.
- 다크 테마 앱은 `QApplication.setStyle("Fusion")` 을 먼저 깐다. OS 무관한 Qt 자체 렌더링이라 체크박스·라디오 indicator 의 ✓ 마크가 SVG 자산 없이 그려짐. `QCheckBox::indicator` 직접 스타일링은 ✓ 렌더링을 꺼뜨림. (출처: 2026-05-29 `fix(ui)` Fusion 적용)
- QThread 의 내장 시그널 `finished`/`started` 를 같은 이름 커스텀 `Signal` 로 정의하면 내장 시그널이 가려짐. 결과 전달용 시그널은 별도 명명(`download_finished` 등)하고, 객체·dict 정리는 내장 `finished` 에 연결해 스레드 완전 종료 후 수행. 동명 섀도잉 시 run() 종료 직전 워커가 GC 되어 "QThread: Destroyed while thread is still running" 크래시. (출처: ADR-006)

### yt-dlp

<a id="lessons-yt-dlp"></a>

- 2025년부터 EJS 의존. Node.js / Deno / Bun 중 하나 PATH 필수. node 고정은 deno/bun 자동 선택을 막으므로 옵션 비워 둘 것. 참고: <https://github.com/yt-dlp/yt-dlp/wiki/EJS>
- `info["thumbnail"]` 은 보통 정확하지만 `info["thumbnails"]` 배열에서 직접 선별 가능. maxresdefault 가 없는 영상 대비 `_pick_thumbnail` 안전망 유효.
- `bestvideo+bestaudio/best` 는 코덱 효율 우선이라 H.264 보다 파일이 작을 수 있음 (ADR-002 참조).
- `postprocess_hook` 은 ffmpeg 머지만이 아니라 **모든 후처리기** 의 started/finished 발사. `d["postprocessor"]` 로 단계 구분 필요. 2026.3.17 기준 체인: `ThumbnailsConvertor → Merger → Metadata → EmbedThumbnail → MoveFiles`. 후크에 퍼센트 키 없음 — 후처리 단계 퍼센트 표시는 현 구조 불가.
- `ExtractAudio` 의 m4a→mp3 재인코딩 시 ffmpeg 가 기본 `-map_metadata 0` 으로 원본 ftyp 박스 (`major_brand` 등) 를 ID3 TXXX 로 옮겨 박음. `-map_metadata -1` 로 끊으면 `FFmpegMetadataPP` 의 TIT2 까지 무효화됨. 선별 제거가 필요하면 `meta_<key>` info dict 주입 또는 별도 ffmpeg 호출 경로.
- 기본 retry/timeout 짧음. GUI 에서는 `socket_timeout`, `retries`, `fragment_retries='infinite'`, `file_access_retries`, `retry_sleep_functions` 명시.
- **`retries`(=세션 내 HTTP 재시도) 는 토큰 만료 403 을 못 고친다**. YouTube 403 은 시작 시점 세션/토큰 만료라 같은 `YoutubeDL` 세션 안에서는 계속 403 — 새 세션(새 `Downloader`, `extract_info` 재실행) 으로 다시 시작해야 새 토큰을 받는다. 자동 회복은 `retries` 위, 세션 전체를 다시 도는 계층에서. 오류 일시/영구 분류는 예외 타입 불가(대부분 `DownloadError`), 메시지 패턴으로. (ADR-007)
- **영구성 4xx(400/401/404/410) 는 `Unable to download webpage: HTTP Error 404 ...` 로 포장돼 온다** — 일시 패턴 `unable to download webpage` 에 오분류돼 헛재시도할 수 있다. 실제 오류 문자열을 직접 뽑아 대조해야 잡힌다(Fake 시뮬레이션으론 못 봄). 영구 4xx 를 일시 패턴보다 먼저 검사하도록 명시. 단 403=토큰만료·429=rate-limit 은 일시 유지. (ADR-007)
- HLS 는 `total_bytes` / `total_bytes_estimate` 둘 다 없어 yt-dlp ETA 산식 불성립. `_eta_str` placeholder 감지 + `pct` × `elapsed` 추정으로 `~M:SS` 우회.
- **`pre_process` 단계 커스텀 PostProcessor 가 info dict 사전 가공의 정공법**. `ydl.add_post_processor(MyPP(), when="pre_process")`. NFC 정규화, `meta_<key>` 사전 주입, 사용자 정의 메타 가공은 이 단계. `MetadataParserPP` INTERPRET 는 기존 값 재해석 도구일 뿐 외부 값 주입 불가. (출처: ADR-004)
- `FFmpegMetadataPP` 는 info dict 의 `title` / `artist` / `description` 을 직접 읽음. 메타 통제는 ffmpeg 인자 우회보다 info dict 정규화 + `pre_process` PP 가 단순·견고.
- **단일 프로세스 병렬 다운로드 미지원**. 안전 구간 1~3개, 상한 ~5개. UI 에서 위험 구간(노랑·빨강) 시각 명시 필요. metube 기본 3, youtube-dl-gui 한 자리 수가 관행.
- [역사적] `ydl.download([url])` 이 `extract_info` 를 다시 돌리므로 사전 가공한 info dict 가 무시되어 `process_ie_result(info, download=True)` 우회 사용. → YouTube 토큰 만료 회귀로 폐기. 현 권장은 `pre_process` PP. (출처: ADR-004)
- [역사적] `process_ie_result(probed, download=True)` 가 NFC 보존 우회로 유효. → YouTube `HTTP Error 403: Forbidden` 회귀로 폐기. 다른 사이트(SoundCloud 등) 에서는 토큰 정책이 느슨해 잠복했었음. 현 권장은 `pre_process` PP. (출처: ADR-004)

### 유니코드 · 파일명

<a id="lessons-unicode"></a>

- 유니코드 정규화는 **클라우드·OS·소스 사이트 경계에서 깨진다**. SoundCloud 한글 메타가 NFD 로 들어올 수 있음. **info dict 진입 지점에서 NFC 통일** 원칙.
- 콘솔 렌더링은 NFD 를 NFC 처럼 그릴 수 있음. `chcp 65001` 의 한글 결합 렌더링에 속지 말 것. NFC/NFD 판정은 **파일 원본 바이트** 에서: m4a 의 `©nam` atom, mp3 의 `TIT2` 프레임을 hex 로. NFC 한글은 UTF-8 3바이트, NFD 는 자모별 2~3개.
- 표시 레이어는 정직하지 않다. 탐색기 속성창은 NFD 분리(정직), VS Code 터미널·ffprobe JSON 은 결합(NFC 처럼 보임). 표시 어긋남으로 데이터 추론 금지.
- ID3v2.3 텍스트 인코딩은 UTF-16(BOM) 호환성이 가장 높고 yt-dlp+ffmpeg 기본이 이를 따름. 우리는 별도 옵션 불필요하나 값은 NFC 여야 함.

### Git

<a id="lessons-git"></a>

- `.gitignore` 는 이미 추적 중인 파일에 영향 없음. `git rm --cached <path>` 로 인덱스에서 제거.
- 의미 단위 분할은 `git add -p` 의 hunk 단위 스테이징.
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`. 참고: <https://www.conventionalcommits.org/>
- `--amend` 후 push 거부는 원격에 형제 분기가 형성된 신호. `git log --oneline --graph --all` 로 진실 먼저 확인. 1인 환경의 `--force-with-lease` 유혹에 주의 — 원격 docs 커밋이 살아 있는 케이스에서 손실 가능.

### 협업 · 커뮤니케이션

<a id="lessons-collab"></a>

- **용어가 같다고 대상도 같지는 않다**. "썸네일" 처럼 일상어가 두 객체를 가리킬 때 먼저 대상부터 확정. (출처: ADR-001)
- 진단 코드(print, 임시 파일) 는 가설 검증 후 즉시 제거. 커밋에 섞지 않음.
- 가설은 한 번에 하나씩 검증. 동시 패치는 원인 추적을 어렵게 함.
- **단일 질문 원칙**: 확인 다이얼로그는 "하나의 질문 + 부가 옵션(체크박스)" 구조가 인지 부담 최소. 두 결정을 Yes/No 로 묶지 말 것.
- **버튼 라벨은 동작을 진실하게 묘사**. "전체 취소" 가 실제로는 "진행 중인 다운로드만 취소" 였던 케이스 — 라벨·동작 어긋남은 UX 부채로 누적.
