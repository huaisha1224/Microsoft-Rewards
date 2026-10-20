# -*- coding: utf-8 -*-
"""关于页截图：切到「关于」页签，截上半屏 + 滚到底截下半屏。"""
import os
import sys

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GUI_DIR)

import app as gui_app  # noqa: E402

SHOT = os.path.join(GUI_DIR, 'screenshots')
os.makedirs(SHOT, exist_ok=True)
OUT = os.path.join(GUI_DIR, '_about_out.txt')


def log(msg: str) -> None:
    with open(OUT, 'a', encoding='utf-8') as fh:
        fh.write(msg + '\n')


def grab(name: str) -> None:
    from PIL import ImageGrab

    a.update_idletasks()
    x, y = a.winfo_rootx(), a.winfo_rooty()
    w, h = a.winfo_width(), a.winfo_height()
    full = ImageGrab.grab()
    full.crop((max(x - 8, 0), max(y - 34, 0), min(x + w + 8, full.width), min(y + h + 8, full.height))).save(
        os.path.join(SHOT, name)
    )
    log('saved ' + name)


open(OUT, 'w', encoding='utf-8').close()
a = gui_app.App()
a.geometry('1060x760+40+30')
a.lift()


def step1() -> None:
    try:
        a.tabs.set('关于')
        a.update_idletasks()
        a.after(400, lambda: shot_top())
    except Exception as exc:  # noqa: BLE001
        log('step1 failed: %r' % exc)
        sys.stdout.flush()
        os._exit(1)


def shot_top() -> None:
    try:
        grab('8-about-top.png')
        a.about_box._parent_canvas.yview_moveto(1.0)
        a.after(400, shot_bottom)
    except Exception as exc:  # noqa: BLE001
        log('shot_top failed: %r' % exc)
        os._exit(1)


def shot_bottom() -> None:
    try:
        grab('8-about-bottom.png')
    except Exception as exc:  # noqa: BLE001
        log('shot_bottom failed: %r' % exc)
    log('DONE')
    sys.stdout.flush()
    os._exit(0)


a.after(1200, step1)
a.mainloop()
