import re
import json
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright, Request


class Login:

    def login(self):

        window = sync_playwright().start()
        browser = window.chromium.launch(channel='msedge', headless=False)
        context = browser.new_context()

        page = context.new_page()
        page.on("request", self.match_request)

        # Get plan json
        page.goto("https://ke.qq.com/user/index/index.html")
        page.wait_for_selector('.login-mask', state='attached')
        page.wait_for_selector('.login-mask', state='detached', timeout=100000)
        page.wait_for_selector('.tab-ctn', state='attached')

        # Load a video url to get token pattern
        page.goto(self.load_initial_url())
        page.wait_for_selector('#main-video', state='attached')

        self.save_cookies(page.context.cookies())

        page.close()
        browser.close()
        window.stop()

        print('登录成功')

    def match_request(self, data: Request):
        if "vod2.myqcloud.com" in data.url and "token" in data.url:
            self.save_token(data.url)
        elif "get_plan_list" in data.url:
            res = data.response()
            if res:
                self.save_plan(res.json())

    def main(self):

        if not self.is_login():
            print('未检测到cookies或token pattern，请重新登录...')
            self.login()
        else:
            relogin = input('检测本地已登陆，是否需要重新登录？\n(重新登录可刷新token pattern和课程表)\n输入Y确认，回车跳过\n')

            if relogin:
                self.clear_cache()
                self.login()

    @staticmethod
    def is_login():
        print("检查登陆状态...")
        return Path('Cache/cookies.json').exists() and Path('Cache/token.json').exists()

    @staticmethod
    def clear_cache():
        cookies = Path('Cache/cookies.json')
        token = Path('Cache/token.json')
        play = Path('Cache/plan.json')

        if cookies.exists():
            cookies.unlink()
        if token.exists():
            token.unlink()
        if play.exists():
            play.unlink()

    @staticmethod
    def save_cookies(cookies):
        with open('Cache/cookies.json', 'w') as f:
            f.write(json.dumps(cookies))

    @staticmethod
    def load_cookie():
        cookies = Path('Cache/cookies.json')
        if cookies.exists():
            res = {}
            for i in json.loads(cookies.read_bytes()):
                res.update({i['name']: i['value']})
            return res

    @staticmethod
    def save_token(token_url: str):
        """
            解析token存入本地token.json

            Args:
                token_url (str): 来自playwright登陆后获取
        """
        token_match = re.findall("token\\.(.+?)\\.", token_url)

        if token_match:
            token = token_match[0].replace("%3D", "=")
        else:
            print("未从url中匹配到token模型，请检查官方是否更新api")
            exit()

        token = base64.b64decode(token.encode()).decode()
        token_dict = {item.split("=")[0]: item.split("=")[1] for item in token.split(';')}

        with open("Cache/token.json", "w") as f:
            f.write(json.dumps(token_dict, indent=4))

    @staticmethod
    def load_token(cid: int, term_id: int):

        token = json.loads(Path('Cache/token.json').read_text())
        token['cid'] = cid
        token['term_id'] = term_id

        token_base = ""
        for key in token.keys():
            token_base += f"{key}={token[key]};"

        return base64.b64encode(token_base[:-1].encode()).decode()

    @staticmethod
    def save_plan(plans):

        with open('Cache/plan.json', 'w') as f:
            f.write(json.dumps(plans, indent=4))

    @staticmethod
    def load_initial_url():
        try:
            plan = json.loads(Path('Cache/plan.json').read_text())
            course = plan['result']['map_list'][0]['map_courses'][0]
            cid = course['cid']
            term_id = course['term_id']
            taid = course['chapter_list'][0]['sub_course_list'][0]['task_list'][0]['taid']
            resid_list = course['chapter_list'][0]['sub_course_list'][0]['task_list'][0]['resid_list'][0]

            url = f'https://ke.qq.com/webcourse/{cid}/{term_id}#taid={taid}&vid={resid_list}'
            return url
        except:
            raise Exception("初始化视频地址失败，请检查课程是否以加入课程表，或官网是否更新API.")


if __name__ == "__main__":
    new = Login()
    new.main()
