# Microsoft-Rewards
[![version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) 
[![status](https://img.shields.io/badge/status-stable-green.svg)](https://github.com/huaisha1224/Microsoft-Rewards)
[![license](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](./LICENSE)
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



## 环境要求：
- Node.js 24+（`node -v` 确认，低于 24 会报 engine 错误）
- Python 3.10+（仅桌面 GUI 需要，用来跑 `gui/app.py`）
- Windows 10/11 x64（桌面 GUI 与 exe 打包为 Windows 专用，核心脚本跨平台）
- 系统安装 Google Chrome（`config.json` 里 `browserChannel` 设为 `chrome` 时推荐，免下载 Chromium）

## 安装使用：

```bash
# 1. 安装依赖
npm install

# 2. 配置账号（.env 已在 .gitignore 中，切勿提交）
copy env.example .env        # Linux/macOS: cp env.example .env
notepad .env                 # 填 ACCOUNT_1_EMAIL / ACCOUNT_1_PASSWORD / ACCOUNT_1_TOTP_SECRET

# 3. 编译
npm run build
```

启动桌面 GUI（推荐）：

```bat
start-gui.bat
```

> 首次使用先装 GUI 依赖：`python -m pip install customtkinter`

或者用命令行直接跑：

```bash
npm start
```

## 免责声明
- 本软件为非官方第三方工具，与 Microsoft Corporation 没有任何隶属、授权或背书关系，Microsoft / Microsoft Rewards / Bing 等名称与商标归微软所有
- 使用自动化脚本获取 Rewards 积分可能违反 Microsoft 服务条款，存在积分被清零、账号被限制功能或永久封禁的风险，请自行判断并承担后果
- 因使用或无法使用本软件造成的账号异常、积分损失、数据丢失或其它任何直接、间接损失，作者不承担任何责任
- 本项目仅供学习与技术交流，请优先使用微软官方服务

## License
本仓库包含基于 [Microsoft-Rewards-Script](https://github.com/TheNetsky/Microsoft-Rewards-Script)（GPL-3.0）的衍生代码，因此同样以 GPL-3.0 发布；`tampermonkey/` 下的油猴脚本为作者原创。完整许可证见 [LICENSE](./LICENSE)。
