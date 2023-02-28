# Microsoft-Rewards
[![version](https://img.shields.io/badge/python-3.4+-blue.svg)](https://www.python.org/download/releases/3.4.0/) 
[![status](https://img.shields.io/badge/status-stable-green.svg)](https://github.com/huaisha1224/Microsoft-Rewards)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![star, issue](https://img.shields.io/badge/star%2C%20issue-welcome-brightgreen.svg)](https://github.com/huaisha1224/Microsoft-Rewards)

赚取每日Microsoft Rewards积分的自动化解决方案


## 主要功能
-	通过Selenium 控制Chrome浏览器访问bing.com，完成每日的搜索任务，来获取Microsoft Rewards每日积分。
-	本项目直接操作Chrome浏览器，不需要用户提供Microsoft Rewards账户和密码，安全可靠。


## 运行环境

- [Python 3](https://www.python.org/)

## 第三方库
- [Selenium](https://www.selenium.dev/)

## 安装使用：

```
pip install -r requirements.txt
```

-	下载安装配置Chrome浏览器驱动

	在Chrome浏览器地址栏输入 'chrome://version/' 查看浏览器版本

-	下载对应版本的 ChromeDriver

	[Chromedriver](https://chromedriver.chromium.org/downloads)


## 更新记录
- 【2023-02-25】提交代码
- 【2023-02-28】添加滕王阁序作为搜索使用


## 备注
- 🌟 代码在Win10 + Python3.8环境中编写，如果在其他平台上运行出行问题，欢迎提issue。


## 待完成的功能
- 【抓取微博热搜用于搜索】
- 【添加定时任务功能】 
- 【添加多用户管理】
- 【兑换提醒】
- 【自动适配浏览器和ChromeDriver】


![image](https://user-images.githubusercontent.com/3378350/221791964-0a8d4ef6-2953-4662-9c41-735e8a4c6828.png)
