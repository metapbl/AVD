# AV_Downloader 작업 로그

> 이 문서는 AV_Downloader 프로젝트의 작업 진척과 잔여 과제를 추적합니다.
> 다음 세션에서 AI 보조를 받을 때 이 파일을 먼저 공유하면 즉시 맥락을 잡을 수 있습니다.

**최종 업데이트**: 2026-05-17

---

## 1. 프로젝트 개요

- **리포지토리**: https://github.com/ggoyong2-ctrl/AV_Downloader
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\AV_Downloader`
- **성격**: yt-dlp 기반 영상·오디오 다운로더 (PySide6 GUI, 다크 테마)
- **원작성**: Claude Sonnet 4.6
- **검토·개선**: Claude Opus 4.7과 협업 중
- **개발 환경**: Windows, Python 3.13/3.14, PowerShell, VS Code, `venv` 활성화

## 2. 의존성 (requirements.txt)

```
certifi==2026.4.22
charset-normalizer==3.4.7
idna==3.15
PySide6==6.11.1
PySide6_Addons==6.11.1
PySide6_Essentials==6.11.1
requests==2.34.2
shiboken6==6.11.1
urllib3==2.7.0
yt-dlp==2026.3.17
```

**시스템 요구사항**: Python 3.10+, ffmpeg (PATH 등록), Node.js (YouTube의 JS 챌린지 해결용, 사실상 필수)

## 3. 폴더 구조

```
AV_Downloader/
├── main.py                          # 진입점
├── config.json                      # 사용자 설정 (gitignore됨)
├── requirements.txt
├── run.bat
├── README.md
├── WORKLOG.md                       # 이 파일
├── .gitignore
├── core/
│   ├── downloader.py                # yt-dlp 다운로드 실행
│   └── info_fetcher.py              # 영상 정보 추출
├── models/
│   └── download_item.py             # 데이터 클래스, 상태 Enum
├── ui/
│   ├── main_window.py               # 메인 윈도우
│   ├── download_item_widget.py      # 목록 항목 위젯
│   ├── add_link_dialog.py           # URL 입력 다이얼로그
│   ├── format_select_dialog.py     # 화질 선택 다이얼로그
│   └── preferences_dialog.py        # 환경설정 다이얼로그
├── utils/
│   ├── config_manager.py            # 설정 JSON 영속화
│   ├── file_utils.py                # 파일명·경로 유틸
│   └── updater.py                   # yt-dlp/앱 자체 업데이트
└── workers/
    ├── download_worker.py           # 다운로드 백그라운드 스레드
    ├── info_worker.py               # 정보 추출 백그라운드 스레드
    └── thumbnail_worker.py          # 썸네일 다운로드 백그라운드 스레드
```

## 4. 완료된 커밋 (시간순)

1. **`Initial commit: yt-dlp based media downloader`**
   - 최초 푸시. `config.json`은 gitignore로 제외 (사용자별 개인 경로 포함)
2. **`chore: fix repo URL, add README, populate requirements.txt`**
   - `utils/updater.py`의 `GITHUB_REPO` 플레이스홀더 수정 (`"본인아이디/AV_Downloader"` → `"ggoyong2-ctrl/AV_Downloader"`)
   - `README.md` 본격 작성 (설치, 실행, 요구사항)
   - `requirements.txt` UTF-8 정상화 (PowerShell `>` 리다이렉션이 UTF-16 LE BOM으로 만들었던 것)
3. **`docs: clarify Node.js requirement for YouTube JS challenges`**
   - Node.js 요구사항 README 추가 (yt-dlp EJS 메커니즘 설명)

## 5. 미커밋 상태의 작업

다음 변경들이 로컬에서 작업되었으나 아직 커밋되지 않았습니다. **디버그 print가 잔존**하므로 정식 커밋 전 정리 필요합니다.

- `workers/download_worker.py`
  - 취소 판별을 문자열 매칭에서 `yt_dlp.utils.DownloadCancelled` 타입 기반으로 변경
- `ui/main_window.py`
  - `__init__`에 `self._thumb_workers: list = []` 추가
  - `_on_info_fetched`의 썸네일 워커 생성부에 cleanup 콜백 연결
  - `_cleanup_thumb_worker` 메서드 추가
  - `_on_cancel_all`에 확인 다이얼로그 추가 (기본 버튼 No)
- `ui/download_item_widget.py`
  - `update_thumbnail`에 빈 픽스맵 방어 추가
  - **디버그 print 잔존**
- `core/info_fetcher.py`
  - `_pick_thumbnail` 메서드 추가 (jpg/png 우선 선택)
  - **디버그 print 잔존**
- `core/downloader.py`
  - 네트워크 재시도 옵션 추가: `retries`, `fragment_retries`, `socket_timeout`, `retry_sleep_functions`
- `workers/thumbnail_worker.py`
  - QPixmap에서 QImage 기반으로 변경 (스레드 안전성 가설 — 결과적으로 효과 없었음)
  - **디버그 print 잔존**

## 6. 진행 중 / 미해결: 썸네일 표시 버그

### 증상

영상에 따라 썸네일이 표시되지 않고 🎬 이모지가 그대로 남는 현상.

- **표시 안 됨**: `https://www.youtube.com/watch?v=PPKuqgyzCXc`
- **표시 됨**: `https://www.youtube.com/watch?v=F644LGcDYUY` (윤찬임 - 쇼팽 왈츠)

### 결정적 단서

진단용 print 결과, **모든 단계가 정상 동작**하는데도 화면에는 안 보임:

```
[InfoFetcher] thumbnail = 'https://i.ytimg.com/vi/PPKuqgyzCXc/maxresdefault.jpg'
[InfoFetcher] thumbnails 개수 = 42
[ThumbnailWorker] 1.시작: https://i.ytimg.com/vi/PPKuqgyzCXc/maxresdefault.jpg
[ThumbnailWorker] 2.응답 수신: status=200, bytes=38729
[ThumbnailWorker] 3.디코딩: loaded=True, isNull=False, size=PySide6.QtCore.QSize(1280, 720)
[ThumbnailWorker] 4.emit 직전
[ThumbnailWorker] 5.emit 완료
[Widget] update_thumbnail 호출: isNull=False, size=PySide6.QtCore.QSize(1280, 720)
[Widget] setPixmap 완료
```

화면에는 비디오플레이어 아이콘(🎬) 그대로. setPixmap은 호출되었으나 픽스맵이 그려지지 않음.

### 시도했으나 실패한 가설

1. **WebP 디코딩 문제** — 실패. 문제 영상의 thumbnail URL은 jpg였음.
2. **QPixmap 스레드 안전성** — 실패. 워커를 QImage 기반으로 바꾸고 메인 스레드에서 QPixmap.fromImage로 변환했으나 동일 증상.
3. **maxresdefault 404** — 실패. 브라우저로 직접 열면 정상 표시됨.

### 다음 세션에서 시도할 후보 (우선순위 순)

1. **★ 모달 다이얼로그 순서 문제** — `_on_info_fetched`에서 `FormatSelectDialog.exec()`(모달)가 호출되는데, 그 모달이 떠 있는 동안 썸네일 시그널이 도착하면 위젯 갱신이 어떻게 처리되는지 확인. **모달이 닫힌 후에 썸네일 워커를 시작**해보는 변경이 첫 시도로 적절.
2. `lbl_thumb`의 `pixmap()` 호출 결과와 `geometry()`, `isVisible()` 직접 출력해 위젯 상태 점검.
3. `QLabel.setScaledContents(True)` 또는 사이즈 정책 변경 시도.
4. `lbl_thumb`의 부모 위젯이 픽스맵을 덮어쓰는지 확인 (Qt Inspector 등).
5. Python 3.13과 3.14 환경 차이 확인 (현재 두 버전 캐시가 공존했던 흔적이 `__pycache__`에 있었음).
6. 아예 `QLabel` 대신 `paintEvent` 오버라이드로 직접 그리기.
7. PySide6 버전 다운그레이드 테스트.

## 7. 남은 작업 (Roadmap)

### 즉시 (디버깅 마무리 후)
- [ ] 썸네일 표시 버그 해결
- [ ] 모든 디버그 print 제거
- [ ] 커밋: `fix: improve cancellation, prevent thumbnail leak, add network retries, fix thumbnail rendering`

### 단기 (3단계 잔여)
- [ ] `_pick_thumbnail`의 jpg 우선 선택 로직 검증 후 유지/조정
- [ ] 썸네일 워커 정리 누수 확인 (실패 케이스에서 `_thumb_workers`에서 빠지는지)

### 중기 (4단계 — 설정 일관성)
- [ ] `PreferencesDialog`의 `settings_saved` 시그널을 `main_window`에서 받아 처리하거나, 시그널 자체 제거
- [ ] `DEFAULT_CONFIG`의 `theme`과 `language` 항목 일단 제거 (실제 미구현 설정 노출 안 함)

### 중장기 (5단계 — 동시성)
- [ ] `max_concurrent` 실제 적용
- [ ] 다운로드 큐 구현, 슬롯 관리
- [ ] `QThreadPool` 활용 검토 (현재 import만 됨, 미사용)

### 장기 (6단계 — 견고성·이식성)
- [ ] 진행률을 `_percent_str` 문자열 파싱 대신 `downloaded_bytes / total_bytes` 숫자 계산으로 전환
- [ ] 파일명 중복 방지 (`nooverwrites: True` 또는 `get_unique_path` 활용)
- [ ] `open_folder` 크로스 플랫폼 분기 (Windows/macOS/Linux)
- [ ] QSS를 `ui/styles/dark.qss` 등 별도 파일로 분리
- [ ] yt-dlp 버전 비교를 `packaging.version`으로 전환
- [ ] `_update_temp.exe`를 `tempfile` 기반 임시 디렉토리로 이동
- [ ] `AppUpdater.replace_and_restart` 대신 GitHub Releases 페이지를 브라우저로 여는 방식 검토

### 기능 확장 (선택)
- [ ] 다크/라이트 테마 전환
- [ ] 다국어 (i18n)
- [ ] 다운로드 이력 영속화
- [ ] 플레이리스트 일괄 다운로드
- [ ] 다운로드 속도 제한

## 8. 핵심 학습 (이번 세션)

- **PowerShell `>` 리다이렉션은 UTF-16 LE BOM으로 파일을 씀**
  - `pip freeze > requirements.txt` 시 텍스트가 깨진다. git이 "Binary files differ"로 인식.
  - 대안: `pip freeze | Out-File -Encoding utf8 requirements.txt` 또는 에디터에서 직접 작성.

- **타입 힌트만으로는 속성이 생성되지 않음**
  - `self.x: list` 만 쓰면 `AttributeError`. 반드시 `self.x: list = []`.

- **yt-dlp는 2025년부터 EJS(외부 JS 런타임) 도입**
  - `js_runtimes`, `remote_components` 옵션은 YouTube 다운로드에 사실상 필수.
  - Node.js / Deno / Bun 중 하나 시스템에 설치 필요.
  - 참고: https://github.com/yt-dlp/yt-dlp/wiki/EJS

- **`.gitignore`는 이미 추적 중인 파일에는 효과 없음**
  - 한 번 추적된 파일을 무시하려면 `git rm --cached <파일>`로 인덱스에서 빼야 함.

- **빈 파일의 git SHA는 `e69de29...`**
  - diff에서 `index e69de29..xxx` 보이면 한쪽이 빈 파일과의 비교.

- **PySide6에서 QPixmap은 GUI 스레드에서만 다뤄야 함 (이론)**
  - 다만 이번 썸네일 버그는 이 가설로 설명되지 않음 — 다른 원인이 있는 것으로 보임.

## 9. 다음 세션 시작 방법

1. 이 파일(`WORKLOG.md`)을 그대로 새 대화의 첫 메시지로 붙여넣기.
2. "6번 항목의 썸네일 버그부터 이어서 진행해주세요" 식으로 요청.
3. 또는 다른 작업부터 시작하고 싶다면 "7번 로드맵의 ○○부터" 식으로 명시.
