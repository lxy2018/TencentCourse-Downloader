from pathlib import Path
from tqdm import tqdm
from typing import List
import httpx
import asyncio
from Crypto.Cipher import AES


class AsyncDownloader(object):

    def __init__(self, *, url: str, key_url: str, file_path: Path, thread_num: int = 20):
        """
            Async Download

            Args:
                thread_num (int): async num
                url (str): download url
                key_url(str): key url to decrypt ts video
                filepath (str): Path
        """

        self.file_path = file_path
        self.filename = file_path.stem

        self.url = url
        self.key_url = key_url
        self.client = httpx.AsyncClient()
        self.thread_num = thread_num

        self.file_size = self._get_file_size()
        self.cut_info = self._cutting()

        # Progress Bar
        self.tqdm_obj: tqdm = tqdm(total=self.file_size, unit_scale=True, unit_divisor=1024, unit="B")

        self._create_folder()

    def _create_folder(self):
        """
            Create folder path
        """
        if not self.file_path.parent.parent.exists():
            self.file_path.parent.parent.mkdir()

        if not self.file_path.parent.exists():
            self.file_path.parent.mkdir()

    def _get_file_size(self):

        with httpx.stream("GET", self.url) as res:
            size = int(res.headers["Content-Length"])
            return size

    def _cutting(self):
        """
        切割成若干份
        :param file_size: 下载文件大小
        :param thread_num: 线程数量
        :return:
        :[0, 31409080],
        :[31409081, 62818160],
        :[62818161, 94227240],
        :[94227241, 125636320],
        :[125636321, 157045400],
        :[157045401, 188454480],
        :[188454481, 219863560],
        :[219863561, 251272640],
        :[251272641, 282681720],
        :[282681721, '-']]
        """
        cut_info: List[List[int | str]] = []
        cut_size = self.file_size // self.thread_num

        for num in range(self.thread_num):
            cut_info.append([cut_size*num + 1, cut_size * (num + 1)])

            if num == self.thread_num - 1:
                cut_info[-1][1] = "-"
            elif num == 0:
                cut_info[0][0] = 0

        return cut_info

    def _merge_files(self):
        """
        合并分段下载的文件
        :param file_path:
        :return:
        """

        with open(self.file_path.absolute(), 'ab') as f_count:
            for index in range(self.thread_num):

                sub_file = self.file_path.parent.joinpath(f"{index}_{self.file_path.name}")

                with open(sub_file.absolute(), 'rb') as sub_write:
                    f_count.write(sub_write.read())

                # 合并完成删除子文件
                sub_file.unlink()

        return

    def _decrypt_ts(self):

        def decrypt(content, key):
            iv = content[:AES.block_size]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = cipher.decrypt(content[AES.block_size:])
            return plaintext.rstrip(b"\0")

        key = httpx.get(self.key_url).content

        with open(self.file_path.absolute(), 'rb') as f:
            content = f.read()

        decrypted_ts = decrypt(content, key)
        with open(self.file_path.absolute(), 'wb') as f:
            f.write(decrypted_ts)

    async def downloader(self, index, start_size, stop_size, retry=False):

        sub_file = self.file_path.parent.joinpath(f"{index}_{self.file_path.name}")

        if sub_file.exists():
            temp_size = sub_file.stat().st_size  # 本地已经下载的文件大小
            if not retry:
                self.tqdm_obj.update(temp_size)  # 更新下载进度条
        else:
            temp_size = 0

        stop_size = "" if stop_size == '-' else stop_size

        headers = {'Range': f'bytes={start_size + temp_size}-{stop_size}'}

        down_file = open(sub_file.absolute(), 'ab')

        try:
            async with self.client.stream("GET", self.url, headers=headers) as response:
                num_bytes_downloaded = response.num_bytes_downloaded
                async for chunk in response.aiter_bytes():
                    if chunk:
                        down_file.write(chunk)
                        self.tqdm_obj.update(response.num_bytes_downloaded - num_bytes_downloaded)
                        num_bytes_downloaded = response.num_bytes_downloaded

        except Exception as e:
            print("{}:请求超时,尝试重连\n报错信息:{}".format(index, e))
            await self.downloader(index, start_size, stop_size, retry=True)

        finally:
            down_file.close()

        return

    async def main_download(self):

        index = 0
        tasks = []
        for info in self.cut_info:
            task = asyncio.create_task(self.downloader(index, info[0], info[1]))
            tasks.append(task)
            index += 1

        await asyncio.gather(*tasks)
        await self.client.aclose()

    def main(self):

        asyncio.run(self.main_download())
        self.tqdm_obj.close()
        self._merge_files()
        self._decrypt_ts()
