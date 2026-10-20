# Microsoft-Rewards
[![version](https://img.shields.io/badge/python-3.4+-blue.svg)](https://www.python.org/download/releases/3.4.0/) 
[![status](https://img.shields.io/badge/status-stable-green.svg)](https://github.com/huaisha1224/Microsoft-Rewards)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![star, issue](https://img.shields.io/badge/star%2C%20issue-welcome-brightgreen.svg)](https://github.com/huaisha1224/Microsoft-Rewards)

赚取每日Microsoft Rewards积分的自动化解决方案



# 说明
本项目有2个分支
- 一个是油猴脚本解决方案
- 另外一个是基于开源项目Microsoft-Rewards-Script的GUI解决方案


## 油猴脚本解决方案
- tampermonkey目录中是油猴脚本，也可以从下面的地址安装
- [Microsoft Bing Rewards每日任务脚本](https://greasyfork.org/zh-CN/scripts/477107)
- [移动端微软Rewards每日任务脚本](https://greasyfork.org/zh-CN/scripts/480355)

## 基于本地浏览器解决方案
## ✨ 核心特性

**账户管理**

- ✅ 多账户支持（`.env` 中 `ACCOUNT_N_*` 环境变量，编号无需连续）
- ✅ 会话存储与持久化（`sessions/`，含指纹持久化）
- ✅ 2FA 支持（TOTP 自动生成并填入验证码）
- ✅ 无密码登录支持
- ✅ 每账户独立代理（HTTP/HTTPS/SOCKS4/SOCKS5）

**自动化与控制**

- ✅ 无头浏览器操作（Patchright 反检测内核）
- ✅ 集群支持（同时多个账户）
- ✅ 可配置任务开关

**搜索与活动**

- ✅ 桌面与移动搜索（配额独立跟踪，互不阻塞）
- ✅ 每日集 / 更多促销 / 打卡 / App 活动 / 每日签到 / 阅读赚取（Read-to-Earn）
- ✅ 搜索加成 perk 激活（"再搜 N 次得积分"）/ 视觉搜索（可选）
- ✅ 连击保护 & 自动领取 dashboard 奖励积分
- ✅ 模拟滚动与随机点击，降低风控风险

**搜索词来源（国内推荐 china + local）**

- ✅ 中国热搜（百度/头条/抖音/微博/知乎，gmya.net 聚合，多源随机 + 限流退避）
- ✅ 本地查询词兜底（`search-queries.json` 中文词库）
- ✅ Bing 建议聚类扩展（`clusterSearch`，每个主词扩展一组相关词再搜索）



## 安装使用：

```
python app.py
```

![image](https://user-images.githubusercontent.com/3378350/230837253-1132c32f-30b5-4ead-9cae-70f8209ef55b.png)

