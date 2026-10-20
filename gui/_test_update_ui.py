# -*- coding: utf-8 -*-
"""GUI 更新提示实测：把本地版本调低，触发真实接口 → 截图 → 硬退出。"""
import os
import sys

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GUI_DIR)

import app as gui_app  # noqa: E402

gui_app.APP_VERSION = '2026.10.17.0'  # 故意比服务器 2026.10.18.1 低

SHOT = os.path.join(GUI_DIR, 'screenshots')
os.makedirs(SHOT, exist_ok=True)


def shoot() -> None:
    try:
        from PIL import ImageGrab

        dlg = getattr(a, '_update_dialog', None)
        print('dlg attr:', repr(dlg))
        try:
            print('exists:', dlg.winfo_exists() if dlg is not None else None)
        except Exception as exc:  # noqa: BLE001
            print('exists check failed:', type(exc).__name__, exc)
        if dlg is not None:
            try:
                dlg.update_idletasks()
                x, y = dlg.winfo_rootx(), dlg.winfo_rooty()
                w, h = dlg.winfo_width(), dlg.winfo_height()
                print('geom:', x, y, w, h)
                full = ImageGrab.grab()
                box = (max(x - 16, 0), max(y - 40, 0), min(x + w + 16, full.width), min(y + h + 16, full.height))
                full.crop(box).save(os.path.join(SHOT, '6-update-dialog.png'))
                print('dialog cropped', box)
            except Exception as exc:  # noqa: BLE001
                print('crop failed:', type(exc).__name__, exc)
        else:
            print('no dialog window')
        ImageGrab.grab().save(os.path.join(SHOT, '6-update-screen.png'))
        print('full screen saved')
    except Exception as exc:  # noqa: BLE001
        print('shot failed:', type(exc).__name__, exc)
    sys.stdout.flush()
    os._exit(0)


a = gui_app.App()
a.geometry('1060x760+40+30')
a.lift()
a.after(7000, shoot)
a.mainloop()
