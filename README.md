# 腾讯课堂视频下载脚本
腾讯课堂太难用了，且投屏效果太差。业余小白借鉴了 https://github.com/aiguoli/qcourse_scripts 做了这个视频下载脚本，改进了一下菜单选择逻辑和多线程下载+进度条，由于官方的token格式老是变化，改为了使用playwright登陆时，自动去课程表下第一个视频内获取当前token的pattern存到本地，添加了一些API的pydantic model。

![Snipaste_01-28_08-13-39](https://user-images.githubusercontent.com/42557951/151505882-d9274ec7-510d-4673-a362-34e881012215.jpg)

## 基本功能
1. playwright模拟登陆保存cookies，自动获取课程表内课程信息
2. 根据课程表内信息选择课程批量下载或单独下载，也可手动设置cid
3. 使用asyncio + httpx + tqdm 单视频协程下载，理论可以轻松跑满网速，提供友好的进度条，支持断点续传


## 使用方法
0. cd到当前文件夹
1. 手动pip下载全部缺少的依赖
2. cmd执行安装playwright install msedge（msedgedriver版本问题，可在该地址下载最新版的驱动 https://msedgewebdriverstorage.z22.web.core.windows.net/）
3. 修改Root Path或使用默认的Data文件夹作为默认下载文件夹
4. 执行python main.py
5. 弹出窗口扫码登陆，选择课程下载
6. 下载完成后的视频为ts格式，可以正常观看，如需转换为mp4可自行使用FFmpeg执行命令：
   ```ffmpeg -i test.ts -acodec copy -vcodec copy -f mp4 test.mp4 ```
