"""
ui_gen_served.py — GenServedMixin: generator served systems tab.
"""

import tkinter as tk
from tkinter import ttk

from defaults import (
    APPB_DESC_DEFAULTS, GEN_SERVED_NORMAL, GEN_SERVED_GENMODE,
    GEN_SERVED_TP_NORMAL, GEN_SERVED_TP_GENMODE,
    APPB_DEFAULTS, MATRIX_DEFAULTS, TP_DEFAULTS,
)
from constants import SYSTEMS


class GenServedMixin:
    """Mixin providing the Generator Served Systems tab."""
    def _build_gen_served_tab(self):
        """Build the Generator Served Systems tab (hidden until Emergency class selected)."""
        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text="Generator Served Systems")
        self._gen_served_tab_id = self.notebook.tabs()[-1]
        self.notebook.hide(self._gen_served_tab_id)

        # Scrollable canvas
        tab_canvas = tk.Canvas(outer, highlightthickness=0)
        tab_scroll = ttk.Scrollbar(outer, orient="vertical", command=tab_canvas.yview)
        tab_canvas.configure(yscrollcommand=tab_scroll.set)
        tab_scroll.pack(side="right", fill="y")
        tab_canvas.pack(side="left", fill="both", expand=True)
        content_wrap = ttk.Frame(tab_canvas, padding=10)
        wrap_id = tab_canvas.create_window((0, 0), window=content_wrap, anchor="nw")
        content_wrap.bind("<Configure>", lambda e: tab_canvas.configure(scrollregion=tab_canvas.bbox("all")))
        tab_canvas.bind("<Configure>", lambda e: tab_canvas.itemconfig(wrap_id, width=e.width))

        ttk.Label(content_wrap, text="Integrations Matrix", font=("", 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Label(content_wrap, text="Emergency Generator / Served Systems", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))

        rows_frame = ttk.Frame(content_wrap)
        rows_frame.pack(fill="x")
        self._gen_served_matrix_rows = []
        self._gen_served_rows_frame = rows_frame
        self._gen_served_content_wrap = content_wrap

        # Default normal/generator mode text — sourced from defaults.py
        GS_DEFAULT_NORMAL  = GEN_SERVED_NORMAL.replace("{{connected_system}}", "{system}")
        GS_DEFAULT_GENMODE = GEN_SERVED_GENMODE.replace("{{connected_system}}", "{system}")
        GS_DEFAULT_TP_NORMAL  = GEN_SERVED_TP_NORMAL.replace("{{connected_system}}", "{system}")
        GS_DEFAULT_TP_GENMODE = GEN_SERVED_TP_GENMODE.replace("{{connected_system}}", "{system}")

        def _add_gen_served_row(integ="", normal="", fire="", tp_normal="", tp_fire=""):
            matrix_rows = self._gen_served_matrix_rows
            sep = ttk.Separator(rows_frame, orient="horizontal")
            sep.pack(fill="x", pady=(16, 8))
            if not matrix_rows:
                sep.pack_forget()

            row_f = ttk.Frame(rows_frame)
            row_f.pack(fill="x", pady=(0, 6))
            row_f.columnconfigure(0, weight=0, minsize=160)
            row_f.columnconfigure(1, weight=1, uniform="gs_col")
            row_f.columnconfigure(2, weight=1, uniform="gs_col")
            widgets = {}

            # Fill defaults using the integration name if normal/fire are empty
            sys_name = integ.strip() or "system"
            if not normal:
                normal = GS_DEFAULT_NORMAL.format(system=sys_name)
            if not fire:
                fire = GS_DEFAULT_GENMODE.format(system=sys_name)
            if not tp_normal:
                tp_normal = GS_DEFAULT_TP_NORMAL.format(system=sys_name)
            if not tp_fire:
                tp_fire = GS_DEFAULT_TP_GENMODE.format(system=sys_name)

            def _remove(rf=row_f, r=widgets):
                if r in matrix_rows:
                    matrix_rows.remove(r)
                rf.destroy()
                sep_w = r.get("_sep")
                if sep_w and hasattr(sep_w, "winfo_exists") and sep_w.winfo_exists():
                    sep_w.destroy()

            widgets["_sep"] = sep if matrix_rows else None

            integ_outer = ttk.Frame(row_f)
            integ_outer.grid(row=0, column=0, rowspan=3, sticky="nwe", padx=(0, 6))
            ttk.Label(integ_outer, text="Integration", font=("", 8), foreground="gray").pack(anchor="w")
            integ_t = tk.Text(integ_outer, wrap="none", height=1, width=32, relief="flat", bd=1)
            integ_t.insert("1.0", integ)
            integ_t.pack(fill="x")
            ttk.Button(integ_outer, text="Remove Integration", command=_remove).pack(anchor="w", pady=(4, 0))
            widgets["integration"] = integ_t

            nm_outer = ttk.Frame(row_f)
            nm_outer.grid(row=0, column=1, sticky="nswe", padx=(0, 4))
            ttk.Label(nm_outer, text="Normal Mode", font=("", 8), foreground="gray").pack(anchor="w")
            normal_t = tk.Text(nm_outer, wrap="word", height=3, relief="flat", bd=1)
            normal_t.insert("1.0", normal)
            normal_t.pack(fill="both", expand=True)
            ttk.Label(nm_outer, text="Test Procedure — Normal Mode:", font=("", 8), foreground="gray").pack(anchor="w", pady=(6, 0))
            tp_normal_t = tk.Text(nm_outer, wrap="word", height=5)
            _lines = [l.strip() for l in tp_normal.strip().split("\n") if l.strip()]
            _lines = ["• " + l.lstrip("- •").strip() for l in _lines] if _lines else []
            tp_normal_t.insert("1.0", "\n".join(_lines))
            tp_normal_t.pack(fill="both", expand=True)
            ttk.Button(nm_outer, text="+ New Bullet",
                       command=lambda t=tp_normal_t: (t.insert(tk.INSERT, "\n• ") if t.get("1.0", "end-1c").strip() else t.insert("1.0", "• "))
                       ).pack(anchor="w", pady=(2, 0))
            widgets["normal_mode"] = normal_t

            fm_outer = ttk.Frame(row_f)
            fm_outer.grid(row=0, column=2, sticky="nswe")
            ttk.Label(fm_outer, text="Generator Mode", font=("", 8), foreground="gray").pack(anchor="w")
            fire_t = tk.Text(fm_outer, wrap="word", height=3, relief="flat", bd=1)
            fire_t.insert("1.0", fire)
            fire_t.pack(fill="both", expand=True)
            ttk.Label(fm_outer, text="Test Procedure — Generator Mode:", font=("", 8), foreground="gray").pack(anchor="w", pady=(6, 0))
            tp_fire_t = tk.Text(fm_outer, wrap="word", height=5)
            _lines2 = [l.strip() for l in tp_fire.strip().split("\n") if l.strip()]
            _lines2 = ["• " + l.lstrip("- •").strip() for l in _lines2] if _lines2 else []
            tp_fire_t.insert("1.0", "\n".join(_lines2))
            tp_fire_t.pack(fill="both", expand=True)
            ttk.Button(fm_outer, text="+ New Bullet",
                       command=lambda t=tp_fire_t: (t.insert(tk.INSERT, "\n• ") if t.get("1.0", "end-1c").strip() else t.insert("1.0", "• "))
                       ).pack(anchor="w", pady=(2, 0))
            widgets["fire_mode"] = fire_t
            widgets["tp_normal"] = tp_normal_t
            widgets["tp_fire"]   = tp_fire_t
            widgets["_tp_frame"] = row_f

            matrix_rows.append(widgets)
            return widgets

        self._add_gen_served_row = _add_gen_served_row
        ttk.Button(content_wrap, text="+ Add Integration",
                   command=_add_gen_served_row).pack(anchor="w", pady=(4, 0))

        # ── Appendix B section ────────────────────────────────────────────
        ttk.Separator(content_wrap, orient="horizontal").pack(fill="x", pady=(16, 6))
        hdr = ttk.Frame(content_wrap)
        hdr.pack(fill="x", pady=(0, 4))
        ttk.Label(hdr, text="Appendix B — Test Results", font=("", 9, "bold")).pack(side="left")
        ttk.Label(hdr, text="  Record pass/fail for each integration test",
                  foreground="gray", font=("", 8)).pack(side="left")

        # Normal / Generator Mode description fields
        desc_frame = ttk.Frame(content_wrap)
        desc_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(desc_frame, text="Normal Mode:", foreground="gray",
                  font=("", 8)).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
        gs_normal_desc_e = ttk.Entry(desc_frame)
        gs_normal_desc_e.insert(0, APPB_DESC_DEFAULTS.get("generator", ("", ""))[0])
        gs_normal_desc_e.grid(row=0, column=1, sticky="we", pady=2, ipady=2)
        ttk.Label(desc_frame, text="Generator Mode:", foreground="gray",
                  font=("", 8)).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
        gs_fire_desc_e = ttk.Entry(desc_frame)
        gs_fire_desc_e.insert(0, APPB_DESC_DEFAULTS.get("generator", ("", ""))[1])
        gs_fire_desc_e.grid(row=1, column=1, sticky="we", pady=2, ipady=2)
        desc_frame.columnconfigure(1, weight=1)

        COL_NO   = 0
        COL_INTG = 1
        COL_NM   = 2
        COL_NT   = 3
        COL_RM   = 4

        appb_rows_frame = ttk.Frame(content_wrap)
        appb_rows_frame.pack(fill="x")
        appb_rows_frame.columnconfigure(COL_NO,   weight=0, minsize=30)
        appb_rows_frame.columnconfigure(COL_INTG, weight=2)
        appb_rows_frame.columnconfigure(COL_NM,   weight=0, minsize=210)
        appb_rows_frame.columnconfigure(COL_NT,   weight=3)
        appb_rows_frame.columnconfigure(COL_RM,   weight=0, minsize=28)

        ttk.Label(appb_rows_frame, text="No.",  font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_NO, sticky="w", padx=(4, 2), pady=(0, 2))
        ttk.Label(appb_rows_frame, text="System Integration", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_INTG, sticky="w", padx=(0, 6), pady=(0, 2))
        ttk.Label(appb_rows_frame, text="Normal / Generator Mode", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_NM, sticky="w", padx=(0, 6), pady=(0, 2))
        ttk.Label(appb_rows_frame, text="Notes", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_NT, sticky="w", padx=(0, 4), pady=(0, 2))

        gs_appb_rows = []
        _next_row = [1]

        def _make_toggle_group_gs(frame, var, options):
            btns = {}
            colors = {"PASS": "#2e7d32", "FAIL": "#c62828", "NT": "#555555"}
            def _repaint_all():
                for v, b in btns.items():
                    active = var.get() == v
                    b.configure(
                        bg=colors.get(v, "#555555") if active else "#d0d0d0",
                        fg="white" if active else "#333333", relief="flat")
            def _click(v):
                var.set("" if var.get() == v else v)
                _repaint_all()
            for v, txt in options:
                b = tk.Button(frame, text=txt, padx=7, pady=2, relief="flat", bd=0,
                              cursor="hand2", font=("", 8), command=lambda v=v: _click(v))
                b.pack(side="left", padx=(0, 3))
                btns[v] = b
            _repaint_all()
            return btns, _repaint_all

        def _add_gs_appb_row(integration="", normal="", fire="", notes=""):
            idx = len(gs_appb_rows) + 1
            grid_row = _next_row[0]
            _next_row[0] += 1
            widgets_b = {"_grid_row": grid_row}

            no_lbl = ttk.Label(appb_rows_frame, text=str(idx), foreground="gray")
            no_lbl.grid(row=grid_row, column=COL_NO, sticky="w", padx=(4, 2), pady=3)
            widgets_b["_no_lbl"] = no_lbl

            integ_t = tk.Text(appb_rows_frame, wrap="word", height=2, relief="flat",
                              bd=1, highlightthickness=1,
                              highlightbackground="#cccccc", highlightcolor="#0078d4")
            integ_t.insert("1.0", integration)
            integ_t.grid(row=grid_row, column=COL_INTG, sticky="nswe", padx=(0, 6), pady=3)
            widgets_b["integration"] = integ_t

            nm_var = tk.StringVar(value=normal)
            fm_var = tk.StringVar(value=fire)
            nf_outer = ttk.Frame(appb_rows_frame)
            nf_outer.grid(row=grid_row, column=COL_NM, sticky="nw", padx=(0, 6), pady=3)
            nm_f = ttk.Frame(nf_outer)
            nm_f.pack(fill="x", pady=(0, 4))
            ttk.Label(nm_f, text="Normal:", foreground="gray", font=("", 8), width=8).pack(side="left")
            _make_toggle_group_gs(nm_f, nm_var, [("PASS","PASS"),("FAIL","FAIL"),("NT","NT")])
            fm_f = ttk.Frame(nf_outer)
            fm_f.pack(fill="x")
            ttk.Label(fm_f, text="Gen:", foreground="gray", font=("", 8), width=8).pack(side="left")
            _make_toggle_group_gs(fm_f, fm_var, [("PASS","PASS"),("FAIL","FAIL"),("NT","NT")])
            widgets_b["normal"] = nm_var
            widgets_b["fire"]   = fm_var

            notes_e = ttk.Entry(appb_rows_frame)
            notes_e.insert(0, notes)
            notes_e.grid(row=grid_row, column=COL_NT, sticky="we", padx=(0, 4), pady=3, ipady=2)
            widgets_b["notes"] = notes_e

            def _remove_b(r=widgets_b):
                if r in gs_appb_rows:
                    gs_appb_rows.remove(r)
                for wval in r.values():
                    if hasattr(wval, "destroy"):
                        try: wval.destroy()
                        except Exception: pass
                for i, rb in enumerate(gs_appb_rows):
                    lbl = rb.get("_no_lbl")
                    if lbl and lbl.winfo_exists():
                        lbl.configure(text=str(i + 1))

            rm_btn = ttk.Button(appb_rows_frame, text="✕", width=2, command=_remove_b)
            rm_btn.grid(row=grid_row, column=COL_RM, padx=(0, 4), pady=3)
            widgets_b["_rm_btn"] = rm_btn

            gs_appb_rows.append(widgets_b)
            return widgets_b

        self._gs_appb_rows      = gs_appb_rows
        self._add_gs_appb_row   = _add_gs_appb_row
        self._gs_normal_desc_e  = gs_normal_desc_e
        self._gs_fire_desc_e    = gs_fire_desc_e

        btn_f2 = ttk.Frame(content_wrap)
        btn_f2.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_f2, text="+ Add Test Row", command=_add_gs_appb_row).pack(side="left")

    def _reorder_tabs(self):
        """Reorder notebook tabs to always match the fixed SYSTEMS order."""
        sys_keys = [s["key"] for s in SYSTEMS]
        position = 3  # start after the 3 fixed tabs (Project Info, Contacts, Building)
        for key in sys_keys:
            # Pre-Action Panel slots BEFORE Pre-Action Sprinkler
            if key == "pre_action":
                pap = getattr(self, "_pre_action_panel_tab_id", None)
                if pap and self.notebook.tab(pap, "state") == "normal":
                    self.notebook.insert(position, pap)
                    position += 1

            tab_id = self.sys_tab_frames.get(key)
            if tab_id and self.notebook.tab(tab_id, "state") == "normal":
                self.notebook.insert(position, tab_id)
                position += 1

            # Generator Served Systems always after Generator
            if key == "generator":
                served = getattr(self, "_gen_served_tab_id", None)
                if served and self.notebook.tab(served, "state") == "normal":
                    self.notebook.insert(position, served)
                    position += 1

    def _build_pre_action_panel_tab(self):
        """Build the Pre-Action Panel tab (hidden until checkbox selected)."""
        from defaults import MATRIX_DEFAULTS, TP_DEFAULTS, APPB_DESC_DEFAULTS, APPB_DEFAULTS
        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text="Pre-Action Panel")
        self._pre_action_panel_tab_id = self.notebook.tabs()[-1]
        self.notebook.hide(self._pre_action_panel_tab_id)

        # Scrollable canvas
        tab_canvas = tk.Canvas(outer, highlightthickness=0)
        tab_scroll = ttk.Scrollbar(outer, orient="vertical", command=tab_canvas.yview)
        tab_canvas.configure(yscrollcommand=tab_scroll.set)
        tab_scroll.pack(side="right", fill="y")
        tab_canvas.pack(side="left", fill="both", expand=True)
        content_wrap = ttk.Frame(tab_canvas, padding=10)
        wrap_id = tab_canvas.create_window((0, 0), window=content_wrap, anchor="nw")
        content_wrap.bind("<Configure>", lambda e: tab_canvas.configure(scrollregion=tab_canvas.bbox("all")))
        tab_canvas.bind("<Configure>", lambda e: tab_canvas.itemconfig(wrap_id, width=e.width))

        # ── Integrations Matrix ───────────────────────────────────────────────
        ttk.Label(content_wrap, text="Integrations Matrix", font=("", 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Label(content_wrap, text="Pre-Action Panel / Pre-Action Sprinkler System", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))

        matrix_rows = []
        matrix_frame = ttk.Frame(content_wrap)
        matrix_frame.pack(fill="x")
        self._pap_matrix_rows = matrix_rows
        self._pap_matrix_frame = matrix_frame

        pap_matrix_defaults = MATRIX_DEFAULTS.get("pre_action_panel", [])
        pap_tp_defaults      = TP_DEFAULTS.get("pre_action_panel", [])

        def _add_pap_matrix_row(integration="", normal="", fire="", tp_normal="", tp_fire=""):
            sep = ttk.Separator(matrix_frame, orient="horizontal")
            sep.pack(fill="x", pady=(16, 8))
            if not matrix_rows:
                sep.pack_forget()

            row_f = ttk.Frame(matrix_frame)
            row_f.pack(fill="x", pady=(0, 6))
            row_f.columnconfigure(0, weight=0, minsize=160)
            row_f.columnconfigure(1, weight=1, uniform="pap_col")
            row_f.columnconfigure(2, weight=1, uniform="pap_col")
            widgets = {}

            def _remove(rf=row_f, r=widgets):
                if r in matrix_rows:
                    matrix_rows.remove(r)
                rf.destroy()
                sep_w = r.get("_sep")
                if sep_w and hasattr(sep_w, "winfo_exists") and sep_w.winfo_exists():
                    sep_w.destroy()

            widgets["_sep"] = sep if matrix_rows else None

            integ_outer = ttk.Frame(row_f)
            integ_outer.grid(row=0, column=0, rowspan=3, sticky="nwe", padx=(0, 6))
            ttk.Label(integ_outer, text="Integration", font=("", 8), foreground="gray").pack(anchor="w")
            integ_t = tk.Text(integ_outer, wrap="none", height=1, width=28, relief="flat", bd=1)
            integ_t.insert("1.0", integration)
            integ_t.pack(fill="x")
            ttk.Button(integ_outer, text="Remove Integration", command=_remove).pack(anchor="w", pady=(4, 0))
            widgets["integration"] = integ_t

            nm_outer = ttk.Frame(row_f)
            nm_outer.grid(row=0, column=1, sticky="nswe", padx=(0, 4))
            ttk.Label(nm_outer, text="Normal Mode", font=("", 8), foreground="gray").pack(anchor="w")
            normal_t = tk.Text(nm_outer, wrap="word", height=3, relief="flat", bd=1)
            normal_t.insert("1.0", normal)
            normal_t.pack(fill="both", expand=True)
            ttk.Label(nm_outer, text="Test Procedure — Normal Mode:", font=("", 8), foreground="gray").pack(anchor="w", pady=(6, 0))
            tp_normal_t = tk.Text(nm_outer, wrap="word", height=4)
            _lines = ["• " + l.lstrip("- •").strip() for l in tp_normal.strip().split("\n") if l.strip()]
            tp_normal_t.insert("1.0", "\n".join(_lines))
            tp_normal_t.pack(fill="both", expand=True)
            ttk.Button(nm_outer, text="+ New Bullet",
                       command=lambda t=tp_normal_t: t.insert(tk.INSERT, "\n• ")).pack(anchor="w", pady=(2, 0))
            widgets["normal_mode"] = normal_t
            widgets["tp_normal"]   = tp_normal_t

            fm_outer = ttk.Frame(row_f)
            fm_outer.grid(row=0, column=2, sticky="nswe")
            ttk.Label(fm_outer, text="Fire Mode", font=("", 8), foreground="gray").pack(anchor="w")
            fire_t = tk.Text(fm_outer, wrap="word", height=3, relief="flat", bd=1)
            fire_t.insert("1.0", fire)
            fire_t.pack(fill="both", expand=True)
            ttk.Label(fm_outer, text="Test Procedure — Fire Mode:", font=("", 8), foreground="gray").pack(anchor="w", pady=(6, 0))
            tp_fire_t = tk.Text(fm_outer, wrap="word", height=4)
            _lines2 = ["• " + l.lstrip("- •").strip() for l in tp_fire.strip().split("\n") if l.strip()]
            tp_fire_t.insert("1.0", "\n".join(_lines2))
            tp_fire_t.pack(fill="both", expand=True)
            ttk.Button(fm_outer, text="+ New Bullet",
                       command=lambda t=tp_fire_t: t.insert(tk.INSERT, "\n• ")).pack(anchor="w", pady=(2, 0))
            widgets["fire_mode"] = fire_t
            widgets["tp_fire"]   = tp_fire_t
            widgets["_tp_frame"] = row_f

            matrix_rows.append(widgets)
            return widgets

        self._add_pap_matrix_row = _add_pap_matrix_row

        # Seed default matrix rows
        for i, (integ, normal, fire) in enumerate(pap_matrix_defaults):
            tp_n, tp_f = pap_tp_defaults[i] if i < len(pap_tp_defaults) else ("", "")
            _add_pap_matrix_row(integ, normal, fire, tp_n, tp_f)

        ttk.Button(content_wrap, text="+ Add Integration",
                   command=_add_pap_matrix_row).pack(anchor="w", pady=(4, 0))

        # ── Appendix B ────────────────────────────────────────────────────────
        ttk.Separator(content_wrap, orient="horizontal").pack(fill="x", pady=(16, 6))
        hdr = ttk.Frame(content_wrap)
        hdr.pack(fill="x", pady=(0, 4))
        ttk.Label(hdr, text="Appendix B — Test Results", font=("", 9, "bold")).pack(side="left")

        desc_frame = ttk.Frame(content_wrap)
        desc_frame.pack(fill="x", pady=(0, 6))
        pap_appb_desc = APPB_DESC_DEFAULTS.get("pre_action_panel", ("", ""))
        ttk.Label(desc_frame, text="Normal Mode:", foreground="gray", font=("", 8)).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
        pap_normal_desc_e = ttk.Entry(desc_frame)
        pap_normal_desc_e.insert(0, pap_appb_desc[0])
        pap_normal_desc_e.grid(row=0, column=1, sticky="we", pady=2, ipady=2)
        ttk.Label(desc_frame, text="Fire Mode:", foreground="gray", font=("", 8)).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
        pap_fire_desc_e = ttk.Entry(desc_frame)
        pap_fire_desc_e.insert(0, pap_appb_desc[1])
        pap_fire_desc_e.grid(row=1, column=1, sticky="we", pady=2, ipady=2)
        desc_frame.columnconfigure(1, weight=1)
        self._pap_appb_normal_desc_e = pap_normal_desc_e
        self._pap_appb_fire_desc_e   = pap_fire_desc_e

        COL_NO   = 0
        COL_INTG = 1
        COL_NM   = 2
        COL_NT   = 3
        COL_RM   = 4

        appb_rows_frame = ttk.Frame(content_wrap)
        appb_rows_frame.pack(fill="x")
        appb_rows_frame.columnconfigure(COL_NO,   weight=0, minsize=30)
        appb_rows_frame.columnconfigure(COL_INTG, weight=2)
        appb_rows_frame.columnconfigure(COL_NM,   weight=0, minsize=210)
        appb_rows_frame.columnconfigure(COL_NT,   weight=3)
        appb_rows_frame.columnconfigure(COL_RM,   weight=0, minsize=28)

        ttk.Label(appb_rows_frame, text="No.",  font=("", 8, "bold"), foreground="gray").grid(row=0, column=COL_NO, sticky="w", padx=(4, 2), pady=(0, 2))
        ttk.Label(appb_rows_frame, text="Integration", font=("", 8, "bold"), foreground="gray").grid(row=0, column=COL_INTG, sticky="w", padx=(0, 6), pady=(0, 2))
        ttk.Label(appb_rows_frame, text="Normal / Fire Mode", font=("", 8, "bold"), foreground="gray").grid(row=0, column=COL_NM, sticky="w", padx=(0, 6), pady=(0, 2))
        ttk.Label(appb_rows_frame, text="Notes", font=("", 8, "bold"), foreground="gray").grid(row=0, column=COL_NT, sticky="w", padx=(0, 4), pady=(0, 2))

        pap_appb_rows = []
        self._pap_appb_rows = pap_appb_rows
        _pap_next_row = [1]

        def _make_toggle_pap(frame, var, options):
            btns = {}
            colors = {"PASS": "#2e7d32", "FAIL": "#c62828", "NT": "#555555"}
            def _repaint():
                for v, b in btns.items():
                    active = var.get() == v
                    b.configure(bg=colors.get(v, "#555") if active else "#d0d0d0",
                                fg="white" if active else "#333", relief="flat")
            def _click(v):
                var.set("" if var.get() == v else v)
                _repaint()
            for v, txt in options:
                b = tk.Button(frame, text=txt, width=4, font=("", 7),
                              command=lambda v=v: _click(v), relief="flat", bd=0)
                b.pack(side="left", padx=1)
                btns[v] = b
            _repaint()
            return var

        def _add_pap_appb_row(integration="", normal="", fire="", notes="", sw_type="", sw_no=""):
            idx = len(pap_appb_rows) + 1
            grid_row = _pap_next_row[0]
            _pap_next_row[0] += 1
            widgets = {"_grid_row": grid_row}

            no_lbl = ttk.Label(appb_rows_frame, text=str(idx), foreground="gray")
            no_lbl.grid(row=grid_row, column=COL_NO, sticky="w", padx=(4, 2), pady=3)
            widgets["_no_lbl"] = no_lbl

            integ_t = tk.Text(appb_rows_frame, wrap="word", height=2, relief="flat", bd=1,
                              highlightthickness=1, highlightbackground="#cccccc", highlightcolor="#0078d4")
            integ_t.insert("1.0", integration)
            integ_t.grid(row=grid_row, column=COL_INTG, sticky="nswe", padx=(0, 6), pady=3)
            widgets["integration"] = integ_t

            nm_var = tk.StringVar(value=normal)
            fm_var = tk.StringVar(value=fire)
            nm_f = ttk.Frame(appb_rows_frame)
            nm_f.grid(row=grid_row, column=COL_NM, sticky="nswe", padx=(0, 6), pady=3)
            ttk.Label(nm_f, text="Normal Mode", font=("", 8), foreground="gray").pack(anchor="w")
            _make_toggle_pap(nm_f, nm_var, [("PASS", "Pass"), ("FAIL", "Fail"), ("NT", "N/T")])
            ttk.Label(nm_f, text="Fire Mode", font=("", 8), foreground="gray").pack(anchor="w", pady=(4, 0))
            _make_toggle_pap(nm_f, fm_var, [("PASS", "Pass"), ("FAIL", "Fail"), ("NT", "N/T")])
            widgets["normal"] = nm_var
            widgets["fire"]   = fm_var

            notes_t = tk.Text(appb_rows_frame, wrap="word", height=4, relief="flat", bd=1,
                              highlightthickness=1, highlightbackground="#cccccc", highlightcolor="#0078d4")
            notes_t.insert("1.0", notes)
            notes_t.grid(row=grid_row, column=COL_NT, sticky="nswe", padx=(0, 4), pady=3)
            widgets["notes"] = notes_t

            rm_btn = tk.Button(appb_rows_frame, text="×", fg="gray", relief="flat",
                               font=("", 10),
                               command=lambda r=widgets: _remove_pap_appb_row(r))
            rm_btn.grid(row=grid_row, column=COL_RM, sticky="n", pady=3)
            widgets["_rm_btn"] = rm_btn

            pap_appb_rows.append(widgets)
            return widgets

        def _remove_pap_appb_row(r):
            for k, w in r.items():
                if k.startswith("_") or not hasattr(w, "grid_remove"):
                    continue
                try:
                    w.grid_remove()
                except Exception:
                    pass
            for k, w in r.items():
                if hasattr(w, "destroy"):
                    try:
                        w.destroy()
                    except Exception:
                        pass
            if r in pap_appb_rows:
                pap_appb_rows.remove(r)

        self._add_pap_appb_row = _add_pap_appb_row

        # Seed default Appendix B rows
        for name in APPB_DEFAULTS.get("pre_action_panel", []):
            _add_pap_appb_row(integration=name)

        ttk.Button(content_wrap, text="+ Add Test Row", command=_add_pap_appb_row).pack(anchor="w", pady=(4, 0))

    def _refresh_pre_action_panel_tab(self):
        """Show/hide the Pre-Action Panel tab based on the checkbox."""
        tab_id = getattr(self, "_pre_action_panel_tab_id", None)
        if tab_id is None:
            return
        var = getattr(self, "pre_action_panel_var", None)
        if var is None:
            return
        pre_action_tab = self.sys_tab_frames.get("pre_action")
        pre_action_present = (pre_action_tab and
                              self.notebook.tab(pre_action_tab, "state") == "normal")
        if var.get() and pre_action_present:
            if self.notebook.tab(tab_id, "state") == "hidden":
                self.notebook.add(tab_id, text="Pre-Action Panel")
            self._reorder_tabs()
        else:
            if self.notebook.tab(tab_id, "state") == "normal":
                self.notebook.hide(tab_id)

    def _refresh_gen_served_tab(self):
        """Show/hide the Generator Served Systems tab based on class selection."""
        if getattr(self, "_loading_gen_served", False):
            return
        tab_id = getattr(self, "_gen_served_tab_id", None)
        if tab_id is None:
            return

        gen_class = getattr(self, "gen_class_var", None)
        if gen_class is None:
            return
        is_emergency = gen_class.get() == "emergency"

        gen_tab_id = self.sys_tab_frames.get("generator")
        gen_state = self.notebook.tab(gen_tab_id, "state") if gen_tab_id else "hidden"
        served_state = self.notebook.tab(tab_id, "state")
        gen_present = gen_state == "normal"

        if is_emergency and gen_present:
            if served_state == "hidden":
                self.notebook.add(tab_id, text="Generator Served Systems")
                self._reorder_tabs()
            self._rebuild_gen_served_matrix()
        else:
            if served_state == "normal":
                self.notebook.hide(tab_id)

    def _rebuild_gen_served_matrix(self):
        """Rebuild the served systems matrix rows, preserving any existing user edits."""
        if getattr(self, "_loading_gen_served", False):
            return
        rows = getattr(self, "_gen_served_matrix_rows", [])
        add_row = getattr(self, "_add_gen_served_row", None)
        if add_row is None:
            return

        GEN_DISPLAY = getattr(self, "_gen_display", {})
        served_labels = [lbl for lbl, var in getattr(self, "gen_served_vars", {}).items() if var.get()]
        served_names  = [GEN_DISPLAY.get(lbl, lbl) for lbl in served_labels]

        # Build set of integration names currently in the matrix
        existing_names = set()
        for r in rows:
            t = r.get("integration")
            if t:
                existing_names.add(t.get("1.0", "end-1c").strip())

        # Add rows for any newly checked systems
        for name in served_names:
            if name not in existing_names:
                add_row(integ=name)  # defaults filled automatically from name

        # Build the expected Appendix B row names in order:
        # Generator #1 Startup, Generator #1 Device Emergency Power, ...
        # Generator #2 Startup, Generator #2 Device Emergency Power, ...
        gen_count = getattr(self, "gen_count_var", None)
        gen_count = gen_count.get() if gen_count else 1
        try:
            gen_count = int(gen_count)
        except (ValueError, TypeError):
            gen_count = 1

        expected_appb_names = []
        for n in range(1, gen_count + 1):
            expected_appb_names.append(f"Generator #{n} Startup")
            for name in served_names:
                expected_appb_names.append(f"Generator #{n} {name} Emergency Power")

        # Sync Appendix B rows: add any missing, in order
        add_appb = getattr(self, "_add_gs_appb_row", None)
        gs_appb  = getattr(self, "_gs_appb_rows", [])
        existing_appb = {r["integration"].get("1.0", "end-1c").strip() for r in gs_appb if r.get("integration")}
        if add_appb:
            for appb_name in expected_appb_names:
                if appb_name not in existing_appb:
                    add_appb(integration=appb_name)

        # Remove Appendix B rows that are no longer in the expected set
        for r in list(gs_appb):
            t = r.get("integration")
            if t:
                name = t.get("1.0", "end-1c").strip()
                if name not in expected_appb_names:
                    for wval in r.values():
                        if hasattr(wval, "destroy"):
                            try: wval.destroy()
                            except Exception: pass
                    if r in gs_appb:
                        gs_appb.remove(r)

        # Remove rows for unchecked systems (only auto-added ones with lorem text)
        to_remove = []
        for r in list(rows):
            t = r.get("integration")
            if t:
                name = t.get("1.0", "end-1c").strip()
                if name not in served_names:
                    to_remove.append(r)
        for r in to_remove:
            frame = r.get("_tp_frame")
            if frame and frame.winfo_exists():
                frame.destroy()
            sep = r.get("_sep")
            if sep and hasattr(sep, "winfo_exists") and sep.winfo_exists():
                sep.destroy()
            if r in rows:
                rows.remove(r)