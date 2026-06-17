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
    """Show a branded splash screen while the app loads.

    Returns (splash, mark_ready).
    Call mark_ready() once the app is fully built — the bar will
    finish its current sweep then close automatically.
    """
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#7e003f")
    splash.attributes("-topmost", True)

    # ── Fullscreen — covers the app loading underneath ───────
    sw = splash.winfo_screenwidth()
    sh = splash.winfo_screenheight()
    splash.geometry(f"{sw}x{sh}+0+0")
    splash.configure(bg="white")

    # ── Centred card (mahogany border → white interior) ──────
    card_outer = tk.Frame(splash, bg="#7e003f", padx=12, pady=12)
    card_outer.place(relx=0.5, rely=0.5, anchor="center")
    inner = tk.Frame(card_outer, bg="white", padx=20, pady=16)
    inner.pack(fill="both", expand=True)

    # ── Logo image (on white — no colour replacement needed) ──
    try:
        from PIL import Image, ImageTk
        logo_path = resource_path("AI_LOGO_TXT.png")
        img = Image.open(logo_path).convert("RGBA")
        white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        white_bg.paste(img, mask=img.split()[3])
        img = white_bg.convert("RGB")
        img.thumbnail((300, 90), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        lbl_img = tk.Label(inner, image=photo, bg="white", bd=0)
        lbl_img.image = photo
        lbl_img.pack(pady=(30, 6))
    except Exception as e:
        print(f"Splash logo load error: {e}")
        tk.Label(inner, text="ARENCON INC.", font=("Arial", 20, "bold"),
                 bg="white", fg="#7e003f").pack(pady=(40, 6))

    # ── Mahogany divider ──────────────────────────────────────
    tk.Frame(inner, bg="#7e003f", height=2, width=340).pack(pady=(4, 14))

    # ── App name ──────────────────────────────────────────────
    tk.Label(inner, text="IST Generator",
             font=("Arial", 15, "bold"),
             bg="white", fg="#000000").pack()

    tk.Label(inner, text="V1.1  |  Integrated Systems Testing Report Generator",
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

    # State shared between animation and mark_ready
    _state = {"ready": False, "width": 0}
    BAR_W  = 340

    def _animate():
        """Pulse the bar back and forth until ready, then sweep to full and close."""
        if not _state["ready"]:
            # Indeterminate bounce: grow to full, reset, repeat
            _state["width"] = (_state["width"] + 8) % (BAR_W + 1)
            bar_fill.place(x=0, y=0, height=5, width=_state["width"])
            splash.after(16, _animate)
        else:
            # App is ready — sweep remaining bar to full then close
            if _state["width"] < BAR_W:
                _state["width"] = min(_state["width"] + 12, BAR_W)
                bar_fill.place(x=0, y=0, height=5, width=_state["width"])
                splash.after(12, _animate)
            else:
                # Bar full — brief pause then launch
                splash.after(120, _do_launch)

    def _do_launch():
        try:
            splash.destroy()
        except Exception:
            pass
        try:
            root.deiconify()
            root.lift()
            root.focus_force()
        except Exception:
            pass

    def mark_ready():
        _state["ready"] = True

    splash.after(50, _animate)
    splash.update()
    return splash, mark_ready


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
    root.title("IST Generator V1.1")
    root.withdraw()

    # Show splash — returns a mark_ready() callable
    splash, mark_ready = show_splash(root)

    # Build the app; on_ready fires after sv_ttk finishes rendering,
    # which signals the splash bar to sweep to full and close.
    app = ISTReportApp(root, on_ready=mark_ready)
    root.mainloop()