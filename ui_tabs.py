"""
ui_tabs.py — TabsMixin: all tab-building UI methods.
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.colorchooser as colorchooser
from tkcalendar import Calendar
from datetime import datetime
import sv_ttk

from spellcheck import attach_spellcheck
from defaults import (
    SYSTEM_DEFAULTS, SPRINKLER_SUBTYPE_ORDER, PRE_ACTION_SUBTYPE_ORDER, get_sprinkler_text,
    MATRIX_DEFAULTS, TP_DEFAULTS, APPB_DEFAULTS, APPB_DESC_DEFAULTS,
    GEN_SERVED_NORMAL, GEN_SERVED_GENMODE, GEN_SERVED_TP_NORMAL, GEN_SERVED_TP_GENMODE,
)
from constants import SYSTEMS, MONITORING_MATRIX_DEFAULTS, LOREM, CONTRACTOR_TYPES, OCCUPANCY_TYPES
from word_gen import pick_date


class TabsMixin:
    """Mixin providing all tab-building methods."""

    def __init__(self, root):
        self.root = root
        self.root.title("IST Report Generator")
        self.root.minsize(1050, 650)
        def _maximize():
            try:
                self.root.state("zoomed")  # Windows
            except Exception:
                self.root.attributes("-zoomed", True)  # Linux
        self.root.after(0, _maximize)

        self.current_data_file = tk.StringVar(value="")
        self.template_path     = tk.StringVar(value="")
        self.output_path       = tk.StringVar(value="")
        self.contractors       = []
        self.sys_ui            = {}  # keyed by system key
        self._sprinkler_subtype_vars = {}  # populated when sprinkler tab is built

        self._build_ui()

    # ============================================================
    #   UI CONSTRUCTION
    # ============================================================

    def _build_ui(self):
        self._build_file_bar()
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self._build_project_info_tab()
        self._build_contacts_tab()
        self._build_building_tab()
        # Build all system tabs then immediately hide them
        # They are shown/hidden via the Building tab system selector
        self.sys_tab_frames = {}   # key -> outer frame widget
        for sys_info in SYSTEMS:
            self._build_system_tab(sys_info)
            # Store reference to the tab frame and hide it
            outer = self.notebook.tabs()[-1]
            self.sys_tab_frames[sys_info["key"]] = outer
            self.notebook.hide(outer)
        self._build_gen_served_tab()
        self._build_pre_action_panel_tab()
        self._build_diagram_tab()
        self._build_action_bar()

        # Re-apply sprinkler button styles whenever the Sprinkler tab is selected
        # (notebook tab switches on Windows can reset tk.Button backgrounds)
        def _on_tab_change(event):
            try:
                tab_text = self.notebook.tab(self.notebook.select(), "text")
                if tab_text == "Sprinkler":
                    for repaint in getattr(self, "_sprinkler_repaints", {}).values():
                        repaint()
            except Exception:
                pass
        self.notebook.bind("<<NotebookTabChanged>>", _on_tab_change)

        # Fire Alarm is always present — locked label, no delete button
        fa_row = ttk.Frame(self.sys_selector_inner)
        fa_row.pack(fill="x", pady=2)
        ttk.Label(fa_row, text="Fire Alarm", anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 6))
        fa_var = tk.StringVar(value="Fire Alarm")
        self.sys_selector_vars = [fa_var]
        fa_tab_id = self.sys_tab_frames.get("fire_alarm")
        if fa_tab_id:
            self.notebook.add(fa_tab_id, text="Fire Alarm")
            self.sys_ui["fire_alarm"]["present"].set(True)
        # Now that fa_int_text and _fa_desc_text_ref are both set, trigger initial previews
        if hasattr(self, "_fa_update_int"):
            self._fa_update_int()
        if hasattr(self, "_fa_update_desc"):
            self._fa_update_desc()
        if hasattr(self, "_fa_refresh"):
            self._fa_refresh()

    # ---------- File bar ----------
    def _build_file_bar(self):
        bar = ttk.LabelFrame(self.root, text="Files", padding=(10, 5))
        bar.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(bar, text="Data File:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(bar, textvariable=self.current_data_file, state="readonly").grid(
            row=0, column=1, sticky="we", padx=5)
        ttk.Button(bar, text="Load Existing…", command=self.load_from_file).grid(row=0, column=2, padx=2)
        ttk.Button(bar, text="Save",           command=self.save_to_file).grid(row=0, column=3, padx=2)
        ttk.Button(bar, text="Save As…",       command=self.save_to_file_as).grid(row=0, column=4, padx=2)
        ttk.Button(bar, text="Clear",          command=lambda: self.current_data_file.set("")).grid(row=0, column=5, padx=2)

        ttk.Label(bar, text="Word Template:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(6, 0))
        ttk.Entry(bar, textvariable=self.template_path, state="readonly").grid(
            row=1, column=1, sticky="we", padx=5, pady=(6, 0))
        ttk.Button(bar, text="Select Template…", command=self.browse_template).grid(
            row=1, column=2, padx=2, pady=(6, 0))
        ttk.Button(bar, text="Clear", command=lambda: self.template_path.set("")).grid(
            row=1, column=3, padx=2, pady=(6, 0))

        ttk.Label(bar, text="Output File:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=(6, 0))
        ttk.Entry(bar, textvariable=self.output_path, state="readonly").grid(
            row=2, column=1, sticky="we", padx=5, pady=(6, 0))
        ttk.Button(bar, text="Browse…", command=self._browse_output_path).grid(
            row=2, column=2, padx=2, pady=(6, 0))
        ttk.Button(bar, text="Clear", command=lambda: self.output_path.set("")).grid(
            row=2, column=3, padx=2, pady=(6, 0))

        bar.columnconfigure(1, weight=1)

        # ── Dark mode slide toggle ────────────────────────────────────────
        self._dark_mode = False

        toggle_frame = ttk.Frame(bar)
        toggle_frame.grid(row=0, column=6, rowspan=3, sticky="ns", padx=(12, 0))

        ttk.Label(toggle_frame, text="Dark Mode", font=("", 8),
                  foreground="gray").pack(anchor="center", pady=(4, 2))

        # Canvas-drawn slide toggle
        TOG_W, TOG_H = 44, 22
        tog_canvas = tk.Canvas(toggle_frame, width=TOG_W, height=TOG_H,
                               highlightthickness=0, bd=0)
        tog_canvas.pack(anchor="center")

        def _draw_toggle(dark):
            tog_canvas.delete("all")
            bg = "#0078d4" if dark else "#cccccc"
            tog_canvas.create_rounded_rect = lambda *a, **k: None  # stub
            # Track
            tog_canvas.create_oval(0, 0, TOG_H, TOG_H, fill=bg, outline="")
            tog_canvas.create_oval(TOG_W - TOG_H, 0, TOG_W, TOG_H, fill=bg, outline="")
            tog_canvas.create_rectangle(TOG_H // 2, 0, TOG_W - TOG_H // 2, TOG_H,
                                        fill=bg, outline="")
            # Knob
            pad = 3
            kx = TOG_W - TOG_H + pad if dark else pad
            tog_canvas.create_oval(kx, pad, kx + TOG_H - pad * 2,
                                   TOG_H - pad, fill="white", outline="")

        def _apply_theme(dark):
            sv_ttk.set_theme("dark" if dark else "light")
            # Update plain tk widgets that don't follow ttk themes
            txt_bg  = "#1e1e1e" if dark else "white"
            txt_fg  = "#d4d4d4" if dark else "black"
            sel_bg  = "#264f78" if dark else "#0078d4"
            ins_clr = "#d4d4d4" if dark else "black"
            def _recolor_widget(w):
                cls = w.winfo_class()
                if cls == "Text":
                    try:
                        w.configure(background=txt_bg, foreground=txt_fg,
                                    insertbackground=ins_clr, selectbackground=sel_bg,
                                    highlightthickness=1,
                                    highlightbackground="#999999" if dark else "#aaaaaa",
                                    highlightcolor="#0078d4")
                    except Exception:
                        pass
                elif cls == "Canvas":
                    # Keep the diagram pegboard white always so it matches the report page
                    if w is not getattr(self, "_diag_canvas", None):
                        try:
                            w.configure(background="#1e1e1e" if dark else "#f0f0f0")
                        except Exception:
                            pass
                for child in w.winfo_children():
                    _recolor_widget(child)
            _recolor_widget(self.root)
            _draw_toggle(dark)

        def _toggle_theme(event=None):
            self._dark_mode = not self._dark_mode
            _apply_theme(self._dark_mode)

        tog_canvas.bind("<Button-1>", _toggle_theme)
        _draw_toggle(False)
        # Apply light theme on startup
        self.root.after(100, lambda: sv_ttk.set_theme("light"))

    # ---------- Project Info ----------
    def _build_project_info_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="Project Info")
        self.project_fields = {}
        row = 0

        def lbl(text, r, c, **kw):
            ttk.Label(tab, text=text, foreground="gray").grid(
                row=r, column=c, sticky="w", padx=(5, 2), pady=1, **kw)

        def ent(key, r, c, width=20, colspan=1):
            e = ttk.Entry(tab, width=width)
            e.grid(row=r, column=c, sticky="we", padx=(0, 8), pady=2, columnspan=colspan)
            self.project_fields[key] = e
            return e

        def section(text, r):
            ttk.Separator(tab, orient="horizontal").grid(
                row=r, column=0, columnspan=12, sticky="we", pady=(12, 2))
            ttk.Label(tab, text=text, font=("", 9, "bold")).grid(
                row=r + 1, column=0, columnspan=12, sticky="w", padx=5, pady=(0, 6))

        section("Project", row); row += 2
        lbl("Description:", row, 0)
        ent("project_description", row, 1, width=50, colspan=5); row += 1
        lbl("Project Number:", row, 0)
        ent("project_number", row, 1, width=18)
        lbl("Version:", row, 2); ent("version", row, 3, width=10)
        lbl("Date:", row, 4); ent("date", row, 5, width=20)
        ttk.Button(tab, text="📅",
                   command=lambda: pick_date(self.project_fields["date"], self.root)
                   ).grid(row=row, column=6, padx=(0, 5), pady=2)
        row += 1

        section("Client (Prepared For)", row); row += 2
        lbl("Company:", row, 0); ent("client_company", row, 1, width=35, colspan=3); row += 1
        lbl("Street Address:", row, 0); ent("client_address", row, 1, width=30, colspan=3); row += 1
        lbl("City:", row, 0); ent("client_city", row, 1, width=20)
        lbl("Province:", row, 2); ent("client_province", row, 3, width=10)
        lbl("Postal Code:", row, 4); ent("client_postal", row, 5, width=12); row += 1

        section("Prepared By", row); row += 2
        lbl("Name:", row, 0); ent("prepared_by", row, 1, width=22)
        lbl("Qualifications:", row, 2); ent("prepared_by_quals", row, 3, width=22)
        lbl("Role:", row, 4); ent("prepared_by_role", row, 5, width=22); row += 1

        section("Reviewed By", row); row += 2
        lbl("Name:", row, 0); ent("reviewed_by", row, 1, width=22)
        lbl("Qualifications:", row, 2); ent("reviewed_by_quals", row, 3, width=22)
        lbl("Role:", row, 4); ent("reviewed_by_role", row, 5, width=22); row += 1

        self.project_fields["date"].insert(0, datetime.now().strftime("%B %d, %Y"))
        self.project_fields["project_description"].insert(
            0, "Fire Protection Systems Integrated Systems Testing Plan")
        self.project_fields["prepared_by_role"].insert(0, "Fire Protection Consultant")
        self.project_fields["reviewed_by_role"].insert(0, "Principal")
        # Odd columns are labels (fixed width), even columns are entries (expand)
        for c in range(6):
            if c % 2 == 0:  # label columns
                tab.columnconfigure(c, weight=0)
            else:           # entry columns
                tab.columnconfigure(c, weight=1)

    # ---------- Building ----------
    def _build_building_tab(self):
        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text="Building")
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        tab = ttk.Frame(canvas, padding=20)
        win_id = canvas.create_window((0, 0), window=tab, anchor="nw")
        tab.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        row = 0

        def lbl(text, r, c, **kw):
            ttk.Label(tab, text=text, foreground="gray").grid(
                row=r, column=c, sticky="w", padx=(5, 2), pady=1, **kw)

        def ent(key, r, c, width=20, colspan=1):
            e = ttk.Entry(tab, width=width)
            e.grid(row=r, column=c, sticky="we", padx=(0, 8), pady=2, columnspan=colspan)
            self.project_fields[key] = e
            return e

        def section(text, r):
            ttk.Separator(tab, orient="horizontal").grid(
                row=r, column=0, columnspan=12, sticky="we", pady=(12, 2))
            ttk.Label(tab, text=text, font=("", 9, "bold")).grid(
                row=r + 1, column=0, columnspan=12, sticky="w", padx=5, pady=(0, 6))

        section("Building", row); row += 2
        lbl("Building Name:", row, 0)
        ent("building_name", row, 1, width=40, colspan=5); row += 1

        self.scope_var = tk.StringVar(value="entire")
        scope_frame = ttk.Frame(tab)
        scope_frame.grid(row=row, column=0, columnspan=6, sticky="w", padx=5, pady=4)
        ttk.Radiobutton(scope_frame, text="Entire Building", variable=self.scope_var,
                        value="entire", command=self._on_scope_change).pack(side="left", padx=(0, 15))
        ttk.Radiobutton(scope_frame, text="Limited Scope", variable=self.scope_var,
                        value="limited", command=self._on_scope_change).pack(side="left", padx=(0, 8))
        self.scope_entry = ttk.Entry(scope_frame, width=50, state="disabled")
        self.scope_entry.pack(side="left")
        self.scope_entry.bind("<KeyRelease>", lambda e: self._update_building_description())
        row += 1

        lbl("Street Address:", row, 0); ent("address", row, 1, width=30, colspan=3); row += 1
        lbl("City:", row, 0); ent("building_city", row, 1, width=20)
        lbl("Province:", row, 2); ent("building_province", row, 3, width=10)
        lbl("Postal Code:", row, 4); ent("building_postal", row, 5, width=12); row += 1
        lbl("Storeys Above Grade:", row, 0)
        ag_spin = ttk.Spinbox(tab, from_=1, to=999, width=10)
        ag_spin.grid(row=row, column=1, sticky="we", padx=(0, 8), pady=2)
        ag_spin.set("1")
        self.project_fields["ag_storeys"] = ag_spin
        lbl("Storeys Below Grade:", row, 2)
        bg_spin = ttk.Spinbox(tab, from_=0, to=999, width=10)
        bg_spin.grid(row=row, column=3, sticky="we", padx=(0, 8), pady=2)
        bg_spin.set("0")
        self.project_fields["bg_storeys"] = bg_spin
        lbl("Construction Type:", row, 4)
        cv = tk.StringVar()
        ccb = ttk.Combobox(tab, textvariable=cv, values=["Combustible", "Non-Combustible"],
                           state="readonly", width=18)
        ccb.grid(row=row, column=5, sticky="we", padx=(0, 8), pady=2)
        self.project_fields["construction_type"] = ccb
        row += 1

        section("Integrated Systems", row); row += 2

        sys_frame = ttk.Frame(tab)
        sys_frame.grid(row=row, column=0, columnspan=6, sticky="nswe", pady=4, padx=5)
        self.sys_selector_inner = ttk.Frame(sys_frame)
        self.sys_selector_inner.pack(fill="both", expand=True)
        ttk.Button(tab, text="+ Add System",
                   command=self._add_system_selector_row).grid(
            row=row + 1, column=0, sticky="w", padx=5, pady=(4, 0))
        self.sys_selector_vars = []   # list of StringVar, one per row
        row += 2

        section("Occupancies", row); row += 2
        occ_frame = ttk.Frame(tab)
        occ_frame.grid(row=row, column=0, columnspan=6, sticky="nswe", pady=4, padx=5)
        self.occ_inner = ttk.Frame(occ_frame)
        self.occ_inner.pack(fill="both", expand=True)
        ttk.Button(tab, text="+ Add Occupancy",
                   command=self._add_occupancy_row).grid(row=row + 1, column=0, sticky="w", padx=5, pady=(4, 0))
        self.occ_vars = []
        self._add_occupancy_row()
        row += 2

        section("Building Description", row); row += 2
        desc_frame = ttk.Frame(tab)
        desc_frame.grid(row=row, column=0, columnspan=6, sticky="nswe", padx=5, pady=4)
        desc_scroll = ttk.Scrollbar(desc_frame, orient="vertical")
        self.building_desc_text = tk.Text(desc_frame, wrap="word", height=8,
                                          yscrollcommand=desc_scroll.set,
                                          undo=True, maxundo=50,
                                          highlightthickness=1,
                                          highlightbackground="#aaaaaa",
                                          highlightcolor="#0078d4")
        desc_scroll.configure(command=self.building_desc_text.yview)
        self.building_desc_text.pack(side="left", fill="both", expand=True)
        desc_scroll.pack(side="right", fill="y")
        attach_spellcheck(self.building_desc_text)
        tab.rowconfigure(row, weight=1)
        row += 1
        for c in range(6):
            if c % 2 == 0:
                tab.columnconfigure(c, weight=0)
            else:
                tab.columnconfigure(c, weight=1)
        self._update_building_description()

    def _update_building_description(self):
        ENTIRE = (
            'This Integrated Systems Testing Plan provides the testing protocols and procedures '
            'of the testing of the integrated systems in accordance with CAN/ULC-S1001, '
            '"Integrated Systems Testing of Fire Protection and Life Safety Systems" '
            'including the integrated testing report which is provided in Appendix B.'
        )
        LIMITED = (
            'This Integrated Systems Testing Plan provides the testing protocols and procedures '
            'of the testing of the integrated systems in accordance with CAN/ULC-S1001, '
            '"Integrated Systems Testing of Fire Protection and Life Safety Systems" '
            'including the integrated testing report which is provided in Appendix B.\n\n'
            'This integrated system testing plan is limited to fire protection and life safety '
            'systems interconnections for the {scope}.  Remaining existing fire protection and '
            'life safety systems interconnections are excluded and outside the scope of this '
            'testing plan.  A single IST will be complete at the end of construction (end of Phase 3).'
        )
        if self.scope_var.get() == "limited":
            scope_text = self.scope_entry.get().strip() or "{{building_scope}}"
            text = LIMITED.format(scope=scope_text)
        else:
            text = ENTIRE
        self.building_desc_text.delete("1.0", "end")
        self.building_desc_text.insert("1.0", text)

    def _on_scope_change(self):
        if self.scope_var.get() == "limited":
            self.scope_entry.configure(state="normal")
            self.scope_entry.focus_set()
        else:
            self.scope_entry.configure(state="disabled")
        self._update_building_description()

    def _add_system_selector_row(self, value=""):
        """Add a system selector row. Locks to a label once selected."""
        var = tk.StringVar(value=value)
        row_frame = ttk.Frame(self.sys_selector_inner)
        row_frame.pack(fill="x", pady=2)

        def _set_system(label, enabled):
            for sys_info in SYSTEMS:
                if sys_info["label"] == label:
                    key = sys_info["key"]
                    tab_id = self.sys_tab_frames.get(key)
                    ui = self.sys_ui.get(key)
                    if tab_id and ui:
                        if enabled:
                            if self.notebook.tab(tab_id, "state") == "hidden":
                                self.notebook.add(tab_id, text=label)
                            ui["present"].set(True)
                            # Reorder all visible system tabs to match SYSTEMS list order
                            self._reorder_tabs()
                        else:
                            if self.notebook.tab(tab_id, "state") == "normal":
                                self.notebook.hide(tab_id)
                            ui["present"].set(False)
                            # If generator removed, also hide served tab
                            if key == "generator":
                                served_tab = getattr(self, "_gen_served_tab_id", None)
                                if served_tab:
                                    try:
                                        if self.notebook.tab(served_tab, "state") == "normal":
                                            self.notebook.hide(served_tab)
                                    except Exception: pass
                            # If pre_action removed, also hide panel tab
                            if key == "pre_action":
                                pap_tab = getattr(self, "_pre_action_panel_tab_id", None)
                                if pap_tab:
                                    try:
                                        if self.notebook.tab(pap_tab, "state") == "normal":
                                            self.notebook.hide(pap_tab)
                                    except Exception: pass
                    break

        def _refresh_all_combos():
            selected = {v.get() for v in self.sys_selector_vars if v.get()}
            all_labels = [s["label"] for s in SYSTEMS]
            for v in self.sys_selector_vars:
                own = v.get()
                available = [l for l in all_labels if l not in selected or l == own]
                for child in self.sys_selector_inner.winfo_children():
                    for w in child.winfo_children():
                        if isinstance(w, ttk.Combobox) and w.cget("textvariable") == str(v):
                            w.configure(values=available)

        def on_select(event=None):
            chosen = var.get()
            if not chosen:
                return
            _set_system(chosen, True)
            _refresh_all_combos()
            if hasattr(self, "_fa_update_int"):
                self._fa_update_int()
            if hasattr(self, "_refresh_gen_checklist"):
                self._refresh_gen_checklist()
            # Lock: swap combobox for a label
            cb.pack_forget()
            ttk.Label(row_frame, text=chosen, anchor="w").pack(
                side="left", fill="x", expand=True, padx=(0, 6))

        def remove():
            old_val = var.get()
            if old_val:
                _set_system(old_val, False)
            self.sys_selector_vars.remove(var)
            row_frame.destroy()
            _refresh_all_combos()
            if hasattr(self, "_fa_update_int"):
                self._fa_update_int()
            if hasattr(self, "_refresh_gen_checklist"):
                self._refresh_gen_checklist()

        if value:
            # Loading from file — show as locked label
            ttk.Label(row_frame, text=value, anchor="w").pack(
                side="left", fill="x", expand=True, padx=(0, 6))
            cb = ttk.Combobox(row_frame, textvariable=var, state="readonly")  # hidden ref
            _set_system(value, True)
            _refresh_all_combos()
            if hasattr(self, "_fa_update_int"):
                self._fa_update_int()
            if hasattr(self, "_refresh_gen_checklist"):
                self._refresh_gen_checklist()
        else:
            selected = {v.get() for v in self.sys_selector_vars if v.get()}
            all_labels = [s["label"] for s in SYSTEMS if s["label"] not in selected]
            cb = ttk.Combobox(row_frame, textvariable=var, values=all_labels, state="readonly")
            cb.pack(side="left", fill="x", expand=True, padx=(0, 6))
            cb.bind("<<ComboboxSelected>>", on_select)

        ttk.Button(row_frame, text="✕", width=3, command=remove).pack(side="right")
        self.sys_selector_vars.append(var)

    def _add_occupancy_row(self, value=""):
        var = tk.StringVar(value=value)
        row_frame = ttk.Frame(self.occ_inner)
        row_frame.pack(fill="x", pady=2)

        def on_occ_select(event=None):
            if not var.get():
                return
            cb.pack_forget()
            ttk.Label(row_frame, text=var.get(), anchor="w", wraplength=700).pack(
                side="left", fill="x", expand=True, padx=(0, 6))

        def remove(rf=row_frame, v=var):
            self.occ_vars.remove(v)
            rf.destroy()

        if value:
            ttk.Label(row_frame, text=value, anchor="w", wraplength=700).pack(
                side="left", fill="x", expand=True, padx=(0, 6))
            cb = ttk.Combobox(row_frame, textvariable=var, state="readonly")  # hidden ref
        else:
            cb = ttk.Combobox(row_frame, textvariable=var, values=OCCUPANCY_TYPES, state="readonly")
            cb.pack(side="left", fill="x", expand=True, padx=(0, 6))
            cb.bind("<<ComboboxSelected>>", on_occ_select)

        ttk.Button(row_frame, text="✕", width=3, command=remove).pack(side="left")
        self.occ_vars.append(var)

    def _get_occupancies(self):
        result = []
        for var in self.occ_vars:
            val = var.get().strip()
            if not val:
                continue
            if " - " in val:
                parts = val.split(" - ", 1)
                result.append({"occ_type": parts[0].strip(), "occ_description": parts[1].strip()})
            else:
                result.append({"occ_type": val, "occ_description": ""})
        return result

    # ---------- Contacts ----------
    def _build_contacts_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="Contacts")
        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="+ Add Contractor", command=self.open_add_contractor).pack(side="left")
        ttk.Label(top, text="  Double-click a row to edit", foreground="gray").pack(side="left")
        cols = ("role", "company", "phone", "name")
        self.contractor_tree = ttk.Treeview(tab, columns=cols, show="headings", height=14)
        self.contractor_tree.heading("role",    text="Role")
        self.contractor_tree.heading("company", text="Company")
        self.contractor_tree.heading("phone",   text="Phone")
        self.contractor_tree.heading("name",    text="Name")
        self.contractor_tree.column("role",    width=220)
        self.contractor_tree.column("company", width=200)
        self.contractor_tree.column("phone",   width=130)
        self.contractor_tree.column("name",    width=160)
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.contractor_tree.yview)
        self.contractor_tree.configure(yscrollcommand=scroll.set)
        self.contractor_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.contractor_tree.bind("<Double-1>", lambda e: self.edit_contractor())
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Edit Selected",   command=self.edit_contractor).pack(side="left", padx=5)
        ttk.Button(actions, text="Delete Selected", command=self.delete_contractor).pack(side="left", padx=5)

    # ---------- System tab ----------

    def _build_action_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bar, text="⚡ Generate Word Report",
                   command=self.generate_report_ui).pack(side="left", padx=5, ipady=4)
        ttk.Button(bar, text="Clear All",
                   command=self.clear_all).pack(side="right", padx=5)

    # ============================================================
    #   FILE ACTIONS
    # ============================================================

    def browse_template(self):
        path = filedialog.askopenfilename(
            title="Select Word Template",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")])
        if path:
            self.template_path.set(path)

    def _browse_output_path(self):
        path = filedialog.asksaveasfilename(
            title="Set Output File",
            defaultextension=".docx",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")])
        if path:
            self.output_path.set(path)

    def save_to_file(self):
        path = self.current_data_file.get()
        if not path:
            self.save_to_file_as()
            return
        self._write_data_file(path)

    def save_to_file_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Data File")
        if not path:
            return
        self.current_data_file.set(path)
        self._write_data_file(path)

    def _write_data_file(self, path):
        try:
            data = self._gather_data()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", f"Data saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save file:\n{e}")

    def load_from_file(self):
        path = filedialog.askopenfilename(
            title="Load Data File",
            filetypes=[("Text/JSON files", "*.txt *.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._populate_from_data(data)
            self.current_data_file.set(path)
            messagebox.showinfo("Loaded", f"Data loaded from:\n{path}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load file:\n{e}")

    # ============================================================
    #   DATA GATHER / POPULATE
    # ============================================================