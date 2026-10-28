# RELEASE — 릴리스 절차 (AVD)
<!-- 근거: D011(onedir), D038(평문 gaindb·yt_dlp), D040(릴리스 게시). 빌드 스크립트는 루트 build.ps1 -->

릴리스 하나 = 태그 `v{버전}` + GitHub Release 에 zip 2개(`AVD-v{버전}-win64.zip`, `AVD-v{버전}-src.zip`). 소스 zip 은 exe 와 같은 커밋이어야 한다 (LGPL 소스 제공).
명령은 모두 리포 루트의 PowerShell 에서 실행한다. 태그·push·`gh release` 는 각각 실행 전 확인한다 (D040).

## 1. 버전 올리기
- `git fetch origin` 뒤 `git rev-list --count main..origin/main` 이 0 인지 본다. 아니면 먼저 병합한다 (GitHub 웹에서 고친 커밋이 빌드에서 빠진다)
- `gh release list --repo metapbl/AVD` 와 `git ls-remote --tags origin` 으로 이미 쓴 번호를 확인한다
- `utils/updater.py > APP_VERSION` 을 새 번호로 바꾼다 (`build.ps1` 이 여기서 zip 이름을 읽는다)

## 2. CHANGELOG
- `CHANGELOG.md` 맨 위 날짜 아래에 `chore(release)` 항목을 추가한다
- 1·2 를 한 커밋으로: `chore(release): v{버전}`. 작성자 확인 `git log -1 --format="%an <%ae>"`

## 3. 빌드
- `.\build.ps1` — 커밋 안 된 변경이 있으면 멈춘다
- 결과: `release\AVD-v{버전}-win64.zip`(안에 `AVD\` 폴더), `release\AVD-v{버전}-src.zip`
- 번들된 yt-dlp 버전을 적어 둔다 (릴리스 노트용):
  `Select-String dist\AVD\_internal\yt_dlp\version.py -Pattern '^__version__'`

## 4. 실기기 최소 확인
exe zip 을 리포 밖 새 폴더에 풀어 `AVD\AVD.exe` 로 확인한다. 하나라도 아니면 게시하지 않는다.
1. YouTube 단일 영상 다운로드 → 완료, 파일 재생됨
2. MP3 + 음량 정규화 → 완료, 태그 기록됨
3. 환경설정 저장 → `AVD.exe` 옆에 `config.json` 생김

## 5. 태그·push
- `git tag v{버전}`
- `git push origin main` → 성공했을 때만 `git push origin v{버전}` (한 줄에 `;` 로 잇지 않는다)

## 6. GitHub Release
- 게시:
  `gh release create v{버전} release\AVD-v{버전}-win64.zip release\AVD-v{버전}-src.zip --repo metapbl/AVD --title "AVD v{버전}" --notes-file {노트 파일}`
- 노트에 넣을 것: 이번 변경 요약(CHANGELOG), 번들 yt-dlp 버전, "ffmpeg/ffprobe·Node.js 는 별도 설치 — README 설치 절", `src.zip` 이 같은 커밋의 소스라는 한 줄
- 확인: `gh release view v{버전} --repo metapbl/AVD --json assets` → zip 2개
