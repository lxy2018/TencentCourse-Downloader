from pathlib import Path
from typing import List, TypeVar
from pydantic import BaseModel


# Choose cid
class ChooseCidModel(BaseModel):
    name: str
    cid: int

# ! get_token


class TokenResult(BaseModel):
    exper: int
    sign: str
    t: str
    us: str


class GetTokenResModel(BaseModel):
    result: TokenResult
    retcode: str


# ! getplayinfo
class TranscodeListItem(BaseModel):
    url: str
    # definition: int 清晰度
    duration: int  # * 时长
    # floatDuration: float 小数时长
    size: int
    totalSize: int  # * 文件大小
    # bitrate: int
    # height: int
    # width: int
    # container: str
    # md5: str
    # videoStreamList: List[VideoStreamListItem]
    # audioStreamList: List[AudioStreamListItem]
    # templateName: str


class BasicInfo(BaseModel):
    name: str
    # description: str
    # tags: List


class VideoInfo(BaseModel):
    basicInfo: BasicInfo
    # drm: Drm
    # masterPlayList: MasterPlayList
    transcodeList: List[TranscodeListItem]


class VideoInfoModel(BaseModel):
    code: int
    message: str
    # requestId: str
    # playerInfo: PlayerInfo
    # coverInfo: CoverInfo
    videoInfo: VideoInfo


# ! Main Term Molder
class TaskInfoItem(BaseModel):
    create_time: int
    csid: int
    endtime: int
    resid_ext: str
    term_id: int
    type: int
    bgtime: int
    name: str
    resid_list: str
    aid: int
    taid: str
    cid: int
    download_path: Path = Path("NotFound")


class SubInfoItem(BaseModel):
    csid: int
    sub_id: int
    introduce: str
    name: str
    endtime: int
    term_id: int
    task_info: List[TaskInfoItem]
    bgtime: int
    cid: int


class ChapterInfoItem(BaseModel):
    ch_id: int
    introduce: str
    name: str
    sub_info: List[SubInfoItem]
    term_id: int
    type: int
    aid: int
    cid: int


class Term(BaseModel):
    name: str
    aid: int
    cid: int
    term_id: int
    pub_time: int
    introduce: str
    chapter_info: List[ChapterInfoItem]


class CourseDetail(BaseModel):
    recordtime: int  # ? 发布时间
    terms: List[Term]
    summary: str
    agency_name: str
    endtime: int
    name: str
    aid: int
    cid: int


class ResultModel(BaseModel):
    course_detail: CourseDetail


class CourseModel(BaseModel):
    result: ResultModel
    retcode: int


OPT = TypeVar('OPT', Term, ChapterInfoItem, SubInfoItem, TaskInfoItem, ChooseCidModel)
