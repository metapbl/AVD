# AV_Downloader 작업 로그

> 이 문서는 AV_Downloader 의 작업 진척, 결정 사항, 잔여 과제를 추적합니다.
> 프로젝트의 변하지 않는 정보(기술 스택·폴더 구조·코딩 컨벤션 등)는 `CLAUDE.md` 에 별도로 관리하며, 이 파일은 시간과 함께 자라는 정보만 담습니다.

**최종 업데이트**: 2026-05-28

---

## 문서 구조

이 파일은 네 섹션으로 구성됩니다.

- **섹션 1 — 빠른 안내**: 새 세션 시작 시 어떻게 이 문서를 활용할지.
- **섹션 2 — Changelog**: 시간 역순으로 모든 의미 있는 변경 사항을 누적.
- **섹션 3 — 현재와 다음**: 진행 중인 작업과 단기·중기·장기 로드맵.
- **섹션 4 — ADR (결정 기록)**: 아키텍처·중대 버그 해결 등 큰 결정의 맥락과 결과.

각 섹션은 서로 다른 시간 척도를 가집니다. 섹션 2 는 한 번 적은 줄을 절대 지우지 않고 누적됩니다. 섹션 3 은 유동적이며 항목이 완료되면 섹션 2 로 옮깁니다. 섹션 4 는 큰 결정이 있을 때만 새 항목이 추가됩니다.

---

## 1. 빠른 안내

### 1.1. 새 세션 시작 방법

`CLAUDE.md` 의 "새 세션 시작 방법" 섹션을 따른다. 환경별(claude.ai 웹 채팅 / Claude Code) 절차가 거기에 정리되어 있다.

### 1.2. 작업 완료 시 갱신 규칙

- 의미 단위가 끝나 커밋이 발생하면 → 섹션 2 (Changelog) 의 맨 위에 한 줄 추가
- 큰 결정(아키텍처·중대 버그 해결)이 있으면 → 섹션 4 (ADR) 에 새 항목 추가
- 새 할 일이 생기면 → 섹션 3 (현재와 다음) 의 적절한 위치에 추가
- 섹션 3 의 항목이 완료되면 → 섹션 2 로 이동하며 섹션 3 에서는 제거 또는 ✅ 표시

---

## 2. Changelog (시간 역순)

> [Keep a Changelog](https://keepachangelog.com/) 형식을 참고하여, 최신 변경이 위로 오도록 누적. 한 번 적은 줄은 절대 지우지 않음.

### 2026-05-28

### 2026-05-28

- **`feat(ui)`**: 동시성 제어 큐 매니저 도입 + `MainWindow` 분할.
  - 신규 `controllers/download_manager.py` (`DownloadManager`, `QObject` 서브클래스): `MainWindow` 가 보유하던 다운로드 워커 오케스트레이션을 통째로 이관. 공개 API 는 `enqueue` / `retry` / `cancel` / `cancel_all` / `is_active` / `active_count` / `forget` 일곱 개. 라이프사이클 시그널 3개 (`item_done` / `item_error` / `item_cancelled`) 만 매니저가 재발사하고, 진행률·속도·ETA·병합은 워커→위젯 직접 연결(매니저 미경유) 로 두어 시그널 비용 최소화. `items` / `widgets` dict 는 `MainWindow` 가 단일 소유자이고 매니저는 참조만 받아 읽기·순회.
  - 신규 `controllers/__init__.py`: 패키지 마커. 한 줄 주석.
  - `ui/main_window.py`: `_on_format_selected` / `_on_retry` 를 매니저 위임 진입점으로 축소. `_on_cancel` / `_on_remove` / `_on_clear_list` 는 매니저의 `cancel` / `cancel_all` 호출로 단순화. 워커 종료 콜백 3개(`_on_download_done` / `_on_download_error` / `_on_download_cancelled`) 는 매니저 시그널 슬롯으로 재정의 — 위젯 상태 갱신과 status_bar 메시지만 책임짐. dispatch 로직(`_dispatch_next` / `_refresh_waiting_labels` / `_start_worker`) 은 매니저로 이사. `_remove_item_quiet` 가 `download_manager.forget(item_id)` 한 줄로 워커 dict 정리 위임. `_on_remove` 끝의 `download_manager.enqueue(item_id)` 호출은 WAITING 항목 제거 시 뒤쪽 WAITING 들의 순번 라벨이 즉시 당겨지도록 dispatch 를 한 번 깨우는 용도(no-op + label refresh).
  - 큐 매니저 정책: 환경설정 슬라이더의 `max_concurrent` 값이 실제 동시 다운로드 수의 한도로 동작. `_dispatch_next` 가 `self.items` 의 dict 순서(=삽입 순서) 를 큐로 보고 빈 슬롯만큼 WAITING 항목들을 차례로 출발시킴. 별도 큐 자료구조를 두지 않음 — `status == WAITING` 인 것이 곧 대기열이라는 단일 출처 원칙. 슬라이더 8 로 키운 채 한 번에 10 개를 추가하면 한 번의 dispatch 로 8 개가 한꺼번에 출발하는 흐름까지 같은 루프가 처리.
  - WAITING 항목 표시 (정책 P): `lbl_status` 에 `"대기 중 (N번째)"` 형태로 순번 표시. N 은 WAITING 항목들 사이의 순번이며 진행 중 항목은 카운트하지 않음. dispatch 직후 `_refresh_waiting_labels` 가 모든 WAITING 위젯의 순번을 다시 그려 한 칸씩 당겨진 상태를 즉시 반영.
  - WAITING 항목 버튼 (정책 Y): `ui/download_item_widget.py` 의 `update_status` 에 WAITING 명시 분기 추가 — 취소·열기 버튼 모두 숨김. "취소" 버튼은 "진행 중인 무언가를 멈춘다" 의 의미가 견고해야 하는데 WAITING 은 진행 중이 아니므로 버튼을 노출하면 거짓말이 됨. 큐에서 빼는 동작은 ✕ 단일 경로로 통일. 신규 `update_waiting_position(n: int)` 메서드 — `MainWindow` (정확히는 매니저) 가 N 을 계산해 위젯에 주입.
  - 재시도 정책 (정책 A): 재시도도 큐 규칙을 준수. `_on_retry` 가 항목을 WAITING 으로 떨어뜨린 뒤 매니저 `retry` 호출 → 슬롯이 비어 있으면 즉시 출발(사용자에겐 즉시로 보임), 슬롯이 꽉 차 있으면 잠시 "대기 중 (N번째)" 로 떨어졌다가 자기 차례에 출발. 슬라이더의 약속("동시 N개")을 재시도가 우회로로 깨지 않는다는 정직함.
  - 검증 시나리오 6개 모두 통과: ① 슬라이더 2, 영상 5개 추가 → 2개 출발 + 3개 "대기 중 (1·2·3번째)", 하나 완료 시 순번 당겨짐. ② WAITING ✕ → 다이얼로그 후 제거, 뒤쪽 순번 당겨짐. ③ 진행 중 취소 → 대기 항목 자동 출발 (매니저 `_on_worker_cancelled` 의 `_dispatch_next`). ④ 슬라이더 6→2 축소 → 이미 도는 6개 워커는 유지, 신규는 한도 2 안에서만 출발(=의도된 동작, 진행 중 워커를 죽이지 않음). ⑤ 재시도 → 슬롯 여유 따라 즉시 또는 잠시 WAITING. ⑥ 영상 1개 추가 → 분할 전과 동일하게 정보 추출 → 화질 선택 → 다운로드 → 완료까지 흐름. ⑥ 은 새 동작이 거의 개입하지 않는 통제군 시나리오로, 분할 자체의 회귀를 잡기 위한 별도 검증.
  - 관련: ADR-003 (분할 구조 결정의 맥락과 대안 기록).
  - 사용자 합의 과정: 1차 응답에서 부분 발췌가 일곱 함수에 흩어져 가독성이 떨어진다는 사용자 지적 → 분할 vs 전체 파일 두 선택지 제시 → 분할 채택. refactor + feat 두 커밋으로 끊을지(a), 한 커밋으로 갈지(b) 다시 합의 → 응답 비용을 고려해 (b) 단일 feat 커밋 채택. (커밋 `954152f`)

- **`feat(ui)`**: 항목 레이아웃 단순화 — 80px 욱여넣기 + 제목 엘라이드.
  - `ui/download_item_widget.py`: 썸네일 80px 안에 우측 4행을 욱여넣는 결정론적 배치. 균등 분배(`stretch=1`) 대신 행별 `setFixedHeight` 로 결정: 제목 26 + 메타 16 + 진행률 16 + 상태행 16 = 74, `info_layout.setSpacing(2)` × 3 간격 = 6, 합 80px ✅. 위젯 전체는 `setFixedHeight(96)` 로 외곽 고정(썸네일 80 + 상하 마진 8+8). 진행률 바 두께를 6 → 16 으로 키워 행 높이와 일치시키고 별도 래퍼 레이아웃 없이 단순화 (사용자 한 줄 제안 "진행률 바의 너비를 넓히면 되지 않을까요" — 산수의 직관적 정답이 사양이 됨)
  - `ui/download_item_widget.py`: 긴 제목 엘라이드 — `lbl_title` 의 size policy `(Ignored, Preferred)` 로 가로 sizeHint 권리 포기 + `resizeEvent` 오버라이드에서 `QFontMetrics.elidedText(ElideRight)` 로 라벨 폭에 맞춰 직접 잘라 표시. 원본 제목은 `self.item.title` 단일 출처에서 매번 다시 가져옴. `update_title` 갱신 시에도 새 원본으로 재엘라이드. 워드랩은 안 켬(항목 높이 들쭉날쭉 방지)
  - 시행착오 한 라운드: 첫 사양은 `progress_bar.setMaximumWidth(400)` + 4행 `stretch=1` 균등 분배였으나 (a) 진행률 바가 부모 폭 가운데에 외롭게 떠 보이는 부작용 (QProgressBar 의 기본 가로 size policy 가 `Expanding` 이라 maxWidth 가 천장 역할만 하고 남은 공간이 좌우로 갈라짐), (b) `stretch=1` 이 QLabel 의 sizeHint 를 넘어선 세로 점유를 강제하지 못해 4행이 위쪽으로 몰리는 현상 — 두 문제가 함께 드러남. 사용자 재합의로 "썸네일 80px 안에 완전히 욱여넣기" 사양 채택, `setMaximumWidth(400)` 제거, 균등 분배 포기. `stretch` 약속은 폰트·환경에 따라 결과가 흔들리므로 행별 `setFixedHeight` 의 결정론이 더 정직하다는 결론
  - 검증: 좁은 윈도우와 넓은 윈도우 양쪽에서 4행이 80px 안에 정확히 들어감 (스크린샷 확인). 진행률 바가 부모 폭을 자연스럽게 따라 변하고 가운데 정렬 부작용 없음. 긴 제목(50자 이상)이 부드럽게 엘라이드되며 ✕/취소 버튼이 잘리지 않음. 항목 두 개 이상이 섞여 있을 때 모든 항목의 높이가 96px 로 일정
  - git 정리 메모: 직전 미푸시 작업분과 합쳐 한 커밋으로 만들기 위해 `--amend` 사용. amend 후 push 가 거부됐는데, 원격에 그 사이 docs(worklog) 커밋(`acd1d4d`) 이 들어와 형제 분기가 형성된 상태였음. `git pull --rebase` 로 선형화 (두 커밋의 파일 교집합이 0 이라 conflict 없음). 1인 개발 환경에서 `--force-with-lease` 의 유혹이 있을 수 있지만, 원격 docs 커밋이 살아 있던 케이스라 force 가 손실을 일으켰을 것 — 분기 의심 시 `git log --oneline --graph --all` 로 진실 먼저 확인하는 절차의 가치를 재확인 (최종 커밋 `8074e43`)

- **`chore`**: GitHub 저장소 이전 (`ggoyong2-ctrl/AV_Downloader` → `metapbl/AVD`). 로컬 폴더명도 `AV_Downloader` → `AVD` 로 변경. `utils/updater.py` 의 `GITHUB_REPO`, `README.md` clone URL, `CLAUDE.md` 의 리포지토리·로컬 경로·raw URL 까지 모두 새 주소로 갱신. 기능 변경 없음. (커밋 `019a420`)

- **`docs(worklog)`**: 2026-05-27 의 `feat(ui)` 환경설정 항목을 실제 최종 구현(`cab59c5`)에 맞춰 정정. 첫 합의의 "3:3:4 단색 컬러 바" 사양은 협의 과정에서 그라데이션 바 + `ConcurrentSlider` (QSlider 서브클래스, `paintEvent` 오버라이드로 트랙 내 위치 안내 점 8개 묘사) 로 재설계되어 대체됨. 같은 제목의 두 커밋(`dd1113d` → `cab59c5`) 의 관계도 명기. 섹션 3 단기 목록의 "환경설정 다이얼로그 정비" 항목은 본 정정과 함께 Changelog 로 이관됨.

### 2026-05-27

- **`feat(ui)`**: 환경설정 다이얼로그 정비 — 동시 다운로드 슬라이더 + last_chosen_ext.
  - `ui/preferences_dialog.py`: SpinBox → 신규 `ConcurrentSlider` (QSlider 서브클래스, `paintEvent` 오버라이드로 트랙 내부에 위치 안내용 점 8개(값 2~9, `#cccccc`, 직경 3px) 묘사. 양 끝값 1·10 은 핸들 자체가 위치 신호). 범위 1~10, 기본 2, 자연수 step. 슬라이더 위에 단일 가로 **그라데이션 바** (stop 0.0/0.22 녹 `#2e7d32`, 0.33/0.55 노 `#c9a227`, 0.66/1.0 빨 `#b03030` — 1·3 / 3·4 그라데이션 / 4·6 / 6·7 그라데이션 / 7·10 구간을 자연스럽게 잇는 5-stop 정의). 그 아래 "권장 / 주의 / 비권장" 라벨 행을 stretch 2/4/3 으로 배치(녹·노·빨 폭과 시각 정합). 우측 상단에 현재 값 큰 숫자, 핸들·숫자 색은 dynamic property + `style().unpolish/polish` 로 1~3 녹 / 4~6 노 / 7~10 빨 구간 동기화. 툴팁에 "yt-dlp 단일 인스턴스 병렬 미지원, 1~3 권장, 높은 값은 IP 차단 위험" 명시. "기본 저장 형식" 콤보 제거 — 동일 기능은 FormatSelectDialog 의 `last_chosen_ext` 로 흡수
  - `ui/format_select_dialog.py`: `__init__` 에 `config` 인자 추가. 포맷 목록 채운 직후 `last_chosen_ext` 키와 일치하는 첫 행을 기본 선택. `_on_confirm` 에서 사용자가 확정한 포맷의 `ext` 를 `config.last_chosen_ext` 로 저장 — 같은 확장자를 반복 선택하는 사용자 패턴을 무비용으로 기억
  - `utils/config_manager.py`: `DEFAULT_CONFIG` 에 `"last_chosen_ext": ""` 추가. 빈 문자열이면 "기억 없음" 으로 보고 첫 행 기본. 기존 `default_ext` 키는 잔존(다른 모듈 영향 미확인 — 정리는 별도 chore 커밋으로)
  - `ui/main_window.py`: `_on_info_fetched` 의 `FormatSelectDialog(info, self)` → `FormatSelectDialog(info, self.config, self)` 한 줄 변경
  - placebo 명시: 본 단계의 슬라이더 값은 `config.max_concurrent` 에 저장되지만 실제 동시성 제어는 후속 "동시성 제어 구현 (큐 매니저)" 에서 도입. `_on_save` 와 `_on_concurrent_changed` 양쪽에 주석으로 명시
  - 사양 근거 (요약): SpinBox ± 버튼이 28px 고정 높이를 벗어나 겹쳐 보이던 UI 버그 + "기본 저장 형식" 콤보가 `FormatSelectDialog` 와 의미 중복이던 점 해소. 컬러 영역 비율은 4K Video Downloader+ 의 1·2·4·6·8 라벨 정책(Safe/Stable/Optimal/Risky)을 참고하되, "Optimal" 같은 마케팅 단어를 피하고 보수적 워딩("권장/주의/비권장") 채택 (4K Downloader 의 "Stable=4" 가 한국어 "주의" 와 의미 충돌하던 점도 회피). 첫 합의의 단색 3-band 컬러 바 대신 그라데이션을 택한 이유는 "구간 경계가 절대선이 아니라 점진적 위험 증가" 라는 메시지를 더 정직하게 전달하기 위함. 위치 안내 점은 사용자의 "숫자 없어도 위치 표시는 필요" 요청에 응답
  - 커밋 분기: 첫 사양(SpinBox→QSlider + 단색 3:3:4 컬러 바) 으로 `dd1113d` 푸시 후, 같은 세션 안에서 그라데이션 + `ConcurrentSlider` (점 8개) 로 재설계해 `cab59c5` 로 재푸시. 두 커밋의 제목이 동일하므로 본 항목이 양자의 관계와 최종 구현(`cab59c5`) 위치를 명시. 중간의 `5e7d73b` 는 본 항목의 1차 워크로그 기록 (이후 본 `docs(worklog)` 2026-05-28 커밋으로 정정됨)
  - 검증: 슬라이더 1·3·4·6·7·10 의 핸들·숫자 색 전환, 그라데이션 바 정렬, 점 8개 가시성, `last_chosen_ext` 기억 동작(같은 영상 두 번 추가 시 직전 선택 ext 의 행이 자동 선택), 환경설정에서 저장 후 재진입 시 슬라이더 값 복원

- **`feat(ui)`**: 삭제·취소 확인 다이얼로그 통일 + "전체 취소" → "목록 비우기" 재정의.
  - 신규 `ui/confirm_remove_dialog.py`: 개별 ✕ 와 일괄 "목록 비우기" 가 공유하는 단일 다이얼로그. 본질 질문은 "목록에서 제거" 하나로 고정, 디스크 삭제는 옵셔널 체크박스로 분리. 기본 포커스는 "닫기" — 엔터 잘못 눌러도 안전. 결과 두 개 노출: `confirmed` / `delete_disk_files`
  - `ui/main_window.py` 의 `_on_cancel`: 워커가 실제로 running 일 때만 "이 다운로드를 취소하시겠습니까?" 확인 (기본 No). 비활성 상태에서의 누름은 무시 — 버튼 라벨이 "재시도" 가 됐을 경계 케이스 방어
  - `ui/main_window.py` 의 `_on_remove`: 상태별 분기 — 진행 중이면 "취소하고 제거" 문구 + 체크박스 없음, DONE+파일 존재면 "다운로드된 파일 삭제" 체크박스, 그 외엔 단순 제거 확인. `skip_confirm=True` 파라미터 추가 — `_on_info_error` / `FormatSelectDialog rejected` 같은 시스템 정리 경로는 사용자 ✕ 가 아니므로 다이얼로그 우회
  - `ui/main_window.py` 의 `_on_cancel_all` → `_on_clear_list` 재명명·재작성: 진행 중 워커 일괄 취소 + 모든 항목 제거 + (체크 시) 완료 항목의 디스크 파일까지 일괄 삭제. 본문에 진행 중 개수 M 명시, 체크박스 "다운로드된 파일들 일괄 삭제" 는 완료+파일 항목이 1개 이상일 때만 노출. 빈 목록에서 누르면 상태바 "목록이 비어 있습니다."
  - `ui/main_window.py` 의 `_build_toolbar`: 버튼 라벨 "전체 취소" → "목록 비우기", objectName `btnCancelAll` → `btnClearList`. 스타일시트 셀렉터 동기 변경
  - `ui/main_window.py` 의 `_remove_item_quiet` 신규 헬퍼: 다이얼로그 없이 위젯·dict·썸네일 워커를 정리하는 내부 루틴. `_on_clear_list` 의 루프와 `_on_remove` 의 단건 처리가 같은 정리 코드를 공유
  - 사양 근거 (요약): "전체 취소" 라는 단어가 사용자 멘탈 모델("화면 청소") 과 어긋났던 점, Yes/No 가 두 개의 서로 다른 질문을 한 축에 욱여넣고 있던 점을 해소. 자세한 합의 과정은 단기 섹션 같은 항목의 발견 메모 참조
  - 검증: 진행 중 취소/✕ 확인 동작, 완료 ✕ 의 체크박스 분기, 목록 비우기의 진행 중 카운트·체크박스 노출 조건, 빈 목록 가드, 시스템 정리 경로(`skip_confirm`) 모두 정상

- **`fix(ui)`**: 취소·에러 상태 진입 시 진행률 바를 0 으로 초기화.
  - `ui/download_item_widget.py`: `update_status` 의 `ERROR` / `CANCELLED` 분기에 `progress_bar.setValue(0)` 한 줄씩 추가. 기존엔 마지막 퍼센트(예: 37%)에 그대로 멈춰 있어 "재시도" 라벨과 시각적 모순 — yt-dlp 는 재시도 시 처음부터 받으므로 멈춘 막대는 "이어받기" 같은 잘못된 신호를 줬음

- **`feat(ux)`**: 취소·재시작·삭제 동선 정비 (잔여물 정리 + 자식 프로세스 종료 + 재시도 + 조건부 파일 삭제).
  - `workers/download_worker.py`: yt-dlp 두 후크(`progress_hook` 의 `filename`, `postprocess_hook` 의 `info_dict["filepath"]`/`__files_to_move`/`_filename`)가 알려준 모든 경로를 `_touched_files: set[str]` 에 누적. 취소·에러 종료 시 그 집합 + 각 경로의 `.part`/`.ytdl`/`.part.ytdl` 형제를 일괄 삭제. prefix 매칭 같은 추측 경로는 쓰지 않음 — yt-dlp 가 명시적으로 알려준 경로만 신뢰
  - `workers/download_worker.py`: 워커 `run()` 진입 직후 우리 프로세스의 자식 PID 집합을 `_pre_pids` 에 스냅샷. 취소·에러 종료 시 재스냅샷해 차분(=내가 도는 동안 새로 늘어난 PID) 만 `terminate()` → 5초 대기 → 남은 것 `kill()`. 동시 다운로드 환경에서 다른 워커의 자식까지 잡지 않도록 워커별 차분이 핵심. Windows 의 파일 잠금이 풀려야 잔여물 삭제가 성공하므로 자식 종료가 잔여물 삭제보다 선행
  - `core/downloader.py`: `postprocessor_hooks` 도 `_wrap_hook` 으로 감싸 머지·임베드·MoveFiles 단계에서도 `DownloadCancelled` 가 전파되도록 함. 기존엔 `progress_hooks` 만 wrap 되어 후처리 중 취소가 안 됐음
  - `ui/download_item_widget.py`: 신규 시그널 `retry_requested(item_id)`. `btn_cancel` 의 라벨·동작을 `item.status` 단일 출처로 전환(`_on_cancel_or_retry` 라우터). `ERROR` / `CANCELLED` 상태에서 버튼을 숨기지 않고 "재시도" 라벨로 노출. 활성 상태 (재)진입 시 "취소" 로 복원 + ERROR 시 빨간 글자 색 원복
  - `ui/main_window.py`: 신규 `_on_retry` — 같은 `format_id` / `ext` / `save_dir` 로 새 `DownloadWorker` 기동 (화질 다이얼로그 안 띄움). `save_path` 가 완료 시점에 파일 경로로 덮어쓰일 수 있어 config 에서 디렉터리를 다시 읽어 사용. `_on_remove` 가 DONE + 디스크 파일 존재 시 "파일도 함께 삭제하시겠습니까?" 확인 (기본값 No), 활성 워커가 살아 있으면 cancel 시그널 송신 (워커가 잔여물 정리)
  - `utils/file_utils.py`: 신규 헬퍼 `snapshot_child_pids()` / `terminate_pids(pids, grace_seconds=5.0)`. psutil 미설치 / 권한 실패 시 빈 집합 반환 → 자식 종료 로직 자체를 우회 (graceful degrade). `terminate_pids` 는 일괄 terminate → `wait_procs` 일괄 대기 → 잔존만 `kill()` 의 3 단계
  - `requirements.txt`: `psutil==6.1.0` 추가. 동시에 UTF-16 LE BOM 으로 깨져 있던 인코딩을 UTF-8 (no BOM) 로 재작성 (CLAUDE.md "PowerShell `>` 리다이렉션 함정" 의 그 케이스)
  - 검증: ① 정상 완료 후 ✕ — 파일 삭제 확인 다이얼로그 (Yes/No 양쪽 정상). ② 다운로드 중 취소 — `.part`/`.ytdl` 잔여 없음, 작업 관리자에 ffmpeg/node 좀비 없음. ③ 재시도 — 화질 다이얼로그 안 뜨고 같은 사양으로 처음부터 받음. ④ 머지 중 취소 — `postprocess_hook` wrap 덕에 즉시 끊김
  - 관련: 부록 A "학습된 교훈" 의 `Python · PySide6` / `yt-dlp` 항목 갱신 권장 (이번 커밋엔 미포함)

### 2026-05-18

- **`fix(ui)`**: 영상 길이가 항상 `0:00` 으로 표시되던 버그 해결.
  - `ui/download_item_widget.py`: `update_meta(uploader, duration)` 공개 메서드 추가. `_build_ui` 와 동일 포맷을 공유하도록 정적 헬퍼 `_format_meta` 로 단일 출처화. `update_title` 과 같은 패턴 — 라벨 갱신 + `self.item` 단일 출처 동기화
  - `ui/main_window.py`: `_on_info_fetched` 에서 `update_title` 직후 `update_meta(info.uploader, info.duration)` 호출 추가
  - 원인: 위젯 생성 시점엔 InfoWorker 가 아직 끝나기 전이라 `item.uploader=""`, `item.duration=0` 이고 `_build_ui` 가 `format_duration(0) → "0:00"` 으로 라벨을 박는다. 이후 `item.duration` 은 갱신되지만 `lbl_meta` 를 다시 그릴 경로가 없어 "  •  0:00" 으로 굳어 있었음

- **`fix(downloader)`**: HLS(SoundCloud 등) 출처에서 남은시간이 "Unknown"으로 표시되던 문제 해결.
  - `workers/download_worker.py`: 다운로드 시작 시각을 워커 상태로 보유하고, yt-dlp 의 `_eta_str` 이 비었거나 unknown placeholder(`Unknown`/`--:--`/`00:00` 등)일 때 `_percent_str` 기반 `pct` 와 측정 `elapsed` 로 ETA 를 직접 추정해 `~M:SS` 형식으로 emit. 추정값은 `~` 접두로 사용자에게 추정임을 표시
  - 원인: HLS 다운로드는 `total_bytes`/`total_bytes_estimate` 가 둘 다 없어 yt-dlp 내부 ETA 산식(`(total - downloaded) / speed`) 이 성립하지 않음. 진행률은 프래그먼트 기준으로 별도 산정돼 정상 표시되지만 ETA 만 공란/placeholder 가 됨
  - 검증: YouTube mp4(기존 정상) + SoundCloud HLS 오디오(`https://soundcloud.com/k55tixoawe96/akmu`) 양쪽에서 ETA 표시 확인
  - 관련: 부록 A "학습된 교훈" 의 `yt-dlp` 항목에 HLS ETA 부재 한 줄 추가 권장 (이번 커밋엔 미포함)

- **`fix(downloader)`**: NFC 메타데이터를 yt-dlp 의 정상 경로로 흘려보내는 구조로 재구성.
  - `core/downloader.py`: 본 다운로드 호출을 `ydl.download([url])` 에서 `ydl.process_ie_result(probed, download=True)` 로 교체. yt-dlp 의 `FFmpegMetadataPP` 가 info dict 의 `title`/`artist` 를 그대로 `-metadata` 인자로 변환하므로, 재추출 없이 우리 NFC dict 를 그대로 후처리 체인에 넘기면 NFC 가 보장된다
  - `core/downloader.py`: mp3 분기에서 `-map_metadata -1` 제거. 이 옵션이 m4a ftyp 잔재(`major_brand` 등) 를 끊는 본래 목적은 달성했으나, FFmpegMetadataPP 가 같은 ffmpeg 호출에서 박는 `-metadata title=…` 까지 함께 무효화해 ID3 TIT2 가 통째로 사라지는 부작용이 확인됨. NFC title 보존이 우선이므로 제거. major_brand 잔재는 무해한 메타 노이즈로 수용
  - 검증: m4a 의 `©nam` atom, mp3 의 TIT2 프레임 모두 NFC UTF-8 (`0xea·0xeb·0xec` 계열) / UTF-16 LE (`0x45 0xc5` 계열) 단일 코드포인트로 박힘. 자모 분리(`0xe1 0x84`) 흔적 없음
  - 관련: 부록 A "학습된 교훈" 의 `yt-dlp` / `유니코드·파일명` 항목 갱신

- **`fix(downloader)`**: 모든 오디오 추출에 NFC 메타 우회로 확장 (중간 단계, 후속 패치로 대체됨).
  - `if ext == "mp3"` 조건을 `if is_audio` 로 넓혀 m4a/wav/aac 에서도 `-metadata title=NFC값` 강제 주입을 시도. mp3 는 우연히 동작했으나 m4a 는 ffmpeg 호출 단계 분리로 인해 미적용. 이후 `process_ie_result` 경로로 근본 해결됨

- **`fix(downloader)`**: 유니코드 NFC 정규화 + MP3 컨테이너 잔재 메타 제거 1차 시도.
  - `utils/file_utils.py`: `normalize_unicode`, `normalize_info_dict` 헬퍼 추가. `sanitize_filename` 도입부에서도 NFC 적용
  - `core/info_fetcher.py`: `extract_info` 직후 info dict 전체에 NFC 적용
  - `core/downloader.py`: 사전 `extract_info(download=False)` 호출 → NFC 화 → `outtmpl` 의 title 자리를 NFC 고정 문자열로 박음. mp3 한정 `-map_metadata -1` + `-metadata title=…` 우회로 도입 (이후 `process_ie_result` 로 대체)

- **`docs(claude)`**: 코드 제시 규칙을 변경 규모 기준으로 재정의 + 터미널 명령 동반 제시 규칙 신설 + VS Code 통합 터미널 명시.

- **`docs(worklog)`**: 사이드 메모 세 건(파일명·ID3 NFC 정규화 / MP3 major_brand 잔재 / Read timed out 회복력) 단기 섹션에 기록. 학습된 교훈에 `yt-dlp` / `유니코드·파일명` 카테고리 추가.

### 2026-05-17

- **`docs(claude)`**: "새 세션 시작 방법" 섹션을 환경별 안내로 개정.
  - claude.ai 웹 채팅 / Claude Code 두 환경 분리
  - 웹 채팅에서는 본문 통째 붙여넣기 대신 GitHub raw URL 던지는 방식 채택 (Claude 가 `crawler` 로 직접 가져옴 — 진짜 HEAD 반영)
  - 로컬 미푸시 변경분 환기 규칙 명문화

- **`fix(ui)`**: 다운로드 진행률을 "N.N% 다운로드 중" 형식으로 상태 라벨에 표시.
  - `workers/download_worker.py`: postprocess 후크에서 `Merger` 후처리기만 머지로 인식하도록 좁힘. 기존엔 `ThumbnailsConvertor` 등 모든 후처리기의 `started`에서 `merging` 시그널이 발사되어, 영상 스트림 종료 직후 라벨이 "병합 중"으로 잠기고 오디오 스트림 다운로드 동안에도 그대로 고정되는 UX 버그가 있었음
  - `workers/download_worker.py`: `_output_path` 갱신을 모든 후처리기의 `finished`에서 수행하도록 변경. 체인 마지막 단계(`MoveFiles`)의 최종 경로를 반영
  - `ui/download_item_widget.py`: `update_progress` 가드 추가 — 상태가 `DOWNLOADING`일 때만 상태 라벨을 "N.N% 다운로드 중"으로 갱신
  - `ui/download_item_widget.py`: `update_status` 가 `self.item.status` 를 단일 출처로 갱신하도록 정리. `MERGING` 분기를 "병합 중" 라벨로 통일하고 ETA 자리에 박던 "병합 중..." 표기 제거
  - 진단으로 확인된 후처리 체인 순서: `ThumbnailsConvertor` → `Merger` → `Metadata` → `EmbedThumbnail` → `MoveFiles` (yt-dlp 2026.3.17 기준)

- **`docs(claude)`**: 코드 제시 규칙에 300줄 기준과 변경 지점 명시 규칙 추가.
  - 약 300줄 미만 파일은 통째로 제시, 그 이상은 함수 단위 부분 발췌
  - 파일 전체를 보낼 때는 코드 블록 바깥에 변경 지점을 한 문장으로 명시

- **`fix(utils)`**: `format_duration` float/None 안전 처리 + `strip_ansi` 헬퍼 추가.

- **`fix(ui)`**: yt-dlp 진행률 메시지의 ANSI 컬러 코드 제거.

- **`docs(claude)`**: Claude 협업 규약 3줄 추가 (소스 코드 참조 / 코드 들여쓰기 / 코드 제시 전 확인).

- **`feat(downloader)`**: 다운로드 파일에 썸네일·메타데이터 임베드 추가.
  - `EmbedThumbnail`, `FFmpegMetadata`, `FFmpegThumbnailsConvertor` (webp→jpg) 후처리기 체인 추가
  - `writethumbnail`, `embedthumbnail` 플래그 활성화
  - MP3 의 경우 `-id3v2_version 3 -write_id3v1 1` 강제 (Windows 탐색기·구형 음악 플레이어 호환)
  - 관련: ADR-001

- **`fix(ui)`**: 워커 라이프사이클, 스레드 안전성, 취소 가드 정비.
  - 썸네일 워커: QPixmap 생성을 워커 스레드 → GUI 스레드로 이동, raw bytes 만 시그널로 전달
  - `ThumbnailWorker` 시그니처에 `item_id` 추가 — 늦은 시그널이 엉뚱한 위젯에 꽂히는 사고 방지
  - `_thumb_workers` 를 list → dict 로 전환, `cancel()` 메서드 추가
  - `_on_cancel_all`: 활성 워커 사전 체크 + 확인 다이얼로그 (실수 방지)
  - `DownloadWorker`: 취소 예외를 문자열 매칭 대신 `isinstance(DownloadCancelled)` 로 판정
  - 관련: ADR-001

- **`chore`**: `.vscode/` 를 `.gitignore` 에 추가.
  - VS Code 워크스페이스 설정이 레포로 들어가는 것을 방지

- **`docs`**: 작업 로그 시스템을 Keep a Changelog + ADR 형식으로 재구조화.
  - `CLAUDE.md` 신규 작성 — 변하지 않는 프로젝트 컨텍스트
  - `WORKLOG.md` 재구조화 — Changelog 와 ADR 분리
  - 협업 모델을 Opus 4.7 단일 체계로 명시 (2026-05-17 부)

- **`docs`**: Node.js 요구사항을 README 에 명시 (yt-dlp EJS 메커니즘 설명).

- **`chore`**: 레포 URL 수정, README 본격 작성, `requirements.txt` UTF-8 정상화.
  - `utils/updater.py` 의 `GITHUB_REPO` 플레이스홀더를 `ggoyong2-ctrl/AV_Downloader` 로
  - PowerShell `>` 리다이렉션이 UTF-16 LE BOM 으로 만든 `requirements.txt` 를 UTF-8 로 재작성

- **`feat`**: 최초 푸시 (Initial commit: yt-dlp based media downloader).
  - 초기 골격은 Claude Sonnet 4.6 작업
  - `config.json` 은 gitignore 처리 (사용자별 개인 경로 포함)

---

## 3. 현재 및 다음 작업 (Current & Next)

> 진행 중인 작업과 앞으로 할 작업을 적습니다. 완료되면 위 **Changelog**로 옮기고 이 섹션에서는 삭제합니다.

### 🔵 진행 중 (In Progress)

*현재 없음.*

### 🟡 단기 (Short‑term, 1~2 세션 내)

- [x] **테스트 영상 다양화 검증** ✅ (2026-05-17 완료, ffprobe로 1·2·3 모두 확인)
  - 커스텀 썸네일이 있는 영상으로 임베드 정상 동작 확인
  - 4K/8K 영상에서 `bestvideo+bestaudio` 동작 확인 (VP9/AV1 코덱)
  - MP3 추출 시 ID3v2.3 태그가 Windows 탐색기에서 정상 표시되는지 확인
- [x] **파일명·ID3 태그 유니코드 NFC 정규화** ✅ (2026-05-18 완료, `process_ie_result` 경로로 m4a/mp3 양쪽 데이터 NFC 확정)
- [x] **`Read timed out` 회복력 — yt-dlp 재시도/타임아웃 옵션 강화** ✅ (2026-05-18 완료, `core/downloader.py` 의 `_BASE_OPTS` 로 socket_timeout/retries/fragment_retries/file_access_retries/retry_sleep_functions 적용. `fragment_retries` 는 CLI 외 경로에선 `float('inf')` 필요 — 핫픽스 `93578c3`)
- [x] **취소·재시작·삭제 동선 정비** ✅ (2026-05-27 완료, 코드는 Changelog 2026-05-27 의 `feat(ux)` 와 `fix(ui)` 두 커밋 참조)
- [x] **삭제·취소 확인 다이얼로그 통일** ✅ (2026-05-27 완료, 코드는 Changelog 2026-05-27 의 `feat(ui)` 커밋 참조)
- [x] **환경설정 다이얼로그 정비** ✅ (2026-05-28 완료, 코드는 Changelog 2026-05-27 의 `feat(ui)` 환경설정 항목 참조 — 최종 구현은 `cab59c5`)
- [x] **항목 레이아웃 단순화** ✅ (2026-05-28 완료, 코드는 Changelog 2026-05-28 의 `feat(ui)` 항목 참조 — 커밋 `8074e43`)
- [x] **동시성 제어 구현 (큐 매니저)** ✅ (2026-05-28 완료, 코드는 Changelog 2026-05-28 의 `feat(ui)` "동시성 제어 큐 매니저 도입 + MainWindow 분할" 항목 참조 — 커밋 `954152f`. 관련 ADR-003)
- [ ] **`_pick_thumbnail` 흔적 정리**
  - `core/info_fetcher.py`에서 의미 없는 공백/정렬 변경분 검토 후 정리 커밋
- [ ] **README.md 업데이트**
  - CLAUDE.md 존재 및 사용법 한 줄 추가
  - WORKLOG.md 구조 변경 사실 한 줄 추가
- [ ] **다운로드 항목 메타데이터 표시 결손**
  - 파일 크기, 해상도, 비디오 코덱/포맷, 오디오 코덱/비트레이트 등이 UI에 표시되지 않음
  - `DownloadWorker.file_size` 시그널은 정의돼 있으나 위젯 슬롯 연결이 없을 가능성 — `main_window.py` 라우팅 확인 필요
  - 해상도/코덱/비트레이트는 `FormatInfo` 에 있을 가능성이 높으나 위젯이 받지 않음 — 데이터 흐름 설계 필요
  - 발견: 2026-05-17 검증 중
- [ ] **MP3 컨테이너 잔재 메타의 *선별적* 제거 (`major_brand` 등)**
  - 1차 시도(`-map_metadata -1`) 는 ID3 TIT2 까지 함께 날리는 부작용으로 철회됨
  - FFmpegMetadataPP 의 `meta_<key>` info dict 주입 경로 또는 후처리 후 별도 ffmpeg 호출로 `major_brand` / `minor_version` / `compatible_brands` 세 키만 표적 제거
  - 우선순위 낮음 (잔재는 디코더 동작에 무해, ffprobe 에서만 보이는 메타 노이즈)
  - 발견: 2026-05-18
- [ ] **SoundCloud 출처의 `comment` 가 트랙 URL 로 자동 채워짐**
  - yt-dlp 의 `FFmpegMetadataPP` 가 `webpage_url` 을 `comment` 로 매핑. 원본 트랙 설명을 잃음
  - `parse_metadata` 또는 `info["comment"]` 사전 주입으로 회피 가능
  - 우선순위 낮음
  - 발견: 2026-05-18 (NFC 검증 중 부수 발견)

### 🟢 중기 (Mid‑term, 다음 마일스톤)

- [ ] **취소 시 부분 파일 정리**
  - `_on_cancel`/`_on_cancel_all` 에서 .part, .ytdl 임시 파일 자동 삭제
- [ ] **네트워크 재시도 로직**
  - `workers/download_worker.py` 에서 일시적 오류(타임아웃, 503 등)는 N회 자동 재시도
- [ ] **포맷 선택 UX 개선**
  - "최고 화질 (자동)"과 "최고 호환 (MP4/H.264)" 분리 (ADR‑002 후보)
- [ ] **다운로드 큐 동시성 제어**
  - 동시 다운로드 N개 제한 설정 (Preferences 항목 추가)

### 🟣 장기 (Long‑term, 백로그)

- [ ] **자동 업데이트 검증**
  - `utils/updater.py` 가 yt‑dlp 신버전 감지 시 안전하게 갱신하는지 확인
- [ ] **다국어 지원**
  - i18n 도입 (한국어/영어 기본)
- [ ] **플레이리스트 일괄 다운로드**
  - 한 URL로 N개 항목 추가
- [ ] **테마/스타일 옵션**
  - 라이트/다크/시스템 자동 전환

---

## 4. 아키텍처 결정 기록 (ADR)

> 중요한 설계 결정을 한 항목씩 기록합니다. 한번 작성된 ADR은 **수정하지 않고** 새 ADR로 대체합니다 (Superseded 표시).
> 참고: [ADR — Architectural Decision Records](https://adr.github.io/)

### ADR‑001: 썸네일 처리 — UI 미리보기와 파일 임베드의 분리

- **상태**: Accepted
- **날짜**: 2026-05-17
- **관련 커밋**: `fix(ui): worker lifecycle...`, `feat(downloader): embed thumbnail...`
- **관련 이슈**: WORKLOG 6번 (해결됨)

#### 맥락 (Context)

"썸네일이 안 보인다"는 동일한 문구가 두 개의 전혀 다른 대상을 가리키고 있었음:

1. **UI 미리보기 썸네일** — `DownloadItemWidget.lbl_thumb` QLabel에 표시되는 작업 화면 내 미리보기
2. **파일 임베드 썸네일** — 다운로드된 mp4/mp3에 메타데이터로 박혀 Windows 탐색기·플레이어 아이콘으로 노출되는 이미지

용어 혼동으로 진단·해결이 수 차례 지연됨. 두 대상은 코드 위치, 라이브러리, 스레드 모델이 완전히 다름.

#### 결정 (Decision)

두 썸네일을 **명시적으로 구분**하여 코드와 문서에 반영한다.

**UI 미리보기 (PySide6 영역)**
- `QPixmap`/`QImage`는 **반드시 GUI 스레드에서만** 생성한다.
- 워커 스레드(`ThumbnailWorker`)는 raw bytes만 시그널로 전달하고, 위젯이 GUI 스레드에서 `QPixmap.loadFromData()`로 변환한다.
- 워커 시그널은 `Qt.QueuedConnection`을 명시한다.
- 워커는 `item_id`를 함께 전달해 위젯 재사용 시 시그널 오염을 방지한다.
- `_thumb_workers`는 dict 구조로 관리하고 cancel 메서드를 제공한다.

**파일 임베드 (yt‑dlp/FFmpeg 영역)**
- yt‑dlp 옵션 `writethumbnail=True`, `embedthumbnail=True`를 설정한다.
- postprocessor 체인을 다음 순서로 구성한다:
  1. `FFmpegThumbnailsConvertor` (webp → jpg 변환)
  2. `EmbedThumbnail` (파일에 임베드)
  3. `FFmpegMetadata` (제목·업로더 등 메타데이터)
- MP3는 `-id3v2_version 3 -write_id3v1 1`로 Windows 탐색기 호환을 보장한다.
- FFmpeg/FFprobe가 PATH에 있어야 한다.

#### 결과 (Consequences)

**긍정**
- 워커 스레드에서 QPixmap을 만들던 잠재적 크래시/표시 누락이 사라짐
- 다운로드 파일이 탐색기·음악 플레이어에서 썸네일을 정상 표시
- 두 대상이 코드·문서·대화에서 분리되어 디버깅 비용 감소

**부정**
- FFmpeg 의존이 명시적으로 필요 (사용자 환경 안내 필요)
- postprocessor 체인이 길어져 다운로드 후처리 시간이 약간 증가

#### 대안 검토

- **A안 — 워커에서 QPixmap 생성 후 emit**: PySide6 규약 위반. 채택 불가.
- **B안 — `info["thumbnail"]` 신뢰 안 하고 자체 선택 로직(`_pick_thumbnail`)**: 진단 결과 yt‑dlp가 이미 maxresdefault를 정확히 반환함. 불필요한 복잡도. 채택 안 함.
- **C안(채택)**: 위 결정 참조.

---

### ADR‑002: (예약됨) 포맷 선택 — "최고 화질" 의미 분리

- **상태**: Proposed
- **날짜**: TBD

현재 "최고 화질"은 yt‑dlp의 `bestvideo+bestaudio/best`로 동작하며, YouTube의 VP9/AV1 우선 정책에 따라 H.264 1080p보다 파일이 작아질 수 있음. 사용자 혼란 방지를 위해 "최고 화질 (자동 · 효율 우선)"과 "최고 호환 (MP4/H.264)"를 분리할지 결정 필요. 추후 작성.

---

### ADR-003: 다운로드 워커 오케스트레이션을 `DownloadManager` 로 분리

- 상태: Accepted
- 날짜: 2026-05-28
- 관련 커밋: `feat(ui): 동시성 제어 큐 매니저 도입 + MainWindow 분할` (`954152f`)

#### 맥락 (Context)

환경설정 슬라이더의 `max_concurrent` 값을 실제 동시 다운로드 수 제어로 승격시키는 작업("동시성 제어 구현") 을 시작하며 `MainWindow` 의 현재 책임 부담을 확인. `MainWindow` 는 이미 ① UI 구성, ② 항목 라이프사이클(추가/제거/일괄정리), ③ 다운로드 워커 오케스트레이션, ④ 썸네일 워커 관리, ⑤ 앱 차원 부수 동작(업데이트 체크/환경설정) 다섯 책임을 짊어진 약 500 줄짜리 클래스였음. 큐 매니저 정책(`_dispatch_next` / `_refresh_waiting_labels` / `_start_worker`) 을 ③ 에 추가하면 ③ 의 무게가 한 단계 더 커지고, 다음 단기 항목인 "다운로드 항목 메타데이터 표시 결손" 이 ② 를 키울 예정이라 분할 시점을 더 늦추기 어려운 상황.

사용자가 1차 코드 제시(부분 발췌)의 가독성 문제를 지적한 것이 직접적 계기. 변경이 일곱 함수에 흩어져 부분 발췌의 이점이 사라졌고, 변경 지점이 묻혀 보였음. 단순 형식 문제가 아니라 분할이 늦었다는 신호로 해석.

#### 결정 (Decision)

다섯 책임 중 ③ 만 떼어내는 **최소 분할** 채택. 신규 패키지 `controllers/` 디렉터리에 `DownloadManager` (`QObject` 서브클래스) 를 신설하고, `MainWindow` 는 매니저에 위임만 수행.

**경계 (boundary):**
- 매니저가 책임지는 것: `DownloadWorker` 의 생성·연결·종료, `dl_workers` dict 보유, 동시성 한도 적용 (`_dispatch_next`), WAITING 순번 라벨 갱신 (`_refresh_waiting_labels`).
- 매니저가 책임지지 않는 것: `InfoWorker` (항목 라이프사이클에 묶임), `ThumbnailWorker` (큐 정책과 무관), 다이얼로그, 위젯 자체의 생성·파괴.
- `items` / `widgets` dict 는 `MainWindow` 가 단일 소유자. 매니저는 참조만 받아 읽기·순회. `ItemRegistry` 같은 추가 추상은 도입하지 않음 (이 규모에 과설계).

**시그널 정책:**
- 진행률·속도·ETA·병합 (`progress` / `speed` / `eta` / `merging`): 워커→위젯 **직접 연결** (매니저 미경유). 라이프사이클이 아니라 흐름이므로 매니저가 중계해 비용을 N 배로 늘릴 이유가 없음.
- 라이프사이클 (`finished` / `error` / `cancelled`): 워커→매니저→`MainWindow` 의 두 단 경로. 매니저가 받아 자체 시그널 (`item_done` / `item_error` / `item_cancelled`) 로 재발사. 이 경로에서 매니저가 `_dispatch_next` 를 호출해 슬롯 한 칸 풀림을 즉시 다음 항목 출발로 이어줌.

**큐 자료구조 부재:**
별도 `Queue` / `deque` 를 두지 않고 `self.items` 의 dict 순서(=삽입 순서) 를 큐로 사용. 대기 중 항목 = `status == WAITING` 인 항목. 단일 출처 원칙 유지 — 두 자료구조를 동기화하는 비용과 그 동기화가 어긋날 위험을 회피.

#### 결과 (Consequences)

- `MainWindow` 는 약 500 줄 → 약 400 줄로 감소. 워커 시그널 연결 잡음이 매니저로 이동하여 `MainWindow` 의 가독성 개선.
- 매니저는 UI 에 직접 의존하지 않음 (`widgets` 를 호출할 때는 인터페이스 메서드만 사용). 향후 단위 테스트 가능성 열림 — `widgets` 자리에 mock 을 주입하면 큐 정책만 검증 가능.
- `CLAUDE.md` 의 "폴더 구조" 섹션에 `controllers/` 디렉터리 추가 갱신 필요 (별도 `docs(claude)` 커밋으로 따라감).
- 다음에 ② 항목 라이프사이클이 커지면 (예: 항목 메타데이터 표시 확장, 항목 정렬·필터링) `ItemRegistry` 같은 추가 분할이 자연스러운 후보. 지금은 미루지만, 매니저 분리가 그 분할의 패턴을 미리 만든 셈.
- 분할이 한 커밋에 기능 추가 (`feat`) 와 묶인 점은 정직성 비용. 두 커밋으로 끊는 (a) 안과 한 커밋으로 가는 (b) 안 사이에서 응답 비용을 이유로 (b) 채택. 검증 시나리오에 "분할 회귀" (시나리오 ⑥, 새 동작이 거의 개입하지 않는 가장 단순한 시나리오 — 영상 1 개 추가 후 완료까지) 를 별도로 둬 분할 부분의 무죄 추정을 확보하는 절차로 부분 보완.

#### 대안 (Alternatives considered)

- **A. 전체 파일 통째 제시 + 분할 없음**: 변경 추적은 쉬워지지만 `MainWindow` 가 계속 비대해짐. 다음 작업에서 같은 고민을 한 번 더 하게 됨.
- **B. 다섯 책임 모두 분할 (controllers/items/workers/ui 등 전면 재배치)**: 이 규모에 과분할. 매니저 외 책임들은 분량이 작아 빼낸 후 한 파일이 다섯 줄짜리 메서드 세 개만 갖는 식이 됨.
- **C. 큐 매니저만 `MainWindow` 안의 별도 메서드 그룹으로 둠 (분할 없음)**: 1차 응답의 형태였음. 변경 가독성이 떨어지고 향후 단위 테스트 가능성이 닫힘.
- **D. refactor 와 feat 두 커밋으로 분리**: 정직하지만 응답을 두 번 끊는 비용이 두 커밋의 청결함을 능가한다고 판단해 단일 feat 로 묶음. 시나리오 ⑥ 으로 분할 회귀 검증을 따로 둠으로써 부분 보완.

---

## 부록 A. 학습된 교훈 (Lessons)

> 같은 실수를 반복하지 않기 위한 메모. 주제별로 누적합니다.

### PowerShell · Windows 환경

- `>` 리다이렉트는 기본적으로 UTF‑16 LE BOM으로 파일을 만든다. UTF‑8이 필요하면 `Out-File -Encoding utf8` 또는 `Set-Content -Encoding utf8`을 명시한다.
- `git diff`가 멈추고 `:`이 보이면 less 페이저다. `q`로 종료, `Space`로 한 페이지, `G`로 끝으로 이동. 페이저 없이 보려면 `git --no-pager diff`.
- 빈 파일의 Git SHA는 `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`.
- PowerShell `git commit -m "..."` 에서 큰따옴표 안에 큰따옴표를 넣으려고 `""` 로 이스케이프하면 빈 문자열로 해석되어 인자가 끊긴다. 큰따옴표 안에는 작은따옴표를 쓰거나, 헤더 한 줄로만 커밋하고 본문은 WORKLOG 로 빼는 게 안전하다.

### Python · PySide6

- 타입 힌트(`self.x: dict = {}`)는 어노테이션일 뿐, 변수를 자동 생성하지 않는 위치도 있다. `__init__`에서 명시적으로 초기화한다.
- `QPixmap`·`QImage`는 GUI 스레드 전용. 워커 스레드에서 만들면 표시 누락·크래시가 발생한다.
- 시그널‑슬롯은 스레드를 넘을 때 `Qt.QueuedConnection`을 명시하면 안전하다.
- `QLabel.setScaledContents(True)`는 0×0 라벨에서 빈 화면을 만들 수 있다. 직접 `scaled()` 호출이 안전하다.

### yt‑dlp

- 2025년부터 EJS(Embedded JavaScript)를 사용. Node.js/Deno/Bun 중 하나가 PATH에 있어야 함. 참고: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- `info["thumbnail"]`은 보통 정확하지만, `info["thumbnails"]` 리스트에서 직접 선별할 수도 있다.
- `bestvideo+bestaudio/best`는 코덱 효율 우선이라 H.264보다 파일이 작을 수 있다.
- `postprocess_hook` 은 ffmpeg 머지만이 아니라 **모든 후처리기**의 started/finished 를 발사한다. `d["postprocessor"]` 값으로 단계를 구분해야 한다. 2026.3.17 기준 ADR-001 체인의 순서는 `ThumbnailsConvertor` → `Merger` → `Metadata` → `EmbedThumbnail` → `MoveFiles`. 또한 postprocess 후크에는 **퍼센트 정보가 없다** (`status`/`postprocessor`/`info_dict`/`_default_template` 4개 키만 제공). 머지·임베드 단계에 퍼센트 진행률 표시는 현 구조로 불가.
- `ExtractAudio` 로 m4a→mp3 재인코딩하면 ffmpeg 가 기본 `-map_metadata 0` 으로 원본 ftyp 박스 필드(`major_brand` 등)를 ID3 의 TXXX 로 옮겨 박는다. MP3 에는 원리상 없어야 할 메타가 남는다. `-map_metadata -1` 로 끊을 수는 있으나 그러면 같은 ffmpeg 호출에서 FFmpegMetadataPP 가 박는 `-metadata title=…` 까지 함께 무효화되어 ID3 TIT2 가 사라진다. 선별 제거가 필요하면 `meta_<key>` info dict 주입 또는 별도 ffmpeg 호출 경로를 써야 한다.
- 기본 retry/timeout 은 짧다. 실서비스 GUI 에서는 `socket_timeout`, `retries`, `fragment_retries='infinite'`, `file_access_retries`, `retry_sleep_functions` 를 명시해 일시적 stall 을 내부에서 흡수시켜야 한다.
- **`ydl.download([url])` 은 내부에서 `extract_info` 를 다시 돌린다.** 우리가 호출 전에 가공한 info dict 가 있어도 무시되고 원본 NFD 메타가 그대로 후처리 체인에 흘러간다. 사전 정규화한 dict 를 유지하려면 `ydl.process_ie_result(info, download=True)` 를 써야 한다. yt-dlp 내부에서도 광범위하게 쓰이는 경로라 안정적.
- **`FFmpegMetadataPP` 는 info dict 의 `title`/`artist`/`description` 등을 직접 읽어 `-metadata` 인자로 변환한다.** 즉 메타 내용을 통제하려면 ffmpeg 인자를 우회로 박는 것보다 info dict 자체를 정규화한 뒤 `process_ie_result` 로 흘리는 것이 단순하고 견고하다. 사용자 정의 키는 `meta_<name>` 또는 `meta_<idx>_<name>` 형태로 info dict 에 박으면 우선 적용된다.
- **yt-dlp 병렬 다운로드 제한**: yt-dlp는 단일 프로세스 내 병렬 다운로드를 공식 지원하지 않는다. 사실상 안전 구간은 1~3개, 상한은 약 5개. 슬라이더·SpinBox 등 UI에서 더 큰 값을 허용하더라도 위험 구간(노랑·빨강)을 시각적으로 명시해야 사용자가 IP 차단·rate limit 위험을 인지할 수 있다. metube 기본값 3, youtube-dl-gui 한 자리 수가 업계 관행. (출처: 2026-05-27 동시 다운로드 수 UI 논의)

### 유니코드·파일명

- 유니코드 정규화는 **클라우드·OS·소스 사이트 경계에서 깨진다**. SoundCloud 의 한글 메타는 NFD(자모 분리, U+1100~U+11FF) 로 들어오는 경우가 있다. macOS 경유 클라우드 동기화도 마찬가지. 우리 앱은 **info dict 진입 지점에서 NFC 로 통일**하는 것을 원칙으로 한다 (`unicodedata.normalize('NFC', ...)`).
- **콘솔 렌더링은 NFD 를 NFC 처럼 그려낼 수 있다.** `chcp 65001` 로 cmd.exe 를 UTF-8 로 바꾸면 한글이 멀쩡히 "기쁨" 으로 보이지만, 실제로는 `ㄱ + ㅣ + ㅃ + ㅡ + ㅁ` 5개 jamo 일 수 있다. 진단할 때는 ffprobe 출력 모양에 속지 말고 실제 코드포인트를 봐야 한다 (`python -c "import sys; print([hex(ord(c)) for c in open(sys.argv[1]).read()])"` 또는 ID3 값을 파일로 떠서 hex dump).
- ID3v2.3 의 텍스트 인코딩은 UTF-16 (BOM 포함) 이 호환성 가장 높다. yt-dlp + ffmpeg 기본 동작이 이를 따르므로 우리는 별도 옵션을 줄 필요 없으나, 값으로 넘어가는 문자열은 NFC 여야 한다.
- **ffprobe JSON 출력 자체도 NFD 를 NFC 처럼 보여줄 수 있다.** `chcp 65001` + ffprobe JSON 으로 한글이 깨끗하게 보이더라도, 콘솔 폰트의 자모 결합 렌더링 결과일 뿐 데이터는 NFD 일 수 있다. 2026-05-18 디버깅 중 이 함정에 두 번 빠졌다. **NFC/NFD 판정은 반드시 파일 원본 바이트에서**: m4a 는 `©nam` atom 의 데이터 영역, mp3 는 `TIT2` 프레임의 텍스트 영역을 직접 hex 로 봐야 한다. NFC 한글 한 글자는 UTF-8 3바이트(`0xea·0xeb·0xec` 시작), NFD 는 자모별 3바이트씩 2~3개(`0xe1 0x84 …` 패턴)다.
- **표시 레이어는 모두 정직하지 않다.** Windows 탐색기 속성창은 NFD 를 분리해서 보여주고(정직), VS Code 터미널은 결합해서 그리고(NFC 처럼 보임), ffprobe JSON 도 결합해서 그린다. 같은 데이터가 어디서는 깨져 보이고 어디서는 멀쩡해 보이는 게 정상이다. 표시 어긋남으로 데이터를 추론하지 말 것.

### Git

- `.gitignore`는 **이미 추적 중인 파일에는 영향 없음**. 빼려면 `git rm --cached <path>`.
- 의미 단위로 커밋을 나누려면 `git add -p`로 hunk 단위 스테이징.
- Conventional Commits 권장: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`. 참고: https://www.conventionalcommits.org/

### 협업 · 커뮤니케이션

- **용어가 같다고 대상도 같지는 않다.** "썸네일"처럼 일상어가 두 개 이상의 기술 객체를 가리킬 때, 먼저 어느 대상인지 확정한다.
- 진단 코드(print, 임시 파일 저장)는 가설 검증 후 즉시 제거하고 커밋에 섞지 않는다.
- 가설은 한 번에 하나씩 검증한다. 동시에 여러 패치를 적용하면 원인 추적이 어려워진다.
- **단일 질문 원칙(다이얼로그 설계)**: 확인 다이얼로그는 "하나의 질문 + 부가 옵션(체크박스)" 구조가 사용자 인지 부담이 가장 낮다. 두 개의 결정을 Yes/No로 강제 묶으면 사용자가 "예"의 의미를 매번 재해석해야 한다. (출처: 2026-05-27 "삭제·취소 확인 다이얼로그 통일" 작업)
- **버튼 라벨은 동작을 진실하게 묘사해야 한다**: "전체 취소"라는 라벨이 실제로는 "진행 중인 다운로드만 취소"였기 때문에 사용자가 "목록 전체 삭제"로 오해. 라벨과 동작이 어긋나면 UX 부채가 누적되므로, 새 동작을 추가하기 전에 라벨부터 재검토할 것. (출처: 2026-05-27 "전체 취소 → 목록 비우기" 리네이밍)
