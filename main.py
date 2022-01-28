import re
import json
import httpx
from typing import List
from pathlib import Path

from login import Login
from downloader import AsyncDownloader
from models import OPT, ChooseCidModel, CourseModel, Term, ChapterInfoItem, SubInfoItem, TaskInfoItem, TokenResult, VideoInfoModel


class TaskUrls(Login):

    def __init__(self, task: TaskInfoItem):

        self.is_valid = True
        self.RESOLUTION = -1  # 分辨率

        self.cid = task.cid
        self.term_id = task.term_id
        self.file_id = self.load_file_id(task)
        self.cookies = super().load_cookie()
        self.token = super().load_token(self.cid, self.term_id)

    def load_file_id(self, task: TaskInfoItem):
        if task.resid_list:
            file_id = int(re.findall("\\d+", task.resid_list)[0])
        else:
            file_id = None
            self.is_valid = False
            print(f"该课程视频可能未开放播放 => [{task.name}]")
        return file_id

    def check_key_url(self, key_url: str):
        """
            Check key_url
            if response is json this is not a right key url
        """
        try:
            httpx.get(key_url).json()
        except:
            return

        raise Exception("Token错误，请尝试重新登录")

    def _get_params(self):
        # 获得sign, t, us这三个参数
        # 这三个参数用来获取视频m3u8
        url = 'https://ke.qq.com/cgi-bin/qcloud/get_token'
        params = {
            'term_id': self.term_id,
            'fileId': self.file_id
        }
        response = httpx.get(url, params=params, cookies=self.cookies).json()

        return TokenResult(**response.get('result'))

    def _get_videoinfo(self, params: TokenResult):

        url = f'https://playvideo.qcloud.com/getplayinfo/v2/1258712167/{self.file_id}'
        response = httpx.get(url, params=params.dict(), cookies=self.cookies).json()
        videoinfo = VideoInfoModel(**response)
        return videoinfo

    def _get_download_urls(self, videoinfo: VideoInfoModel):
        """
            获取该videoinfo下的ts视频下载链接、key密匙下载链接

            Args:
                videoinfo (VideoInfoModel):
                cid (int):
                term_id (int):
                token (str):

            Returns:
                [tuple]: (download_url,key_url)
        """
        # 分辨率
        ts_url = videoinfo.videoInfo.transcodeList[self.RESOLUTION].url
        m3u8_text = httpx.get(ts_url + '&token=' + self.token).text

        pattern = re.compile(r'(https://ke.qq.com/cgi-bin/qcloud/get_dk.+)"')
        return ts_url.replace('.m3u8', '.ts'), pattern.findall(m3u8_text)[0]

    def get(self):
        """
            获取视频下载url和key解密url

            From : task =>
            : term_id
            : cid
            : file_id

            From : term_id & file_id =>
            : params

            From : params & file_id =>
            : videoinfo

            From : videoinfo & cid & term_id & token =>
            : ts_url
            : key_url

            Args:
                task (TaskInfoItem): 最终选择的课程

            Return: (ts_url,key_url)
        """

        params = self._get_params()
        videoinfo = self._get_videoinfo(params)
        ts_url, key_url = self._get_download_urls(videoinfo)
        self.check_key_url(key_url)

        return ts_url, key_url


class Course(object):

    def __init__(self, root_path, cid: int):
        # Initial
        if not cid:
            self.cid = self._choose_cid()

        self.root_path = root_path
        self.course_data = self._get_course_data(self.cid)
        self.course_name = self.course_data.result.course_detail.name
        self.terms: List[Term] = self.course_data.result.course_detail.terms

    def _choose_menu_index(self, options: List[OPT], is_all=True):
        """
            菜单选择

            Args:
                options (List[OPT]):
                is_all (bool, optional): 是否允许选择全部. Defaults to True.

            Returns:
                index : -1 为选择全部
        """
        print("*"*30)

        if len(options) == 1:
            return 0

        for item in options:
            print(str(options.index(item) + 1) + '. ' + item.name)

        while True:
            print("*"*30)
            try:
                if is_all:
                    index = int(input("请输入序号,回车确认(输入0下载当前列表全部)：\n"))
                else:
                    index = int(input("请输入序号,回车确认：\n"))

            except ValueError:
                index = -99

            if index <= len(options) and index >= 0:
                if is_all:
                    break
                else:
                    if index > 0:
                        break

            print("请输入正确的序号！")

        return index - 1

    def _choose_cid(self):
        """
            从cache plan中获取所有课程名字+cid

            Returns:
                [List]: [{name: string,cid: int},...]
        """
        with open("Cache/plan.json") as f:
            plan_data = json.loads(f.read())

        courses: List[ChooseCidModel] = []
        for play in plan_data['result']['map_list']:
            name = play['map_courses'][0]['cname']
            cid = play['map_courses'][0]['cid']
            courses.append(ChooseCidModel(**{"name": name, "cid": cid}))

        course = courses[self._choose_menu_index(courses, is_all=False)]
        return course.cid

    def _get_course_data(self, cid: int):
        # 获取课程全部信息

        url = f'https://ke.qq.com/cgi-bin/course/basic_info?cid={cid}'
        course_data = CourseModel(**httpx.get(url).json())

        return course_data

    def _map_task_path(self, tasks: List[TaskInfoItem]):
        """
            根据task taid值寻找父级sub name作为父级文件夹
            增加对应键download_path
        """

        def _replace_illegal(name: str):

            name = re.sub("<|>|/|:|\"|\\*|\\?", "", name)
            return name.replace("\\", "")

        _map = {}

        for term in self.terms:
            for chaper in term.chapter_info:
                for sub in chaper.sub_info:
                    for task in sub.task_info:
                        index = chaper.sub_info.index(sub)
                        _map.update({task.taid: str(index+1) + "_" + sub.name})

        for task in tasks:
            sub_name = _map.get(task.taid, "NotFound")
            task_path = _replace_illegal(self.course_name) + "/" + _replace_illegal(sub_name)
            _path = Path(self.root_path).joinpath(task_path).joinpath(task.name+".ts")
            task.download_path = _path

        return tasks

    def _get_tasks(self, data: OPT):
        """
            根据类型判断输入data层级返回该data下所有tasks

            Args:
                data:OPT

            Returns:
                tasks:list[TaskInfoItem]
        """
        tasks: List[TaskInfoItem] = []

        if isinstance(data, Term):
            for chaper in data.chapter_info:
                for subs in chaper.sub_info:
                    for task in subs.task_info:
                        tasks.append(task)

        elif isinstance(data, ChapterInfoItem):
            for subs in data.sub_info:
                for task in subs.task_info:
                    tasks.append(task)

        elif isinstance(data, SubInfoItem):
            for task in data.task_info:
                tasks.append(task)

        elif isinstance(data, TaskInfoItem):
            tasks.append(data)

        return self._map_task_path(tasks)

    def main(self):
        # Select Term
        term = self.terms[self._choose_menu_index(self.terms, is_all=False)]

        # Select chapter
        chapters: List[ChapterInfoItem] = term.chapter_info
        chapter_index = self._choose_menu_index(chapters)
        chapter = chapters[chapter_index]

        if chapter_index == -1:
            tasks = self._get_tasks(term)
            return tasks

        # Select sub
        subs: List[SubInfoItem] = chapter.sub_info
        sub_index = self._choose_menu_index(subs)
        sub = subs[sub_index]

        if sub_index == -1:
            tasks = self._get_tasks(chapter)
            return tasks

        # Select task
        tasks: List[TaskInfoItem] = sub.task_info
        task_index = self._choose_menu_index(tasks)
        task = tasks[task_index]

        if task_index == -1:
            tasks = self._get_tasks(sub)
            return tasks

        # Return single task
        tasks = self._get_tasks(task)
        return tasks


class Download(object):

    def __init__(self, tasks: List[TaskInfoItem]):
        self.tasks = tasks

    def main(self):

        print(f"共:{len(self.tasks)} 个视频等待下载...")

        for task in tasks:
            print("*"*30)
            if task.download_path.exists():
                print(f"{task.name} Already exists.")
                continue

            urls = TaskUrls(task)
            if urls.is_valid:
                print(f"正在下载({tasks.index(task) + 1}/{len(self.tasks)}): => [{task.name}]")
                ts_url, key_url = urls.get()
                download = AsyncDownloader(url=ts_url, key_url=key_url, file_path=task.download_path)
                download.main()


if __name__ == '__main__':

    # 默认下载文件夹
    ROOT_PATH = "Data"

    # 执行登陆检查cookies/token/plan
    Login().main()

    # 根据cid获取课程基础信息，默认为提供课程表内课程进行选择
    # 也可在下面手动指定cid，跳过课程表选择
    tasks = Course(ROOT_PATH, cid=0).main()

    # 获取所有需要下载的tasks后开始下载
    Download(tasks).main()
