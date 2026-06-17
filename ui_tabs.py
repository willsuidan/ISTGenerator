"""
ui_tabs.py — TabsMixin: all tab-building UI methods.
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import sv_ttk

from spellcheck import attach_spellcheck
from constants import SYSTEMS, OCCUPANCY_TYPES
from word_gen import pick_date
from ui_scroll import bind_mousewheel
from defaults import (
    NOTIFICATION_DEFAULTS, format_weeks_notice,
    PPE_DEFAULTS, BUILDING_PHASE_TEXT,
    SAFETY_PROTOCOLS_INTRO_PPE, SAFETY_PROTOCOLS_INTRO_NO_PPE, SAFETY_PROTOCOLS_BODY,
    SPECIAL_HAZARDS_DEFAULT, TEAM_COMMUNICATIONS_DEFAULT, OCCUPANT_NOTIFICATION_DEFAULT,
)


class TabsMixin:
    """Mixin providing all tab-building methods."""

    def __init__(self, root, on_ready=None):
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
        self.contractors       = [
            {"role": "Owner/Owner's Representative", "company": "", "name": "", "phone": ""},
            {"role": "Fire Protection Engineer", "company": "ARENCON Inc.", "name": "", "phone": "905-615-1774"},
            {"role": "Integrated Testing Coordinator", "company": "ARENCON Inc.", "name": "", "phone": "905-615-1774"},
        ]
        self.sys_ui            = {}  # keyed by system key
        self._sprinkler_subtype_vars = {}  # populated when sprinkler tab is built

        self._build_ui()

        # Signal ready after theme settles — gives sv_ttk time to finish rendering
        if on_ready:
            self.root.after(200, on_ready)

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
        self._build_personnel_safety_tab()
        self._build_forms_documentation_tab()
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

        # Fire Alarm is always present — shown as a static chip (built in _build_building_tab)
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
            # Recolor system chips (plain tk widgets, not picked up by _recolor_widget)
            chip_bg  = "#2d2d2d" if dark else "#f0f0f0"
            chip_fg  = "#cccccc" if dark else "#222222"
            chip_btn = "#888888"
            chip_bdr = "#555555" if dark else "#cccccc"
            for chip, lbl, btn in getattr(self, "_chip_widgets", []):
                try:
                    chip.configure(bg=chip_bg, highlightbackground=chip_bdr)
                    lbl.configure(bg=chip_bg, fg=chip_fg)
                    if btn:
                        btn.configure(bg=chip_bg, fg=chip_btn, activebackground=chip_bg)
                except Exception:
                    pass
            _draw_toggle(dark)

        def _toggle_theme(event=None):
            self._dark_mode = not self._dark_mode
            dark = self._dark_mode
            self._show_overlay(
                "Applying theme…",
                lambda: _apply_theme(dark)
            )

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

        def section(text, r, note=None):
            ttk.Separator(tab, orient="horizontal").grid(
                row=r, column=0, columnspan=12, sticky="we", pady=(12, 2))
            hdr = ttk.Frame(tab)
            hdr.grid(row=r + 1, column=0, columnspan=12, sticky="w", padx=5, pady=(0, 6))
            ttk.Label(hdr, text=text, font=("", 9, "bold")).pack(side="left")
            if note:
                ttk.Label(hdr, text=f"  ({note})", foreground="gray", font=("", 8)).pack(side="left")

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

        # ── Integrated Testing Notes ──────────────────────────────────────────
        section("Integrated Testing Notes", row, note="Appendix B"); row += 2

        notes_outer = ttk.Frame(tab)
        notes_outer.grid(row=row, column=0, columnspan=7, sticky="nswe", padx=5, pady=4)
        tab.rowconfigure(row, weight=1)
        row += 1

        self.ist_notes = []           # list of tk.Text widgets
        self._ist_notes_outer = notes_outer

        def _add_ist_note(text=""):
            note_row = ttk.Frame(notes_outer)
            note_row.pack(fill="x", pady=(0, 4))

            dark = getattr(self, "_dark_mode", False)
            txt_bg  = "#1e1e1e" if dark else "white"
            txt_fg  = "#d4d4d4" if dark else "black"
            ins_clr = "#d4d4d4" if dark else "black"

            t = tk.Text(note_row, wrap="word", height=2,
                        relief="flat", bd=1,
                        highlightthickness=1,
                        highlightbackground="#aaaaaa",
                        highlightcolor="#0078d4",
                        background=txt_bg, foreground=txt_fg,
                        insertbackground=ins_clr,
                        undo=True, maxundo=50)
            t.pack(side="left", fill="x", expand=True, padx=(0, 4))
            if text:
                t.insert("1.0", text)
            attach_spellcheck(t)

            def _remove(widget=t, frame=note_row):
                if widget in self.ist_notes:
                    self.ist_notes.remove(widget)
                frame.destroy()

            rm_btn = ttk.Button(note_row, text="✕", width=2, command=_remove)
            rm_btn.pack(side="left")

            self.ist_notes.append(t)
            return t

        self._add_ist_note = _add_ist_note

        # Seed 5 blank rows by default
        for _ in range(5):
            _add_ist_note()

        ttk.Button(notes_outer, text="+ Add Note",
                   command=lambda: _add_ist_note()).pack(anchor="w", pady=(4, 0))

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
        bind_mousewheel(canvas)
        row = 0

        def lbl(text, r, c, **kw):
            ttk.Label(tab, text=text, foreground="gray").grid(
                row=r, column=c, sticky="w", padx=(5, 2), pady=1, **kw)

        def ent(key, r, c, width=20, colspan=1):
            e = ttk.Entry(tab, width=width)
            e.grid(row=r, column=c, sticky="we", padx=(0, 8), pady=2, columnspan=colspan)
            self.project_fields[key] = e
            return e

        def section(text, r, note=None):
            ttk.Separator(tab, orient="horizontal").grid(
                row=r, column=0, columnspan=12, sticky="we", pady=(12, 2))
            hdr = ttk.Frame(tab)
            hdr.grid(row=r + 1, column=0, columnspan=12, sticky="w", padx=5, pady=(0, 6))
            ttk.Label(hdr, text=text, font=("", 9, "bold")).pack(side="left")
            if note:
                ttk.Label(hdr, text=f"  ({note})", foreground="gray", font=("", 8)).pack(side="left")

        section("Building", row, note="Section 1.1"); row += 2
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
        ag_spin = ttk.Spinbox(tab, from_=0, to=999, width=10)
        ag_spin.grid(row=row, column=1, sticky="we", padx=(0, 8), pady=2)
        ag_spin.set("1")
        self.project_fields["ag_storeys"] = ag_spin
        lbl("Storeys Below Grade:", row, 2)
        bg_spin = ttk.Spinbox(tab, from_=0, to=999, width=10)
        bg_spin.grid(row=row, column=3, sticky="we", padx=(0, 8), pady=2)
        bg_spin.set("0")
        self.project_fields["bg_storeys"] = bg_spin
        lbl("Mezzanine Levels:", row, 4)
        mezz_spin = ttk.Spinbox(tab, from_=0, to=999, width=10)
        mezz_spin.grid(row=row, column=5, sticky="we", padx=(0, 8), pady=2)
        mezz_spin.set("0")
        self.project_fields["mezz_lvls"] = mezz_spin
        row += 1
        lbl("Construction Type:", row, 0)
        cv = tk.StringVar()
        ccb = ttk.Combobox(tab, textvariable=cv, values=["Combustible", "Non-Combustible"],
                           state="readonly", width=18)
        ccb.grid(row=row, column=1, sticky="we", padx=(0, 8), pady=2)
        self.project_fields["construction_type"] = ccb
        row += 1

        # ── Occupancies ───────────────────────────────────────────────────────
        section("Occupancies", row, note="Section 1.1"); row += 2
        occ_frame = ttk.Frame(tab)
        occ_frame.grid(row=row, column=0, columnspan=6, sticky="nswe", padx=5, pady=(0, 4))
        self.occ_inner = ttk.Frame(occ_frame)
        self.occ_inner.pack(anchor="w", fill="x")
        ttk.Button(occ_frame, text="+ Add Occupancy",
                   command=self._add_occupancy_row).pack(anchor="w", pady=(6, 0))
        self.occ_vars = []
        self._add_occupancy_row()
        row += 2

        # ── Integrated Systems ────────────────────────────────────────────────
        section("Integrated Systems", row, note="Section 1.3"); row += 2
        sys_outer = ttk.Frame(tab)
        sys_outer.grid(row=row, column=0, columnspan=6, sticky="nswe", padx=5, pady=(0, 4))
        sys_frame = ttk.Frame(sys_outer)
        sys_frame.pack(anchor="w", fill="x")
        # Fire Alarm chip — always present, non-removable
        self._chip_widgets = []   # track all (frame, label, btn) for theme recolor
        self._make_static_chip(sys_frame, "Fire Alarm")
        self.sys_selector_inner = sys_frame   # chips pack directly into sys_frame
        ttk.Button(sys_outer, text="+ Add System",
                   command=self._add_system_selector_row).pack(anchor="w", pady=(6, 0))
        self.sys_selector_vars = []
        row += 2

        section("Building Description", row, note="Section 1.1"); row += 2
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
            'testing plan.'
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

    def _chip_colors(self):
        """Return (bg, fg, btn_fg, border) appropriate for current theme."""
        dark = getattr(self, "_dark_mode", False)
        if dark:
            return "#2d2d2d", "#cccccc", "#888888", "#555555"
        else:
            return "#f0f0f0", "#222222", "#888888", "#cccccc"

    def _make_static_chip(self, parent, text):
        """Render a non-removable chip (e.g. Fire Alarm)."""
        bg, fg, _, border = self._chip_colors()
        chip = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=border)
        chip.pack(anchor="w", pady=2)
        lbl = tk.Label(chip, text=text, bg=bg, fg=fg, font=("", 9), padx=8, pady=3)
        lbl.pack(side="left")
        chips = getattr(self, "_chip_widgets", [])
        chips.append((chip, lbl, None))
        self._chip_widgets = chips

    def _add_system_selector_row(self, value=""):
        """Add a system selector row. Pending selection shows a combobox; once
        selected, collapses to a compact theme-aware chip with an inline ✕ button."""
        var = tk.StringVar(value=value)

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
                            self._reorder_tabs()
                        else:
                            if self.notebook.tab(tab_id, "state") == "normal":
                                self.notebook.hide(tab_id)
                            ui["present"].set(False)
                            if key == "generator":
                                served_tab = getattr(self, "_gen_served_tab_id", None)
                                if served_tab:
                                    try:
                                        if self.notebook.tab(served_tab, "state") == "normal":
                                            self.notebook.hide(served_tab)
                                    except Exception: pass
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

        def _lock_as_chip(chosen, pending_frame=None):
            if pending_frame:
                pending_frame.destroy()
            bg, fg, btn_fg, border = self._chip_colors()
            chip = tk.Frame(self.sys_selector_inner, bg=bg,
                            highlightthickness=1, highlightbackground=border)
            chip.pack(anchor="w", pady=2)
            lbl = tk.Label(chip, text=chosen, bg=bg, fg=fg, font=("", 9), padx=8, pady=3)
            lbl.pack(side="left")

            def remove():
                _set_system(chosen, False)
                self.sys_selector_vars.remove(var)
                chip.destroy()
                if (chip, lbl, rm_btn) in getattr(self, "_chip_widgets", []):
                    self._chip_widgets.remove((chip, lbl, rm_btn))
                _refresh_all_combos()
                if hasattr(self, "_fa_update_int"):
                    self._fa_update_int()
                if hasattr(self, "_refresh_gen_checklist"):
                    self._refresh_gen_checklist()

            rm_btn = tk.Button(chip, text="✕", bg=bg, fg=btn_fg,
                               activebackground=bg, activeforeground="#c62828",
                               relief="flat", bd=0, font=("", 8), padx=4, pady=2,
                               cursor="hand2", command=remove)
            rm_btn.pack(side="left")
            chips = getattr(self, "_chip_widgets", [])
            chips.append((chip, lbl, rm_btn))
            self._chip_widgets = chips

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
            _lock_as_chip(chosen, pending_frame=pending_row)

        if value:
            cb = ttk.Combobox(self.sys_selector_inner, textvariable=var, state="readonly")
            _set_system(value, True)
            _refresh_all_combos()
            if hasattr(self, "_fa_update_int"):
                self._fa_update_int()
            if hasattr(self, "_refresh_gen_checklist"):
                self._refresh_gen_checklist()
            _lock_as_chip(value, pending_frame=None)
        else:
            pending_row = ttk.Frame(self.sys_selector_inner)
            pending_row.pack(anchor="w", pady=2)
            selected = {v.get() for v in self.sys_selector_vars if v.get()}
            all_labels = [s["label"] for s in SYSTEMS if s["label"] not in selected]
            cb = ttk.Combobox(pending_row, textvariable=var, values=all_labels,
                              state="readonly", width=28)
            cb.pack(side="left", padx=(0, 4))
            cb.bind("<<ComboboxSelected>>", on_select)

            def _cancel():
                self.sys_selector_vars.remove(var)
                pending_row.destroy()

            ttk.Button(pending_row, text="Cancel", command=_cancel).pack(side="left")

        self.sys_selector_vars.append(var)

    def _add_occupancy_row(self, value=""):
        var = tk.StringVar(value=value)

        def _lock_as_occ_chip(chosen, pending_frame=None):
            if pending_frame:
                pending_frame.destroy()
            bg, fg, btn_fg, border = self._chip_colors()
            chip = tk.Frame(self.occ_inner, bg=bg,
                            highlightthickness=1, highlightbackground=border)
            chip.pack(anchor="w", pady=2)
            lbl = tk.Label(chip, text=chosen, bg=bg, fg=fg, font=("", 9),
                           padx=8, pady=3)
            lbl.pack(side="left")

            def remove():
                self.occ_vars.remove(var)
                chip.destroy()
                if (chip, lbl, rm_btn) in getattr(self, "_chip_widgets", []):
                    self._chip_widgets.remove((chip, lbl, rm_btn))
                if not self.occ_vars:
                    self._add_occupancy_row()

            rm_btn = tk.Button(chip, text="✕", bg=bg, fg=btn_fg,
                               activebackground=bg, activeforeground="#c62828",
                               relief="flat", bd=0, font=("", 8), padx=4, pady=2,
                               cursor="hand2", command=remove)
            rm_btn.pack(side="left")
            chips = getattr(self, "_chip_widgets", [])
            chips.append((chip, lbl, rm_btn))
            self._chip_widgets = chips

        def on_occ_select(event=None):
            chosen = var.get()
            if not chosen:
                return
            _lock_as_occ_chip(chosen, pending_frame=pending_row)

        if value:
            cb = ttk.Combobox(self.occ_inner, textvariable=var, state="readonly")  # hidden ref
            _lock_as_occ_chip(value, pending_frame=None)
        else:
            pending_row = ttk.Frame(self.occ_inner)
            pending_row.pack(fill="x", pady=2)
            cb = ttk.Combobox(pending_row, textvariable=var, values=OCCUPANCY_TYPES,
                              state="readonly", width=60)
            cb.pack(side="left", fill="x", expand=True, padx=(0, 4))
            cb.bind("<<ComboboxSelected>>", on_occ_select)

            def _cancel_occ():
                self.occ_vars.remove(var)
                pending_row.destroy()
                if not self.occ_vars:
                    self.root.after(0, self._add_occupancy_row)

            ttk.Button(pending_row, text="Cancel", command=_cancel_occ).pack(side="left")

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
        ttk.Button(top, text="+ Add Contact", command=self.open_add_contact).pack(side="left")
        ttk.Label(top, text="  Double-click to edit  ·  Drag to reorder", foreground="gray").pack(side="left")
        ttk.Label(top, text="  (Section 1.2)", foreground="gray", font=("", 8)).pack(side="left")
        cols = ("role", "company", "phone", "name")
        self.contact_tree = ttk.Treeview(tab, columns=cols, show="headings", height=14)
        self.contact_tree.heading("role",    text="Role")
        self.contact_tree.heading("company", text="Company")
        self.contact_tree.heading("phone",   text="Phone")
        self.contact_tree.heading("name",    text="Name")
        self.contact_tree.column("role",    width=220)
        self.contact_tree.column("company", width=200)
        self.contact_tree.column("phone",   width=130)
        self.contact_tree.column("name",    width=160)
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.contact_tree.yview)
        self.contact_tree.configure(yscrollcommand=scroll.set)
        self.contact_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.contact_tree.bind("<Double-1>", lambda e: self.edit_contact())

        # ── Drag-to-reorder ──────────────────────────────────────────────
        _drag = {"item": None}

        def _drag_start(event):
            item = self.contact_tree.identify_row(event.y)
            if item:
                _drag["item"] = item
                self.contact_tree.selection_set(item)

        def _drag_motion(event):
            if not _drag["item"]:
                return
            target = self.contact_tree.identify_row(event.y)
            if not target or target == _drag["item"]:
                return
            bbox = self.contact_tree.bbox(target)
            if not bbox:
                return
            mid = bbox[1] + bbox[3] // 2
            src_idx = int(_drag["item"])
            tgt_idx = int(target)
            dst_idx = tgt_idx if event.y < mid else tgt_idx + 1
            dst_idx = max(0, min(len(self.contractors) - 1, dst_idx))
            if dst_idx != src_idx:
                moved = self.contractors.pop(src_idx)
                self.contractors.insert(dst_idx, moved)
                self._refresh_contact_tree()
                new_iid = str(dst_idx)
                self.contact_tree.selection_set(new_iid)
                self.contact_tree.focus(new_iid)
                _drag["item"] = new_iid

        def _drag_end(event):
            _drag["item"] = None

        self.contact_tree.bind("<ButtonPress-1>",  _drag_start)
        self.contact_tree.bind("<B1-Motion>",       _drag_motion)
        self.contact_tree.bind("<ButtonRelease-1>", _drag_end)
        # ────────────────────────────────────────────────────────────────

        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Edit Selected",   command=self.edit_contact).pack(side="left", padx=5)
        ttk.Button(actions, text="Delete Selected", command=self.delete_contact).pack(side="left", padx=5)
        ttk.Label(actions, text="  Drag rows to reorder",
                  foreground="gray").pack(side="left")
        self.root.after(0, self._refresh_contact_tree)

    # ---------- Personnel Safety tab ----------

    def _build_personnel_safety_tab(self):
        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text="Personnel Safety")
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        tab = ttk.Frame(canvas, padding=20)
        win_id = canvas.create_window((0, 0), window=tab, anchor="nw")
        tab.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        bind_mousewheel(canvas)

        def text_box(parent, height, default_text):
            f = ttk.Frame(parent)
            f.pack(fill="both", expand=True, pady=(0, 8))
            sb = ttk.Scrollbar(f, orient="vertical")
            t = tk.Text(f, wrap="word", height=height, yscrollcommand=sb.set, undo=True, maxundo=50,
                        highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
            sb.configure(command=t.yview)
            t.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            attach_spellcheck(t)
            t.insert("1.0", default_text)
            return t

        # ── Notifications (Section 4) ─────────────────────────────────────
        noti_hdr = ttk.Frame(tab)
        noti_hdr.pack(anchor="w", pady=(0, 6))
        ttk.Label(noti_hdr, text="Notifications", font=("", 10, "bold")).pack(side="left")
        ttk.Label(noti_hdr, text="  (Section 4)", foreground="gray", font=("", 8)).pack(side="left")

        # -- Notice to Integrated Testing Participants --
        part_hdr = ttk.Frame(tab)
        part_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(part_hdr, text="Notification to Integrated Testing Participants",
                  font=("", 9, "bold")).pack(side="left")
        ttk.Label(part_hdr, text="  (Section 4.1)", foreground="gray", font=("", 8)).pack(side="left")

        part_notice_f = ttk.Frame(tab)
        part_notice_f.pack(anchor="w", pady=(0, 4))
        ttk.Label(part_notice_f, text="Notice Period (weeks):").pack(side="left", padx=(0, 6))
        self.participant_wks_notice_var = tk.IntVar(value=NOTIFICATION_DEFAULTS["participant_wks_notice"])
        part_spin = ttk.Spinbox(part_notice_f, from_=1, to=52, increment=1,
                                 textvariable=self.participant_wks_notice_var, width=12)
        part_spin.pack(side="left")

        self._noti_participants_text = text_box(
            tab, 3,
            NOTIFICATION_DEFAULTS["noti_to_participants"].replace(
                "{{participant_wks_notice}}", format_weeks_notice(self.participant_wks_notice_var.get())))

        def _update_noti_participants(event=None):
            template = NOTIFICATION_DEFAULTS["noti_to_participants"]
            try:
                wks = self.participant_wks_notice_var.get()
            except tk.TclError:
                wks = NOTIFICATION_DEFAULTS["participant_wks_notice"]
            preview = template.replace("{{participant_wks_notice}}", format_weeks_notice(wks))
            self._noti_participants_text.delete("1.0", "end")
            self._noti_participants_text.insert("1.0", preview)
        self._update_noti_participants = _update_noti_participants
        part_spin.bind("<<Increment>>", lambda e: self.root.after(1, _update_noti_participants))
        part_spin.bind("<<Decrement>>", lambda e: self.root.after(1, _update_noti_participants))
        part_spin.bind("<KeyRelease>", _update_noti_participants)
        part_spin.bind("<FocusOut>", _update_noti_participants)

        # -- Notice to Building Occupants --
        occ_hdr = ttk.Frame(tab)
        occ_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(occ_hdr, text="Notification to Building Occupants",
                  font=("", 9, "bold")).pack(side="left")
        ttk.Label(occ_hdr, text="  (Section 4.2)", foreground="gray", font=("", 8)).pack(side="left")

        occ_notice_f = ttk.Frame(tab)
        occ_notice_f.pack(anchor="w", pady=(0, 4))
        ttk.Label(occ_notice_f, text="Notice Period (hours):").pack(side="left", padx=(0, 6))
        self.occupant_hrs_notice_var = tk.IntVar(value=NOTIFICATION_DEFAULTS["occupant_hrs_notice"])
        occ_spin = ttk.Spinbox(occ_notice_f, from_=0, to=999, increment=12,
                                textvariable=self.occupant_hrs_notice_var, width=12)
        occ_spin.pack(side="left")

        self._noti_occupants_text = text_box(
            tab, 4,
            NOTIFICATION_DEFAULTS["noti_to_occupants"].replace(
                "{{occupant_hrs_notice}}", str(self.occupant_hrs_notice_var.get())))

        def _update_noti_occupants(event=None):
            template = NOTIFICATION_DEFAULTS["noti_to_occupants"]
            try:
                hrs = str(self.occupant_hrs_notice_var.get())
            except tk.TclError:
                hrs = occ_spin.get()
            preview = template.replace("{{occupant_hrs_notice}}", hrs)
            self._noti_occupants_text.delete("1.0", "end")
            self._noti_occupants_text.insert("1.0", preview)
        self._update_noti_occupants = _update_noti_occupants
        occ_spin.bind("<<Increment>>", lambda e: self.root.after(1, _update_noti_occupants))
        occ_spin.bind("<<Decrement>>", lambda e: self.root.after(1, _update_noti_occupants))
        occ_spin.bind("<KeyRelease>", _update_noti_occupants)
        occ_spin.bind("<FocusOut>", _update_noti_occupants)

        # -- Example Posted Notice --
        prop_hdr = ttk.Frame(tab)
        prop_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(prop_hdr, text="Example of Proposed Notice",
                  font=("", 9, "bold")).pack(side="left")
        ttk.Label(prop_hdr, text="  (Section 4.2)", foreground="gray", font=("", 8)).pack(side="left")

        self._prop_notice_text = text_box(tab, 4, NOTIFICATION_DEFAULTS["prop_notice_example"])

        # ── Personnel Safety (Section 5) ──────────────────────────────────
        ps_hdr = ttk.Frame(tab)
        ps_hdr.pack(anchor="w", pady=(16, 6))
        ttk.Label(ps_hdr, text="Personnel Safety", font=("", 10, "bold")).pack(side="left")
        ttk.Label(ps_hdr, text="  (Section 5)", foreground="gray", font=("", 8)).pack(side="left")

        # -- Safety Protocols --
        sp_hdr = ttk.Frame(tab)
        sp_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(sp_hdr, text="Safety Protocols", font=("", 9, "bold")).pack(side="left")
        ttk.Label(sp_hdr, text="  (Section 5.1)", foreground="gray", font=("", 8)).pack(side="left")

        # Building phase
        phase_f = ttk.Frame(tab)
        phase_f.pack(anchor="w", pady=(0, 4))
        ttk.Label(phase_f, text="Building Phase:").pack(side="left", padx=(0, 6))
        self.building_phase_var = tk.StringVar(value="occupied")
        ttk.Radiobutton(phase_f, text="Occupied", variable=self.building_phase_var,
                        value="occupied").pack(side="left", padx=(0, 8))
        ttk.Radiobutton(phase_f, text="Under Construction", variable=self.building_phase_var,
                        value="construction").pack(side="left")

        # PPE required toggle
        ppe_req_f = ttk.Frame(tab)
        ppe_req_f.pack(anchor="w", pady=(0, 4))
        ttk.Label(ppe_req_f, text="PPE Required:").pack(side="left", padx=(0, 6))
        self.ppe_required_var = tk.BooleanVar(value=True)
        ttk.Radiobutton(ppe_req_f, text="Yes", variable=self.ppe_required_var,
                        value=True).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(ppe_req_f, text="No", variable=self.ppe_required_var,
                        value=False).pack(side="left")

        # PPE list
        self.ppe_items = list(PPE_DEFAULTS)
        ppe_f = ttk.Frame(tab)
        ppe_f.pack(anchor="w", fill="x", pady=(0, 6))
        ttk.Label(ppe_f, text="PPE Items (drag to reorder):", foreground="gray").pack(anchor="w")
        ppe_tree = ttk.Treeview(ppe_f, columns=("item",), show="headings", height=5)
        ppe_tree.heading("item", text="PPE Item")
        ppe_tree.column("item", width=260)
        ppe_tree.pack(fill="x")

        def _refresh_ppe_tree():
            ppe_tree.delete(*ppe_tree.get_children())
            for i, item in enumerate(self.ppe_items):
                ppe_tree.insert("", "end", iid=str(i), values=(item,))

        self._refresh_ppe_tree = _refresh_ppe_tree
        _refresh_ppe_tree()

        ppe_add_f = ttk.Frame(ppe_f)
        ppe_add_f.pack(fill="x", pady=(4, 0))
        ppe_entry = ttk.Entry(ppe_add_f, width=30)
        ppe_entry.pack(side="left", padx=(0, 4))

        def _add_ppe():
            val = ppe_entry.get().strip()
            if val:
                self.ppe_items.append(val)
                ppe_entry.delete(0, "end")
                _refresh_ppe_tree()
                _update_safety_protocols()

        def _remove_ppe():
            sel = ppe_tree.selection()
            if sel:
                del self.ppe_items[int(sel[0])]
                _refresh_ppe_tree()
                _update_safety_protocols()

        ppe_entry.bind("<Return>", lambda e: _add_ppe())
        ppe_add_btn = ttk.Button(ppe_add_f, text="+ Add", command=_add_ppe)
        ppe_add_btn.pack(side="left", padx=(0, 4))
        ppe_remove_btn = ttk.Button(ppe_add_f, text="Remove", command=_remove_ppe)
        ppe_remove_btn.pack(side="left")

        # Drag-to-reorder for PPE list
        _ppe_drag = {"item": None}

        def _ppe_drag_start(event):
            item = ppe_tree.identify_row(event.y)
            if item:
                _ppe_drag["item"] = item
                ppe_tree.selection_set(item)

        def _ppe_drag_motion(event):
            if not _ppe_drag["item"]:
                return
            target = ppe_tree.identify_row(event.y)
            if not target or target == _ppe_drag["item"]:
                return
            bbox = ppe_tree.bbox(target)
            if not bbox:
                return
            mid = bbox[1] + bbox[3] // 2
            src_idx = int(_ppe_drag["item"])
            tgt_idx = int(target)
            dst_idx = tgt_idx if event.y < mid else tgt_idx + 1
            dst_idx = max(0, min(len(self.ppe_items) - 1, dst_idx))
            if dst_idx != src_idx:
                moved = self.ppe_items.pop(src_idx)
                self.ppe_items.insert(dst_idx, moved)
                _refresh_ppe_tree()
                new_iid = str(dst_idx)
                ppe_tree.selection_set(new_iid)
                ppe_tree.focus(new_iid)
                _ppe_drag["item"] = new_iid
                _update_safety_protocols()

        def _ppe_drag_end(event):
            _ppe_drag["item"] = None

        ppe_tree.bind("<ButtonPress-1>",  _ppe_drag_start)
        ppe_tree.bind("<B1-Motion>",       _ppe_drag_motion)
        ppe_tree.bind("<ButtonRelease-1>", _ppe_drag_end)

        ppe_widgets = [ppe_tree, ppe_entry, ppe_add_btn, ppe_remove_btn]

        def _update_ppe_state(*_):
            state = ["!disabled"] if self.ppe_required_var.get() else ["disabled"]
            for w in ppe_widgets:
                w.state(state)

        self._update_ppe_state = _update_ppe_state

        self._safety_protocols_text = text_box(tab, 12, "")

        def _update_safety_protocols(event=None):
            phase_text = BUILDING_PHASE_TEXT.get(self.building_phase_var.get(), BUILDING_PHASE_TEXT["occupied"])
            if self.ppe_required_var.get():
                intro = SAFETY_PROTOCOLS_INTRO_PPE.replace("{{building_phase}}", phase_text)
                parts = [intro]
                if self.ppe_items:
                    parts.append("\n".join(f"•  {item}" for item in self.ppe_items))
                parts.append(SAFETY_PROTOCOLS_BODY)
            else:
                intro = SAFETY_PROTOCOLS_INTRO_NO_PPE.replace("{{building_phase}}", phase_text)
                parts = [intro, SAFETY_PROTOCOLS_BODY]
            preview = "\n\n".join(parts)
            self._safety_protocols_text.delete("1.0", "end")
            self._safety_protocols_text.insert("1.0", preview)

        self._update_safety_protocols = _update_safety_protocols
        self.building_phase_var.trace_add("write", lambda *_: _update_safety_protocols())
        self.ppe_required_var.trace_add("write", lambda *_: (_update_ppe_state(), _update_safety_protocols()))
        _update_ppe_state()
        _update_safety_protocols()

        # -- Special Hazards --
        sh_hdr = ttk.Frame(tab)
        sh_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(sh_hdr, text="Special Hazards", font=("", 9, "bold")).pack(side="left")
        ttk.Label(sh_hdr, text="  (Section 5.2)", foreground="gray", font=("", 8)).pack(side="left")
        self._special_hazards_text = text_box(tab, 3, SPECIAL_HAZARDS_DEFAULT)

        # -- Team Communications --
        tc_hdr = ttk.Frame(tab)
        tc_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(tc_hdr, text="Team Communications", font=("", 9, "bold")).pack(side="left")
        ttk.Label(tc_hdr, text="  (Section 5.3)", foreground="gray", font=("", 8)).pack(side="left")
        self._team_communications_text = text_box(tab, 12, TEAM_COMMUNICATIONS_DEFAULT)

        # -- Occupant Notification of Emergencies --
        on_hdr = ttk.Frame(tab)
        on_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(on_hdr, text="Occupant Notification of Emergencies", font=("", 9, "bold")).pack(side="left")
        ttk.Label(on_hdr, text="  (Section 5.4)", foreground="gray", font=("", 8)).pack(side="left")
        self._occupant_notification_text = text_box(tab, 3, OCCUPANT_NOTIFICATION_DEFAULT)

    # ---------- Forms and Documentation tab ----------

    def _build_forms_documentation_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="Forms and Documentation")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        hdr = ttk.Frame(tab)
        hdr.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(hdr, text="Forms and Documentation", font=("", 9, "bold")).pack(side="left")
        ttk.Label(hdr, text="  (Sections 6 & 7)", foreground="gray", font=("", 8)).pack(side="left")

        dark = getattr(self, "_dark_mode", False)
        txt_bg  = "#1e1e1e" if dark else "white"
        txt_fg  = "#d4d4d4" if dark else "black"
        ins_clr = "#d4d4d4" if dark else "black"

        text_frame = ttk.Frame(tab)
        text_frame.grid(row=1, column=0, sticky="nswe")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        sb = ttk.Scrollbar(text_frame, orient="vertical")
        self._forms_doc_text = tk.Text(
            text_frame, wrap="word",
            yscrollcommand=sb.set,
            undo=True, maxundo=50,
            relief="flat", bd=1,
            highlightthickness=1,
            highlightbackground="#aaaaaa",
            highlightcolor="#0078d4",
            background=txt_bg, foreground=txt_fg,
            insertbackground=ins_clr,
        )
        sb.configure(command=self._forms_doc_text.yview)
        self._forms_doc_text.grid(row=0, column=0, sticky="nswe")
        sb.grid(row=0, column=1, sticky="ns")
        attach_spellcheck(self._forms_doc_text)

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

    def _show_overlay(self, message, callback, duration_ms=900):
        """Show a full-window Arencon-branded overlay, run callback mid-way, then dismiss."""
        root = self.root
        root.update_idletasks()
        rw = root.winfo_width()  or root.winfo_screenwidth()
        rh = root.winfo_height() or root.winfo_screenheight()
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()

        dark    = getattr(self, "_dark_mode", False)
        # Outer overlay background matches current theme
        ov_bg   = "#1a1a1a" if dark else "white"
        # Inner card is always white (matches startup splash)
        card_bg = "white"
        fg_sub  = "#555555"
        fg_msg  = "#888888"
        bar_trk = "#e0e0e0"

        ov = tk.Toplevel(root)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        ov.geometry(f"{rw}x{rh}+{rx}+{ry}")
        ov.configure(bg=ov_bg)

        # ── Mahogany border → white interior (identical to startup splash) ──
        border = tk.Frame(ov, bg="#7e003f", padx=12, pady=12)
        border.place(relx=0.5, rely=0.5, anchor="center")
        inner = tk.Frame(border, bg=card_bg, padx=30, pady=24)
        inner.pack(fill="both", expand=True)

        # Logo (on white bg — same as startup splash)
        try:
            from PIL import Image, ImageTk
            import sys, os
            def _res(p):
                if hasattr(sys, "_MEIPASS"):
                    return os.path.join(sys._MEIPASS, p)
                return os.path.join(os.path.dirname(os.path.abspath(__file__)), p)
            img = Image.open(_res("AI_LOGO_TXT.png")).convert("RGBA")
            white_bg_img = Image.new("RGBA", img.size, (255, 255, 255, 255))
            white_bg_img.paste(img, mask=img.split()[3])
            img = white_bg_img.convert("RGB")
            img.thumbnail((240, 72), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl_img = tk.Label(inner, image=photo, bg=card_bg, bd=0)
            lbl_img.image = photo
            lbl_img.pack(pady=(0, 10))
        except Exception as e:
            print(f"Overlay logo load error: {e}")
            tk.Label(inner, text="ARENCON INC.", font=("Arial", 16, "bold"),
                     bg=card_bg, fg="#7e003f").pack(pady=(0, 10))

        # Mahogany divider
        tk.Frame(inner, bg="#7e003f", height=2, width=300).pack(pady=(0, 14))

        # App name line — black to match startup splash
        tk.Label(inner, text="IST Generator",
                 font=("Arial", 13, "bold"), bg=card_bg, fg="#000000").pack()
        tk.Label(inner, text="V1.1  |  Integrated Systems Testing Report Generator",
                 font=("Arial", 8), bg=card_bg, fg=fg_sub).pack(pady=(2, 12))

        # Status message
        tk.Label(inner, text=message, font=("Arial", 8),
                 bg=card_bg, fg=fg_msg).pack(pady=(0, 6))

        # Progress bar (identical sizing to startup splash)
        bar_frame = tk.Frame(inner, bg=card_bg)
        bar_frame.pack(fill="x")
        bar_bg_f = tk.Frame(bar_frame, bg=bar_trk, width=300, height=5)
        bar_bg_f.pack(fill="x")
        bar_bg_f.pack_propagate(False)
        bar_fill = tk.Frame(bar_bg_f, bg="#7e003f", height=5, width=0)
        bar_fill.place(x=0, y=0, height=5)

        # ── Three-phase sequence ─────────────────────────────────────────
        # Phase 1: 300ms pre-wait — bar animates from 0→50%, overlay covers app
        # Phase 2: fire callback + update — work completes, overlay still covers
        # Phase 3: 300ms post-wait — bar sweeps 50→100%, then close
        _w     = [0]
        _BAR_W = 300
        _PRE_STEPS  = 10   # steps to reach 50% during pre-wait (300ms / 30ms each)
        _POST_STEPS = 10   # steps from 50→100% during post-wait

        def _phase3(n=0):
            target = _BAR_W // 2 + int((_BAR_W // 2) * (n + 1) / _POST_STEPS)
            _w[0] = min(target, _BAR_W)
            bar_fill.place(x=0, y=0, height=5, width=_w[0])
            if n + 1 < _POST_STEPS:
                ov.after(15, lambda: _phase3(n + 1))
            else:
                ov.after(80, ov.destroy)

        def _phase2():
            callback()
            ov.update_idletasks()
            _phase3()   # no post-wait — sweep to full immediately after callback

        def _phase1(n=0):
            _w[0] = int((_BAR_W // 2) * (n + 1) / _PRE_STEPS)
            bar_fill.place(x=0, y=0, height=5, width=_w[0])
            if n + 1 < _PRE_STEPS:
                ov.after(15, lambda: _phase1(n + 1))
            else:
                _phase2()            # pre-wait done → fire callback immediately

        ov.after(10, lambda: _phase1(0))  # start bar right away

    def load_from_file(self):
        path = filedialog.askopenfilename(
            title="Load Data File",
            filetypes=[("Text/JSON files", "*.txt *.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load file:\n{e}")
            return

        def _do_load():
            try:
                self._populate_from_data(data)
                self.current_data_file.set(path)
            except Exception as e2:
                messagebox.showerror("Load Error", f"Could not load file:\n{e2}")

        self._show_overlay("Loading data file…", _do_load)

    # ============================================================
    #   DATA GATHER / POPULATE
    # ============================================================