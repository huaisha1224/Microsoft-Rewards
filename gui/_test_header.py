# -*- coding: utf-8 -*-
"""顶部标题栏改版后截图（确认项目目录文字与检查更新按钮已消失）。"""
import os
import sys

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GUI_DIR)

import app as gui_app  # noqa: E402

SHOT = os.path.join(GUI_DIR, 'screenshots')
os.makedirs(SHOT, exist_ok=True)
OUT = os.path.join(GUI_DIR, '_header_out.txt')


def log(msg: str) -> None:
    with open(OUT, 'a', encoding='utf-8') as fh:
        fh.write(msg + '\n')


open(OUT, 'w', encoding='utf-8').close()
a = gui_app.App()
a.geometry('1060x760+40+30')
a.lift()


def shoot() -> None:
    try:
        from PIL import ImageGrab

        a.update_idletasks()
        x, y = a.winfo_rootx(), a.winfo_rooty()
        w, h = a.winfo_width(), a.winfo_height()
        full = ImageGrab.grab()
        # 只截顶部 160px，方便看清标题栏
        img = full.crop((max(x - 8, 0), max(y - 34, 0), min(x + w + 8, full.width), min(y + 160, full.height)))
        img.save(os.path.join(SHOT, '9-header.png'))
        log('saved 9-header.png %dx%d' % (img.width, img.height))
        log('has btn_check_update attr: %s' % hasattr(a, 'btn_check_update'))
    except Exception as exc:  # noqa: BLE001
        log('failed: %r' % exc)
    sys.stdout.flush()
    os._exit(0)


a.after(1800, shoot)
a.mainloop()
