# -*- coding: utf-8 -*-
"""Run the built bot (node dist/index.js) as a child process and stream output."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from typing import Callable, Dict, Optional

NODE_NAME = 'node.exe' if os.name == 'nt' else 'bin/node'

# Without this the frozen (--windowed) GUI would pop a console window for every
# node.exe / taskkill it spawns.
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')
BALANCE_RE = re.compile(r'currentBalance=(\d+)')
GAIN_RE = re.compile(r'pointsGained=(\d+)')
EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub('', text)


def classify(line: str) -> str:
    upper = line.upper()
    if '[ERROR]' in upper or ' ERROR' in upper or '失败' in line:
        return 'error'
    if '[WARN]' in upper or ' WARNING' in upper or '警告' in line:
        return 'warn'
    if '成功' in line or 'COLLECTED' in upper or 'POINTSGAINED' in upper:
        return 'ok'
    return 'info'


class BotRunner:
    """Thin subprocess wrapper with line callbacks."""

    def __init__(self) -> None:
        self.proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self.on_line: Optional[Callable[[str], None]] = None
        self.on_exit: Optional[Callable[[int], None]] = None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(
        self,
        node_exe: str,
        cwd: str,
        env_overrides: Optional[Dict[str, str]] = None,
        entry: str = 'dist/index.js',
    ) -> None:
        if self.running:
            raise RuntimeError('已有任务在运行')

        # A parent shell may still carry ACCOUNT_* values; drop them so the
        # overrides below are the single source of truth.
        env = {k: v for k, v in os.environ.items() if not k.startswith('ACCOUNT_')}
        env['PYTHONIOENCODING'] = 'utf-8'
        env['NODE_NO_WARNINGS'] = '1'
        if env_overrides:
            env.update(env_overrides)

        self.proc = subprocess.Popen(
            [node_exe, entry],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            creationflags=_NO_WINDOW,
        )
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        proc = self.proc
        if proc is None or proc.stdout is None:
            return
        try:
            for line in iter(proc.stdout.readline, ''):
                if self.on_line:
                    self.on_line(strip_ansi(line.rstrip('\r\n')))
        except (ValueError, OSError):
            pass
        finally:
            try:
                proc.stdout.close()
            except Exception:
                pass
        code = proc.wait()
        if self.on_exit:
            self.on_exit(code)

    def stop(self) -> None:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        if os.name == 'nt':
            subprocess.run(
                ['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                capture_output=True,
                creationflags=_NO_WINDOW,
            )
        else:
            proc.terminate()


def app_root() -> str:
    """Project root, valid for both `python gui/app.py` and a frozen exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def detect_node() -> str:
    """Node next to the app first, then the portable copy, then whatever is on PATH."""
    # 1) bundled alongside the exe: ./node.exe, ./node/node.exe, ./runtime/node.exe
    root = app_root()
    for sub in ('', 'node', 'runtime', os.path.join('runtime', 'node')):
        candidate = os.path.join(root, sub, NODE_NAME)
        if os.path.isfile(candidate):
            return candidate

    # 2) portable Node under ~/.workbuddy (this machine's setup) - newest first
    base = os.path.join(os.path.expanduser('~'), '.workbuddy', 'binaries', 'node', 'versions')
    if os.path.isdir(base):
        ranked = []
        for name in os.listdir(base):
            candidate = os.path.join(base, name, NODE_NAME)
            if os.path.isfile(candidate):
                digits = re.sub(r'[^0-9]', '', name)
                ranked.append((int(digits[:2]) if len(digits) >= 2 else 0, candidate))
        if ranked:
            ranked.sort(reverse=True)
            for major, candidate in ranked:
                if major >= 24:
                    return candidate
            return ranked[0][1]

    # 3) fall back to PATH
    from shutil import which

    return which('node') or which('node.exe') or ''


def detect_system_chrome() -> str:
    """Path to an installed Google Chrome, or '' when absent.

    Uses the App Paths registry key (covers per-user and machine installs),
    then falls back to the common install directories.
    """
    if os.name != 'nt':
        return ''
    try:
        import winreg
    except ImportError:
        return ''

    key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe'
    for hive, view in (
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_CURRENT_USER, 0),
    ):
        try:
            with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | view) as key:
                value = winreg.QueryValueEx(key, '')[0]
                value = value.strip().strip('"')
                if value and os.path.isfile(value):
                    return value
        except OSError:
            continue

    bases = (
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
        os.environ.get('LOCALAPPDATA', ''),
    )
    for base in bases:
        if not base:
            continue
        candidate = os.path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe')
        if os.path.isfile(candidate):
            return candidate
    return ''
