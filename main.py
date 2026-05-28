"""
IST Report Generator — Entry point.
Run this file to launch the application.

The ISTReportApp class is assembled from mixins:
  - TabsMixin      (ui_tabs.py)      — all tab-building UI
  - DiagramMixin   (ui_diagram.py)   — interconnection diagram canvas
  - GenServedMixin (ui_gen_served.py)— generator served systems tab
  - DataMixin      (ui_data.py)      — data gather/populate, save/load, report UI

Word document generation lives in word_gen.py.
Shared constants live in constants.py.
Content defaults live in defaults.py.
"""

import tkinter as tk
import sys
import os


def resource_path(relative_path):
    """Get absolute path to resource — works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def show_splash(root):
    """Show a branded splash screen while the app loads."""
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#7e003f")
    splash.attributes("-topmost", True)

    # ── Size & centre ────────────────────────────────────────
    W, H = 480, 280
    sw = splash.winfo_screenwidth()
    sh = splash.winfo_screenheight()
    x  = (sw - W) // 2
    y  = (sh - H) // 2
    splash.geometry(f"{W}x{H}+{x}+{y}")

    # ── Mahogany border → white interior ─────────────────────
    border = tk.Frame(splash, bg="#7e003f", padx=12, pady=12)
    border.pack(fill="both", expand=True)
    inner = tk.Frame(border, bg="white")
    inner.pack(fill="both", expand=True)

    # ── Logo image (on white — no colour replacement needed) ──
    logo_loaded = False
    try:
        from PIL import Image, ImageTk
        logo_path = resource_path("AI_LOGO_TXT.png")
        img = Image.open(logo_path).convert("RGBA")
        # Paste onto white background so transparency is clean
        white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        white_bg.paste(img, mask=img.split()[3])
        img = white_bg.convert("RGB")
        img.thumbnail((300, 90), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        lbl_img = tk.Label(inner, image=photo, bg="white", bd=0)
        lbl_img.image = photo
        lbl_img.pack(pady=(30, 6))
        logo_loaded = True
    except Exception:
        pass

    if not logo_loaded:
        tk.Label(inner, text="ARENCON INC.", font=("Arial", 20, "bold"),
                 bg="white", fg="#7e003f").pack(pady=(40, 6))

    # ── Mahogany divider ──────────────────────────────────────
    tk.Frame(inner, bg="#7e003f", height=2, width=340).pack(pady=(4, 14))

    # ── App name ──────────────────────────────────────────────
    tk.Label(inner, text="AI IST Generator",
             font=("Arial", 15, "bold"),
             bg="white", fg="#7e003f").pack()

    tk.Label(inner, text="V1.0  |  Integrated Systems Testing Report Generator",
             font=("Arial", 8),
             bg="white", fg="#555555").pack(pady=(2, 0))

    # ── Loading bar ───────────────────────────────────────────
    bar_frame = tk.Frame(inner, bg="white")
    bar_frame.pack(pady=(20, 0))
    tk.Label(bar_frame, text="Loading…", font=("Arial", 8),
             bg="white", fg="#888888").pack(anchor="w")
    bar_bg = tk.Frame(bar_frame, bg="#e0e0e0", width=340, height=5)
    bar_bg.pack(fill="x")
    bar_fill = tk.Frame(bar_bg, bg="#7e003f", height=5, width=0)
    bar_fill.place(x=0, y=0, height=5)

    _bar_width = [0]
    def _animate_bar():
        if _bar_width[0] < 340:
            _bar_width[0] = min(_bar_width[0] + 6, 340)
            bar_fill.place(x=0, y=0, height=5, width=_bar_width[0])
            splash.after(18, _animate_bar)
    splash.after(50, _animate_bar)

    splash.update()
    return splash


from ui_tabs import TabsMixin
from ui_system_tab import SystemTabMixin
from ui_diagram import DiagramMixin
from ui_gen_served import GenServedMixin
from ui_data import DataMixin


class ISTReportApp(TabsMixin, SystemTabMixin, DiagramMixin, GenServedMixin, DataMixin):
    """
    Main application class. Inherits __init__ and _build_ui from TabsMixin.
    All other behaviour comes from the other mixins via Python MRO.
    """


if __name__ == "__main__":
    # Create root first but keep it hidden
    root = tk.Tk()
    root.withdraw()

    # Show splash as a Toplevel on the hidden root
    splash = show_splash(root)

    # Build the main app while splash is visible
    app = ISTReportApp(root)

    def _launch():
        splash.destroy()
        root.deiconify()
        root.lift()
        root.focus_force()

    root.after(1800, _launch)
    root.mainloop()