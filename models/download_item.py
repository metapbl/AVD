# models/download_item.py
# 다운로드 항목 하나의 데이터 구조를 정의하는 파일

from dataclasses import dataclass, field
from enum import Enum


class DownloadStatus(Enum):
    """다운로드 상태값 정의"""
    WAITING    = "대기중"
    FETCHING   = "정보 가져오는 중"
    DOWNLOADING = "다운로드 중"
    MERGING    = "병합 중"
    DONE       = "완료"
    ERROR      = "오류"
    CANCELLED  = "취소됨"


@dataclass
class DownloadItem:
    """다운로드 항목 하나를 표현하는 데이터 클래스"""

    # 기본 정보
    url         : str                          # 원본 URL
    title       : str  = "제목 가져오는 중..."  # 영상 제목
    thumbnail   : str  = ""                    # 썸네일 URL (후보 리스트의 첫 항목)
    duration    : int  = 0                     # 영상 길이 (초)
    uploader    : str  = ""                    # 업로더 이름

    # 다운로드 옵션
    format_id   : str  = "bestvideo+bestaudio" # 선택한 화질/형식
    ext         : str  = "mp4"                 # 저장 확장자
    save_path   : str  = ""                    # 저장 경로

    # 진행 상태
    status      : DownloadStatus = field(
                    default=DownloadStatus.WAITING)
    progress    : float = 0.0                  # 진행률 0.0 ~ 100.0
    speed       : str   = ""                   # 다운로드 속도 문자열
    eta         : str   = ""                   # 남은 시간 문자열
    file_size   : str   = ""                   # 전체 파일 크기 문자열
    error_msg   : str   = ""                   # 오류 발생 시 메시지

    # 썸네일 후보 URL 리스트 (화질 내림차순). 단일 thumbnail 이 404 여도
    # 다음 후보로 폴백해 미리보기를 채우기 위함. 비어 있으면 thumbnail 만 사용.
    thumbnail_candidates: list = field(default_factory=list)

    # 고유 ID (항목 구분용)
    item_id     : str   = field(default_factory=lambda: "")

    def __post_init__(self):
        # item_id가 없으면 URL 기반으로 자동 생성
        if not self.item_id:
            import uuid
            self.item_id = str(uuid.uuid4())[:8]
        # 후보 리스트가 비었는데 단일 썸네일이 있으면 그것으로 보정
        if not self.thumbnail_candidates and self.thumbnail:
            self.thumbnail_candidates = [self.thumbnail]

    @property
    def is_done(self) -> bool:
        return self.status == DownloadStatus.DONE

    @property
    def is_active(self) -> bool:
        return self.status in (
            DownloadStatus.FETCHING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.MERGING,
        )