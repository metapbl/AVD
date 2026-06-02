# workers/playlist_probe_worker.py
# 플레이리스트 URL 에서 항목 목록만 가볍게 추출하는 백그라운드 워커.
# InfoWorker 가 단건 풀 추출(extract_flat=False)을 담당하는 것과 달리,
# 이 워커는 extract_flat 로 각 항목의 id/title/duration/url 만 빠르게 긁는다.
# 포맷은 캐지 않는다 — 항목별 풀 추출은 펼쳐진 뒤 기존 InfoWorker 가 맡는다.

import yt_dlp
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from utils.file_utils import normalize_info_dict


# 한 플레이리스트에서 받아올 최대 항목 수. ADR 합의값.
# yt-dlp 의 playlistend 와 추출 후 슬라이스 양쪽으로 이중 방어.
PLAYLIST_ITEM_LIMIT = 500


@dataclass
class PlaylistEntry:
    """플레이리스트 항목 하나 — flat 추출 단계의 가벼운 표현."""
    url      : str   # 개별 영상 URL (이후 InfoWorker 가 풀 추출)
    title    : str   # 표시용 제목 (flat 단계라 '제목 없음' 일 수 있음)
    duration : int   # 초 단위 (flat 단계라 0 일 수 있음)


@dataclass
class PlaylistResult:
    """probe 결과 — 플레이리스트 전체 메타와 항목 목록."""
    title      : str                  # 플레이리스트 제목
    entries    : list[PlaylistEntry]  # 항목 목록 (상한 적용 후)
    total_found: int                  # 상한 적용 전 실제 발견 개수


class PlaylistProbeWorker(QThread):
    """
    플레이리스트 URL 을 flat 모드로 추출해 항목 목록을 emit 하는 워커.

    시그널:
        finished : 추출 성공 시 PlaylistResult 전달
        error    : 실패 시 에러 메시지 문자열 전달

    설계 메모:
    - extract_flat="in_playlist" 로 각 항목의 메타만 받는다. 포맷·썸네일
      풀 추출을 하지 않으므로 수백 개여도 빠르다.
    - playlistend 로 yt-dlp 단계에서 1차 상한, 추출 후 슬라이스로 2차 상한.
    - 단일 영상 URL 이 잘못 들어와도(_type 이 playlist 가 아님) 방어적으로
      빈 결과 대신 error 를 낸다 — 호출 측(PlaylistFlow)이 플레이리스트
      판정을 이미 했다는 전제이지만, 판정이 빗나간 경우의 안전망.
    """

    finished = Signal(object)  # PlaylistResult
    error    = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        ydl_opts = {
            "quiet"             : True,
            "no_warnings"       : True,
            "extract_flat"      : "in_playlist",
            "playlistend"       : PLAYLIST_ITEM_LIMIT,
            "js_runtimes"       : {"node": {}},
            "remote_components" : ["ejs:github"],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
        except Exception as e:
            self.error.emit(str(e))
            return

        if not isinstance(info, dict):
            self.error.emit("플레이리스트 정보를 해석할 수 없습니다.")
            return

        # flat 추출이라도 NFC 정규화는 적용 — 제목의 NFD 한글 방어.
        info = normalize_info_dict(info)

        raw_entries = info.get("entries")
        if not raw_entries:
            # _type 이 playlist 가 아니거나(단일 영상) entries 가 빈 경우.
            self.error.emit("플레이리스트 항목을 찾지 못했습니다.")
            return

        # entries 는 제너레이터일 수 있어 list 로 적재 (상한까지만).
        collected: list[PlaylistEntry] = []
        total = 0
        for e in raw_entries:
            if not isinstance(e, dict):
                continue
            total += 1
            if len(collected) >= PLAYLIST_ITEM_LIMIT:
                # 상한 도달 — total 카운트는 계속 세지 않는다(제너레이터
                # 소진 비용 회피). total 은 "최소 이만큼" 의 의미가 된다.
                break

            entry_url = self._pick_entry_url(e)
            if not entry_url:
                continue

            collected.append(PlaylistEntry(
                url      = entry_url,
                title    = e.get("title") or "제목 없음",
                duration = int(e.get("duration") or 0),
            ))

        if not collected:
            self.error.emit("재생 가능한 항목이 없습니다.")
            return

        result = PlaylistResult(
            title       = info.get("title") or "플레이리스트",
            entries     = collected,
            total_found = max(total, len(collected)),
        )
        self.finished.emit(result)

    def _pick_entry_url(self, entry: dict) -> str:
        """
        flat 항목 dict 에서 개별 영상 URL 을 고른다.

        extract_flat 결과의 항목은 'url' 에 영상 URL 또는 ID 가 들어온다.
        - 완전한 http(s) URL 이면 그대로 사용.
        - YouTube 의 경우 'url' 이 영상 ID 만일 수 있어 'id' 로 watch URL 조립.
        - 'webpage_url' 이 있으면 우선.
        """
        webpage = entry.get("webpage_url")
        if isinstance(webpage, str) and webpage.startswith(("http://", "https://")):
            return webpage

        url = entry.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url

        # ie_key / id 로 YouTube watch URL 조립 (flat 추출의 흔한 형태).
        vid = entry.get("id")
        if isinstance(vid, str) and vid:
            return f"https://www.youtube.com/watch?v={vid}"

        return ""
