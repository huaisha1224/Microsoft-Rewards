#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""版本检查与更新提示（标准库实现，零第三方依赖）。

原实现依赖 requests + packaging，在 PyInstaller 打包时容易漏 hidden-import，
且网络请求直接跑在 Tk 主线程上会卡界面。这里改成 urllib + 手写版本比较，
并提供 `fetch_latest()` 供 GUI 在后台线程调用。

版本号规则：点分数字，段数不限，缺的段按 0 补齐。
    2026.10.18.1  >  2026.10.18   >  2026.10.9
非数字段（如 1.0.0-beta）比较时按 0 处理，仅用于尽力而为的排序。
"""

from __future__ import annotations

import json
import re
import webbrowser
from typing import Dict, List, Optional, Tuple

DEFAULT_BASE = 'https://api.hs2049.cn/tools/'


# --------------------------------------------------------------- 版本比较
def parse_version(text: str) -> List[int]:
    """把 '2026.10.18.1' 解析成 [2026, 10, 18, 1]。非法输入返回 []。"""
    if not text:
        return []
    parts = re.split(r'[.\-+_]', str(text).strip())
    out: List[int] = []
    for part in parts:
        digits = re.match(r'\d+', part)
        out.append(int(digits.group(0)) if digits else 0)
    return out


def is_newer(server_version: str, local_version: str) -> bool:
    """服务器版本是否比本地版本新。"""
    remote = parse_version(server_version)
    local = parse_version(local_version)
    if not remote:
        return False
    width = max(len(remote), len(local))
    remote += [0] * (width - len(remote))
    local += [0] * (width - len(local))
    return remote > local


# --------------------------------------------------------------- 网络请求
def fetch_latest(
    tool_name: str,
    timeout: float = 8.0,
    base: str = DEFAULT_BASE,
) -> Tuple[Optional[Dict], Optional[str]]:
    """请求版本接口。

    返回 ``(data, error)``：成功时 data 是解析后的 dict、error 为 None；
    失败时 data 为 None、error 是可读的中文原因。**不抛异常**，方便调用方
    在后台线程里直接用。
    """
    url = f'{base}{tool_name}'
    try:
        # 延迟 import，缩短 GUI 冷启动时间
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen

        req = Request(url, headers={'User-Agent': 'MRS-Client/1.0', 'Accept': 'application/json'})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        data = json.loads(raw.decode('utf-8', errors='replace'))
        if not isinstance(data, dict):
            return None, '接口返回格式异常'
        if not data.get('Version'):
            return None, '接口返回缺少 Version 字段'
        return data, None
    except HTTPError as exc:
        return None, f'HTTP {exc.code}'
    except URLError as exc:
        return None, f'网络不可用（{exc.reason}）'
    except json.JSONDecodeError:
        return None, '接口返回的不是合法 JSON'
    except Exception as exc:  # 兜底，绝不把异常抛给 GUI
        return None, f'{type(exc).__name__}: {exc}'


# --------------------------------------------------------------- 独立工具用的便捷入口
def check_updates(tool_name: str, local_version: str) -> None:
    """老接口：请求接口 → 有新版本就提示并打开下载页。

    保留下来给其它工具复用（行为与原版一致）；本项目的 GUI 走
    `fetch_latest()` + 自绘对话框，体验更好。
    """
    from tkinter import messagebox

    data, error = fetch_latest(tool_name)
    if error:
        messagebox.showerror('更新检查失败', f'无法检查更新：{error}')
        return
    assert data is not None
    server_version = str(data.get('Version') or '')
    if is_newer(server_version, local_version):
        messagebox.showinfo(
            '发现新版本',
            f'当前版本：{local_version}\n最新版本：{server_version}\n\n点击确定后将打开下载链接',
        )
        url = data.get('DownloadUrl')
        if url:
            webbrowser.open(url)


if __name__ == '__main__':  # 手工调试：python gui/update_checker.py 2026.10.18
    import sys as _sys

    _local = _sys.argv[1] if len(_sys.argv) > 1 else '0'
    _info, _err = fetch_latest('MicrosoftRewards')
    if _err:
        print('ERROR:', _err)
    else:
        print('server:', _info)
        print('local :', _local)
        print('newer :', is_newer(str(_info.get('Version')), _local))
