"""
ui_diagram.py — DiagramMixin: interconnection diagram canvas tab.
"""

import os
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.colorchooser as colorchooser

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

from constants import SYSTEMS


class DiagramMixin:
    """Mixin providing the interconnection diagram tab and all canvas logic."""
    def _build_diagram_tab(self):
        """Pegboard-style canvas: drag boxes, draw arrows, pick colors, export PNG."""

        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text="Interconnection Diagram")
        self._diag_tab_id = self.notebook.tabs()[-1]

        # ── Toolbar ────────────────────────────────────────────
        toolbar = ttk.Frame(outer, padding=(6, 4))
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="+ Add Box",           command=self._diag_add_box).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Delete Box",          command=self._diag_delete_selected).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="Refresh from Matrix", command=self._diag_refresh_from_matrix).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Label(toolbar, text="Right-click to edit box · Corner handles to resize · Edge pegs to draw arrows · Right-click arrow to delete",
                  foreground="gray").pack(side="left")

        # ── Image for report row ───────────────────────────────
        img_bar = ttk.Frame(outer, padding=(6, 2))
        img_bar.pack(side="top", fill="x")

        ttk.Button(img_bar, text="Generate PNG", command=self._diag_generate_and_select).pack(side="left", padx=(2, 2))
        ttk.Button(img_bar, text="Browse…",      command=self._diag_browse_png).pack(side="left", padx=2)
        ttk.Button(img_bar, text="Clear",        command=self._diag_clear_png).pack(side="left", padx=2)
        ttk.Label(img_bar, text="Image for Report:").pack(side="left", padx=(8, 4))
        self._diag_png_path_var = tk.StringVar(value="")
        ttk.Entry(img_bar, textvariable=self._diag_png_path_var,
                  state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._diag_selected_png = None

        # ── Canvas ────────────────────────────────────────────
        canvas_frame = ttk.Frame(outer)
        canvas_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        hbar = ttk.Scrollbar(canvas_frame, orient="horizontal")
        vbar = ttk.Scrollbar(canvas_frame, orient="vertical")
        hbar.pack(side="bottom", fill="x")
        vbar.pack(side="right",  fill="y")

        self._diag_canvas = tk.Canvas(
            canvas_frame, bg="#f5f5f5", cursor="crosshair",
            xscrollcommand=hbar.set, yscrollcommand=vbar.set,
            scrollregion=(0, 0, 2400, 1600),
        )
        hbar.config(command=self._diag_canvas.xview)
        vbar.config(command=self._diag_canvas.yview)
        self._diag_canvas.pack(fill="both", expand=True)

        # ── Internal state ─────────────────────────────────────
        # Each box: {id, x, y, w, h, title, subtitles:[], color, canvas_ids:[]}
        self._diag_boxes   = []
        # Each arrow: {src, dst, canvas_ids:[]}
        self._diag_arrows  = []
        self._diag_sel     = None   # selected box id
        self._diag_next_id = 1

        # Drag state
        self._diag_drag        = None   # {id, ox, oy} for box move
        self._diag_arrow_drag  = None   # {src, line_id} for arrow drawing
        self._diag_resize_drag = None   # {id, corner, orig} for corner resize

        c = self._diag_canvas
        c.bind("<ButtonPress-1>",   self._diag_on_press)
        c.bind("<B1-Motion>",       self._diag_on_drag)
        c.bind("<ButtonRelease-1>", self._diag_on_release)
        c.bind("<ButtonPress-3>",   self._diag_on_right)

        # Draw grid dots
        self._diag_draw_grid()

        # Seed with Fire Alarm (4×6 pegs = 160×240) and Monitoring always present
        self._diag_add_box(title="FIRE ALARM SYSTEM", subtitles=[],
                           x=480, y=240, color="#ffcccc", fixed_id="fire_alarm",
                           force_w=160, force_h=240)
        self._diag_add_box(title="MONITORING", subtitles=["FIRE SIGNAL RECEIVING CENTRE"],
                           x=880, y=80, color="#e8d5f5", fixed_id="monitoring",
                           force_w=200)

    def _diag_draw_grid(self):
        c = self._diag_canvas
        c.delete("grid")
        for x in range(0, 2400, 40):
            for y in range(0, 1600, 40):
                c.create_oval(x-1, y-1, x+1, y+1, fill="#cccccc", outline="", tags="grid")

    @staticmethod
    def _diag_snap(value, grid=40):
        return round(value / grid) * grid

    @staticmethod
    def _diag_box_dims(subtitles, title=""):
        """Return (w, h) snapped to the 40px grid that fits the content."""
        GRID = 40
        # Height: title row ~20px + each subtitle ~14px + padding 16px
        raw_h = 20 + len(subtitles) * 14 + 16
        h = max(GRID * 2, math.ceil(raw_h / GRID) * GRID)
        # Width: title uses Arial 9 bold (~7.5px/char), subtitles Arial 7 (~6px/char)
        # Take the max so the title always fits on one line
        title_w = len(title) * 7 + 24   if title    else 0
        sub_w   = max((len(s) * 6 + 24  for s in subtitles), default=0)
        raw_w   = max(title_w, sub_w)
        w = max(GRID * 4, math.ceil(raw_w / GRID) * GRID)
        return w, h

    def _diag_box_by_id(self, bid):
        return next((b for b in self._diag_boxes if b["id"] == bid), None)

    def _diag_redraw_box(self, box):
        c = self._diag_canvas
        for cid in box.get("canvas_ids", []):
            c.delete(cid)
        box["canvas_ids"] = []

        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        sel = box["id"] == self._diag_sel
        outline = "#e63946" if sel else "#333333"
        lw      = 3        if sel else 2

        rid = c.create_rectangle(x, y, x+w, y+h,
                                  fill=box["color"], outline=outline, width=lw,
                                  tags=("box", f"box_{box['id']}"))
        box["canvas_ids"].append(rid)

        # Title — bold, centred horizontally and vertically within the box
        n_subs   = len(box["subtitles"])
        # Total content height: title (14px) + gap (6px) + subtitles
        content_h = 14 + (6 + n_subs * 14 if n_subs else 0)
        content_y = y + (h - content_h) // 2  # top of content block

        tid = c.create_text(x + w//2, content_y + 7, text=box["title"],
                             font=("Arial", 9, "bold", "underline"),
                             anchor="center", justify="center", width=w - 10,
                             tags=("box", f"box_{box['id']}"))
        box["canvas_ids"].append(tid)

        # Subtitles — small, centred
        for i, sub in enumerate(box["subtitles"]):
            sid = c.create_text(x + w//2, content_y + 14 + 6 + i * 14 + 7, text=sub,
                                 font=("Arial", 7), anchor="center", justify="center",
                                 width=w - 10,
                                 tags=("box", f"box_{box['id']}"))
            box["canvas_ids"].append(sid)

        # Peg circles on all four edges at every grid interval
        GRID = 40
        R = 5  # circle radius
        def _edge_pegs(box_x, box_y, box_w, box_h):
            """Yield (px, py, side) for every peg along each edge."""
            # Top edge: x varies, y fixed at top
            for px in range(box_x + GRID, box_x + box_w, GRID):
                yield px, box_y, "top"
            # Bottom edge
            for px in range(box_x + GRID, box_x + box_w, GRID):
                yield px, box_y + box_h, "bottom"
            # Left edge: y varies, x fixed at left
            for py in range(box_y + GRID, box_y + box_h, GRID):
                yield box_x, py, "left"
            # Right edge
            for py in range(box_y + GRID, box_y + box_h, GRID):
                yield box_x + box_w, py, "right"

        for px, py, _ in _edge_pegs(x, y, w, h):
            eid = c.create_oval(px - R, py - R, px + R, py + R,
                                fill="#555555", outline="white", width=1,
                                tags=("handle", f"handle_{box['id']}"))
            box["canvas_ids"].append(eid)

        # Corner handles (white squares) — drag to resize
        HANDLE = 5
        for cnr_x, cnr_y in [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]:
            rid2 = c.create_rectangle(cnr_x-HANDLE, cnr_y-HANDLE, cnr_x+HANDLE, cnr_y+HANDLE,
                                       fill="white", outline="#555", width=1,
                                       tags=("corner", f"corner_{box['id']}"))
            box["canvas_ids"].append(rid2)

        c.tag_raise("box")
        self._diag_redraw_arrows()

    # ── Peg helpers ────────────────────────────────────────────

    @staticmethod
    def _diag_box_pegs(box):
        """Yield all (px, py) peg positions on the edges of a box."""
        GRID = 40
        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        for px in range(x + GRID, x + w, GRID):
            yield px, y         # top
            yield px, y + h     # bottom
        for py in range(y + GRID, y + h, GRID):
            yield x,     py     # left
            yield x + w, py     # right

    def _diag_nearest_peg(self, box, cx, cy):
        """Return the peg on the box edge closest to (cx, cy)."""
        best = min(self._diag_box_pegs(box),
                   key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2,
                   default=None)
        return best or (box["x"] + box["w"] // 2, box["y"] + box["h"] // 2)

    def _diag_redraw_arrows(self):
        c = self._diag_canvas
        for arrow in self._diag_arrows:
            for cid in arrow.get("canvas_ids", []):
                c.delete(cid)
            arrow["canvas_ids"] = []
            src = self._diag_box_by_id(arrow["src"])
            dst = self._diag_box_by_id(arrow["dst"])
            if not src or not dst:
                continue

            waypoints = arrow.get("waypoints")
            if not waypoints or len(waypoints) < 2:
                sx2 = arrow.get("src_px", src["x"] + src["w"] // 2)
                sy2 = arrow.get("src_py", src["y"] + src["h"] // 2)
                dx2 = arrow.get("dst_px", dst["x"] + dst["w"] // 2)
                dy2 = arrow.get("dst_py", dst["y"] + dst["h"] // 2)
                waypoints = [(sx2, sy2), (dx2, dy2)]

            flat = [v for pt in waypoints for v in pt]
            aid = c.create_line(*flat, arrow="last", arrowshape=(10, 12, 4),
                                 fill="#222222", width=2, tags="arrow")
            arrow["canvas_ids"] = [aid]
            c.tag_lower("arrow")
            c.tag_lower("grid")


    def _diag_add_box(self, title="NEW BOX", subtitles=None, x=100, y=100,
                      color="#d0e8ff", fixed_id=None, w=None, force_w=None, force_h=None):
        if subtitles is None:
            subtitles = []
        box_w, box_h = self._diag_box_dims(subtitles, title)
        if force_w is not None:
            box_w = force_w
        elif w is not None:
            box_w = self._diag_snap(w)
        if force_h is not None:
            box_h = force_h
        box = {
            "id":         fixed_id or f"box_{self._diag_next_id}",
            "x": self._diag_snap(x), "y": self._diag_snap(y),
            "w": box_w, "h": box_h,
            "title":      title,
            "subtitles":  subtitles,
            "color":      color,
            "canvas_ids": [],
        }
        self._diag_next_id += 1
        self._diag_boxes.append(box)
        self._diag_redraw_box(box)

    def _diag_refresh_from_matrix(self):
        """Sync boxes from the integration matrix — adds missing systems, updates subtitles."""
        SYSTEM_COLORS = {
            "fire_alarm":       "#ffcccc",
            "sprinkler":        "#d0f0d0",
            "standpipe":        "#d0f0d0",
            "pre_action":       "#d0f0d0",
            "pre_action_panel": "#d0f0d0",
            "fire_pump":        "#ffd9b3",
            "generator":        "#fff0b3",
            "maglock":          "#cce0ff",
            "door_holders":     "#cce0ff",
            "ahu":              "#ffe4b3",
            "smoke_dampers":    "#e8e8e8",
            "fire_shutters":    "#e8e8e8",
            "kitchen_hood":     "#f5d5e0",
            "elevator":         "#d5e8f5",
        }
        LABEL_MAP = {
            "fire_alarm":       "FIRE ALARM SYSTEM",
            "sprinkler":        "SPRINKLER SYSTEM",
            "standpipe":        "STANDPIPE SYSTEM",
            "pre_action":       "PRE-ACTION SPRINKLER",
            "pre_action_panel": "PRE-ACTION PANEL",
            "fire_pump":        "FIRE PUMP",
            "generator":        "GENERATOR",
            "maglock":          "ELECTROMAGNETIC LOCKS",
            "door_holders":     "DOOR HOLDERS",
            "ahu":              "AIR HANDLING UNIT",
            "smoke_dampers":    "SMOKE DAMPERS",
            "fire_shutters":    "FIRE SHUTTERS",
            "kitchen_hood":     "KITCHEN HOOD",
            "elevator":         "ELEVATOR",
        }
        existing_ids = {b["id"] for b in self._diag_boxes}
        auto_x, auto_y = 880, 260
        COL_W, ROW_H = 200, 120

        # Build set of actually selected system keys from the selector vars
        selected_labels = {v.get() for v in self.sys_selector_vars if v.get()}
        selected_keys = {s["key"] for s in SYSTEMS if s["label"] in selected_labels}
        # Fire alarm is always present
        selected_keys.add("fire_alarm")

        for sys_info in SYSTEMS:
            key = sys_info["key"]
            if key not in selected_keys:
                continue
            ui  = self.sys_ui.get(key, {})
            matrix = ui.get("matrix", {})
            # Fire alarm: skip monitoring rows (always standard — not shown on diagram)
            if key == "fire_alarm":
                subs = []
            else:
                rows = matrix.get("_rows", [])
                subs = []
                for r in rows:
                    w = r.get("integration")
                    txt = w.get("1.0", "end-1c").strip() if w else ""
                    if txt:
                        subs.append(txt.upper())

            # Pick grid-snapped dimensions for this box
            title = LABEL_MAP.get(key, key.upper())
            box_w, box_h = self._diag_box_dims(subs, title)

            if key in existing_ids:
                box = self._diag_box_by_id(key)
                if box:
                    box["subtitles"] = subs
                    if key != "fire_alarm":
                        box["w"], box["h"] = box_w, box_h
                    self._diag_redraw_box(box)
            else:
                n_placed = len([b for b in self._diag_boxes if b["id"] not in ("fire_alarm", "monitoring")])
                col = n_placed % 2
                row = n_placed // 2
                self._diag_add_box(
                    title=title,
                    subtitles=subs,
                    x=auto_x + col * COL_W,
                    y=auto_y + row * ROW_H,
                    color=SYSTEM_COLORS.get(key, "#e0e0e0"),
                    fixed_id=key,
                )

        # Remove boxes for systems that are no longer selected
        # (never remove fire_alarm or monitoring — they're always present)
        c = self._diag_canvas

        # Handle pre_action_panel separately — driven by checkbox not selector
        pap_present = (getattr(self, "pre_action_panel_var", None) and
                       self.pre_action_panel_var.get() and
                       "pre_action" in selected_keys)
        if pap_present:
            pap_matrix_rows = getattr(self, "_pap_matrix_rows", [])
            pap_subs = []
            for r in pap_matrix_rows:
                w = r.get("integration")
                txt = w.get("1.0", "end-1c").strip() if w else ""
                if txt:
                    pap_subs.append(txt.upper())
            pap_title = "PRE-ACTION PANEL"
            pap_w, pap_h = self._diag_box_dims(pap_subs, pap_title)
            if "pre_action_panel" in existing_ids:
                box = self._diag_box_by_id("pre_action_panel")
                if box:
                    box["subtitles"] = pap_subs
                    box["w"], box["h"] = pap_w, pap_h
                    self._diag_redraw_box(box)
            else:
                n_placed = len([b for b in self._diag_boxes if b["id"] not in ("fire_alarm", "monitoring")])
                col = n_placed % 2
                row = n_placed // 2
                self._diag_add_box(
                    title=pap_title,
                    subtitles=pap_subs,
                    x=auto_x + col * COL_W,
                    y=auto_y + row * ROW_H,
                    color="#d0f0d0",
                    fixed_id="pre_action_panel",
                )
        else:
            # Remove pre_action_panel box if panel was unchecked
            for box in list(self._diag_boxes):
                if box["id"] == "pre_action_panel":
                    for cid in box["canvas_ids"]:
                        c.delete(cid)
                    self._diag_boxes.remove(box)

        effective_selected = selected_keys | ({"pre_action_panel"} if pap_present else set())
        for box in list(self._diag_boxes):
            if box["id"] in ("fire_alarm", "monitoring"):
                continue
            if box["id"] not in effective_selected:
                for cid in box["canvas_ids"]:
                    c.delete(cid)
                self._diag_boxes.remove(box)

        # Remove any arrow whose src or dst box no longer exists
        live_ids = {b["id"] for b in self._diag_boxes}
        for arrow in list(self._diag_arrows):
            if arrow["src"] not in live_ids or arrow["dst"] not in live_ids:
                for cid in arrow.get("canvas_ids", []):
                    self._diag_canvas.delete(cid)
                self._diag_arrows.remove(arrow)

    # ── Canvas event handlers ──────────────────────────────────

    def _diag_hit_box(self, cx, cy):
        """Return box under canvas coords (cx,cy), or None."""
        for box in reversed(self._diag_boxes):
            if box["x"] <= cx <= box["x"]+box["w"] and box["y"] <= cy <= box["y"]+box["h"]:
                return box
        return None

    def _diag_hit_box_near(self, cx, cy, tolerance=20):
        """Return box under (cx,cy), or nearest box within tolerance px."""
        hit = self._diag_hit_box(cx, cy)
        if hit:
            return hit
        best, best_d = None, float("inf")
        for box in self._diag_boxes:
            # Clamp cx,cy to box rect and measure distance
            nx = max(box["x"], min(cx, box["x"] + box["w"]))
            ny = max(box["y"], min(cy, box["y"] + box["h"]))
            d = ((cx - nx) ** 2 + (cy - ny) ** 2) ** 0.5
            if d < tolerance and d < best_d:
                best_d = d
                best = box
        return best

    def _diag_hit_handle(self, cx, cy):
        """Return (box, peg_x, peg_y) if a peg circle on any edge is under (cx,cy)."""
        GRID = 40
        HIT  = 8
        for box in self._diag_boxes:
            x, y, w, h = box["x"], box["y"], box["w"], box["h"]
            # top/bottom edges
            for px in range(x + GRID, x + w, GRID):
                for py in (y, y + h):
                    if abs(cx - px) <= HIT and abs(cy - py) <= HIT:
                        return box, px, py
            # left/right edges
            for py in range(y + GRID, y + h, GRID):
                for px in (x, x + w):
                    if abs(cx - px) <= HIT and abs(cy - py) <= HIT:
                        return box, px, py
        return None, None, None

    def _diag_hit_corner(self, cx, cy):
        """Return (box, corner_name) if a corner resize handle is under (cx,cy)."""
        HANDLE = 8
        for box in self._diag_boxes:
            x, y, w, h = box["x"], box["y"], box["w"], box["h"]
            for hx, hy, name in [(x, y, "nw"), (x+w, y, "ne"), (x, y+h, "sw"), (x+w, y+h, "se")]:
                if abs(cx - hx) <= HANDLE and abs(cy - hy) <= HANDLE:
                    return box, name
        return None, None

    def _diag_canvas_coords(self, event):
        c = self._diag_canvas
        return c.canvasx(event.x), c.canvasy(event.y)

    def _diag_on_press(self, event):
        cx, cy = self._diag_canvas_coords(event)

        # Check corner handles first (resize)
        box, corner = self._diag_hit_corner(cx, cy)
        if box:
            self._diag_sel = box["id"]
            self._diag_resize_drag = {"id": box["id"], "corner": corner,
                                       "orig": (box["x"], box["y"], box["w"], box["h"])}
            for b in self._diag_boxes:
                self._diag_redraw_box(b)
            return

        # Check edge handles BEFORE arrow endpoints — peg circles always start a new arrow.
        # This allows multiple arrows to originate from the same peg.
        handle_box, peg_x, peg_y = self._diag_hit_handle(cx, cy)
        if handle_box:
            c = self._diag_canvas
            lid = c.create_line(peg_x, peg_y, peg_x, peg_y, arrow="last",
                                 arrowshape=(10,12,4), fill="#e63946", width=2, dash=(4,3))
            self._diag_arrow_drag = {
                "src":      handle_box["id"],
                "start_x":  peg_x,
                "start_y":  peg_y,
                "path":     [(peg_x, peg_y)],
                "line_id":  lid,
            }
            return

        # Check existing arrow endpoints — drag to re-route (only reached if not on a peg circle)
        HIT = 9
        for idx, arrow in enumerate(self._diag_arrows):
            for end in ("src", "dst"):
                px_key = f"{end}_px";  py_key = f"{end}_py"
                if px_key not in arrow:
                    continue
                epx, epy = arrow[px_key], arrow[py_key]
                if abs(cx - epx) <= HIT and abs(cy - epy) <= HIT:
                    c = self._diag_canvas
                    lid = c.create_line(epx, epy, cx, cy, arrow="last",
                                        arrowshape=(10, 12, 4), fill="#e63946",
                                        width=2, dash=(4, 3))
                    self._diag_arrow_drag = {
                        "arrow_idx": idx,
                        "end":       end,
                        "start_x":   epx,
                        "start_y":   epy,
                        "line_id":   lid,
                    }
                    return

        box = self._diag_hit_box(cx, cy)
        if box:
            self._diag_sel = box["id"]
            self._diag_drag = {"id": box["id"], "ox": cx - box["x"], "oy": cy - box["y"]}
            for b in self._diag_boxes:
                self._diag_redraw_box(b)
        else:
            self._diag_sel = None
            for b in self._diag_boxes:
                self._diag_redraw_box(b)

    def _diag_on_drag(self, event):
        cx, cy = self._diag_canvas_coords(event)
        GRID = 40

        if self._diag_resize_drag:
            box = self._diag_box_by_id(self._diag_resize_drag["id"])
            if box:
                ox, oy, ow, oh = self._diag_resize_drag["orig"]
                corner = self._diag_resize_drag["corner"]
                snap = lambda v: max(GRID, round(v / GRID) * GRID)
                if corner == "se":
                    box["w"] = snap(cx - ox);  box["h"] = snap(cy - oy)
                elif corner == "sw":
                    new_w = snap(ox + ow - cx)
                    box["x"] = round((ox + ow - new_w) / GRID) * GRID
                    box["w"] = new_w;           box["h"] = snap(cy - oy)
                elif corner == "ne":
                    box["w"] = snap(cx - ox)
                    new_h = snap(oy + oh - cy)
                    box["y"] = round((oy + oh - new_h) / GRID) * GRID
                    box["h"] = new_h
                elif corner == "nw":
                    new_w = snap(ox + ow - cx);  new_h = snap(oy + oh - cy)
                    box["x"] = round((ox + ow - new_w) / GRID) * GRID
                    box["y"] = round((oy + oh - new_h) / GRID) * GRID
                    box["w"] = new_w;            box["h"] = new_h
                self._diag_redraw_box(box)
            return

        if self._diag_arrow_drag and "arrow_idx" not in self._diag_arrow_drag:
            c = self._diag_canvas
            GRID = 40
            # Snap cursor to nearest grid point
            snapped_x = round(cx / GRID) * GRID
            snapped_y = round(cy / GRID) * GRID
            path = self._diag_arrow_drag["path"]
            # Only append if we've moved to a new grid point
            last = path[-1]
            if (snapped_x, snapped_y) != last:
                # Only allow 90° moves: prefer axis-aligned step from last point
                lx, ly = last
                dx = abs(snapped_x - lx)
                dy = abs(snapped_y - ly)
                if dx >= dy:
                    snapped_y = ly   # horizontal move
                else:
                    snapped_x = lx   # vertical move
                if (snapped_x, snapped_y) != last:
                    # If this backtracks to the second-to-last point, pop instead
                    if len(path) >= 2 and (snapped_x, snapped_y) == path[-2]:
                        path.pop()
                    else:
                        path.append((snapped_x, snapped_y))
            # Redraw preview line from path
            flat = [v for pt in path for v in pt]
            if len(flat) >= 4:
                c.coords(self._diag_arrow_drag["line_id"], *flat)
            return

        if self._diag_drag:
            box = self._diag_box_by_id(self._diag_drag["id"])
            if box:
                raw_x = max(0, int(cx - self._diag_drag["ox"]))
                raw_y = max(0, int(cy - self._diag_drag["oy"]))
                box["x"] = round(raw_x / GRID) * GRID
                box["y"] = round(raw_y / GRID) * GRID
                self._diag_redraw_box(box)

    def _diag_on_release(self, event):
        cx, cy = self._diag_canvas_coords(event)
        if self._diag_resize_drag:
            self._diag_resize_drag = None
            return
        if self._diag_arrow_drag:
            c = self._diag_canvas
            # Delete preview line BEFORE hit-testing so it doesn't block
            c.delete(self._diag_arrow_drag["line_id"])
            self._diag_arrow_drag["line_id"] = None

            # ── Re-dragging an existing arrow endpoint ──────────────
            if "arrow_idx" in self._diag_arrow_drag:
                arrow = self._diag_arrows[self._diag_arrow_drag["arrow_idx"]]
                end   = self._diag_arrow_drag["end"]   # "src" or "dst"
                other_id = arrow["dst"] if end == "src" else arrow["src"]
                new_box = self._diag_hit_box_near(cx, cy)
                if new_box and new_box["id"] != other_id:
                    if end == "src":
                        npx, npy = self._diag_nearest_peg(new_box, cx, cy)
                        arrow["src"]    = new_box["id"]
                        arrow["src_px"] = npx
                        arrow["src_py"] = npy
                    else:
                        # Use existing elbow_x to pick correct arrival edge
                        ex = arrow.get("elbow_x")
                        if ex is not None:
                            npx, npy = self._diag_peg_for_arrival(new_box, ex, cy)
                        else:
                            npx, npy = self._diag_nearest_peg(new_box, cx, cy)
                        arrow["dst"]    = new_box["id"]
                        arrow["dst_px"] = npx
                        arrow["dst_py"] = npy
                    arrow.pop("elbow_x", None)
                    self._diag_redraw_arrows()
                else:
                    self._diag_redraw_arrows()   # restore original
                self._diag_arrow_drag = None
                return

            # ── New arrow drop ───────────────────────────────────────
            dst = self._diag_hit_box_near(cx, cy)
            if dst and dst["id"] != self._diag_arrow_drag["src"]:
                path = self._diag_arrow_drag.get("path", [])
                spx = self._diag_arrow_drag["start_x"]
                spy = self._diag_arrow_drag["start_y"]
                dpx, dpy = self._diag_nearest_peg(dst, cx, cy)
                if path:
                    path[-1] = (dpx, dpy)
                else:
                    path = [(spx, spy), (dpx, dpy)]
                self._diag_arrows.append({
                    "src":        self._diag_arrow_drag["src"],
                    "dst":        dst["id"],
                    "src_px":     spx,
                    "src_py":     spy,
                    "dst_px":     dpx,
                    "dst_py":     dpy,
                    "waypoints":  path,
                    "canvas_ids": [],
                })
                self._diag_redraw_arrows()
            self._diag_arrow_drag = None
            return
        self._diag_drag = None

    def _diag_on_right(self, event):
        """Right-click: edit box if clicked on one, otherwise delete arrow."""
        cx, cy = self._diag_canvas_coords(event)

        # Box takes priority — open edit dialog
        box = self._diag_hit_box(cx, cy)
        if box:
            self._diag_edit_box(box)
            return

        # Otherwise check arrows — hit any segment to delete
        for arrow in list(self._diag_arrows):
            waypoints = arrow.get("waypoints", [])
            if len(waypoints) < 2:
                continue
            hit = False
            for i in range(len(waypoints) - 1):
                ax, ay = waypoints[i]
                bx, by = waypoints[i + 1]
                # Horizontal segment
                if ay == by and abs(cy - ay) < 10 and min(ax, bx) - 8 <= cx <= max(ax, bx) + 8:
                    hit = True; break
                # Vertical segment
                if ax == bx and abs(cx - ax) < 10 and min(ay, by) - 8 <= cy <= max(ay, by) + 8:
                    hit = True; break
            if hit:
                if messagebox.askyesno("Delete Arrow", "Delete this arrow?"):
                    for cid in arrow.get("canvas_ids", []):
                        self._diag_canvas.delete(cid)
                    self._diag_arrows.remove(arrow)
                return

    def _diag_edit_box(self, box):
        dlg = tk.Toplevel(self.root)
        dlg.title("Edit Box")
        dlg.geometry("360x380")
        dlg.transient(self.root)
        dlg.grab_set()
        f = ttk.Frame(dlg, padding=16)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Title:").grid(row=0, column=0, sticky="w", pady=4)
        title_e = ttk.Entry(f, width=36)
        title_e.insert(0, box["title"])
        title_e.grid(row=0, column=1, columnspan=2, pady=4, sticky="we")

        ttk.Label(f, text="Subtitles\n(one per line):").grid(row=1, column=0, sticky="nw", pady=4)
        sub_t = tk.Text(f, width=28, height=7, font=("Arial", 9))
        sub_t.insert("1.0", "\n".join(box["subtitles"]))
        sub_t.grid(row=1, column=1, columnspan=2, pady=4)

        # Fill color
        ttk.Label(f, text="Fill Color:").grid(row=2, column=0, sticky="w", pady=4)
        color_var = tk.StringVar(value=box.get("color", "#ffffff"))
        color_preview = tk.Label(f, bg=color_var.get(), width=6, relief="solid", borderwidth=1)
        color_preview.grid(row=2, column=1, sticky="w", padx=(0,4), pady=4)
        def pick_color():
            _, chosen = colorchooser.askcolor(color=color_var.get(), title="Pick Fill Color")
            if chosen:
                color_var.set(chosen); color_preview.config(bg=chosen)
        ttk.Button(f, text="Choose…", command=pick_color).grid(row=2, column=2, sticky="w", pady=4)

        # Border color
        ttk.Label(f, text="Border Color:").grid(row=3, column=0, sticky="w", pady=4)
        border_var = tk.StringVar(value=box.get("border", "#000000"))
        border_preview = tk.Label(f, bg=border_var.get(), width=6, relief="solid", borderwidth=1)
        border_preview.grid(row=3, column=1, sticky="w", padx=(0,4), pady=4)
        def pick_border():
            _, chosen = colorchooser.askcolor(color=border_var.get(), title="Pick Border Color")
            if chosen:
                border_var.set(chosen); border_preview.config(bg=chosen)
        ttk.Button(f, text="Choose…", command=pick_border).grid(row=3, column=2, sticky="w", pady=4)

        def save():
            box["title"]     = title_e.get().strip().upper()
            box["subtitles"] = [l.strip() for l in sub_t.get("1.0","end-1c").splitlines() if l.strip()]
            box["color"]     = color_var.get()
            box["border"]    = border_var.get()
            # Never auto-resize the fire_alarm box
            if box["id"] != "fire_alarm":
                box["w"], box["h"] = self._diag_box_dims(box["subtitles"], box["title"])
            self._diag_redraw_box(box)
            dlg.destroy()

        btn_row = ttk.Frame(f)
        btn_row.grid(row=4, column=0, columnspan=3, sticky="e", pady=8)
        ttk.Button(btn_row, text="Save", command=save).pack(side="right")

    def _diag_delete_selected(self):
        if not self._diag_sel:
            return
        box = self._diag_box_by_id(self._diag_sel)
        if not box:
            return
        if not messagebox.askyesno("Delete Box", f"Delete '{box['title']}'?"):
            return
        for cid in box["canvas_ids"]:
            self._diag_canvas.delete(cid)
        # Remove connected arrows
        for arrow in [a for a in self._diag_arrows if a["src"] == self._diag_sel or a["dst"] == self._diag_sel]:
            for cid in arrow.get("canvas_ids", []):
                self._diag_canvas.delete(cid)
            self._diag_arrows.remove(arrow)
        self._diag_boxes.remove(box)
        self._diag_sel = None

    def _diag_export_to_path(self, path):
        """Export diagram to a specific path for auto-embed during report generation."""
        self._diag_render_image(path)

    def _diag_render_image(self, path):
        """
        Shared PNG renderer used by both Export PNG and auto-embed.
        No grid dots. Arrowhead drawn at midpoint of each line.
        """
        if not _PIL_AVAILABLE:
            return False

        if not self._diag_boxes:
            return False

        SCALE = 2
        PAD   = 60  # extra padding to ensure arrowheads aren't clipped

        min_x = min(b["x"] for b in self._diag_boxes)
        min_y = min(b["y"] for b in self._diag_boxes)
        max_x = max(b["x"] + b["w"] for b in self._diag_boxes)
        max_y = max(b["y"] + b["h"] for b in self._diag_boxes)

        # Expand bounds to include all arrow waypoints
        for arrow in self._diag_arrows:
            for wx, wy in (arrow.get("waypoints") or []):
                min_x = min(min_x, wx)
                min_y = min(min_y, wy)
                max_x = max(max_x, wx)
                max_y = max(max_y, wy)

        min_x -= PAD;  min_y -= PAD
        max_x += PAD;  max_y += PAD

        W_px = max(1, (max_x - min_x) * SCALE)
        H_px = max(1, (max_y - min_y) * SCALE)

        img  = Image.new("RGB", (W_px, H_px), "#ffffff")
        draw = ImageDraw.Draw(img)

        def sx(v): return int((v - min_x) * SCALE)
        def sy(v): return int((v - min_y) * SCALE)

        # Draw arrows behind boxes
        for arrow in self._diag_arrows:
            src = self._diag_box_by_id(arrow["src"])
            dst = self._diag_box_by_id(arrow["dst"])
            if not src or not dst:
                continue
            waypoints = arrow.get("waypoints")
            if not waypoints or len(waypoints) < 2:
                spx = arrow.get("src_px", src["x"] + src["w"] // 2)
                spy = arrow.get("src_py", src["y"] + src["h"] // 2)
                dpx = arrow.get("dst_px", dst["x"] + dst["w"] // 2)
                dpy = arrow.get("dst_py", dst["y"] + dst["h"] // 2)
                waypoints = [(spx, spy), (dpx, dpy)]

            pts_img = [(sx(px), sy(py)) for px, py in waypoints]
            draw.line(pts_img, fill="#222222", width=2 * SCALE)

            if len(pts_img) >= 2:
                px_prev, py_prev = pts_img[-2]
                px_tip,  py_tip  = pts_img[-1]
                angle = math.atan2(py_tip - py_prev, px_tip - px_prev)
                AL  = 14 * SCALE
                tip = (px_tip, py_tip)
                l1  = (int(px_tip - AL * math.cos(angle - 0.38)), int(py_tip - AL * math.sin(angle - 0.38)))
                l2  = (int(px_tip - AL * math.cos(angle + 0.38)), int(py_tip - AL * math.sin(angle + 0.38)))
                draw.polygon([tip, l1, l2], fill="#222222")

        # Draw boxes on top
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 10 * SCALE)
            font_sub   = ImageFont.truetype("arial.ttf",    8 * SCALE)
        except Exception:
            font_title = ImageFont.load_default()
            font_sub   = font_title

        for box in self._diag_boxes:
            x1, y1 = sx(box["x"]),            sy(box["y"])
            x2, y2 = sx(box["x"] + box["w"]), sy(box["y"] + box["h"])
            draw.rectangle([x1, y1, x2, y2], fill=box["color"],
                           outline=box.get("border", "#000000"), width=2 * SCALE)
            cx = (x1 + x2) // 2
            n_subs    = len(box["subtitles"])
            content_h = (18 + (6 + n_subs * 16 if n_subs else 0)) * SCALE
            top       = y1 + ((y2 - y1) - content_h) // 2
            title_y   = top + 9 * SCALE

            # Draw title text
            draw.text((cx, title_y), box["title"],
                      fill="#000000", font=font_title, anchor="mm")

            # Manual underline: measure text width and draw line beneath
            try:
                bbox = font_title.getbbox(box["title"])
                text_w = bbox[2] - bbox[0]
            except AttributeError:
                text_w = len(box["title"]) * 6 * SCALE
            ul_y = title_y + (9 * SCALE) // 2  # just below baseline
            draw.line([(cx - text_w // 2, ul_y), (cx + text_w // 2, ul_y)],
                      fill="#000000", width=SCALE)

            for i, sub in enumerate(box["subtitles"]):
                draw.text((cx, top + (18 + 6 + i * 16 + 8) * SCALE), sub,
                          fill="#000000", font=font_sub, anchor="mm")

        img.save(path)
        return True

    def _diag_generate_and_select(self):
        """Export PNG from current canvas state, then set it as the report image."""
        if not _PIL_AVAILABLE:
            messagebox.showerror("Missing Library", "Pillow is required.\nRun: pip install Pillow")
            return
        if not self._diag_boxes:
            messagebox.showwarning("Empty Diagram", "No boxes to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Diagram PNG", defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")])
        if not path:
            return
        if self._diag_render_image(path):
            self._diag_selected_png = path
            self._diag_png_path_var.set(path)
            if messagebox.askyesno("PNG Saved", "Diagram saved and selected for report.\n\nOpen the image now?"):
                os.startfile(path)

    def _diag_browse_png(self):
        """Browse for an existing PNG to use in the report."""
        path = filedialog.askopenfilename(
            title="Select Diagram Image",
            filetypes=[("PNG image", "*.png"), ("All images", "*.png *.jpg *.jpeg"), ("All files", "*.*")])
        if path:
            self._diag_selected_png = path
            self._diag_png_path_var.set(path)

    def _diag_clear_png(self):
        """Clear the selected diagram image."""
        self._diag_selected_png = None
        self._diag_png_path_var.set("")

    def _diag_get_state(self):
        """Serialise diagram state for save/load."""
        return {
            "boxes":  [{"id": b["id"], "x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"],
                         "title": b["title"], "subtitles": b["subtitles"],
                         "color": b["color"], "border": b.get("border", "#000000")}
                        for b in self._diag_boxes],
            "arrows": [{"src": a["src"], "dst": a["dst"],
                        "src_px": a.get("src_px"), "src_py": a.get("src_py"),
                        "dst_px": a.get("dst_px"), "dst_py": a.get("dst_py"),
                        "waypoints": a.get("waypoints"),
                        "color": a.get("color", "#888888")} for a in self._diag_arrows],
        }

    def _diag_set_state(self, state):
        """Restore diagram from saved state."""
        c = self._diag_canvas
        for b in self._diag_boxes:
            for cid in b["canvas_ids"]:
                c.delete(cid)
        for a in self._diag_arrows:
            for cid in a.get("canvas_ids", []):
                c.delete(cid)
        self._diag_boxes  = []
        self._diag_arrows = []

        for bd in state.get("boxes", []):
            box = {
                "id": bd["id"], "x": bd["x"], "y": bd["y"],
                "w": bd["w"],   "h": bd["h"],
                "title":     bd["title"].upper(),
                "subtitles": [s.upper() for s in bd["subtitles"]],
                "color": bd["color"], "border": bd.get("border", "#000000"),
                "canvas_ids": [],
            }
            self._diag_boxes.append(box)
            self._diag_redraw_box(box)

        for ad in state.get("arrows", []):
            wp = ad.get("waypoints")
            # Legacy: rebuild from src/dst pegs if no waypoints stored
            if not wp:
                spx, spy = ad.get("src_px"), ad.get("src_py")
                dpx, dpy = ad.get("dst_px"), ad.get("dst_py")
                if spx is not None and dpx is not None:
                    wp = [(spx, spy), (dpx, dpy)]
            self._diag_arrows.append({
                "src": ad["src"], "dst": ad["dst"],
                "src_px": ad.get("src_px"), "src_py": ad.get("src_py"),
                "dst_px": ad.get("dst_px"), "dst_py": ad.get("dst_py"),
                "waypoints": wp,
                "color": ad.get("color", "#888888"), "canvas_ids": [],
            })
        self._diag_redraw_arrows()