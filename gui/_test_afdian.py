import os, sys
GUI = r"H:\Code\Microsoft-Rewards-Script-4-china\gui"
sys.path.insert(0, GUI)
import app as gui_app

OUT = os.path.join(GUI, "_afdian_out.txt")
SHOT = os.path.join(GUI, "screenshots")
os.makedirs(SHOT, exist_ok=True)

def log(m):
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")

open(OUT, "w", encoding="utf-8").close()
log("AFDIAN_URL = %s" % gui_app.AFDIAN_URL)

a = gui_app.App()
a.geometry("1060x760+40+30")
a.lift()

def shoot():
    try:
        from PIL import ImageGrab
        a.update_idletasks()
        x, y = a.winfo_rootx(), a.winfo_rooty()
        w, h = a.winfo_width(), a.winfo_height()
        full = ImageGrab.grab()
        full.crop((max(x-8,0), max(y-34,0), min(x+w+8, full.width), min(y+h+8, full.height))).save(os.path.join(SHOT, "10-afdian.png"))
        log("saved 10-afdian.png")
    except Exception as exc:
        log("shot failed %r" % exc)
    sys.stdout.flush()
    os._exit(0)

def to_bottom():
    try:
        a.tabs.set("关于")
        a.about_box._parent_canvas.yview_moveto(1.0)
        a.after(500, shoot)
    except Exception as exc:
        log("scroll failed %r" % exc)
        os._exit(1)

a.after(1200, to_bottom)
a.mainloop()
