# -*- coding: utf-8 -*-
"""Microsoft Rewards 助手 - 桌面配置与运行面板 (Plan B)

A customtkinter shell around the existing Node backend. It edits `.env`
(accounts) and `config.json` (task settings) directly, so no Control API
daemon has to be running, and it can launch `node dist/index.js` itself.

Run with:  python gui/app.py
"""

from __future__ import annotations

import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox
from typing import Dict, List, Optional

import customtkinter as ctk

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_store as cs  # noqa: E402
import env_store  # noqa: E402
import update_checker  # noqa: E402
from client_version import APP_NAME, APP_VERSION, TOOL_NAME  # noqa: E402
from runner import BotRunner, classify, detect_node, detect_system_chrome  # noqa: E402

def _resolve_paths() -> tuple:
    """Find the project root for both `python gui/app.py` and a frozen exe.

    When frozen, ``__file__`` points into PyInstaller's temporary _MEIPASS
    directory, so the real project root is wherever the exe lives.  When run
    from source it is simply the parent of gui/.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        return exe_dir, exe_dir
    gui_dir = os.path.dirname(os.path.abspath(__file__))
    return gui_dir, os.path.dirname(gui_dir)


GUI_DIR, ROOT = _resolve_paths()
ENV_PATH = os.path.join(ROOT, '.env')
CONFIG_PATH = os.path.join(ROOT, 'config.json')
CONFIG_EXAMPLE = os.path.join(ROOT, 'config.example.json')

EMAIL_RE = re.compile(r'^[\w.+-]+@[\w-]+\.[\w.-]+$')

SCOPE_ALL = '全部账号'

GEO_CHOICES = ['CN', 'auto', 'US', 'HK', 'TW', 'JP', 'GB', 'DE', 'FR', 'NL', 'SG', 'AU', 'CA']
LANG_CHOICES = ['zh-CN', 'en', 'en-US', 'en-GB', 'zh-TW', 'ja', 'ko', 'de', 'fr', 'nl', 'pt-BR']

ACCENT = '#2F6FED'
DANGER = '#C0392B'

# 链接参数
# UPSTREAM_URL = 'https://github.com/TheNetsky/Microsoft-Rewards-Script'
UPSTREAM_URL = 'https://space.bilibili.com/37443749'
AFDIAN_URL = 'https://ifdian.net/a/huaisha2049'
VERSION_API = f'{update_checker.DEFAULT_BASE}{TOOL_NAME}'

ctk.set_appearance_mode('light')
ctk.set_default_color_theme('blue')

# CTkFont needs a live Tk root, so these are built right after App() exists.
FONT: Optional[ctk.CTkFont] = None
FONT_BOLD: Optional[ctk.CTkFont] = None
FONT_TITLE: Optional[ctk.CTkFont] = None
FONT_SMALL: Optional[ctk.CTkFont] = None
FONT_MONO: Optional[ctk.CTkFont] = None


def _init_fonts() -> None:
    global FONT, FONT_BOLD, FONT_TITLE, FONT_SMALL, FONT_MONO
    if FONT is not None:
        return
    FONT = ctk.CTkFont(family='Microsoft YaHei UI', size=13)
    FONT_BOLD = ctk.CTkFont(family='Microsoft YaHei UI', size=13, weight='bold')
    FONT_TITLE = ctk.CTkFont(family='Microsoft YaHei UI', size=17, weight='bold')
    FONT_SMALL = ctk.CTkFont(family='Microsoft YaHei UI', size=11)
    FONT_MONO = ctk.CTkFont(family='Consolas', size=12)


def _build_time() -> str:
    """构建时间：打包后取 exe 的修改时间，源码运行时取 app.py 的修改时间。"""
    try:
        target = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(target)))
    except Exception:  # noqa: BLE001
        return '未知'


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        _init_fonts()
        self.title('Microsoft Rewards 助手')
        self.geometry('1060x760')
        self.minsize(960, 640)

        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.config_data: Dict = cs.load(CONFIG_PATH, CONFIG_EXAMPLE)
        self.accounts: List[Dict] = []
        self.selected_slot: Optional[int] = None
        self._row_frames: Dict[int, ctk.CTkFrame] = {}
        self.log_queue: 'queue.Queue[str]' = queue.Queue()
        self.runner = BotRunner()
        self.runner.on_line = lambda line: self.log_queue.put(line)
        self.runner.on_exit = lambda code: self.log_queue.put(f'__EXIT__{code}')

        # 更新检查状态
        self._update_checking = False
        self._update_info: Optional[Dict] = None
        self._update_dialog: Optional[ctk.CTkToplevel] = None

        self._build_layout()
        self.reload_accounts()
        self._load_tasks_into_ui()
        self._refresh_run_controls()
        self.after(120, self._drain_logs)
        # 启动后稍等界面画完再查版本，避免和首屏渲染抢资源
        self.after(800, self._check_update)

        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ---------------------------------------------------------------- layout
    def _build_layout(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=18, pady=(14, 6))

        ctk.CTkLabel(header, text=APP_NAME, font=FONT_TITLE).pack(side='left')
        ctk.CTkLabel(
            header,
            text=f'v{APP_VERSION}',
            font=FONT_SMALL,
            text_color='gray45',
        ).pack(side='left', padx=(8, 0), pady=(5, 0))

        self.tabs = ctk.CTkTabview(self, anchor='w')
        self.tabs.pack(fill='both', expand=True, padx=14, pady=(4, 14))
        for name in ('账号管理', '任务设置', '运行', '关于'):
            self.tabs.add(name)
        seg = getattr(self.tabs, '_segmented_button', None)
        if seg is not None:
            seg.configure(font=FONT)

        self._build_accounts_tab()
        self._build_tasks_tab()
        self._build_run_tab()
        self._build_about_tab()

        self.status = ctk.CTkLabel(self, text='就绪', font=FONT_SMALL, text_color='gray50', anchor='w')
        self.status.pack(fill='x', padx=20, pady=(0, 10))

    def _set_status(self, text: str, color: str = 'gray50') -> None:
        self.status.configure(text=text, text_color=color)

    # --------------------------------------------------------------- tab 1
    def _build_accounts_tab(self) -> None:
        frame = self.tabs.tab('账号管理')

        bar = ctk.CTkFrame(frame, fg_color='transparent')
        bar.pack(fill='x', padx=14, pady=(12, 8))
        for text, width, cmd, color in (
            ('+ 新增账号', 110, self._add_account, ACCENT),
            ('编辑', 80, self._edit_account, None),
            ('删除', 80, self._delete_account, DANGER),
            ('刷新', 80, self.reload_accounts, None),
        ):
            kwargs = {'fg_color': color, 'hover_color': color} if color else {}
            ctk.CTkButton(bar, text=text, width=width, font=FONT, command=cmd, **kwargs).pack(
                side='left', padx=(0, 8)
            )
        ctk.CTkLabel(
            bar,
            text='凭据保存在 .env，列表不显示密码',
            font=FONT_SMALL,
            text_color='gray50',
        ).pack(side='right')

        head = ctk.CTkFrame(frame, fg_color='transparent')
        head.pack(fill='x', padx=14)
        for label, width in (('邮箱', 320), ('区域', 70), ('语言', 90), ('代理', 190), ('凭据', 150)):
            ctk.CTkLabel(head, text=label, width=width, anchor='w', font=FONT_SMALL,
                         text_color='gray50').pack(side='left')

        self.acc_list = ctk.CTkScrollableFrame(frame, label_text='已配置账号', label_font=FONT)
        self.acc_list.pack(fill='both', expand=True, padx=14, pady=(2, 14))

    def reload_accounts(self) -> None:
        try:
            self.accounts = env_store.list_accounts(ENV_PATH)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('读取失败', f'无法解析 .env：\n{exc}')
            self.accounts = []
        if self.selected_slot not in {item['slot'] for item in self.accounts}:
            self.selected_slot = None
        self._render_accounts()
        self._refresh_scope_options()
        self._refresh_run_controls()

    def _render_accounts(self) -> None:
        for child in self.acc_list.winfo_children():
            child.destroy()
        self._row_frames.clear()

        if not self.accounts:
            ctk.CTkLabel(
                self.acc_list,
                text='还没有配置账号。点击「+ 新增账号」开始，写入后会在 .env 生成 ACCOUNT_N_* 字段。',
                font=FONT,
                text_color='gray50',
                wraplength=760,
                justify='left',
            ).pack(anchor='w', padx=10, pady=24)
            return

        for acc in self.accounts:
            row = ctk.CTkFrame(self.acc_list, corner_radius=6, height=34)
            row.pack(fill='x', pady=3)
            row.pack_propagate(False)
            self._row_frames[acc['slot']] = row

            creds = []
            creds.append('密码' if acc['has_password'] else '免密')
            if acc['has_totp']:
                creds.append('TOTP')
            if acc['has_recovery_email']:
                creds.append('恢复邮箱')

            proxy = acc['proxy_url'] or '—'
            if acc['proxy_url'] and acc['proxy_port']:
                proxy = f"{acc['proxy_url']}:{acc['proxy_port']}"

            for text, width in (
                (acc['email'], 320),
                (acc['geo_locale'], 70),
                (acc['lang_code'], 90),
                (proxy, 190),
                (' / '.join(creds), 150),
            ):
                ctk.CTkLabel(row, text=text, width=width, anchor='w', font=FONT).pack(side='left', padx=2)

            self._bind_row_click(row, acc['slot'])
        self._paint_selection()

    def _bind_row_click(self, widget: tk.Misc, slot: int) -> None:
        widget.bind('<Button-1>', lambda _e: self._select(slot))
        for child in widget.winfo_children():
            self._bind_row_click(child, slot)

    def _select(self, slot: int) -> None:
        self.selected_slot = slot
        self._paint_selection()
        self._sync_scope_from_selection()
        self._refresh_run_controls()

    def _paint_selection(self) -> None:
        for slot, row in self._row_frames.items():
            selected = slot == self.selected_slot
            row.configure(fg_color=('#DCE7FF' if selected else '#EEF1F6'))

    # --- account dialog
    def _add_account(self) -> None:
        slot = env_store.next_free_slot(ENV_PATH)
        data = self._account_dialog(slot, None)
        if data is None:
            return
        env_store.upsert_account(ENV_PATH, slot, data)
        self.selected_slot = slot
        self.reload_accounts()
        self._set_status(f'已保存账号 #{slot}：{data["EMAIL"]}', '#1E8449')

    def _edit_account(self) -> None:
        if self.selected_slot is None:
            messagebox.showinfo('提示', '先在列表里选中一个账号。')
            return
        existing = next((a for a in self.accounts if a['slot'] == self.selected_slot), None)
        data = self._account_dialog(self.selected_slot, existing)
        if data is None:
            return
        env_store.upsert_account(ENV_PATH, self.selected_slot, data)
        self.reload_accounts()
        self._set_status(f'已更新账号 #{self.selected_slot}', '#1E8449')

    def _delete_account(self) -> None:
        if self.selected_slot is None:
            messagebox.showinfo('提示', '先在列表里选中一个账号。')
            return
        existing = next((a for a in self.accounts if a['slot'] == self.selected_slot), None)
        email = existing['email'] if existing else f'#{self.selected_slot}'
        if not messagebox.askyesno('确认删除', f'确定删除账号 {email} 吗？\n（.env 中该槽位会被注释掉，可手工恢复）'):
            return
        env_store.delete_account(ENV_PATH, self.selected_slot)
        self.selected_slot = None
        self.reload_accounts()
        self._set_status(f'已删除账号 {email}', '#1E8449')

    def _account_dialog(self, slot: int, existing: Optional[Dict]) -> Optional[Dict[str, Optional[str]]]:
        dialog = ctk.CTkToplevel(self)
        dialog.title(f'账号 #{slot}' if existing is None else f'编辑账号 #{slot}')
        dialog.geometry('560x620')
        dialog.resizable(False, True)
        dialog.transient(self)
        dialog.grab_set()

        result: Dict[str, Optional[str]] = {}

        body = ctk.CTkScrollableFrame(dialog, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=18, pady=14)

        def field(label: str, widget: tk.Misc, hint: str = '') -> None:
            wrap = ctk.CTkFrame(body, fg_color='transparent')
            wrap.pack(fill='x', pady=(0, 10))
            ctk.CTkLabel(wrap, text=label, font=FONT_BOLD).pack(anchor='w')
            widget.pack(fill='x', pady=(3, 0))
            if hint:
                ctk.CTkLabel(wrap, text=hint, font=FONT_SMALL, text_color='gray50',
                             wraplength=500, justify='left').pack(anchor='w')

        ent_email = ctk.CTkEntry(body, font=FONT, placeholder_text='name@outlook.com')
        field('邮箱 *', ent_email)
        if existing:
            ent_email.insert(0, existing['email'])

        ent_pwd = ctk.CTkEntry(body, font=FONT, show='●')
        field('密码', ent_pwd, '留空表示不修改。无密码 / 仅用 Authenticator 的账号可留空。')
        if existing and existing['has_password']:
            ent_pwd.configure(placeholder_text='（已保存，留空不修改）')

        ent_totp = ctk.CTkEntry(body, font=FONT, show='●')
        field('TOTP 密钥', ent_totp, '两步验证的 secret（非每次的 6 位数字）。留空表示不修改。')
        if existing and existing['has_totp']:
            ent_totp.configure(placeholder_text='（已保存，留空不修改）')

        ent_recover = ctk.CTkEntry(body, font=FONT)
        field('恢复邮箱', ent_recover, '选填，用于登录验证时自动选择。')
        if existing and existing['has_recovery_email']:
            ent_recover.configure(placeholder_text='（已保存，留空表示清除）')

        region_row = ctk.CTkFrame(body, fg_color='transparent')
        region_row.pack(fill='x', pady=(0, 10))
        ctk.CTkLabel(region_row, text='区域 / 语言', font=FONT_BOLD).pack(anchor='w')
        inner = ctk.CTkFrame(region_row, fg_color='transparent')
        inner.pack(fill='x', pady=(3, 0))
        cmb_geo = ctk.CTkComboBox(inner, values=GEO_CHOICES, font=FONT, width=150)
        cmb_geo.pack(side='left')
        cmb_lang = ctk.CTkComboBox(inner, values=LANG_CHOICES, font=FONT, width=150)
        cmb_lang.pack(side='left', padx=10)
        ctk.CTkLabel(inner, text='国内账号建议 CN + zh-CN', font=FONT_SMALL,
                     text_color='gray50').pack(side='left')
        cmb_geo.set((existing or {}).get('geo_locale', 'CN') or 'CN')
        cmb_lang.set((existing or {}).get('lang_code', 'zh-CN') or 'zh-CN')

        ctk.CTkLabel(body, text='代理（选填）', font=FONT_BOLD).pack(anchor='w', pady=(8, 0))
        ent_proxy_url = ctk.CTkEntry(body, font=FONT, placeholder_text='http://127.0.0.1 或 socks5://...')
        field('代理地址', ent_proxy_url)
        ent_proxy_port = ctk.CTkEntry(body, font=FONT, placeholder_text='8080')
        field('代理端口', ent_proxy_port)
        ent_proxy_user = ctk.CTkEntry(body, font=FONT)
        field('代理用户名', ent_proxy_user, 'SOCKS 代理不支持带认证的写法。')
        ent_proxy_pwd = ctk.CTkEntry(body, font=FONT, show='●')
        field('代理密码', ent_proxy_pwd)
        if existing:
            ent_proxy_url.insert(0, existing['proxy_url'])
            ent_proxy_port.insert(0, str(existing['proxy_port']))
            if existing['has_proxy_credentials']:
                ent_proxy_user.configure(placeholder_text='（已保存，留空不修改）')
                ent_proxy_pwd.configure(placeholder_text='（已保存，留空不修改）')

        chk_mobile = ctk.CTkCheckBox(body, text='保存移动端浏览器指纹', font=FONT)
        chk_mobile.pack(anchor='w', pady=(6, 2))
        chk_desktop = ctk.CTkCheckBox(body, text='保存桌面端浏览器指纹', font=FONT)
        chk_desktop.pack(anchor='w')
        if existing:
            if existing['save_fingerprint_mobile']:
                chk_mobile.select()
            if existing['save_fingerprint_desktop']:
                chk_desktop.select()
        else:
            chk_mobile.select()
            chk_desktop.select()

        def submit() -> None:
            email = ent_email.get().strip()
            if not EMAIL_RE.match(email):
                messagebox.showwarning('邮箱格式不对', f'请填写有效邮箱地址：\n{email}')
                return
            result.update(
                {
                    'EMAIL': email,
                    # empty string = leave the stored secret untouched
                    'PASSWORD': ent_pwd.get().strip() or (None if existing else ''),
                    'TOTP_SECRET': ent_totp.get().strip() or None,
                    'RECOVERY_EMAIL': ent_recover.get().strip() or (None if existing else ''),
                    'GEO_LOCALE': cmb_geo.get().strip() or 'auto',
                    'LANG_CODE': cmb_lang.get().strip() or 'en',
                    'PROXY_URL': ent_proxy_url.get().strip(),
                    'PROXY_PORT': ent_proxy_port.get().strip() or '0',
                    'PROXY_USERNAME': ent_proxy_user.get().strip() or None,
                    'PROXY_PASSWORD': ent_proxy_pwd.get().strip() or None,
                    'SAVE_FINGERPRINT_MOBILE': 'true' if chk_mobile.get() else 'false',
                    'SAVE_FINGERPRINT_DESKTOP': 'true' if chk_desktop.get() else 'false',
                }
            )
            dialog.destroy()

        footer = ctk.CTkFrame(dialog, fg_color='transparent')
        footer.pack(fill='x', padx=18, pady=(0, 16))
        ctk.CTkButton(footer, text='取消', width=90, font=FONT, fg_color='gray60',
                      hover_color='gray50', command=dialog.destroy).pack(side='right', padx=(8, 0))
        ctk.CTkButton(footer, text='保存', width=90, font=FONT, command=submit).pack(side='right')

        dialog.wait_window()
        return result or None

    # --------------------------------------------------------------- tab 2
    def _build_tasks_tab(self) -> None:
        frame = self.tabs.tab('任务设置')

        top = ctk.CTkFrame(frame, fg_color='transparent')
        top.pack(fill='x', padx=16, pady=(14, 6))
        ctk.CTkLabel(top, text='速度档位', font=FONT_BOLD).pack(side='left')
        self.preset_var = tk.StringVar(value='标准')
        self.preset_bar = ctk.CTkSegmentedButton(
            top,
            values=cs.PRESET_ORDER + ['自定义'],
            variable=self.preset_var,
            font=FONT,
            width=380,
            command=self._on_preset,
        )
        self.preset_bar.pack(side='left', padx=12)

        self.preset_hint = ctk.CTkLabel(frame, text='', font=FONT_SMALL, text_color='gray50',
                                        wraplength=940, justify='left')
        self.preset_hint.pack(fill='x', padx=18, pady=(0, 8))

        box = ctk.CTkScrollableFrame(frame, label_text='任务开关', label_font=FONT)
        box.pack(fill='both', expand=True, padx=16, pady=(0, 8))

        # 12 个开关排 3 列 x 4 行，比 2 列 6 行矮一半，正好塞进可视区
        COLS = 3
        grid = ctk.CTkFrame(box, fg_color='transparent')
        grid.pack(fill='both', expand=True)
        grid.grid_columnconfigure(tuple(range(COLS)), weight=1)

        self.worker_vars: Dict[str, tk.BooleanVar] = {}
        for i, (key, label, tip) in enumerate(cs.WORKER_FIELDS):
            var = tk.BooleanVar(value=False)
            self.worker_vars[key] = var
            cell = ctk.CTkFrame(grid, corner_radius=6, fg_color='#F4F6FA')
            cell.grid(row=i // COLS, column=i % COLS, sticky='nsew', padx=4, pady=3)
            chk = ctk.CTkCheckBox(cell, text=label, variable=var, font=FONT,
                                  command=self._on_worker_toggle)
            chk.pack(anchor='w', padx=10, pady=(8, 0))
            ctk.CTkLabel(cell, text=tip, font=FONT_SMALL, text_color='gray50',
                         wraplength=250, justify='left').pack(anchor='w', padx=10, pady=(0, 8))

        pace = ctk.CTkFrame(frame, fg_color='transparent')
        pace.pack(fill='x', padx=16, pady=(10, 4))
        ctk.CTkLabel(pace, text='搜索节奏', font=FONT_BOLD).pack(side='left')
        self.delay_var = tk.StringVar(value='官方默认')
        self.delay_bar = ctk.CTkSegmentedButton(
            pace,
            values=cs.DELAY_ORDER + ['自定义'],
            variable=self.delay_var,
            font=FONT,
            width=520,
            command=self._on_delay_preset,
        )
        self.delay_bar.pack(side='left', padx=12)

        self.delay_hint = ctk.CTkLabel(frame, text='', font=FONT_SMALL, text_color='gray50',
                                       wraplength=940, justify='left')
        self.delay_hint.pack(fill='x', padx=18, pady=(0, 6))

        adv = ctk.CTkFrame(frame, fg_color='transparent')
        adv.pack(fill='x', padx=16, pady=(6, 4))
        self.var_headless = tk.BooleanVar(value=False)
        self.var_debug = tk.BooleanVar(value=False)
        self.var_humanize = tk.BooleanVar(value=False)
        ctk.CTkSwitch(adv, text='无头模式（不弹浏览器窗口）', variable=self.var_headless,
                      font=FONT).pack(side='left', padx=(0, 16))
        ctk.CTkSwitch(adv, text='调试日志', variable=self.var_debug, font=FONT).pack(side='left', padx=(0, 16))
        ctk.CTkSwitch(adv, text='拟人化（随机完成度 + 静默时段）', variable=self.var_humanize,
                      font=FONT).pack(side='left')

        adv2 = ctk.CTkFrame(frame, fg_color='transparent')
        adv2.pack(fill='x', padx=16, pady=(0, 10))
        ctk.CTkLabel(adv2, text='并发账号数', font=FONT).pack(side='left')
        self.cmb_clusters = ctk.CTkComboBox(adv2, values=[str(i) for i in range(1, 9)],
                                            width=70, font=FONT)
        self.cmb_clusters.pack(side='left', padx=6)
        ctk.CTkLabel(adv2, text='浏览器', font=FONT).pack(side='left', padx=(16, 0))
        self.cmb_channel = ctk.CTkComboBox(adv2, values=['chromium', 'chrome', 'msedge'],
                                           width=110, font=FONT)
        self.cmb_channel.pack(side='left', padx=6)
        ctk.CTkButton(adv2, text='保存设置', width=100, font=FONT, command=self._save_tasks).pack(side='right')
        ctk.CTkButton(adv2, text='重新载入', width=90, font=FONT, fg_color='gray60',
                      hover_color='gray50', command=self._load_tasks_into_ui).pack(side='right', padx=(0, 8))

    def _load_tasks_into_ui(self) -> None:
        self.config_data = cs.load(CONFIG_PATH, CONFIG_EXAMPLE)
        simple = cs.get_simple(self.config_data)
        for key, var in self.worker_vars.items():
            var.set(bool(simple['workers'].get(key, False)))
        self.var_headless.set(simple['headless'])
        self.var_debug.set(simple['debugLogs'])
        self.var_humanize.set(simple['humanize'])
        self.cmb_clusters.set(str(simple['clusters']))
        self.cmb_channel.set(simple['browserChannel'])
        preset = cs.detect_preset(self.config_data)
        self.preset_var.set(preset)
        self.preset_hint.configure(text=cs.PRESET_HINTS.get(preset, '当前为自定义组合，保存后以实际开关为准。'))

        delay = cs.detect_delay_preset(self.config_data)
        self.delay_var.set(delay)
        self.delay_hint.configure(
            text=cs.DELAY_HINTS.get(delay, '当前为自定义间隔，保存后以 config.json 中的实际值为准。')
        )

    def _on_preset(self, value: str) -> None:
        if value == '自定义':
            self.preset_hint.configure(text='当前为自定义组合，保存后以实际开关为准。')
            return
        for key, enabled in cs.PRESET_WORKERS[value].items():
            self.worker_vars[key].set(enabled)
        self.preset_hint.configure(text=cs.PRESET_HINTS.get(value, ''))

    def _on_delay_preset(self, value: str) -> None:
        self.delay_hint.configure(
            text=cs.DELAY_HINTS.get(value, '当前为自定义间隔，保存后以 config.json 中的实际值为准。')
        )

    def _on_worker_toggle(self) -> None:
        workers = {key: var.get() for key, var in self.worker_vars.items()}
        matched = ''
        for name in cs.PRESET_ORDER:
            if workers == cs.PRESET_WORKERS[name]:
                matched = name
                break
        self.preset_var.set(matched or '自定义')
        self.preset_hint.configure(
            text=cs.PRESET_HINTS.get(matched, '当前为自定义组合，保存后以实际开关为准。')
        )

    def _save_tasks(self) -> None:
        simple = {
            'headless': self.var_headless.get(),
            'debugLogs': self.var_debug.get(),
            'humanize': self.var_humanize.get(),
            'clusters': int(self.cmb_clusters.get() or 1),
            'browserChannel': self.cmb_channel.get() or 'chromium',
            'workers': {key: var.get() for key, var in self.worker_vars.items()},
            'delay_preset': self.delay_var.get(),
        }
        cs.apply_simple(self.config_data, simple)
        try:
            cs.save(CONFIG_PATH, self.config_data)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('保存失败', f'写入 config.json 出错：\n{exc}')
            return
        self._set_status(f'已保存 config.json（旧版本已备份为 config.json.bak）', '#1E8449')
        self._refresh_browser_status()

    def _refresh_browser_status(self) -> None:
        """Show whether the configured browser channel is actually usable."""
        channel = str((self.config_data or {}).get('browserChannel') or 'chromium')
        if channel == 'chrome':
            if detect_system_chrome():
                self.lbl_browser.configure(
                    text='浏览器：使用系统 Google Chrome（已检测到，无需额外下载）',
                    text_color=ACCENT,
                )
            else:
                self.lbl_browser.configure(
                    text='⚠ 未检测到系统 Google Chrome：请先安装 Chrome，否则任务无法启动',
                    text_color=DANGER,
                )
        elif channel == 'msedge':
            self.lbl_browser.configure(
                text='浏览器：系统 Microsoft Edge（实验性选项，访问积分页面可能崩溃）',
                text_color='gray50',
            )
        else:
            self.lbl_browser.configure(
                text='浏览器：内置补丁版 Chromium（需要本机已下载浏览器组件）',
                text_color='gray50',
            )

    # --------------------------------------------------------------- tab 3
    def _build_run_tab(self) -> None:
        frame = self.tabs.tab('运行')

        bar = ctk.CTkFrame(frame, fg_color='transparent')
        bar.pack(fill='x', padx=16, pady=(14, 8))
        self.btn_start = ctk.CTkButton(bar, text='开始', width=110, font=FONT_BOLD,
                                       fg_color='#1E8449', hover_color='#186A3B',
                                       command=self._start)
        self.btn_start.pack(side='left')
        self.btn_stop = ctk.CTkButton(bar, text='停止', width=90, font=FONT,
                                      fg_color=DANGER, hover_color='#96281B', state='disabled',
                                      command=self._stop)
        self.btn_stop.pack(side='left', padx=8)

        ctk.CTkLabel(bar, text='跑哪个账号', font=FONT).pack(side='left', padx=(16, 0))
        self.scope_var = tk.StringVar(value=SCOPE_ALL)
        self.cmb_scope = ctk.CTkComboBox(bar, values=[SCOPE_ALL], variable=self.scope_var,
                                         width=300, font=FONT)
        self.cmb_scope.pack(side='left', padx=6)
        self.lbl_scope = ctk.CTkLabel(bar, text='', font=FONT_SMALL, text_color='gray50')
        self.lbl_scope.pack(side='left')
        # Driven by the variable, not by `command=` - `command` only fires when the
        # user picks from the dropdown, so programmatic set() would leave the hint stale.
        self.scope_var.trace_add('write', lambda *_: self._refresh_run_controls())

        cards = ctk.CTkFrame(frame, fg_color='transparent')
        cards.pack(fill='x', padx=16, pady=(0, 10))
        self.stat_state = self._stat_card(cards, '状态', '空闲')
        self.stat_account = self._stat_card(cards, '当前账号', '—')
        self.stat_points = self._stat_card(cards, '本次获得', '0')

        node_row = ctk.CTkFrame(frame, fg_color='transparent')
        node_row.pack(fill='x', padx=16, pady=(0, 8))
        ctk.CTkLabel(node_row, text='Node 可执行文件', font=FONT).pack(side='left')
        self.ent_node = ctk.CTkEntry(node_row, font=FONT_SMALL)
        self.ent_node.pack(side='left', fill='x', expand=True, padx=8)
        self.ent_node.insert(0, detect_node())
        ctk.CTkButton(node_row, text='浏览…', width=80, font=FONT, command=self._browse_node).pack(side='left')

        self.lbl_browser = ctk.CTkLabel(frame, text='', font=FONT_SMALL, justify='left')
        self.lbl_browser.pack(anchor='w', padx=16, pady=(0, 8))
        self._refresh_browser_status()

        log_head = ctk.CTkFrame(frame, fg_color='transparent')
        log_head.pack(fill='x', padx=16, pady=(4, 2))
        ctk.CTkLabel(log_head, text='运行日志', font=FONT_BOLD).pack(side='left')
        self.var_autoscroll = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(log_head, text='自动滚动', variable=self.var_autoscroll,
                        font=FONT_SMALL).pack(side='right')
        ctk.CTkButton(log_head, text='清空', width=70, font=FONT_SMALL, fg_color='gray60',
                      hover_color='gray50', command=self._clear_log).pack(side='right', padx=(0, 10))

        self.log = ctk.CTkTextbox(frame, font=FONT_MONO, wrap='none', activate_scrollbars=True)
        self.log.pack(fill='both', expand=True, padx=16, pady=(0, 16))
        self.log.tag_config('error', foreground='#C0392B')
        self.log.tag_config('warn', foreground='#B9770E')
        self.log.tag_config('ok', foreground='#1E8449')
        self.log.tag_config('info', foreground='#333333')
        self.log.configure(state='disabled')

    def _stat_card(self, parent: tk.Misc, title: str, value: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, corner_radius=8, fg_color='#F4F6FA', width=220, height=62)
        card.pack(side='left', padx=(0, 10))
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=title, font=FONT_SMALL, text_color='gray50').pack(anchor='w', padx=12, pady=(7, 0))
        label = ctk.CTkLabel(card, text=value, font=FONT_BOLD)
        label.pack(anchor='w', padx=12)
        return label

    def _browse_node(self) -> None:
        path = filedialog.askopenfilename(title='选择 node.exe', filetypes=[('node', 'node.exe'), ('All', '*.*')])
        if path:
            self.ent_node.delete(0, 'end')
            self.ent_node.insert(0, path)

    # --- run scope (which account to run) ----------------------------------
    def _scope_options(self) -> List[str]:
        return [SCOPE_ALL] + ['#%d  %s' % (acc['slot'], acc['email']) for acc in self.accounts]

    def _refresh_scope_options(self) -> None:
        """Rebuild the account picker and keep the current choice if still valid."""
        options = self._scope_options()
        current = self.cmb_scope.get()
        self.cmb_scope.configure(values=options)
        self.cmb_scope.set(current if current in options else SCOPE_ALL)

    def _selected_scope_slot(self) -> Optional[int]:
        """Slot number chosen in the run tab, or None for 'all accounts'."""
        value = self.cmb_scope.get().strip()
        if not value or value == SCOPE_ALL:
            return None
        match = re.match(r'#(\d+)', value)
        return int(match.group(1)) if match else None

    def _sync_scope_from_selection(self) -> None:
        """Mirror the account-manager selection into the run tab picker."""
        if self.selected_slot is None:
            return
        acc = next((a for a in self.accounts if a['slot'] == self.selected_slot), None)
        if acc is not None:
            self.cmb_scope.set('#%d  %s' % (acc['slot'], acc['email']))

    def _refresh_run_controls(self) -> None:
        running = self.runner.running
        self.btn_start.configure(state='disabled' if running else 'normal')
        self.btn_stop.configure(state='normal' if running else 'disabled')

        slot = self._selected_scope_slot()
        if slot is None:
            self.lbl_scope.configure(
                text='共 %d 个账号，按编号从小到大依次执行' % len(self.accounts) if self.accounts
                else '尚未添加账号，请到「账号管理」添加',
                text_color='gray50',
            )
            return
        acc = next((a for a in self.accounts if a['slot'] == slot), None)
        if acc is None:
            self.lbl_scope.configure(text='该账号已不存在，请重新选择', text_color=DANGER)
        else:
            self.lbl_scope.configure(text='只跑 %s' % acc['email'], text_color='gray50')

    def _start(self) -> None:
        node_exe = self.ent_node.get().strip()
        if not node_exe or not os.path.isfile(node_exe):
            messagebox.showwarning('找不到 Node', '请指定正确的 node.exe（项目要求 Node ≥ 24）。')
            return
        if not os.path.isfile(os.path.join(ROOT, 'dist', 'index.js')):
            messagebox.showwarning(
                '尚未构建',
                '缺少 dist/index.js。请先在项目目录执行：\n\n  npm install\n  npm run build',
            )
            return
        if str((self.config_data or {}).get('browserChannel') or 'chromium') == 'chrome' \
                and not detect_system_chrome():
            messagebox.showwarning(
                '缺少浏览器',
                '当前浏览器设置为「系统 Chrome」，但本机未检测到 Google Chrome。\n\n'
                '请先安装 Chrome，或在「任务设置」里把浏览器改回 chromium。',
            )
            return
        if not self.accounts:
            messagebox.showinfo('没有账号', '请先在「账号管理」里添加至少一个账号。')
            return

        slot = self._selected_scope_slot()
        if slot is not None and slot not in {a['slot'] for a in self.accounts}:
            messagebox.showinfo('账号不存在', '所选账号已不存在，请重新选择要跑的账号。')
            return
        scope = SCOPE_ALL if slot is None else \
            next(a['email'] for a in self.accounts if a['slot'] == slot)

        try:
            overrides = env_store.child_env_for_slot(ENV_PATH, slot)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('读取 .env 失败', str(exc))
            return

        self._clear_log()
        try:
            self.runner.start(node_exe, ROOT, env_overrides=overrides)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('启动失败', str(exc))
            return

        self.stat_state.configure(text='运行中')
        self.stat_points.configure(text='0')
        self._append_log(f'$ node dist/index.js   [{scope}]', 'info')
        self._refresh_run_controls()
        self._set_status('任务运行中…', ACCENT)

    def _stop(self) -> None:
        self.runner.stop()
        self._append_log('已请求停止…', 'warn')
        self._set_status('正在停止…')

    # --- log plumbing
    def _clear_log(self) -> None:
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')

    def _append_log(self, text: str, tag: str = 'info') -> None:
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n', tag)
        if int(float(self.log.index('end'))) > 4000:
            self.log.delete('1.0', '600.0')
        if self.var_autoscroll.get():
            self.log.see('end')
        self.log.configure(state='disabled')

    def _drain_logs(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                if line.startswith('__EXIT__'):
                    code = line[len('__EXIT__'):]
                    self._append_log(f'=== 进程结束，退出码 {code} ===', 'ok' if code == '0' else 'error')
                    self.stat_state.configure(text='空闲')
                    self._refresh_run_controls()
                    self._set_status(f'任务结束（退出码 {code}）')
                    continue
                tag = classify(line)
                self._append_log(line, tag)
                self._update_live_stats(line)
        except queue.Empty:
            pass
        self.after(120, self._drain_logs)

    def _update_live_stats(self, line: str) -> None:
        from runner import BALANCE_RE, EMAIL_RE, GAIN_RE

        email = EMAIL_RE.search(line)
        if email and ('account' in line.lower() or '账号' in line):
            self.stat_account.configure(text=email.group(0))
        gained = GAIN_RE.search(line)
        if gained:
            self.stat_points.configure(text=gained.group(1))
        balance = BALANCE_RE.search(line)
        if balance:
            self.stat_points.configure(text=f'{gained.group(1) if gained else "0"}（余额 {balance.group(1)}）')

    # --------------------------------------------------------------- tab 4
    def _build_about_tab(self) -> None:
        frame = self.tabs.tab('关于')
        box = ctk.CTkScrollableFrame(frame, fg_color='transparent')
        box.pack(fill='both', expand=True, padx=16, pady=(12, 10))
        self.about_box = box  # 供调试 / 截图脚本滚动用

        wrap = 860

        def card(title: str, bg: str = '#F4F6FA', border: Optional[str] = None,
                 title_color: str = '#22303C') -> ctk.CTkFrame:
            outer = ctk.CTkFrame(
                box,
                corner_radius=8,
                fg_color=bg,
                border_width=1 if border else 0,
                border_color=border or bg,
            )
            outer.pack(fill='x', pady=(0, 9))
            ctk.CTkLabel(
                outer, text=title, font=FONT_BOLD, text_color=title_color, anchor='w'
            ).pack(fill='x', padx=16, pady=(12, 2))
            return outer

        def para(parent: ctk.CTkFrame, text: str, color: str = '#3A4550', bottom: int = 12) -> None:
            ctk.CTkLabel(
                parent,
                text=text,
                font=FONT,
                text_color=color,
                anchor='w',
                justify='left',
                wraplength=wrap,
            ).pack(fill='x', padx=16, pady=(0, bottom))

        # ---- 头部：名称 / 版本 / 快捷操作
        head = ctk.CTkFrame(box, corner_radius=8, fg_color='#EAF1FD')
        head.pack(fill='x', pady=(0, 9))
        ctk.CTkLabel(
            head, text=APP_NAME, font=FONT_TITLE, text_color='#1B2A3A', anchor='w'
        ).pack(fill='x', padx=16, pady=(14, 0))
        ctk.CTkLabel(
            head,
            text=f'版本 v{APP_VERSION}　·　构建于 {_build_time()}　·　Windows 10/11 64 位',
            font=FONT_SMALL,
            text_color='#4A5A6A',
            anchor='w',
        ).pack(fill='x', padx=16, pady=(2, 10))

        row = ctk.CTkFrame(head, fg_color='transparent')
        row.pack(anchor='w', padx=16, pady=(0, 14))
        ctk.CTkButton(
            row,
            text='检查更新',
            width=96,
            height=30,
            font=FONT,
            fg_color=ACCENT,
            hover_color='#245BC7',
            command=lambda: self._check_update(silent=False),
        ).pack(side='left')
        # ctk.CTkButton(
        #     row,
        #     text='打开程序目录',
        #     width=112,
        #     height=30,
        #     font=FONT,
        #     fg_color='transparent',
        #     border_width=1,
        #     border_color='#9FB4D6',
        #     text_color='#2A3B4D',
        #     hover_color='#DCE7F9',
        #     command=self._open_root_dir,
        # ).pack(side='left', padx=(10, 0))
        ctk.CTkButton(
            row,
            text='不会用看这里',
            width=126,
            height=30,
            font=FONT,
            fg_color='transparent',
            border_width=1,
            border_color='#9FB4D6',
            text_color='#2A3B4D',
            hover_color='#DCE7F9',
            command=lambda: self._open_download(UPSTREAM_URL),
        ).pack(side='left', padx=(10, 0))

        # ---- 功能
        about = card('关于')
        para(
            about,
            '· 本软件是基于开源项目Microsoft-Rewards-Script v4 China版本的二次开发，添加了GUI界面方便使用。\n'
            '· 软件完全免费，不包含任何广告或弹窗，不收集任何个人信息。\n'
            '· 如果你觉得本软件有帮助，可以给个爱发电，谢谢！\n'
        )
        link_row = ctk.CTkFrame(about, fg_color='transparent')
        link_row.pack(fill='x', padx=16, pady=(0, 12))
        sponsor = ctk.CTkLabel(
            link_row,
            text='♥ 点击这里支持一下（爱发电）',
            font=FONT_BOLD,
            text_color='#E0507A',
            cursor='hand2',
        )
        sponsor.pack(side='left')
        sponsor.bind('<Button-1>', lambda _e: self._open_download(AFDIAN_URL))
        ctk.CTkButton(
            link_row,
            text='打开爱发电',
            width=96,
            height=26,
            font=FONT_SMALL,
            fg_color='#E0507A',
            hover_color='#C63D66',
            command=lambda: self._open_download(AFDIAN_URL),
        ).pack(side='left', padx=(12, 0))
        url_label = ctk.CTkLabel(
            link_row,
            text=AFDIAN_URL,
            font=FONT_SMALL,
            text_color='#8A94A6',
            cursor='hand2',
        )
        url_label.pack(side='right')
        url_label.bind('<Button-1>', lambda _e: self._open_download(AFDIAN_URL))

        # ---- 上手
        # para(
        #     card('怎么用'),
        #     '1. 「账号管理」填微软账号邮箱与密码；开了两步验证的，再填 TOTP 密钥\n'
        #     '2. 「任务设置」选速度档位与任务开关；浏览器保持 chrome 即可，直接用系统安装的 Google Chrome\n'
        #     '3. 「运行」选择账号后点开始。首次运行会在弹出的浏览器里要求手动登录一次，'
        #     '之后交给 sessions 里的会话自动完成\n'
        #     '4. 建议每天固定时间跑一次；跑之前别手动用同一个号搜太多，否则配额会先被消耗掉',
        # )

        # ---- 数据与隐私
        # para(
        #     card('数据与隐私'),
        #     '· 所有数据只存在本机程序目录，不上传云端：\n'
        #     '      .env（账号密码，明文）、sessions（登录状态）、config.json（任务设置）、logs（运行日志）\n'
        #     f'· 唯一的外部请求是检查更新：向 {VERSION_API} 取版本号与下载地址，不上报任何账号信息\n'
        #     '· sessions 目录删掉就要重新登录；换电脑时把整个程序目录拷过去即可（含 .env 与 sessions）\n'
        #     '· .env 是明文保存密码的，不要把程序目录连同 .env 一起发给别人',
        # )

        # ---- 免责声明（醒目色块）
        warn = card('免责声明', bg='#FFF7E8', border='#E3B04B', title_color='#8A5300')
        para(
            warn,
            '· 使用自动化脚本获取 Rewards 积分可能违反 Microsoft 服务条款，存在积分被清零、'
            '账号被限制功能或永久封禁的风险。是否使用、用在哪个账号上，请你自行判断并承担后果\n'
            '· 因使用或无法使用本软件而造成的账号异常、积分损失、数据丢失或其它任何直接、间接损失，'
            '作者不承担任何责任\n'
            '· 本项目仅供学习与技术交流，请在使用后 24 小时内删除，并优先使用微软官方服务；'
            '使用者应自行遵守所在地法律法规与微软服务条款',
            color='#6B4A0F',
            bottom=14,
        )

        # ---- 致谢
        para(
            card('致谢与技术栈'),
            '· 上游项目：TheNetsky / Microsoft-Rewards-Script（v4 架构，GPL-3.0 许可）；\n'
            '  本项目是其国内本地化分支（V4-china），同样以 GPL-3.0 开源，修改点见仓库 README\n'
            '· 浏览器自动化：Patchright（Playwright 反检测内核）；编程语言：TypeScript / Node.js 24\n'
            '· 图形界面：Python + customtkinter；打包：PyInstaller\n',
            bottom=8,
        )

    def _open_root_dir(self) -> None:
        try:
            os.startfile(ROOT)  # noqa: S606 - Windows only
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('打开失败', f'{exc}\n\n目录：{ROOT}')

    # ------------------------------------------------------------- 版本更新
    def _check_update(self, silent: bool = True) -> None:
        """查询版本接口。silent=True 用于启动自动检查（失败不打扰用户）。"""
        if self._update_checking:
            return
        self._update_checking = True
        if not silent:
            self._set_status('正在检查更新…')
        threading.Thread(target=self._update_worker, args=(silent,), daemon=True).start()

    def _update_worker(self, silent: bool) -> None:
        data, error = update_checker.fetch_latest(TOOL_NAME)
        try:
            self.after(0, lambda: self._on_update_result(data, error, silent))
        except Exception:
            self._update_checking = False

    def _on_update_result(self, data: Optional[Dict], error: Optional[str], silent: bool) -> None:
        self._update_checking = False

        if error or not data:
            if not silent:
                self._set_status(f'检查更新失败：{error}', DANGER)
            return

        server = str(data.get('Version') or '')
        if update_checker.is_newer(server, APP_VERSION):
            self._update_info = data
            self._set_status(f'发现新版本 v{server}（当前 v{APP_VERSION}）', ACCENT)
            self._show_update_dialog(data)
        elif not silent:
            self._set_status(f'已是最新版本 v{APP_VERSION}', '#1E8E3E')

    def _show_update_dialog(self, info: Dict) -> None:
        """自绘更新提示框；出任何异常都退回原生 messagebox。"""
        server = str(info.get('Version') or '')
        desc = str(info.get('Description') or '').strip()
        url = str(info.get('DownloadUrl') or '').strip()

        if self._update_dialog is not None:
            try:
                if self._update_dialog.winfo_exists():
                    self._update_dialog.deiconify()
                    self._update_dialog.lift()
                    self._update_dialog.focus_force()
                    return
            except Exception:
                pass
            self._update_dialog = None

        try:
            dlg = ctk.CTkToplevel(self)
        except Exception:
            if messagebox.askyesno(
                '发现新版本',
                f'当前版本：v{APP_VERSION}\n最新版本：v{server}\n\n是否打开下载页面？',
            ):
                self._open_download(url)
            return

        self._update_dialog = dlg
        dlg.title('发现新版本')
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.protocol('WM_DELETE_WINDOW', dlg.destroy)

        body = ctk.CTkFrame(dlg, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=22, pady=(18, 10))

        ctk.CTkLabel(body, text=f'发现新版本 v{server}', font=FONT_TITLE, anchor='w').pack(
            fill='x'
        )
        ctk.CTkLabel(
            body,
            text=f'当前版本 v{APP_VERSION}　→　最新版本 v{server}',
            font=FONT_SMALL,
            text_color='gray40',
            anchor='w',
        ).pack(fill='x', pady=(4, 0))
        # if desc:
        #     ctk.CTkLabel(
        #         body,
        #         text=f'更新说明：{desc}',
        #         font=FONT_SMALL,
        #         text_color='gray30',
        #         anchor='w',
        #         justify='left',
        #         wraplength=400,
        #     ).pack(fill='x', pady=(10, 0))
        # ctk.CTkLabel(
        #     body,
        #     text='点击「立即更新」会用浏览器打开下载页面，下载后替换旧的 MRS助手.exe 即可\n'
        #     '（同目录下的 node.exe / dist / sessions 不用动）。',
        #     font=FONT_SMALL,
        #     text_color='gray50',
        #     anchor='w',
        #     justify='left',
        #     wraplength=400,
        # ).pack(fill='x', pady=(12, 0))

        btns = ctk.CTkFrame(dlg, fg_color='transparent')
        btns.pack(fill='x', padx=22, pady=(4, 18))

        def _later() -> None:
            try:
                dlg.destroy()
            finally:
                self._update_dialog = None

        def _go() -> None:
            self._open_download(url)
            _later()

        ctk.CTkButton(
            btns,
            text='稍后再说',
            width=96,
            height=32,
            font=FONT,
            fg_color='transparent',
            border_width=1,
            border_color='#B9C0CC',
            text_color='#33414F',
            hover_color='#EDF1F7',
            command=_later,
        ).pack(side='right')
        ctk.CTkButton(
            btns,
            text='立即更新',
            width=110,
            height=32,
            font=FONT_BOLD,
            fg_color=ACCENT,
            hover_color='#245BC7',
            command=_go,
        ).pack(side='right', padx=(0, 10))

        dlg.update_idletasks()
        width, height = 470, dlg.winfo_reqheight()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - width) // 2
            y = self.winfo_rooty() + (self.winfo_height() - height) // 3
        except Exception:
            x = y = 200
        dlg.geometry(f'{width}x{height}+{max(x, 0)}+{max(y, 0)}')

        def _grab() -> None:
            try:
                dlg.lift()
                dlg.focus_force()
                dlg.grab_set()
            except Exception:
                pass

        dlg.after(60, _grab)

    def _open_download(self, url: str) -> None:
        if not url:
            messagebox.showwarning('下载地址缺失', '接口没有返回下载地址，请稍后再试。')
            return
        try:
            webbrowser.open(url)
        except Exception as exc:
            messagebox.showerror('打开链接失败', f'{exc}\n\n请手动访问：\n{url}')

    # ---------------------------------------------------------------- close
    def _on_close(self) -> None:
        if self.runner.running:
            if not messagebox.askyesno('仍在运行', '任务还在运行，确定停止并退出吗？'):
                return
            self.runner.stop()
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
