from selenium import webdriver
import time
from PIL import Image as Im
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import re
import base64
import cv2
import numpy as np
import random
import urllib.request
import requests
import sys
from selenium.webdriver.chrome.options import Options

class Youzan(object):

    def __init__(self, user, pwd):
        self.user = user
        self.pwd =pwd
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(chrome_options=chrome_options)

    def __handle_slider_img(self, image):
        """
        对滑块进行二值化处理
        :param image: cv类型的图片对象
        :return:
        """
        kernel = np.ones((8, 8), np.uint8)  # 去滑块的前景噪声内核
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 灰度化

        # 灰化背景
        width, heigth = gray.shape
        for h in range(heigth):
            for w in range(width):
                if gray[w, h] == 0:
                    gray[w, h] = 96

        # 排除背景
        binary = cv2.inRange(gray, 96, 96)
        res = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)  # 开运算去除白色噪点
        return res

    def _match_template(self, img_target, img_template):
        """
        模板匹配（用于寻找缺口）
        :param img_target: 带有缺口的背景图
        :param img_template: 缺口的滑块图
        :return: 缺口所在的位置的x轴距离
        """
        # print("图片缺口模板匹配")

        img_target = cv2.imread(img_target)
        img_template = cv2.imread(img_template)

        # 滑块图片处理
        tpl = self.__handle_slider_img(img_template)  # 误差来源就在于滑块的背景图为白色

        # 图片高斯滤波
        blurred = cv2.GaussianBlur(img_target, (3, 3), 0)

        # 图片灰度化
        gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)

        width, height = tpl.shape[:2]

        # 灰度化模板匹配
        result = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)  # 使用灰度化图片
        # print("result = {}".format(len(np.where(result >= 0.5)[0])))

        # 查找数组中匹配的最大值
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        left_up = max_loc
        right_down = (left_up[0] + height, left_up[1] + width)
        image = cv2.rectangle(img_target, left_up, right_down, (7, 279, 151), 2)

        cv2.imwrite('./captcha1.png', image)
        # print('大图缺口x坐标为：%d' % max_loc[0])

        return left_up[0]

    def _get_tracks(self, distance):
        """
        根据偏移量获取移动轨迹3
        :param distance: 偏移量
        :return: 移动轨迹
        """
        track = []
        mid1 = round(distance * random.uniform(0.1, 0.2))
        mid2 = round(distance * random.uniform(0.65, 0.76))
        mid3 = round(distance * random.uniform(0.84, 0.88))
        # 设置初始位置、初始速度、时间间隔
        current, v, t = 0, 0, 0.2
        distance = round(distance)

        while current < distance:
            # 四段加速度
            if current < mid1:
                a = random.randint(10, 15)
            elif current < mid2:
                a = random.randint(30, 40)
            elif current < mid3:
                a = -70
            else:
                a = random.randint(-25, -18)

            # 初速度 v0
            v0 = v
            # 当前速度 v = v0 + at
            v = v0 + a * t
            v = v if v >= 0 else 0
            move = v0 * t + 1 / 2 * a * (t ** 2)
            move = round(move if move >= 0 else 1)
            # 当前位移
            current += move
            # 加入轨迹
            track.append(move)

        # print("current={}, distance={}".format(current, distance))

        # 超出范围
        back_tracks = []
        out_range = distance - current
        if out_range < -8:
            sub = int(out_range + 8)
            back_tracks = [-1, sub, -3, -1, -1, -1, -1]
        elif out_range < -2:
            sub = int(out_range + 3)
            back_tracks = [-1, -1, sub]

        # print("forward_tracks={}, back_tracks={}".format(track, back_tracks))
        return {'forward_tracks': track, 'back_tracks': back_tracks}

    def get_random_float(self, min, max, digits=4):
        """
        :param min:
        :param max:
        :param digits:
        :return:
        """
        return round(random.uniform(min, max), digits)

    def _slider_action(self, tracks):
        """
        移动滑块
        :return:
        """
        # print("开始移动滑块")

        # slider = self.driver.find_element_by_class_name('JDJRV-slide-btn')
        slider = self.driver.find_element_by_id('slideIconRef')

        ActionChains(self.driver).click_and_hold(slider).perform()

        # 正向滑动
        for track in tracks['forward_tracks']:
            yoffset_random = random.uniform(-2, 4)
            ActionChains(self.driver).move_by_offset(xoffset=track, yoffset=yoffset_random).perform()

        time.sleep(random.uniform(0.06, 0.5))

        # 反向滑动
        for back_tracks in tracks['back_tracks']:
            yoffset_random = random.uniform(-2, 2)
            ActionChains(self.driver).move_by_offset(xoffset=back_tracks, yoffset=yoffset_random).perform()

        # 抖动
        ActionChains(self.driver).move_by_offset(
            xoffset=self.get_random_float(0, -1.67),
            yoffset=self.get_random_float(-1, 1)
        ).perform()
        ActionChains(self.driver).move_by_offset(
            xoffset=self.get_random_float(0, 1.67),
            yoffset=self.get_random_float(-1, 1)
        ).perform()

        time.sleep(self.get_random_float(0.2, 0.6))
        ActionChains(self.driver).release().perform()

        # print("滑块移动成功")
        time.sleep(2)
        return True

    def move(self):
        r1 = WebDriverWait(self.driver, 30, 1).until(EC.presence_of_element_located((By.ID, "bigImg"))).get_attribute("src")
        response=urllib.request.urlopen(r1)
        img=response.read()
        with open('./captcha1.png','wb') as f:
             f.write(img)

        r2 = WebDriverWait(self.driver, 30, 1).until(EC.presence_of_element_located((By.ID, "smallImg"))).get_attribute("src")
        response=urllib.request.urlopen(r2)
        img=response.read()
        with open('./captcha2.png','wb') as f:
             f.write(img)

        distance = self._match_template('./captcha1.png', './captcha2.png')

        # 原图缩略图比例
        distance = distance * 280 / 560

        # print('小图缺口x坐标为：%d' % distance)

        # 获取滑块移动轨迹 14为减去初始值
        tracks = self._get_tracks(distance-14)

        # 滑动滑块
        self._slider_action(tracks=tracks)

        if "login" in self.driver.current_url:
            return False
        else:
            return True

    def login_(self):

        self.driver.get("https://account.youzan.com/login")
        time.sleep(5)
        self.driver.find_element_by_xpath("/html/body/div[1]/div/div[1]/div[1]/div/div[1]/p").click()
        self.driver.find_element_by_xpath("/html/body/div[1]/div/div[1]/div[1]/div/form/div[1]/div[2]/input").clear()
        self.driver.find_element_by_xpath("/html/body/div[1]/div/div[1]/div[1]/div/form/div[1]/div[2]/input").send_keys(self.user)
        self.driver.find_element_by_xpath("/html/body/div[1]/div/div[1]/div[1]/div/form/div[2]/div/input").clear()
        self.driver.find_element_by_xpath("/html/body/div[1]/div/div[1]/div[1]/div/form/div[2]/div/input").send_keys(self.pwd)
        self.driver.find_element_by_xpath("/html/body/div[1]/div/div[1]/div[1]/div/form/div[3]/button").click()

        # 开始反复滑动直到成功验证
        huadong_num = 1
        while 1:
            time.sleep(1)
            if self.move():
                break
            huadong_num += 1

        # print("登陆成功, 成功率为：", 1/huadong_num * 100, "%")
        time.sleep(5)
        # 登陆后进入具体商铺
        self.driver.find_element_by_class_name('shop-list-item').click()
        time.sleep(5)
        # 进入账单页面
        self.driver.find_element_by_xpath("/html/body/aside/nav[1]/ul/li[7]/a").click()

        c = self.driver.get_cookies()
        cookies = {}
        # 获取cookie中的name和value,转化成requests可以使用的形式
        for cookie in c:
            # if cookie['name'] == 'sid':
            cookies[cookie['name']] = cookie['value']
        print(cookies)
        self.driver.quit()

if __name__ == '__main__':
    user = ''
    pwd = ''

    youzan = Youzan(user, pwd)
    youzan.login_()