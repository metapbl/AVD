# ui/download_item_widget.py
# 다운로드 목록에서 항목 하나를 표시하는 위젯

import html

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QProgressBar, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFontMetrics
from models.download_item import DownloadItem, DownloadStatus
from utils.file_utils import format_duration, open_folder


# ── 자동 선택 포맷 식별자 ────────────────────────────
# core/info_fetcher.py 의 _parse_formats 가 통합 포맷에 박는 format_id.
# 메타 라벨·다이얼로그가 이 값을 보면 코덱/비트레이트 대신 "자동" 으로 표시.
# 단일 출처 — 여기 값이 바뀌면 info_fetcher 의 통합 포맷 진입 부분도 같이 바꿀 것.
AUTO_FORMAT_ID = "bestvideo+bestaudio/best"


# ── 코덱 정규화 매핑 ─────────────────────────────────
# yt-dlp 의 raw vcodec/acodec 문자열을 사람 친화 이름으로 옮기는 매핑.
# 모듈 최상위에 두어 FormatSelectDialog 등 다른 위젯에서도 재사용 가능.
# 매칭 규칙: raw 문자열을 소문자화한 뒤 (a) 정확 일치, (b) 접두사 일치 순으로
# 검사한다. avc1.640028 / vp09.00.40.08 / mp4a.40.2 같은 점 포함 식별자를
# 접두사 매칭으로 한 번에 처리.

_VCODEC_PREFIX_MAP = {
    "avc1": "H.264",
    "h264": "H.264",
    "vp09": "VP9",
    "vp9" : "VP9",
    "av01": "AV1",
    "av1" : "AV1",
    "hev1": "H.265",
    "hvc1": "H.265",
    "h265": "H.265",
    "hevc": "H.265",
}

_ACODEC_PREFIX_MAP = {
    "mp4a"  : "AAC",
    "aac"   : "AAC",
    "opus"  : "Opus",
    "mp3"   : "MP3",
    "vorbis": "Vorbis",
    "flac"  : "FLAC",
    "ec-3"  : "EAC3",
    "eac3"  : "EAC3",
    "ac-3"  : "AC3",
    "ac3"   : "AC3",
}


def humanize_codec(raw: str, kind: str) -> str:
    """
    raw vcodec/acodec 문자열을 사람 친화 이름으로 정규화.

    kind: "video" 또는 "audio". 빈값/"none"/미매칭이면 빈 문자열을 돌려
    표시 단계에서 해당 세그먼트를 통째로 생략하게 한다.

    매칭 규칙: 소문자화 → 접두사 우선 일치. avc1.640028 같은 점 포함
    문자열도 "avc1" 접두사로 잡힌다.
    """
    if not raw:
        return ""
    s = raw.strip().lower()
    if not s or s == "none":
        return ""

    mapping = _VCODEC_PREFIX_MAP if kind == "video" else _ACODEC_PREFIX_MAP
    for prefix, name in mapping.items():
        if s == prefix or s.startswith(prefix):
            return name
    return ""


def format_bitrate(abr: float, tbr: float) -> str:
    """
    오디오 비트레이트를 "192kbps" 형식 문자열로 만든다.
    abr 우선, 없으면 tbr 사용. 둘 다 0/없음이면 빈 문자열.
    소수점은 반올림해 정수 kbps 로 표기 — 사용자에게 보일 정밀도가 아니다.
    """
    rate = abr if abr and abr > 0 else (tbr if tbr and tbr > 0 else 0.0)
    if rate <= 0:
        return ""
    return f"{int(round(rate))}kbps"


def format_codec_segment(
    vcodec: str, acodec: str, ext: str,
    abr: float, tbr: float,
    is_audio: bool,
) -> str:
    """
    메타 라벨·다이얼로그 행에 들어갈 코덱·포맷·비트레이트 세그먼트를 만든다.

    반환 형식:
    - 영상 (is_audio=False):
        "H.264 MP4 • AAC 192kbps"  (모두 있을 때)
        "H.264 MP4 • AAC"          (비트레이트 없음)
        "H.264 MP4"                (오디오 정보 없음)
        "MP4"                      (vcodec 도 미확정 — 거의 없음)
        ""                         (전부 미확정 — 호출 측이 "자동" 폴백)
    - 오디오 (is_audio=True):
        "MP3 320kbps"  /  "MP3"  /  ""

    빈 문자열을 반환하는 경우 호출 측에서 "자동" 등 폴백을 결정한다.
    """
    v_name = humanize_codec(vcodec, "video")
    a_name = humanize_codec(acodec, "audio")
    ext_up = (ext or "").upper()
    bitrate = format_bitrate(abr, tbr)

    if is_audio:
        # 오디오 전용: "MP3 320kbps" 또는 "MP3"
        # acodec 이 없으면 ext 로 폴백 (MP3 항목의 acodec="mp3" 가 누락된 경우)
        name = a_name or ext_up
        if not name:
            return ""
        if bitrate:
            return f"{name} {bitrate}"
        return name

    # 영상: "H.264 MP4 • AAC 192kbps"
    # 비디오 세그먼트
    video_seg = ""
    if v_name and ext_up:
        video_seg = f"{v_name} {ext_up}"
    elif v_name:
        video_seg = v_name
    elif ext_up:
        video_seg = ext_up

    # 오디오 세그먼트 (acodec 가 있을 때만 — 미확정이면 통째로 생략)
    audio_seg = ""
    if a_name:
        audio_seg = f"{a_name} {bitrate}" if bitrate else a_name

    if video_seg and audio_seg:
        return f"{video_seg}  •  {audio_seg}"
    return video_seg or audio_seg


class DownloadItemWidget(QWidget):
    """
    다운로드 항목 하나를 표시하는 위젯

    시그널:
        cancel_requested  : 취소 버튼 클릭 시 (라벨이 "취소" 일 때)
        retry_requested   : 재시도 버튼 클릭 시 (라벨이 "재시도" 일 때 — ERROR/CANCELLED)
        open_requested    : 폴더 열기 버튼 클릭 시
        remove_requested  : 항목 삭제 버튼 클릭 시

    레이아웃 사양 (2026-05-28 합의):
        - 썸네일 120×80
        - 위젯 전체 fixed height 96 (썸네일 80 + 상하 마진 8+8)
        - 우측 4행은 썸네일 80px 안에 욱여넣음:
            제목 26 + 메타 16 + 진행률 16 + 상태행 16 = 74
            + info_layout.spacing 2 × 3 = 6
            = 80 ✅
        - 진행률 바 두께 16 (행 높이와 동일 — 별도 래퍼 불필요)
        - 균등 분배(stretch=1)는 쓰지 않음. 행별 setFixedHeight 로 결정론적 배치.
    """

    cancel_requested = Signal(str)  # item_id 전달
    retry_requested  = Signal(str)  # item_id 전달 — ERROR / CANCELLED 상태에서 재시도
    open_requested   = Signal(str)  # item_id 전달
    remove_requested = Signal(str)  # item_id 전달

    def __init__(self, item: DownloadItem, parent=None):
        super().__init__(parent)
        self.item = item
        # 확장자 표시 가드:
        # 화질 선택 전엔 확장자가 확정되지 않았으므로 제목 라벨에 섞지 않는다.
        # MainWindow._on_format_selected 가 update_ext 를 부른 뒤에야 True 가 된다.
        self._ext_known: bool = False
        self._ext: str = ""

        # 메타 라벨의 코덱·비트레이트 세그먼트 단일 출처.
        # 화질 선택 전엔 모두 빈 값/0 → _format_meta 가 코덱 세그먼트를 생략.
        # _on_format_selected 가 update_format_meta 로 채운 뒤부터 표시된다.
        # _fmt_chosen 은 "사용자가 한 번이라도 포맷을 골랐는가" 의 표식.
        # _fmt_format_id 는 통합 포맷("자동 선택") 판별 단일 출처 — 코덱이
        # 빈 값이어도 이 값이 AUTO_FORMAT_ID 면 "자동" 으로 표시.
        self._fmt_chosen    : bool  = False
        self._fmt_format_id : str   = ""
        self._fmt_vcodec    : str   = ""
        self._fmt_acodec    : str   = ""
        self._fmt_ext       : str   = ""
        self._fmt_abr       : float = 0.0
        self._fmt_tbr       : float = 0.0
        self._fmt_is_audio  : bool  = False

        self.setFixedHeight(96)  # 썸네일 80 + 상하 마진 8+8
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        """UI 구성"""

        # 전체 가로 레이아웃
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(12)

        # ── 썸네일 영역 ──
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(120, 80)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setStyleSheet(
            "background:#1e1e1e; border-radius:4px;"
        )
        self.lbl_thumb.setText("🎬")
        root.addWidget(self.lbl_thumb)

        # ── 정보 + 진행률 영역 ──
        # 4행 행별 고정 높이로 썸네일 80px 안에 욱여넣는다.
        # spacing 2 × 3 간격 = 6px, 라벨 예산 80-6=74px,
        # 제목 26 + 메타 16 + 진행률 16 + 상태행 16 = 74 ✅
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 제목 — 긴 제목이 우측 버튼 컬럼을 윈도우 밖으로 밀어내지 않도록
        # 가로 sizeHint 권리를 포기시킨다(Ignored). 실제 텍스트 잘라내기는
        # resizeEvent → _apply_title_elide 에서 QFontMetrics 로 처리.
        # 원본 제목은 self.item.title 단일 출처에서 항상 다시 가져온다.
        # RichText 모드 — 확장자만 노란색으로 강조하기 위해 HTML 사용.
        self.lbl_title = QLabel(self.item.title)
        self.lbl_title.setObjectName("itemTitle")
        self.lbl_title.setWordWrap(False)
        self.lbl_title.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_title.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.lbl_title.setFixedHeight(26)
        info_layout.addWidget(self.lbl_title)

        # 업로더 + 재생시간 (+ 코덱·포맷·비트레이트) — 위젯 생성 시점엔
        # 업로더/재생시간만 들어가고, _on_format_selected 가 update_format_meta
        # 를 부른 뒤부터 코덱 세그먼트가 추가된다.
        self.lbl_meta = QLabel(self._build_meta_text())
        self.lbl_meta.setObjectName("itemMeta")
        self.lbl_meta.setFixedHeight(16)
        info_layout.addWidget(self.lbl_meta)

        # 진행률 바 — 두께 16 으로 행 자체의 높이와 동일하게.
        # 별도 래퍼 레이아웃 없이 바 자체가 행이 된다.
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setTextVisible(False)
        info_layout.addWidget(self.progress_bar)

        # 상태 + 속도 + 남은시간 + 크기
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_status = QLabel(self.item.status.value)
        self.lbl_status.setObjectName("itemStatus")
        self.lbl_status.setFixedHeight(16)
        self.lbl_speed  = QLabel("")
        self.lbl_speed.setObjectName("itemMeta")
        self.lbl_speed.setFixedHeight(16)
        self.lbl_eta    = QLabel("")
        self.lbl_eta.setObjectName("itemMeta")
        self.lbl_eta.setFixedHeight(16)
        # 크기 라벨 — "48.20 / 128.50 MiB" 형식. DownloadWorker.file_size 가
        # 매니저를 경유해 update_file_size 로 들어온다.
        self.lbl_size   = QLabel("")
        self.lbl_size.setObjectName("itemMeta")
        self.lbl_size.setFixedHeight(16)
        status_row.addWidget(self.lbl_status)
        status_row.addStretch()
        status_row.addWidget(self.lbl_speed)
        status_row.addSpacing(12)
        status_row.addWidget(self.lbl_eta)
        status_row.addSpacing(12)
        status_row.addWidget(self.lbl_size)
        info_layout.addLayout(status_row)

        root.addLayout(info_layout, stretch=1)

        # ── 버튼 영역 ──
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        # 취소/재시도 버튼 — 같은 버튼을 상태에 따라 라벨·동작 전환.
        # 라우터 메서드(_on_cancel_or_retry) 가 item.status 를 보고
        # cancel_requested / retry_requested 중 하나를 발사한다.
        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setFixedWidth(60)
        self.btn_cancel.clicked.connect(self._on_cancel_or_retry)
        btn_layout.addWidget(self.btn_cancel)

        # 폴더 열기 버튼 (완료 후 표시)
        self.btn_open = QPushButton("📂 열기")
        self.btn_open.setObjectName("btnOpen")
        self.btn_open.setFixedWidth(60)
        self.btn_open.setVisible(False)
        self.btn_open.clicked.connect(
            lambda: self.open_requested.emit(self.item.item_id)
        )
        btn_layout.addWidget(self.btn_open)

        # 삭제 버튼
        self.btn_remove = QPushButton("✕")
        self.btn_remove.setObjectName("btnRemove")
        self.btn_remove.setFixedWidth(60)
        self.btn_remove.clicked.connect(
            lambda: self.remove_requested.emit(self.item.item_id)
        )
        btn_layout.addWidget(self.btn_remove)

        btn_layout.addStretch()
        root.addLayout(btn_layout)

    def _apply_style(self):
        """위젯 스타일 적용"""
        self.setStyleSheet("""
            DownloadItemWidget {
                background: #2b2b2b;
                border-radius: 8px;
                border: 1px solid #3a3a3a;
            }
            QLabel#itemTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#itemMeta {
                color: #888888;
                font-size: 11px;
            }
            QLabel#itemStatus {
                color: #4a90d9;
                font-size: 11px;
            }
            QProgressBar {
                background: #3c3c3c;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: #4a90d9;
                border-radius: 3px;
            }
            QPushButton#btnCancel {
                background: #555;
                color: #fff;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton#btnCancel:hover { background: #e05555; }
            QPushButton#btnOpen {
                background: #4a90d9;
                color: #fff;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton#btnOpen:hover { background: #5aa0e9; }
            QPushButton#btnRemove {
                background: #444;
                color: #aaa;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton#btnRemove:hover { background: #e05555; color: #fff; }
        """)

    # ── 사적 포맷 헬퍼 ───────────────────────────────

    def _build_meta_text(self) -> str:
        """
        lbl_meta 라벨에 들어갈 전체 문자열을 만든다.

        구성 단위는 두 단계:
        1. "업로더  •  재생시간"      — 항상 표시 (위젯 생성 직후부터)
        2. " • 코덱·포맷·비트레이트"  — 화질 선택 이후만 표시.
           통합 포맷(AUTO_FORMAT_ID) 은 코덱이 미확정이므로 "자동" 으로 표시.
           단, 사후 갱신(update_format_meta_resolved) 이 들어와 _fmt_format_id
           가 빈 값으로 바뀌면 실제 코덱 세그먼트가 그려진다.

        update_meta / update_format_meta / update_format_meta_resolved 가
        단일 출처 (self.item.uploader/duration, self._fmt_*) 를 갱신한 뒤
        이 헬퍼를 호출해 라벨을 다시 박는다.
        """
        base = (
            f"{self.item.uploader}  •  {format_duration(self.item.duration)}"
        )

        # 화질 선택 전 — 코덱 세그먼트 없음
        if not self._fmt_chosen:
            return base

        # 통합 포맷("최고 화질 자동 선택") — 코덱 미확정. 무조건 "자동".
        # 이 분기를 segment 폴백보다 앞에 두는 이유: 통합 포맷은 ext="mp4"
        # 가 박혀 있어 segment 가 "MP4" 를 반환하는데, 그러면 "자동" 폴백이
        # 작동하지 않기 때문. format_id 단일 출처로 명확히 식별한다.
        # 사후 갱신(update_format_meta_resolved) 이 _fmt_format_id 를 비우면
        # 여기 분기를 빠져나가 아래 segment 가 그려진다.
        if self._fmt_format_id == AUTO_FORMAT_ID:
            return f"{base}  •  자동"

        seg = format_codec_segment(
            vcodec   = self._fmt_vcodec,
            acodec   = self._fmt_acodec,
            ext      = self._fmt_ext,
            abr      = self._fmt_abr,
            tbr      = self._fmt_tbr,
            is_audio = self._fmt_is_audio,
        )
        if not seg:
            # 코덱이 모두 비어 있는 비통합 포맷 — 거의 없겠지만 안전망.
            seg = "자동"
        return f"{base}  •  {seg}"

    # ── 제목 엘라이드 ─────────────────────────────────

    def _apply_title_elide(self):
        """
        lbl_title 의 현재 폭에 맞춰 제목 + (선택된) 확장자를 RichText 로
        조립해 다시 박는다. 원본 제목은 self.item.title 단일 출처, 확장자는
        self._ext (update_ext 가 채움) 단일 출처에서 매번 다시 가져온다.

        호출 지점:
        - resizeEvent: 항목 폭이 바뀔 때마다 다시 잘라 박는다
        - update_title: 제목 자체가 갱신되어 단일 출처가 바뀌었을 때
        - update_ext: 화질 선택으로 확장자가 확정되었을 때

        표시 규칙:
        - 확장자 미확정(self._ext_known is False) — 제목만 표시. RichText
          모드이므로 HTML 이스케이프는 그대로 적용한다.
        - 확장자 확정 + 잘림 없음 — "제목.mp4" (공백 없이 부착)
        - 확장자 확정 + 잘림 발생 — "제목… .mp4" (Qt 기본 줄임표 + 공백 1 + 확장자)
        - 확장자는 항상 잘리지 않는다. 가용 폭에서 확장자 부분 폭을 먼저
          빼고 제목만 elidedText 한다.
        """
        fm = QFontMetrics(self.lbl_title.font())
        avail = self.lbl_title.width()

        # 라벨 폭이 아직 0 일 수 있는 첫 paint 직전 케이스 — 그땐 원본 그대로.
        # 이후 resizeEvent 가 진짜 폭으로 다시 호출한다. RichText 모드이므로
        # HTML 이스케이프는 적용해서 박아 둔다.
        if avail <= 0:
            self.lbl_title.setText(html.escape(self.item.title))
            return

        title = self.item.title

        # 확장자 미확정 — 제목만 elide 해서 박는다.
        if not self._ext_known or not self._ext:
            elided = fm.elidedText(
                title, Qt.TextElideMode.ElideRight, avail
            )
            self.lbl_title.setText(html.escape(elided))
            return

        # 확장자 확정 — 두 가지 부착 문자열을 후보로 두고 잘림 여부에 따라 선택.
        # 잘림 없을 때: ".mp4"  (공백 없이)
        # 잘림 있을 때: " .mp4" (Qt 기본 줄임표 U+2026 뒤 공백 1 + 점 + 확장자)
        ext_no_gap   = f".{self._ext}"
        ext_with_gap = f" .{self._ext}"

        # 잘림 여부를 판정하려면 일단 잘림 없을 때 기준으로 제목 elide 를 한 번 해 본다.
        # 가용 폭에서 ".ext" 폭을 뺀 영역에 제목 전체가 들어가면 잘림 없음 확정.
        budget_no_gap = avail - fm.horizontalAdvance(ext_no_gap)
        if budget_no_gap < 0:
            budget_no_gap = 0
        elided_try = fm.elidedText(
            title, Qt.TextElideMode.ElideRight, budget_no_gap
        )

        if elided_try == title:
            # 잘림 없음 — 공백 없이 ".mp4" 부착
            title_html = html.escape(title)
            ext_html   = html.escape(ext_no_gap)
        else:
            # 잘림 발생 — " .mp4" 부착. 가용 폭에서 " .ext" 폭을 빼고 다시 elide.
            budget_with_gap = avail - fm.horizontalAdvance(ext_with_gap)
            if budget_with_gap < 0:
                budget_with_gap = 0
            elided = fm.elidedText(
                title, Qt.TextElideMode.ElideRight, budget_with_gap
            )
            title_html = html.escape(elided)
            ext_html   = html.escape(ext_with_gap)

        # 확장자만 #ffd060 (노란빛) 으로 강조. 굵기·크기는 라벨 기본을 따른다.
        self.lbl_title.setText(
            f'{title_html}'
            f'<span style="color:#ffd060;">{ext_html}</span>'
        )

    def resizeEvent(self, event):
        """
        항목 폭이 바뀌면 제목 엘라이드를 다시 적용.
        Qt 의 QLabel 은 자동 엘라이드를 제공하지 않으므로 직접 처리.
        """
        super().resizeEvent(event)
        self._apply_title_elide()

    # ── 버튼 라우터 ───────────────────────────────────

    def _on_cancel_or_retry(self):
        """
        btn_cancel 의 라우터.

        같은 버튼을 라벨에 따라 두 가지 동작으로 쓴다 — "취소" / "재시도".
        판단 기준은 라벨 텍스트가 아니라 self.item.status (단일 출처).
        라벨은 표시일 뿐이며 update_status 에서 상태에 맞춰 갱신된다.
        """
        if self.item.status in (DownloadStatus.ERROR, DownloadStatus.CANCELLED):
            self.retry_requested.emit(self.item.item_id)
        else:
            self.cancel_requested.emit(self.item.item_id)

    # ── 외부에서 호출하는 업데이트 메서드 ──

    def update_progress(self, pct: float):
        """
        진행률 바 업데이트.
        다운로드 단계에서는 상태 라벨도 "38.5% 다운로드 중" 형식으로 함께 갱신.
        병합 등 다른 단계에서 들어오는 progress 시그널은 라벨을 덮지 않는다.

        비활성 상태(DONE/ERROR/CANCELLED/WAITING) 진입 후 큐에 남아 있던
        progress 시그널이 0/100 막대를 다시 박는 것을 막는다. 재시도 직전
        잠시 WAITING 으로 떨어진 항목의 막대가 흔들리지 않도록 WAITING 도
        가드 대상.
        """
        if self.item.status in (
            DownloadStatus.DONE,
            DownloadStatus.ERROR,
            DownloadStatus.CANCELLED,
            DownloadStatus.WAITING,
        ):
            return

        self.progress_bar.setValue(int(pct))

        if self.item.status == DownloadStatus.DOWNLOADING:
            self.lbl_status.setText(f"{pct:.1f}% 다운로드 중")

    def update_speed(self, speed: str):
        """
        속도 레이블 업데이트.

        활성 다운로드 단계(DOWNLOADING) 에서만 표시. 병합·완료·에러·취소
        진입 후 늦게 도착한 speed 시그널이 빈 라벨을 다시 채우는 잔재를 막는다.
        """
        if self.item.status != DownloadStatus.DOWNLOADING:
            return
        self.lbl_speed.setText(speed)

    def update_eta(self, eta: str):
        """
        남은시간 레이블 업데이트.

        활성 다운로드 단계(DOWNLOADING) 에서만 표시. update_status 가
        MERGING/DONE/ERROR/CANCELLED 진입 시 라벨을 비우는데, 그 직후 큐에
        남아 있던 eta 시그널 한두 개가 도착해 잔재 "남은시간 0:42" 를 다시
        박는 경우가 있다. 상태 게이트로 차단.

        워커가 status="finished" 시점에 빈 문자열로 명시적 클리어를 보낼
        수 있다. 그때는 "남은시간 " 접두사가 단독으로 남지 않도록 라벨을
        깔끔히 비운다.
        """
        if self.item.status != DownloadStatus.DOWNLOADING:
            return
        if not eta:
            self.lbl_eta.setText("")
            return
        self.lbl_eta.setText(f"남은시간 {eta}")

    def update_file_size(self, size: str):
        """
        파일 크기 라벨 업데이트.

        DownloadWorker 가 "48.20 / 128.50 MiB" 또는 "128.50 MiB" 같은 합성
        문자열로 emit. 빈 문자열이면 라벨을 지운다 (초기 한 틱이나 HLS 같이
        크기 정보가 없는 경우). 활성 다운로드 단계에서만 반영 — 병합·완료
        진입 후 잔재 시그널이 라벨을 되살리는 것을 막는다.
        """
        if self.item.status != DownloadStatus.DOWNLOADING:
            return
        self.lbl_size.setText(size or "")

    def update_status(self, status: DownloadStatus):
        """
        상태 레이블 + 버튼 라벨 업데이트.

        버튼 전환 규약:
        - WAITING   : 취소·열기 모두 숨김. ✕ 만 노출 — 큐 대기 중에는 취소할
                      워커가 없으므로 "취소" 버튼은 거짓말이 된다. 큐에서 빼는
                      동작은 ✕ 단일 경로로 통일.
        - DONE      : 취소/재시도 숨김, "열기" 노출
        - ERROR     : "재시도" 라벨, 가시
        - CANCELLED : "재시도" 라벨, 가시 (사용자 취소도 재시도 가능)
        - 그 외(FETCHING/DOWNLOADING/MERGING) : "취소" 라벨로 복원

        status 라벨의 ERROR 시 빨간색은 활성 상태 (재)진입 시 원복한다.
        ERROR / CANCELLED 시에는 진행률 바도 0 으로 초기화.
        """
        # 단일 출처 동기화 — 이후 update_progress 의 가드가 올바로 동작하도록
        self.item.status = status

        self.lbl_status.setText(status.value)
        # 활성 상태로 (재)진입할 때 ERROR 시 적용된 빨간 색을 원복
        self.lbl_status.setStyleSheet("")

        if status == DownloadStatus.WAITING:
            # 큐 대기 — 취소·열기 모두 숨김, ✕ 만 노출.
            # 순번 라벨("대기 중 (N번째)") 은 MainWindow 가 dispatch 직후
            # update_waiting_position 으로 주입한다. 그때까지는 enum 의
            # 기본 라벨("대기중") 이 표시된다.
            self.btn_cancel.setVisible(False)
            self.btn_open.setVisible(False)
            self.progress_bar.setValue(0)
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")
            self.lbl_size.setText("")

        elif status == DownloadStatus.DONE:
            # 완료 시 — 취소/재시도 자리 숨기고 "열기" 노출
            self.btn_cancel.setVisible(False)
            self.btn_open.setVisible(True)
            self.progress_bar.setValue(100)
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")
            self.lbl_size.setText("")

        elif status == DownloadStatus.ERROR:
            # 에러 — 버튼을 "재시도" 라벨로 전환 (숨기지 않음)
            self.btn_cancel.setText("재시도")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)
            self.lbl_status.setStyleSheet("color: #e05555;")
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")
            self.lbl_size.setText("")
            self.progress_bar.setValue(0)

        elif status == DownloadStatus.CANCELLED:
            # 사용자 취소 — 에러와 동일하게 재시도 가능
            self.btn_cancel.setText("재시도")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")
            self.lbl_size.setText("")
            self.progress_bar.setValue(0)

        elif status == DownloadStatus.MERGING:
            # 병합 단계: 상태 자리에 "병합 중" 표기, 속도/ETA/크기 자리는 비움.
            self.lbl_status.setText("병합 중")
            self.lbl_speed.setText("")
            self.lbl_eta.setText("")
            self.lbl_size.setText("")
            # 활성 상태이므로 라벨은 "취소" 로 복원
            self.btn_cancel.setText("취소")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)

        else:
            # FETCHING / DOWNLOADING — 활성 상태.
            # 이전에 ERROR/CANCELLED 였다가 재시도로 돌아온 경우를 위해
            # "취소" 로 라벨 복원 + 열기 버튼 숨김.
            self.btn_cancel.setText("취소")
            self.btn_cancel.setVisible(True)
            self.btn_open.setVisible(False)

    def update_waiting_position(self, n: int):
        """
        큐 대기 순번 갱신.

        MainWindow._refresh_waiting_labels 가 dispatch 직후 호출.
        N 은 WAITING 항목들 사이의 순번(진행 중 항목은 카운트하지 않음).
        N == 1 이면 "다음에 출발할 항목" 의 의미.

        상태가 WAITING 이 아닐 때 호출되면 무시한다 — 경계 케이스 방어
        (dispatch 와 status 전이 사이의 짧은 시간 차).
        """
        if self.item.status != DownloadStatus.WAITING:
            return
        self.lbl_status.setText(f"대기 중 ({n}번째)")

    def update_title(self, title: str):
        """제목 레이블 업데이트"""
        self.item.title = title
        # _apply_title_elide 가 self.item.title 단일 출처에서 다시 조립하므로
        # 여기서 lbl_title 에 직접 setText 할 필요는 없다.
        self._apply_title_elide()

    def update_ext(self, ext: str):
        """
        파일 확장자 표시 갱신.

        화질 선택이 끝나 항목의 ext 가 확정되면 MainWindow._on_format_selected
        가 호출한다. 호출 후부터 lbl_title 의 우측 끝에 ".ext" 가 노란빛
        (#ffd060) 으로 표시되며, 폭이 좁아 잘릴 때도 확장자는 잘리지 않고
        제목만 줄임표 처리된다.

        ext 는 점 없이 ("mp4", "webm" 등) 받는다.
        """
        self._ext = (ext or "").lstrip(".")
        self._ext_known = bool(self._ext)
        self._apply_title_elide()

    def update_meta(self, uploader: str, duration: int):
        """
        업로더·재생시간 레이블 업데이트.

        위젯 생성 시점에는 InfoWorker 가 아직 끝나지 않아 uploader/duration
        이 빈 값이거나 0 이다. _build_ui 가 박은 초기 "  •  0:00" 라벨을
        InfoWorker 완료 후 이 메서드로 덮어쓴다. update_title 과 같은 패턴
        — 라벨 갱신 + 단일 출처(self.item) 동기화.

        코덱 세그먼트(self._fmt_*) 는 update_format_meta 가 별도로 관리하며
        여기서는 건드리지 않는다. _build_meta_text 가 두 출처를 합쳐 라벨을
        조립한다.
        """
        self.item.uploader = uploader
        self.item.duration = duration
        self.lbl_meta.setText(self._build_meta_text())

    def update_format_meta(
        self,
        format_id: str,
        vcodec: str,
        acodec: str,
        ext: str,
        abr: float,
        tbr: float,
        is_audio: bool,
    ):
        """
        화질 선택 후 코덱·포맷·비트레이트 정보를 메타 라벨에 반영.

        MainWindow._on_format_selected 가 FormatInfo 의 raw 필드를 그대로
        넘긴다. 정규화·생략 판정은 _build_meta_text → format_codec_segment
        에서 일괄 처리.

        format_id 는 통합 포맷("자동 선택") 식별 단일 출처. AUTO_FORMAT_ID
        와 일치하면 _build_meta_text 가 코덱 세그먼트 대신 "자동" 으로 표시.
        다운로드가 시작되어 사후 갱신(update_format_meta_resolved) 이 들어오면
        _fmt_format_id 가 빈 값으로 바뀌어 실제 코덱 세그먼트가 그려진다.
        """
        self._fmt_chosen    = True
        self._fmt_format_id = format_id or ""
        self._fmt_vcodec    = vcodec or ""
        self._fmt_acodec    = acodec or ""
        self._fmt_ext       = ext or ""
        self._fmt_abr       = abr or 0.0
        self._fmt_tbr       = tbr or 0.0
        self._fmt_is_audio  = bool(is_audio)
        self.lbl_meta.setText(self._build_meta_text())

    def update_format_meta_resolved(
        self,
        vcodec: str,
        acodec: str,
        ext: str,
        abr: float,
        tbr: float,
    ):
        """
        다운로드/후처리 진행 중 yt-dlp 가 확정한 코덱·비트레이트로 메타 라벨을
        사후 갱신.

        DownloadWorker.codec_info_resolved 시그널에 연결되어 호출. 같은
        다운로드에서 여러 번 호출될 수 있고 마지막 호출의 값이 최종 진실.

        정책:
        - 화질 선택 전(_fmt_chosen=False) 호출은 무시 — 사용자 의도가 박혀
          있지 않은 상태의 라벨 변경 방지.
        - 오디오 전용(self._fmt_is_audio=True) 항목은 사후 갱신 거부 —
          info_dict 의 acodec/abr 은 ffmpeg 재인코딩 전 원본 트랙 값이라
          "MP3 192kbps" 가 "Opus 160kbps" 같은 거짓으로 덮이는 사고를 막는다.
          MP3 의 진실은 core/downloader.py 의 MP3_BITRATE_KBPS 단일 출처.
        - 통합 포맷("자동") 도, 수동 선택도 모두 갱신 대상. 통합 포맷은
          _fmt_format_id 를 빈 값으로 바꿔 _build_meta_text 의 "자동" 분기를
          빠져나오게 한다.
        - vcodec/acodec 둘 다 비어 들어오면 무시 (의미 없는 갱신).
        """
        if not self._fmt_chosen:
            return
        if self._fmt_is_audio:
            return

        v = (vcodec or "").strip()
        a = (acodec or "").strip()
        # 둘 다 비거나 "none" 이면 의미 없음 — 직전 표시 유지
        if (not v or v == "none") and (not a or a == "none"):
            return

        # 통합 포맷이었다면 "자동" 분기에서 빠져나오게 format_id 를 비운다.
        # 수동 선택은 원래 빈 값이거나 다른 format_id 라 분기 변화 없음.
        self._fmt_format_id = ""

        # 새 정보로 덮어쓴다. vcodec/acodec 중 한쪽이 비어 들어오면 기존 값
        # 유지 (예: vcodec 만 들어오는 비디오-only fragment 경계 케이스).
        if v and v != "none":
            self._fmt_vcodec = v
        if a and a != "none":
            self._fmt_acodec = a
        if ext:
            self._fmt_ext = ext
        if abr and abr > 0:
            self._fmt_abr = float(abr)
        if tbr and tbr > 0:
            self._fmt_tbr = float(tbr)

        self.lbl_meta.setText(self._build_meta_text())

    def update_thumbnail(self, data: bytes):
        """
        썸네일 이미지 업데이트.

        v7 변경: QPixmap 인자 → bytes 인자.
        QPixmap 생성·디코드를 이 메서드(GUI 스레드) 안에서 수행한다.
        워커 스레드에서 만든 QPixmap 은 paint engine 에서 빈 텍스처로
        그려지는 버그가 있어 GUI 스레드 단독 생성이 필수.
        """
        if not data:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            # 디코드 실패 — 라벨은 기본 이모지 유지
            return

        # 라벨의 실제 크기 사용. 초기 0x0 회피용으로 fixed size fallback.
        target_w = self.lbl_thumb.width()  or 120
        target_h = self.lbl_thumb.height() or 80

        scaled = pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        try:
            self.lbl_thumb.setPixmap(scaled)
            self.lbl_thumb.setText("")
            # paint 강제 트리거 — modal 다이얼로그 직후의 paint 누락 방어
            self.lbl_thumb.update()
        except RuntimeError:
            # 위젯이 이미 삭제된 경우 (사용자가 항목을 빠르게 지웠을 때)
            pass
