#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = "Sam.huang"

from time import sleep
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def Chrome_Rewards(url):
    """使用Chrome浏览器访问bing.com 网站
    """
    # 启用Chrome浏览器参数配置
    chrome_options = webdriver.ChromeOptions()
    # 添加用户数据目录
    chrome_options.add_argument("--user-data-dir="+r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data")
    
    # 使用用户已有的缓存
    chrome_options.add_argument("--profile-directory=Default")
    #   设置为开发者模式、避免出现浏览器上提示 受到测试软件的控制
    chrome_options.add_experimental_option('excludeSwitches',['enable-automation'])
    
    # 创建webdriver对象
    driver = webdriver.Chrome(options=chrome_options)
    # 设置浏览器窗口大小
    driver.set_window_size(1024, 768)
    driver.get(url)

    # 定位搜索框并输入关键字
    search_box = driver.find_element_by_name("q")
    search_box.send_keys("ChatGPT")
    search_box.send_keys(Keys.RETURN)
    
    # 等待搜索结果加载完毕
    # driver.implicitly_wait(10)
    sleep(20)
    driver.quit()

def Edge_test(url):
    edge_options = webdriver.EdgeOptions()
    edge_options.add_argument("--user-data-dir="+r"C:\Users\Administrator\AppData\Local\Microsoft\Edge\User Data\\")
    edge_options.add_argument("--profile-directory=Default")    # 使用缓存
    edge_options.add_argument('--no-sandbox')
    edge_options.add_experimental_option('excludeSwitches',['enable-automation'])     #设置为开发者模式
    br = webdriver.Edge(options=edge_options)
    br.get(url)
    sleep(10)
    br.quit()

if __name__== "__main__":
    url = 'http://www.bing.com'
    Chrome_Rewards(url)