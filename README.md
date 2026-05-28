# AV Downloader

yt-dlp 기반의 영상·오디오 다운로더. YouTube를 비롯해 yt-dlp가 지원하는 1000여 개 사이트에서 동작합니다.

## 주요 기능

- 영상과 오디오(MP3) 다운로드
- 화질 선택 (자동 최고화질 / 해상도별 수동 선택)
- 진행률·속도·남은 시간 실시간 표시
- 클립보드 URL 자동 감지
- yt-dlp 자동 업데이트 확인
- 다크 테마 GUI (PySide6 기반)

## 요구 사항

- **Python 3.10 이상**
- **ffmpeg** — 영상/오디오 병합과 MP3 변환에 필요합니다. 시스템 PATH에 등록되어 있어야 합니다.
  - Windows: [공식 빌드](https://www.gyan.dev/ffmpeg/builds/) 다운로드 후 PATH 등록
  - 또는 `winget install Gyan.FFmpeg`
- **운영체제**: 현재 Windows 환경에서 검증되었습니다. macOS/Linux는 일부 기능(폴더 열기 등)이 동작하지 않을 수 있습니다.
- **Node.js** (선택, 그러나 YouTube 다운로드에는 사실상 필수) — yt-dlp가 YouTube의 자바스크립트 챌린지를 해결하기 위해 외부 JS 런타임을 요구합니다.
  - Windows: [Node.js 공식 사이트](https://nodejs.org/) 또는 `winget install OpenJS.NodeJS`
  - 자세한 내용: [yt-dlp EJS Wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS)


## 설치

```bash
git clone https://github.com/metapbl/AVD.git AV_Downloader
cd AV_Downloader

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

## 실행

```bash
python main.py
```


## 설정

첫 실행 시 사용자 홈 폴더의 `Downloads`로 저장 경로가 자동 설정됩니다. 앱 내 **⚙ 설정** 버튼에서 변경할 수 있습니다.

## 사용된 주요 라이브러리

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 영상 추출 핵심 엔진
- [PySide6](https://doc.qt.io/qtforpython-6/) — GUI 프레임워크
- [requests](https://requests.readthedocs.io/) — 썸네일·업데이트 체크

## 라이선스

MIT License. 자세한 내용은 [LICENSE](LICENSE) 파일 참조.

## 면책

이 도구는 개인적 학습과 백업 목적으로 사용하시기 바랍니다. 각 사이트의 이용약관과 저작권법을 준수하는 것은 사용자의 책임입니다.
