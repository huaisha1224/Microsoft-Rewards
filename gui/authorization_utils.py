#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""授权码校验模块（明文白名单 + 注册表记住）。

定位：挡住「拿免费软件去倒卖」的人，不是防破解 —— 所以故意做得一眼能看懂，
      明文授权码就写在 gui/license_keys.py 里，想改直接改。

机制：
  1. 白名单是明文码集合（VALID_LICENSE_CODES），比较时忽略大小写/空格/横杠；
  2. 首次输入正确授权码后写入 HKCU\\Software\\Huaisha2049\\MicrosoftRewardsHelper，
     之后每次只读注册表，静默通过；
  3. 注册表写失败不阻塞使用：本次放行 + 提示，下次再输即可；
  4. 白名单为空（开源副本没有 license_keys.py）→ 一律放行。

换码：
  双击「01添加授权码.bat」输入新码即可（自动改写 license_keys.py），
  然后跑 build-exe.bat 重新打包。

命令行：
  python gui/authorization_utils.py                  # 查看当前白名单与授权状态
  python gui/authorization_utils.py --add "CODE"     # 添加授权码
  python gui/authorization_utils.py --remove "CODE"  # 作废授权码
"""

__author__ = 'Huaisha2049'

import os
import secrets
import sys
import winreg

REG_KEY_PATH = r'Software\Huaisha2049\MicrosoftRewardsHelper'
REG_VALUE_NAME = 'License'

# 获取授权码的提示语（可按渠道改）
LICENSE_HINT = '在 B 站后台回复关键词「积分」即可获取最新授权码'

# 「获取授权码」按钮打开的页面
LICENSE_PAGE_URL = 'https://space.bilibili.com/37443749'

KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'license_keys.py')

try:
    from license_keys import VALID_LICENSE_CODES
except ImportError:  # 开源副本没有这个文件 → 不做限制
    VALID_LICENSE_CODES = set()


# ------------------------------------------------------------------ 基础逻辑
def normalize(code: str) -> str:
    """去掉所有空白并转大写，用于保存和显示。"""
    return ''.join(str(code).split()).upper()


def _squash(code: str) -> str:
    """只保留字母和数字，用于比较（横杠、空格、大小写都不计较）。"""
    return ''.join(ch for ch in str(code) if ch.isalnum()).upper()


def valid_codes() -> set:
    """当前生效的白名单（已归一化）。"""
    return {_squash(c) for c in VALID_LICENSE_CODES if _squash(c)}


def verify_code(code: str) -> bool:
    """校验授权码。白名单为空（开源构建）时一律放行。"""
    codes = valid_codes()
    if not codes:
        return True
    target = _squash(code)
    return bool(target) and target in codes


def read_license_from_registry() -> str:
    """从注册表读授权码，读不到返回空串（不弹窗、不抛异常）。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, REG_VALUE_NAME)
            return str(value or '')
    except OSError:
        return ''


def write_license_to_registry(code: str) -> bool:
    """写入注册表，成功返回 True。失败静默返回 False（由调用方决定怎么提示）。"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH) as key:
            winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, normalize(code))
        return True
    except OSError:
        return False


def is_authorized() -> bool:
    """静默检查：白名单为空 → True；注册表里有合法码 → True。"""
    if not valid_codes():
        return True
    stored = read_license_from_registry()
    return bool(stored) and verify_code(stored)


# ------------------------------------------------------- 白名单维护（明文改写）
def generate_code(groups: int = 4, size: int = 4) -> str:
    """随机生成授权码，形如 H7K9-3MXP-QW4T-8ZBN（去掉 I/O/0/1 这类易混字符）。"""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    raw = ''.join(secrets.choice(alphabet) for _ in range(groups * size))
    return '-'.join(raw[i:i + size] for i in range(0, len(raw), size))


_TEMPLATE = '''# license_keys.py
# -*- coding:utf-8 -*-
"""授权码白名单（明文，**不进开源仓库**）。

这一个文件就是全部开关：
- 加码：加一行 'XXXX-XXXX-XXXX-XXXX'
        （也可以双击「01添加授权码.bat」输入，它会自动写到这里）
- 作废：删掉对应那行
- 比较时忽略大小写、空格和横杠，用户怎么打都不影响

改完要重新跑 build-exe.bat，装到别人机器上的 exe 才会带新码；
自己用 start-gui.bat 跑源码的话，重启窗口就生效。

sync-github.py 已排除本文件；.gitignore 也加了 /gui/license_keys.py，
开源副本里没有它 → 白名单为空 → 开源构建不做授权限制（这是有意的）。
"""

VALID_LICENSE_CODES = {
%s}
'''


def _write_codes(codes, path: str = None) -> bool:
    """整体重写 license_keys.py（保持同样的模板，字典序）。"""
    path = path or KEYS_FILE
    body = ''.join("    '%s',\n" % code for code in sorted(codes))
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(_TEMPLATE % body)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def add_code(code: str, path: str = None) -> str:
    """加一条码。返回 'added' / 'exists' / 'empty' / 'failed'。"""
    code = normalize(code)
    if not _squash(code):
        return 'empty'
    current = {normalize(c) for c in VALID_LICENSE_CODES if normalize(c)}
    if any(_squash(c) == _squash(code) for c in current):
        return 'exists'
    current.add(code)
    if not _write_codes(current, path):
        return 'failed'
    VALID_LICENSE_CODES.clear()
    VALID_LICENSE_CODES.update(current)
    return 'added'


def remove_code(code: str, path: str = None) -> str:
    """删一条码。返回 'removed' / 'missing' / 'empty' / 'failed'。"""
    code = normalize(code)
    if not _squash(code):
        return 'empty'
    current = {normalize(c) for c in VALID_LICENSE_CODES if normalize(c)}
    left = {c for c in current if _squash(c) != _squash(code)}
    if len(left) == len(current):
        return 'missing'
    if not _write_codes(left, path):
        return 'failed'
    VALID_LICENSE_CODES.clear()
    VALID_LICENSE_CODES.update(left)
    return 'removed'


# ------------------------------------------------------------------ 输入弹窗
def _fonts():
    import customtkinter as ctk

    return {
        'title': ctk.CTkFont(family='Microsoft YaHei UI', size=15, weight='bold'),
        'body': ctk.CTkFont(family='Microsoft YaHei UI', size=12),
        'small': ctk.CTkFont(family='Microsoft YaHei UI', size=11),
    }


def prompt_license(parent) -> bool:
    """弹出授权输入框。通过并已保存（或本次可放行）返回 True，用户取消返回 False。

    必须在主线程调用（GUI 线程），内部用 wait_window 阻塞。
    """
    import customtkinter as ctk

    fonts = _fonts()
    dlg = ctk.CTkToplevel(parent)
    dlg.title('授权验证')
    dlg.resizable(False, False)
    dlg.geometry('440x280')
    dlg.transient(parent)
    try:
        dlg.grab_set()
    except Exception:  # noqa: BLE001
        pass

    # 居中到父窗口
    try:
        parent.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 440) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 280) // 3
        dlg.geometry('+%d+%d' % (max(x, 0), max(y, 0)))
    except Exception:  # noqa: BLE001
        pass

    body = ctk.CTkFrame(dlg, fg_color='transparent')
    body.pack(fill='both', expand=True, padx=24, pady=(20, 8))

    ctk.CTkLabel(body, text='请输入授权码', font=fonts['title'], anchor='w').pack(fill='x')
    ctk.CTkLabel(
        body,
        text='本软件免费提供，近期发现有人倒卖。请输入授权码后继续使用。\n' + LICENSE_HINT,
        font=fonts['small'],
        text_color='gray40',
        justify='left',
        anchor='w',
        wraplength=390,
    ).pack(fill='x', pady=(6, 14))

    entry = ctk.CTkEntry(body, width=390, height=36, font=fonts['body'],
                         placeholder_text='格式示例：XXXX-XXXX-XXXX-XXXX')
    entry.pack(fill='x')

    err = ctk.CTkLabel(body, text='', font=fonts['small'], text_color='#C0392B', anchor='w')
    err.pack(fill='x', pady=(6, 0))

    result = {'ok': False}

    def submit() -> None:
        code = entry.get()
        if not normalize(code):
            err.configure(text='请输入授权码')
            return
        if not verify_code(code):
            err.configure(text='授权码无效，请核对后重新输入')
            entry.select_range(0, 'end')
            entry.focus_set()
            return
        if not write_license_to_registry(code):
            # 码是对的，只是写不了注册表 —— 本次放行，别卡住付费用户
            err.configure(text='授权码正确，但写入注册表失败（本次仍可运行）', text_color='#B8860B')
            dlg.after(1200, lambda: finish(True))
            return
        finish(True)

    def finish(ok: bool) -> None:
        result['ok'] = ok
        try:
            dlg.grab_release()
        except Exception:  # noqa: BLE001
            pass
        dlg.destroy()

    btns = ctk.CTkFrame(dlg, fg_color='transparent')
    btns.pack(fill='x', padx=24, pady=(4, 18))

    def open_page() -> None:
        import webbrowser

        webbrowser.open(LICENSE_PAGE_URL)

    ctk.CTkButton(btns, text='获取授权码', width=104, height=28,
                  font=fonts['small'], fg_color='transparent',
                  hover_color=('gray85', 'gray25'), text_color='#1F6AA5',
                  border_width=1, border_color='#1F6AA5',
                  command=open_page).pack(side='left')

    ctk.CTkButton(btns, text='取消', width=110, fg_color='gray75', hover_color='gray65',
                  text_color='black', command=lambda: finish(False)).pack(side='right')
    ctk.CTkButton(btns, text='确定授权', width=110, command=submit).pack(side='right', padx=(0, 10))

    entry.bind('<Return>', lambda _e: submit())
    dlg.bind('<Escape>', lambda _e: finish(False))
    dlg.protocol('WM_DELETE_WINDOW', lambda: finish(False))
    dlg.after(120, entry.focus_set)

    parent.wait_window(dlg)
    return result['ok']


def check_license(parent=None) -> bool:
    """兼容老接口：已授权直接 True；否则弹框让用户输入。

    parent 传 GUI 窗口；不传则自建临时根窗口（仅适合脚本调试）。
    """
    if is_authorized():
        return True
    if parent is None:
        import tkinter as _tk

        root = _tk.Tk()
        root.withdraw()
        try:
            return prompt_license(root)
        finally:
            root.destroy()
    return prompt_license(parent)


# ------------------------------------------------------------------ CLI
def _main(argv) -> int:
    if len(argv) >= 2 and argv[1] == '--new':
        code = generate_code()
        add_code(code)
        print('已生成并添加新授权码：%s' % code)
        print('把它发给用户，让他填进「授权验证」窗口。')
        print('当前白名单 %d 条：%s' % (len(VALID_LICENSE_CODES), ', '.join(sorted(VALID_LICENSE_CODES)) or '（空）'))
        print('提醒：记得跑 build-exe.bat 重新打包，别人机器上的 exe 才会认这个码。')
        return 0

    if len(argv) >= 3 and argv[1] in ('--add', '--remove'):
        action = argv[1]
        code = argv[2]
        result = add_code(code) if action == '--add' else remove_code(code)
        messages = {
            'added': '已添加：%s' % normalize(code),
            'exists': '已存在，无需重复添加：%s' % normalize(code),
            'removed': '已作废：%s' % normalize(code),
            'missing': '白名单里没有这个码：%s' % normalize(code),
            'empty': '授权码不能为空',
            'failed': '写入 license_keys.py 失败（文件被占用或没有写权限）',
        }
        print(messages.get(result, result))
        print('当前白名单 %d 条：%s' % (len(VALID_LICENSE_CODES), ', '.join(sorted(VALID_LICENSE_CODES)) or '（空）'))
        if result in ('added', 'removed'):
            print('提醒：记得跑 build-exe.bat 重新打包，别人机器上的 exe 才会生效。')
        return 0 if result in ('added', 'exists', 'removed') else 1

    ok = is_authorized()
    print('白名单：%s' % (', '.join(sorted(VALID_LICENSE_CODES)) or '（空 → 不做限制）'))
    print('当前授权状态：%s' % ('已授权' if ok else '未授权'))
    if read_license_from_registry():
        print('注册表里存的码：%s' % read_license_from_registry())
    print('用法：--new 自动生成并添加 | --add CODE 添加指定码 | --remove CODE 作废')
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv))
