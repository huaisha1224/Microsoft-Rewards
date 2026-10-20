# -*- coding: utf-8 -*-
"""客户端版本号 —— 改版本只改这里。

发布新版本时要做两件事：
1. 把 APP_VERSION 改成新版本号（点分数字，段数不限，例如 2026.10.19 / 2026.10.19.1）

两边一致时用户端不会弹更新提示；服务器更大就提示，更小则忽略。
"""

# 当前客户端版本（与服务器接口的 Version 字段直接比较）
APP_VERSION = '2026.10.20.1'

# 版本接口里的工具名，对应 https://api.hs2049.cn/tools/<TOOL_NAME>
TOOL_NAME = 'MicrosoftRewards'

# 程序显示名
APP_NAME = 'Microsoft Rewards 助手'
