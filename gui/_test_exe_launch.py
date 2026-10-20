# -*- coding: utf-8 -*-
"""启动项目根目录的 MRS助手.exe，截图后强制结束（验证打包后能正常渲染）。"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, 'MRS助手.exe')
SHOTS = os.path.join(ROOT, 'gui', 'screenshots')
os.makedirs(SHOTS, exist_ok=True)
STATUS = os.path.join(ROOT, 'gui', '_test_exe_out.txt')

lines = []


def log(msg: str) -> None:
    lines.append(msg)
    with open(STATUS, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))


log('exe exists: %s' % os.path.exists(EXE))
proc = subprocess.Popen([EXE], cwd=ROOT)
log('pid: %s' % proc.pid)
time.sleep(14)
log('poll after 14s: %s' % proc.poll())
try:
    from PIL import ImageGrab

    img = ImageGrab.grab()
    path = os.path.join(SHOTS, '7-exe-update-version.png')
    img.save(path)
    log('screenshot: %s (%dx%d)' % (path, img.width, img.height))
except Exception as exc:  # noqa: BLE001
    log('screenshot failed: %s' % exc)

subprocess.run(['taskkill', '/IM', 'MRS助手.exe', '/F'], capture_output=True)
time.sleep(2)
log('poll after kill: %s' % proc.poll())
log('DONE')
