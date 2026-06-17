"""
ui_system_tab.py — Per-system tab builder and all system-specific UI helpers.
This is a mixin combined with TabsMixin in main.py.
Change this file for anything inside a system tab: fields, live previews,
matrix rows, Appendix B rows, or the FA initiating device panel.
"""

import tkinter as tk
from tkinter import ttk

from spellcheck import attach_spellcheck
from defaults import (
    SYSTEM_DEFAULTS, SPRINKLER_SUBTYPE_ORDER, PRE_ACTION_SUBTYPE_ORDER, get_sprinkler_text,
    APPB_DEFAULTS, APPB_DESC_DEFAULTS, APPB_SW_TYPE_DEFAULTS, MATRIX_DEFAULTS, TP_DEFAULTS,
)
from constants import MONITORING_MATRIX_DEFAULTS, LOREM
from ui_scroll import bind_mousewheel, enable_text_autoresize


class SystemTabMixin:
    @staticmethod
    def _attach_entry_placeholder(entry, placeholder, color="#999999"):
        """
        Show grey hint text in an empty ttk.Entry; clears on focus and
        reappears on focus-out if the field is left empty.

        get()/insert()/delete() are wrapped on this instance so the
        placeholder text is never returned/treated as real content by
        callers elsewhere (e.g. data gather/save, report generation).
        """
        normal_fg = entry.cget("foreground")
        orig_get    = entry.get
        orig_insert = entry.insert
        orig_delete = entry.delete

        def _show_placeholder():
            orig_insert(0, placeholder)
            entry.configure(foreground=color)
            entry._is_placeholder = True

        def _hide_placeholder():
            if getattr(entry, "_is_placeholder", False):
                orig_delete(0, "end")
                entry.configure(foreground=normal_fg)
                entry._is_placeholder = False

        def _get():
            if getattr(entry, "_is_placeholder", False):
                return ""
            return orig_get()

        def _insert(index, text):
            if text == "":
                return
            _hide_placeholder()
            orig_insert(index, text)

        def _delete(*args):
            orig_delete(*args)
            entry._is_placeholder = False
            entry.configure(foreground=normal_fg)
            if not orig_get() and entry.focus_get() is not entry:
                _show_placeholder()

        def _on_focus_in(event=None):
            _hide_placeholder()

        def _on_focus_out(event=None):
            if not orig_get():
                _show_placeholder()

        entry.get    = _get
        entry.insert = _insert
        entry.delete = _delete
        entry.bind("<FocusIn>",  _on_focus_in,  add="+")
        entry.bind("<FocusOut>", _on_focus_out, add="+")

        _show_placeholder()

    @staticmethod
    def _enable_tree_drag_reorder(tree, data_list, refresh_fn):
        """
        Allow rows of a ttk.Treeview backed by `data_list` (a list of dicts,
        one per row in display order) to be reordered by click-and-drag.
        `refresh_fn()` redraws the tree (and any live preview) after each move.
        """
        drag = {"index": None}

        def _on_press(event):
            row = tree.identify_row(event.y)
            drag["index"] = tree.index(row) if row else None

        def _on_motion(event):
            src = drag["index"]
            if src is None:
                return
            row = tree.identify_row(event.y)
            if not row:
                return
            dst = tree.index(row)
            if dst != src:
                data_list.insert(dst, data_list.pop(src))
                drag["index"] = dst
                refresh_fn()
                children = tree.get_children()
                if 0 <= dst < len(children):
                    tree.selection_set(children[dst])

        def _on_release(event):
            drag["index"] = None

        tree.bind("<ButtonPress-1>",  _on_press,   add="+")
        tree.bind("<B1-Motion>",      _on_motion,  add="+")
        tree.bind("<ButtonRelease-1>", _on_release, add="+")

    def _build_system_tab(self, sys_info):
        key   = sys_info["key"]
        label = sys_info["label"]

        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text=label)

        present_var = tk.BooleanVar(value=True)

        # Outer scrollable canvas so the tab can scroll vertically
        tab_canvas = tk.Canvas(outer, highlightthickness=0)
        tab_scroll = ttk.Scrollbar(outer, orient="vertical", command=tab_canvas.yview)
        tab_canvas.configure(yscrollcommand=tab_scroll.set)
        tab_scroll.pack(side="right", fill="y")
        tab_canvas.pack(side="left", fill="both", expand=True)
        content_wrap = ttk.Frame(tab_canvas, padding=10)
        wrap_id = tab_canvas.create_window((0, 0), window=content_wrap, anchor="nw")
        def _refresh_scroll(event=None):
            tab_canvas.configure(scrollregion=tab_canvas.bbox("all"))

        content_wrap.bind("<Configure>", _refresh_scroll)

        def _on_canvas_resize(e):
            tab_canvas.itemconfig(wrap_id, width=e.width)
            self.root.after(0, _refresh_scroll)

        tab_canvas.bind("<Configure>", _on_canvas_resize)
        bind_mousewheel(tab_canvas)

        # Top section: text boxes left, right panel right
        content = ttk.Frame(content_wrap)
        content.pack(fill="both", expand=True)

        # ── Right panels (packed before left so left fills remaining) ──────
        if key == "fire_alarm":
            right = ttk.Frame(content, width=520)
            right.pack(side="right", fill="both", padx=(8, 0))
            self._build_fa_initiating_panel(right, present_var, None)

        if key == "fire_pump":
            right = ttk.Frame(content, width=220)
            right.pack(side="right", fill="y", padx=(8, 0))
            right.pack_propagate(False)
            ttk.Label(right, text="Fire Pump Location", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
            fp_frame = ttk.Frame(right)
            fp_frame.pack(fill="x")
            ttk.Label(fp_frame, text="Room:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=3)
            self.fp_room_entry = ttk.Entry(fp_frame, width=16)
            self.fp_room_entry.grid(row=0, column=1, sticky="we", pady=3)
            ttk.Label(fp_frame, text="Level:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=3)
            self.fp_floor_entry = ttk.Entry(fp_frame, width=16)
            self.fp_floor_entry.grid(row=1, column=1, sticky="we", pady=3)
            fp_frame.columnconfigure(1, weight=1)

        if key == "generator":
            right = ttk.Frame(content, width=320)
            right.pack(side="right", fill="both", padx=(8, 0))

            ttk.Label(right, text="Generator Details", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
            gen_det_frame = ttk.Frame(right)
            gen_det_frame.pack(fill="x", pady=(0, 6))

            ttk.Label(gen_det_frame, text="No. of Generators:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=3)
            self.gen_count_var = tk.IntVar(value=1)
            ttk.Spinbox(gen_det_frame, from_=1, to=99, textvariable=self.gen_count_var,
                        width=6).grid(row=0, column=1, sticky="w", pady=3)

            ttk.Label(gen_det_frame, text="Type:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=3)
            self.gen_type_var = tk.StringVar(value="diesel")
            gen_type_frame = ttk.Frame(gen_det_frame)
            gen_type_frame.grid(row=1, column=1, sticky="w", pady=3)
            ttk.Radiobutton(gen_type_frame, text="Diesel", variable=self.gen_type_var,
                            value="diesel").pack(side="left", padx=(0, 8))
            ttk.Radiobutton(gen_type_frame, text="Natural Gas", variable=self.gen_type_var,
                            value="natural gas").pack(side="left")

            ttk.Label(gen_det_frame, text="Class:").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=3)
            self.gen_class_var = tk.StringVar(value="non-emergency")
            gen_class_frame = ttk.Frame(gen_det_frame)
            gen_class_frame.grid(row=2, column=1, sticky="w", pady=3)
            ttk.Radiobutton(gen_class_frame, text="Emergency (Fire and Life Safety)",
                            variable=self.gen_class_var, value="emergency",
                            command=lambda: self._refresh_gen_served_tab()).pack(anchor="w")
            ttk.Radiobutton(gen_class_frame, text="Non-Emergency (Non-Fire-and-Life-Safety)",
                            variable=self.gen_class_var, value="non-emergency",
                            command=lambda: self._refresh_gen_served_tab()).pack(anchor="w")

            ttk.Label(gen_det_frame, text="Room:").grid(row=3, column=0, sticky="w", padx=(0, 4), pady=3)
            self.gen_room_entry = ttk.Entry(gen_det_frame, width=16)
            self.gen_room_entry.grid(row=3, column=1, sticky="we", pady=3)

            ttk.Label(gen_det_frame, text="Floor:").grid(row=4, column=0, sticky="w", padx=(0, 4), pady=3)
            self.gen_floor_entry = ttk.Entry(gen_det_frame, width=16)
            self.gen_floor_entry.grid(row=4, column=1, sticky="we", pady=3)

            gen_det_frame.columnconfigure(1, weight=1)

            ttk.Separator(right, orient="horizontal").pack(fill="x", pady=(0, 6))
            ttk.Label(right, text="Served Systems", font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))
            self.gen_check_inner = ttk.Frame(right)
            self.gen_check_inner.pack(fill="both", expand=True, pady=(0, 4))
            self.gen_served_vars = {}
            self.gen_custom_served = []  # list of {"label": str, "var": BooleanVar}
            GEN_DISPLAY = {
                "Fire Alarm": "Fire Alarm System",
                "Fire Pump": "Fire Pump", "Maglocks": "Electromagnetic Locks",
                "Door Holders": "Door Holders", "AHU/Fan": "Air Handling Units",
                "Smoke Dampers": "Smoke Dampers", "Fire Shutters": "Fire Shutters",
                "Kitchen Hood": "Kitchen Hood Suppression System",
                "Water Mist": "Water Mist System", "Elevator": "Elevator",
            }
            self._gen_display = GEN_DISPLAY

            # ── Custom served system entry ────────────────────────────────
            custom_add_frame = ttk.Frame(right)
            custom_add_frame.pack(fill="x", pady=(2, 0))
            self._gen_custom_entry = ttk.Entry(custom_add_frame, width=18)
            self._gen_custom_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

            def _add_custom_served(event=None):
                label = self._gen_custom_entry.get().strip()
                if not label:
                    return
                # Prevent duplicates
                existing = [c["label"] for c in self.gen_custom_served]
                if label in existing or label in GEN_DISPLAY:
                    return
                var = tk.BooleanVar(value=True)
                self.gen_custom_served.append({"label": label, "var": var})
                self._gen_custom_entry.delete(0, "end")
                _refresh_gen_checklist()

            self._gen_custom_btn = ttk.Button(custom_add_frame, text="+", width=2,
                                              command=_add_custom_served)
            self._gen_custom_btn.pack(side="left")
            self._gen_custom_entry.bind("<Return>", _add_custom_served)
            # Start disabled (non-emergency is the default)
            self._gen_custom_entry.state(["disabled"])
            self._gen_custom_btn.state(["disabled"])

        if key == "pre_action":
            # Plain frame — grows naturally to show all content
            right = ttk.Frame(content, padding=(6, 6))
            right.pack(side="right", fill="y", padx=(8, 0))
            rinner = right

            ttk.Label(rinner, text="Pre-Action Details", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))

            # Designated Pre-Action Panel checkbox
            self.pre_action_panel_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                rinner, text="Designated Pre-Action Panel",
                variable=self.pre_action_panel_var,
                command=lambda: self._refresh_pre_action_panel_tab()
            ).pack(anchor="w", pady=(0, 2))
            ttk.Label(rinner, text="Check if a dedicated pre-action panel is present on-site.",
                      foreground="gray", font=("", 8), wraplength=280, justify="left").pack(anchor="w", pady=(0, 10))

            ttk.Separator(rinner, orient="horizontal").pack(fill="x", pady=(0, 8))

            # ── Pre-Action Protected Areas list ──────────────────────
            ttk.Label(rinner, text="Pre-Action Protected Areas",
                      font=("", 8, "bold")).pack(anchor="w", pady=(0, 3))
            self.pa_protected_areas = []
            pa_tree = ttk.Treeview(rinner, columns=("area",), show="headings", height=3)
            pa_tree.heading("area", text="Area / Room")
            pa_tree.column("area", width=240)
            pa_tree.pack(fill="x", pady=(0, 4))
            self.pa_protected_areas_tree = pa_tree

            def _refresh_pa_tree():
                pa_tree.delete(*pa_tree.get_children())
                for i, a in enumerate(self.pa_protected_areas):
                    pa_tree.insert("", "end", iid=str(i), values=(a,))

            pa_entry = ttk.Entry(rinner, width=30)
            pa_entry.pack(fill="x", pady=(0, 4), ipady=3)
            pa_entry.bind("<Return>", lambda e: _add_pa_area() or self.root.after(10, lambda: self._update_preac_desc() if hasattr(self, "_update_preac_desc") else None))
            self.pa_area_entry = pa_entry

            def _add_pa_area():
                val = pa_entry.get().strip()
                if val:
                    self.pa_protected_areas.append(val)
                    pa_entry.delete(0, "end")
                    _refresh_pa_tree()

            def _remove_pa_area():
                sel = pa_tree.selection()
                if sel:
                    del self.pa_protected_areas[int(sel[0])]
                    _refresh_pa_tree()

            pa_tree.bind("<Double-1>", lambda e: (
                pa_entry.delete(0, "end"),
                pa_entry.insert(0, self.pa_protected_areas[int(pa_tree.selection()[0])]) if pa_tree.selection() else None,
                self.pa_protected_areas.__delitem__(int(pa_tree.selection()[0])) if pa_tree.selection() else None,
                _refresh_pa_tree()
            ))

            pa_btn_f = ttk.Frame(rinner)
            pa_btn_f.pack(fill="x", pady=(0, 12))
            ttk.Button(pa_btn_f, text="+ Add",  command=_add_pa_area).pack(side="left", padx=(0, 4))
            ttk.Button(pa_btn_f, text="Remove", command=_remove_pa_area).pack(side="left")
            self._refresh_pa_tree = _refresh_pa_tree

            ttk.Separator(rinner, orient="horizontal").pack(fill="x", pady=(0, 8))

            # ── Control Valve Locations list ─────────────────────────
            ttk.Label(rinner, text="Control Valve Locations",
                      font=("", 8, "bold")).pack(anchor="w", pady=(0, 3))
            self.pa_valve_locations = []
            cv_tree = ttk.Treeview(rinner, columns=("loc",), show="headings", height=3)
            cv_tree.heading("loc", text="Location")
            cv_tree.column("loc", width=240)
            cv_tree.pack(fill="x", pady=(0, 4))
            self.pa_valve_tree = cv_tree

            def _refresh_cv_tree():
                cv_tree.delete(*cv_tree.get_children())
                for i, v in enumerate(self.pa_valve_locations):
                    cv_tree.insert("", "end", iid=str(i), values=(v,))

            cv_entry = ttk.Entry(rinner, width=30)
            cv_entry.pack(fill="x", pady=(0, 4), ipady=3)
            cv_entry.bind("<Return>", lambda e: _add_cv() or self.root.after(10, lambda: self._update_preac_desc() if hasattr(self, "_update_preac_desc") else None))
            self.pa_valve_entry = cv_entry

            def _add_cv():
                val = cv_entry.get().strip()
                if val:
                    self.pa_valve_locations.append(val)
                    cv_entry.delete(0, "end")
                    _refresh_cv_tree()

            def _remove_cv():
                sel = cv_tree.selection()
                if sel:
                    del self.pa_valve_locations[int(sel[0])]
                    _refresh_cv_tree()

            cv_btn_f = ttk.Frame(rinner)
            cv_btn_f.pack(fill="x", pady=(0, 4))
            ttk.Button(cv_btn_f, text="+ Add",  command=_add_cv).pack(side="left", padx=(0, 4))
            ttk.Button(cv_btn_f, text="Remove", command=_remove_cv).pack(side="left")
            self._refresh_cv_tree = _refresh_cv_tree

            # ── Pre-Action live description preview ───────────────
            def _update_preac_desc(event=None):
                # Get desc_text from local closure (set after right panel)
                _dt = desc_text if "desc_text" in dir() else None
                target = _dt
                if target is None:
                    return

                # Protected areas
                areas = getattr(self, "pa_protected_areas", [])
                if areas:
                    if len(areas) == 1:
                        areas_str = areas[0]
                        area_verb = "is"
                    elif len(areas) == 2:
                        areas_str = f"{areas[0]} and {areas[1]}"
                        area_verb = "are"
                    else:
                        areas_str = ", ".join(areas[:-1]) + f", and {areas[-1]}"
                        area_verb = "are"
                else:
                    areas_str = "{{preac_protec_areas}}"
                    area_verb = "is"

                # System type from subtype vars
                selected_var = getattr(self, "_pre_action_selected_var", None)
                if selected_var:
                    raw = selected_var.get()
                    # Strip "Pre-Action (" prefix and trailing ")"
                    if raw.startswith("Pre-Action (") and raw.endswith(")"):
                        type_str = raw[len("Pre-Action ("):-1]
                    else:
                        type_str = raw
                else:
                    type_str = "Single Interlock"

                # Valve locations as bulleted list (same format as generator)
                valves = getattr(self, "pa_valve_locations", [])
                if valves:
                    vlv_str = "\n".join(f"\t\u2022  {v}" for v in valves)
                else:
                    vlv_str = "\t\u2022  {{preac_vlv_locs}}"

                # Panel or fire alarm
                has_panel = getattr(self, "pre_action_panel_var", tk.BooleanVar()).get()
                pan_or_fa = "the designated pre-action panel" if has_panel else "the fire alarm system"

                template = SYSTEM_DEFAULTS.get("pre_action", {}).get("description", LOREM)
                preview = template
                preview = preview.replace("{{preac_protec_areas}}", areas_str)
                preview = preview.replace("{{preac_area_verb}}", area_verb)
                preview = preview.replace("{{preac_type}}", type_str)
                preview = preview.replace("{{preac_vlv_locs}}", vlv_str)
                preview = preview.replace("{{preac_pan_or_fa}}", pan_or_fa)
                target.delete("1.0", "end")
                target.insert("1.0", preview)
                # Also keep the integrations text in sync
                int_ref = getattr(self, "_pre_action_int_text_ref", None)
                if int_ref is not None:
                    try:
                        int_tmpl = SYSTEM_DEFAULTS.get("pre_action", {}).get("integrations", "")
                        current = int_ref.get("1.0", "end-1c")
                        # Only auto-update if user hasn't made custom edits
                        for _v in ("the designated pre-action panel", "the fire alarm system",
                                   "the Pre-Action Panel", "the Fire Alarm",
                                   "{{preac_pan_or_fa}}"):
                            if current.strip() == int_tmpl.replace("{{preac_pan_or_fa}}", _v).strip():
                                int_ref.delete("1.0", "end")
                                int_ref.insert("1.0", int_tmpl.replace("{{preac_pan_or_fa}}", pan_or_fa))
                                break
                    except Exception:
                        pass

            self._update_preac_desc = _update_preac_desc

            # Hook into add/remove for areas and valves
            _orig_add_pa  = _add_pa_area
            _orig_rem_pa  = _remove_pa_area
            _orig_add_cv  = _add_cv
            _orig_rem_cv  = _remove_cv

            def _add_pa_area_h():
                _orig_add_pa()
                self.root.after(10, _update_preac_desc)
            def _remove_pa_area_h():
                _orig_rem_pa()
                self.root.after(10, _update_preac_desc)
            def _add_cv_h():
                _orig_add_cv()
                self.root.after(10, _update_preac_desc)
            def _remove_cv_h():
                _orig_rem_cv()
                self.root.after(10, _update_preac_desc)

            # Rebind buttons to hooked versions
            for w in cv_btn_f.winfo_children():
                if isinstance(w, ttk.Button):
                    t = w.cget("text")
                    if t == "+ Add":  w.configure(command=_add_cv_h)
                    if t == "Remove": w.configure(command=_remove_cv_h)
            for w in pa_btn_f.winfo_children():
                if isinstance(w, ttk.Button):
                    t = w.cget("text")
                    if t == "+ Add":  w.configure(command=_add_pa_area_h)
                    if t == "Remove": w.configure(command=_remove_pa_area_h)

            # Hook panel checkbox
            self.pre_action_panel_var.trace_add("write", lambda *_: _update_preac_desc())

        if key == "elevator":
            right = ttk.Frame(content, width=280)
            right.pack(side="right", fill="y", padx=(8, 0))
            right.pack_propagate(False)
            ttk.Label(right, text="Elevator Details", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
            elev_frame = ttk.Frame(right)
            elev_frame.pack(fill="x")

            ttk.Label(elev_frame, text="No. of Elevators:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=4)
            self.elev_count_var = tk.IntVar(value=1)
            ttk.Spinbox(elev_frame, from_=1, to=99, textvariable=self.elev_count_var,
                        width=6, command=lambda: _update_elev_preview()).grid(row=0, column=1, sticky="w", pady=4)

            ttk.Label(elev_frame, text="Primary Recall:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=4)
            self.elev_primary_floor = ttk.Entry(elev_frame, width=18)
            self.elev_primary_floor.grid(row=1, column=1, sticky="we", pady=4)
            self._attach_entry_placeholder(self.elev_primary_floor, "e.g. Ground Floor")

            ttk.Label(elev_frame, text="Alternate Recall:").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=4)
            self.elev_alternate_floor = ttk.Entry(elev_frame, width=18)
            self.elev_alternate_floor.grid(row=2, column=1, sticky="we", pady=4)
            self._attach_entry_placeholder(self.elev_alternate_floor, "e.g. Second Floor")

            elev_frame.columnconfigure(1, weight=1)

            NUM_TO_TEXT = {
                1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
                6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
                11: "Eleven", 12: "Twelve",
            }

            def _update_elev_preview(event=None):
                count = self.elev_count_var.get()
                count_txt = NUM_TO_TEXT.get(count, str(count))
                elevator_s = "elevator" if count == 1 else "elevators"
                elevator_verb = "is" if count == 1 else "are"
                prim = self.elev_primary_floor.get().strip() or "{{elev_prim_rcl}}"
                alt  = self.elev_alternate_floor.get().strip() or "{{elev_alt_rcl}}"
                template = SYSTEM_DEFAULTS.get("elevator", {}).get("description", "")
                preview = template
                preview = preview.replace("{{elev_count_txt}}", count_txt)
                preview = preview.replace("{{elev_count_num}}", str(count))
                preview = preview.replace("{{elevator_s}}", elevator_s)
                preview = preview.replace("{{elevator_verb}}", elevator_verb)
                preview = preview.replace("{{elev_prim_rcl}}", prim)
                preview = preview.replace("{{elev_alt_rcl}}", alt)
                desc_text.delete("1.0", "end")
                desc_text.insert("1.0", preview)
                it = getattr(self, "_elev_int_text_ref", None)
                if it:
                    int_template = SYSTEM_DEFAULTS.get("elevator", {}).get("integrations", "")
                    it.delete("1.0", "end")
                    it.insert("1.0", int_template.replace("{{elevator_s}}", elevator_s).replace("{{elevator_verb}}", elevator_verb))
                # Refresh Appendix B rows to match elevator count
                self._refresh_elevator_appb_rows()

                # Live-update {{elev_prim_rcl}} / {{elev_alt_rcl}} placeholders in the
                # Integrations Matrix test-procedure bullet boxes
                try:
                    rows_ref = matrix_rows
                except NameError:
                    rows_ref = None
                if rows_ref is not None:
                    prev_prim = getattr(self, "_elev_prim_disp_prev", "{{elev_prim_rcl}}")
                    prev_alt  = getattr(self, "_elev_alt_disp_prev", "{{elev_alt_rcl}}")
                    if prev_prim != prim or prev_alt != alt:
                        for row in rows_ref:
                            for tw_key in ("tp_normal", "tp_fire"):
                                tw = row.get(tw_key)
                                if tw is None:
                                    continue
                                content = tw.get("1.0", "end-1c")
                                new_content = content.replace(prev_prim, prim).replace(prev_alt, alt)
                                if new_content != content:
                                    tw.delete("1.0", "end")
                                    tw.insert("1.0", new_content)
                    self._elev_prim_disp_prev = prim
                    self._elev_alt_disp_prev  = alt

            self._update_elev_preview = _update_elev_preview
            self.elev_primary_floor.bind("<KeyRelease>", _update_elev_preview)
            self.elev_alternate_floor.bind("<KeyRelease>", _update_elev_preview)
            self.elev_count_var.trace_add("write", lambda *_: _update_elev_preview())

        if key == "water_mist":
            right = ttk.Frame(content, width=280)
            right.pack(side="right", fill="both", padx=(8, 0))
            right.pack_propagate(False)
            wm_rcan = tk.Canvas(right, highlightthickness=0)
            wm_rscr = ttk.Scrollbar(right, orient="vertical", command=wm_rcan.yview)
            wm_rcan.configure(yscrollcommand=wm_rscr.set)
            wm_rscr.pack(side="right", fill="y")
            wm_rcan.pack(side="left", fill="both", expand=True)
            wm_rinner = ttk.Frame(wm_rcan, padding=(6, 6))
            wm_rid = wm_rcan.create_window((0, 0), window=wm_rinner, anchor="nw")
            wm_rinner.bind("<Configure>", lambda e: wm_rcan.configure(scrollregion=wm_rcan.bbox("all")))
            wm_rcan.bind("<Configure>", lambda e: wm_rcan.itemconfig(wm_rid, width=e.width))
            bind_mousewheel(wm_rcan)

            ttk.Label(wm_rinner, text="Water Mist Details", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
            ttk.Label(wm_rinner, text="Protected Areas", font=("", 8, "bold")).pack(anchor="w", pady=(0, 3))
            self.wm_protected_areas = []
            wm_area_tree = ttk.Treeview(wm_rinner, columns=("area",), show="headings", height=5)
            wm_area_tree.heading("area", text="Area / Room")
            wm_area_tree.column("area", width=230)
            wm_area_tree.pack(fill="x", pady=(0, 4))
            self.wm_area_tree = wm_area_tree

            def _refresh_wm_area_tree():
                wm_area_tree.delete(*wm_area_tree.get_children())
                for i, v in enumerate(self.wm_protected_areas):
                    wm_area_tree.insert("", "end", iid=str(i), values=(v,))

            wm_area_entry = ttk.Entry(wm_rinner, width=28)
            wm_area_entry.pack(fill="x", pady=(0, 4), ipady=3)
            wm_area_entry.bind("<Return>", lambda e: _add_wm_area())
            self.wm_area_entry = wm_area_entry

            def _add_wm_area():
                val = wm_area_entry.get().strip()
                if val:
                    self.wm_protected_areas.append(val)
                    wm_area_entry.delete(0, "end")
                    _refresh_wm_area_tree()
                    if hasattr(self, "_watermist_refresh_text"):
                        self._watermist_refresh_text()

            def _remove_wm_area():
                sel = wm_area_tree.selection()
                if sel:
                    del self.wm_protected_areas[int(sel[0])]
                    _refresh_wm_area_tree()
                    if hasattr(self, "_watermist_refresh_text"):
                        self._watermist_refresh_text()

            wm_btn_f = ttk.Frame(wm_rinner)
            wm_btn_f.pack(fill="x", pady=(0, 4))
            ttk.Button(wm_btn_f, text="+ Add",  command=_add_wm_area).pack(side="left", padx=(0, 4))
            ttk.Button(wm_btn_f, text="Remove", command=_remove_wm_area).pack(side="left")
            self._refresh_wm_area_tree = _refresh_wm_area_tree

        # ── Left: text boxes ───────────────────────────────────────────────
        left = ttk.Frame(content)
        left.pack(side="left", fill="both", expand=True)

        # Pre-Action sub-type selector (Single/Double Interlock)
        pre_action_subtype_vars = {}
        if key == "pre_action":
            pa_st_frame = ttk.LabelFrame(left, text="System Type", padding=(6, 4))
            pa_st_frame.pack(fill="x", pady=(0, 8))
            pa_spr_repaints = {}
            # Use a single StringVar so only one can be selected at a time (radio behaviour)
            pa_selected_var = tk.StringVar(value="Pre-Action (Single Interlock)")
            self._pre_action_selected_var = pa_selected_var
            for subtype in PRE_ACTION_SUBTYPE_ORDER:
                var = tk.BooleanVar(value=(subtype == "Pre-Action (Single Interlock)"))
                pre_action_subtype_vars[subtype] = var
                cell = tk.Frame(pa_st_frame, cursor="hand2")
                cell.pack(side="left", padx=(0, 6))
                lbl = tk.Label(cell, text=subtype, padx=10, pady=5, relief="flat", bd=0)
                lbl.pack()
                def _pa_repaint(v=var, c=cell, l=lbl):
                    if v.get():
                        c.configure(bg="#0078d4"); l.configure(bg="#0078d4", fg="white")
                    else:
                        c.configure(bg="#d0d0d0"); l.configure(bg="#d0d0d0", fg="#333333")
                def _pa_toggle(this_subtype=subtype, this_var=var, repaint=_pa_repaint):
                    # Deselect all others first (radio behaviour)
                    for s, v in pre_action_subtype_vars.items():
                        v.set(False)
                    this_var.set(True)
                    pa_selected_var.set(this_subtype)
                    for r in pa_spr_repaints.values():
                        r()
                    if hasattr(self, "_update_preac_desc"):
                        self.root.after(10, self._update_preac_desc)
                cell.bind("<Button-1>", lambda e, t=_pa_toggle: t())
                lbl.bind("<Button-1>", lambda e, t=_pa_toggle: t())
                _pa_repaint()
                pa_spr_repaints[subtype] = _pa_repaint
            self._pre_action_subtype_vars = pre_action_subtype_vars
            self._pre_action_subtype_repaints = pa_spr_repaints

        # Sprinkler sub-type selector
        sprinkler_subtype_vars = {}
        if key == "sprinkler":
            st_frame = ttk.LabelFrame(left, text="System Type", padding=(6, 4))
            st_frame.pack(fill="x", pady=(0, 8))

            # Create a ttk style for toggle-style Checkbuttons (blue when selected)
            style = ttk.Style()
            style.configure("Toggle.TCheckbutton",
                            relief="flat", padding=(10, 5))

            def _refresh_sprinkler_text():
                active = {s for s, v in sprinkler_subtype_vars.items() if v.get()}
                nd, ni = get_sprinkler_text(active)
                # Substitute {{sprk_type}} with human-readable label
                _type_map = {"Wet Pipe": "wet-pipe", "Dry Pipe": "dry-pipe"}
                _sel = [s for s in SPRINKLER_SUBTYPE_ORDER if sprinkler_subtype_vars.get(s, tk.BooleanVar()).get()]
                if len(_sel) == 1:
                    _type_str = _type_map.get(_sel[0], _sel[0].lower())
                elif len(_sel) == 2:
                    _type_str = f"{_type_map.get(_sel[0], _sel[0].lower())} and {_type_map.get(_sel[1], _sel[1].lower())}"
                else:
                    _type_str = "wet-pipe"
                nd = nd.replace("{{sprk_type}}", _type_str)
                # Substitute {{sprk_vlv_locs}} with bulleted valve locations
                _vlocs = getattr(self, "sprk_valve_locations", [])
                _vlv_str = ("\n".join(f"\t\u2022  {v}" for v in _vlocs)
                            if _vlocs else "\t\u2022  {{sprk_vlv_locs}}")
                nd = nd.replace("{{sprk_vlv_locs}}", _vlv_str)
                desc_text.delete("1.0", "end"); desc_text.insert("1.0", nd)
                int_text.delete("1.0", "end");  int_text.insert("1.0", ni)

            self._sprinkler_refresh_text = _refresh_sprinkler_text

            spr_repaints = {}
            for subtype in SPRINKLER_SUBTYPE_ORDER:
                var = tk.BooleanVar(value=(subtype == "Wet Pipe"))
                sprinkler_subtype_vars[subtype] = var

                # Plain tk.Frame+Label toggle — fully owns its background,
                # immune to ttk theme engine resets on Windows.
                cell = tk.Frame(st_frame, cursor="hand2")
                cell.pack(side="left", padx=(0, 6))
                lbl = tk.Label(cell, text=subtype, padx=10, pady=5,
                               relief="flat", bd=0)
                lbl.pack()

                def _repaint(v=var, c=cell, l=lbl):
                    if v.get():
                        c.configure(bg="#0078d4")
                        l.configure(bg="#0078d4", fg="white")
                    else:
                        c.configure(bg="#d0d0d0")
                        l.configure(bg="#d0d0d0", fg="#333333")

                def _toggle(v=var, repaint=_repaint):
                    active_now = {s for s, sv in sprinkler_subtype_vars.items() if sv.get()}
                    if v.get() and len(active_now) == 1:
                        return
                    v.set(not v.get())
                    repaint()
                    _refresh_sprinkler_text()

                cell.bind("<Button-1>", lambda e, t=_toggle: t())
                lbl.bind("<Button-1>", lambda e, t=_toggle: t())
                _repaint()
                spr_repaints[subtype] = _repaint

            self._sprinkler_repaints = spr_repaints

        if sprinkler_subtype_vars:  # only overwrite when this is the sprinkler tab
            self._sprinkler_subtype_vars = sprinkler_subtype_vars

        if key == "sprinkler":
            # Right panel — Control Valve Locations (plain frame, no inner scroll)
            spr_right = ttk.Frame(content, padding=(6, 6))
            spr_right.pack(side="right", fill="y", padx=(8, 0))
            spr_rinner = spr_right

            ttk.Label(spr_rinner, text="Sprinkler Details", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
            ttk.Label(spr_rinner, text="Control Valve Locations",
                      font=("", 8, "bold")).pack(anchor="w", pady=(0, 3))
            self.sprk_valve_locations = []
            spr_vlv_tree = ttk.Treeview(spr_rinner, columns=("loc",), show="headings", height=5)
            spr_vlv_tree.heading("loc", text="Location")
            spr_vlv_tree.column("loc", width=230)
            spr_vlv_tree.pack(fill="x", pady=(0, 4))
            self.sprk_valve_tree = spr_vlv_tree

            def _refresh_spr_vlv_tree():
                spr_vlv_tree.delete(*spr_vlv_tree.get_children())
                for i, v in enumerate(self.sprk_valve_locations):
                    spr_vlv_tree.insert("", "end", iid=str(i), values=(v,))

            spr_vlv_entry = ttk.Entry(spr_rinner, width=28)
            spr_vlv_entry.pack(fill="x", pady=(0, 4), ipady=3)
            spr_vlv_entry.bind("<Return>", lambda e: _add_spr_vlv())
            self.spr_vlv_entry = spr_vlv_entry

            def _add_spr_vlv():
                val = spr_vlv_entry.get().strip()
                if val:
                    self.sprk_valve_locations.append(val)
                    spr_vlv_entry.delete(0, "end")
                    _refresh_spr_vlv_tree()
                    if hasattr(self, "_sprinkler_refresh_text"):
                        self._sprinkler_refresh_text()

            def _remove_spr_vlv():
                sel = spr_vlv_tree.selection()
                if sel:
                    del self.sprk_valve_locations[int(sel[0])]
                    _refresh_spr_vlv_tree()
                    if hasattr(self, "_sprinkler_refresh_text"):
                        self._sprinkler_refresh_text()

            spr_vlv_btn_f = ttk.Frame(spr_rinner)
            spr_vlv_btn_f.pack(fill="x", pady=(0, 4))
            ttk.Button(spr_vlv_btn_f, text="+ Add",  command=_add_spr_vlv).pack(side="left", padx=(0, 4))
            ttk.Button(spr_vlv_btn_f, text="Remove", command=_remove_spr_vlv).pack(side="left")
            self._refresh_spr_vlv_tree = _refresh_spr_vlv_tree

        if key == "standpipe":
            # Right panel — Control Valve Locations (plain frame, no inner scroll)
            stnd_right = ttk.Frame(content, padding=(6, 6))
            stnd_right.pack(side="right", fill="y", padx=(8, 0))
            stnd_rinner = stnd_right

            ttk.Label(stnd_rinner, text="Standpipe Details", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
            ttk.Label(stnd_rinner, text="Control Valve Locations",
                      font=("", 8, "bold")).pack(anchor="w", pady=(0, 3))
            self.stnd_valve_locations = []
            stnd_vlv_tree = ttk.Treeview(stnd_rinner, columns=("loc",), show="headings", height=5)
            stnd_vlv_tree.heading("loc", text="Location")
            stnd_vlv_tree.column("loc", width=230)
            stnd_vlv_tree.pack(fill="x", pady=(0, 4))
            self.stnd_valve_tree = stnd_vlv_tree

            def _refresh_stnd_vlv_tree():
                stnd_vlv_tree.delete(*stnd_vlv_tree.get_children())
                for i, v in enumerate(self.stnd_valve_locations):
                    stnd_vlv_tree.insert("", "end", iid=str(i), values=(v,))

            stnd_vlv_entry = ttk.Entry(stnd_rinner, width=28)
            stnd_vlv_entry.pack(fill="x", pady=(0, 4), ipady=3)
            stnd_vlv_entry.bind("<Return>", lambda e: _add_stnd_vlv())
            self.stnd_vlv_entry = stnd_vlv_entry

            def _add_stnd_vlv():
                val = stnd_vlv_entry.get().strip()
                if val:
                    self.stnd_valve_locations.append(val)
                    stnd_vlv_entry.delete(0, "end")
                    _refresh_stnd_vlv_tree()
                    if hasattr(self, "_standpipe_refresh_text"):
                        self._standpipe_refresh_text()

            def _remove_stnd_vlv():
                sel = stnd_vlv_tree.selection()
                if sel:
                    del self.stnd_valve_locations[int(sel[0])]
                    _refresh_stnd_vlv_tree()
                    if hasattr(self, "_standpipe_refresh_text"):
                        self._standpipe_refresh_text()

            stnd_vlv_btn_f = ttk.Frame(stnd_rinner)
            stnd_vlv_btn_f.pack(fill="x", pady=(0, 4))
            ttk.Button(stnd_vlv_btn_f, text="+ Add",  command=_add_stnd_vlv).pack(side="left", padx=(0, 4))
            ttk.Button(stnd_vlv_btn_f, text="Remove", command=_remove_stnd_vlv).pack(side="left")
            self._refresh_stnd_vlv_tree = _refresh_stnd_vlv_tree

        desc_hdr = ttk.Frame(left)
        desc_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(desc_hdr, text="System Overview Description", font=("", 9, "bold")).pack(side="left")
        ttk.Label(desc_hdr, text="  (Section 1.3)", foreground="gray", font=("", 8)).pack(side="left")
        df = ttk.Frame(left)
        df.pack(fill="both", expand=True, pady=(0, 8))
        ds = ttk.Scrollbar(df, orient="vertical")
        desc_text = tk.Text(df, wrap="word", height=12, yscrollcommand=ds.set, undo=True, maxundo=50,
                            highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
        ds.configure(command=desc_text.yview)
        desc_text.pack(side="left", fill="both", expand=True)
        ds.pack(side="right", fill="y")
        attach_spellcheck(desc_text)
        if key == "sprinkler":
            _init_desc, _ = get_sprinkler_text({"Wet Pipe"})
            desc_text.insert("1.0", _init_desc)
        elif key == "pre_action":
            # Seed with the template text; live preview will fill placeholders
            desc_text.insert("1.0", SYSTEM_DEFAULTS.get("pre_action", {}).get("description", LOREM))
            # Fire the live preview after the tab is fully built
            self.root.after(50, lambda: self._update_preac_desc() if hasattr(self, "_update_preac_desc") else None)
        else:
            desc_text.insert("1.0", SYSTEM_DEFAULTS.get(key, {}).get("description", LOREM))

        integ_hdr = ttk.Frame(left)
        integ_hdr.pack(anchor="w", pady=(0, 3))
        ttk.Label(integ_hdr, text="System Integrations & Functional Objectives", font=("", 9, "bold")).pack(side="left")
        ttk.Label(integ_hdr, text="  (Section 1.3)", foreground="gray", font=("", 8)).pack(side="left")
        if_ = ttk.Frame(left)
        if_.pack(fill="both", expand=True)
        is_ = ttk.Scrollbar(if_, orient="vertical")
        int_text = tk.Text(if_, wrap="word", height=9, yscrollcommand=is_.set, undo=True, maxundo=50,
                           highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
        is_.configure(command=int_text.yview)
        int_text.pack(side="left", fill="both", expand=True)
        is_.pack(side="right", fill="y")
        attach_spellcheck(int_text)
        if key == "sprinkler":
            _, _init_int = get_sprinkler_text({"Wet Pipe"})
            int_text.insert("1.0", _init_int)
        else:
            int_text.insert("1.0", SYSTEM_DEFAULTS.get(key, {}).get("integrations", LOREM))

        if key == "fire_alarm":
            self.fa_int_text = int_text
            self._fa_desc_text_ref = desc_text
        if key == "pre_action":
            self._pre_action_int_text_ref = int_text  # for live {{preac_pan_or_fa}} update
        if key == "generator":
            self._gen_int_text_ref = int_text
            if hasattr(self, "_update_gen_desc"):
                self._update_gen_desc()
        if key == "elevator":
            self._elev_int_text_ref = int_text
            if hasattr(self, "_update_elev_preview"):
                self._update_elev_preview()

        # ── Standpipe live description refresh ────────────────────────────
        if key == "standpipe":
            def _refresh_standpipe_text():
                vlocs = getattr(self, "stnd_valve_locations", [])
                vlv_str = ("\n".join(f"\t\u2022  {v}" for v in vlocs)
                           if vlocs else "\t\u2022  {{stnd_vlv_locs}}")
                template = SYSTEM_DEFAULTS.get("standpipe", {}).get("description", LOREM)
                preview = template.replace("{{stnd_vlv_locs}}", vlv_str)
                desc_text.delete("1.0", "end")
                desc_text.insert("1.0", preview)
            self._standpipe_refresh_text = _refresh_standpipe_text
            _refresh_standpipe_text()

        # ── Water mist live description refresh ───────────────────────────
        if key == "water_mist":
            def _refresh_watermist_text():
                areas = getattr(self, "wm_protected_areas", [])
                if len(areas) == 1:
                    areas_str = areas[0]
                    verb = "is"
                elif len(areas) == 2:
                    areas_str = f"{areas[0]} and {areas[1]}"
                    verb = "are"
                elif len(areas) > 2:
                    areas_str = ", ".join(areas[:-1]) + f", and {areas[-1]}"
                    verb = "are"
                else:
                    areas_str = "{{watmist_protec_area}}"
                    verb = "is"
                template = SYSTEM_DEFAULTS.get("water_mist", {}).get("description", LOREM)
                preview = template.replace("{{watmist_protec_area}}", areas_str)
                preview = preview.replace("{{watmist_area_verb}}", verb)
                desc_text.delete("1.0", "end")
                desc_text.insert("1.0", preview)
            self._watermist_refresh_text = _refresh_watermist_text
            _refresh_watermist_text()
        if key == "fire_pump":
            def _update_fp_desc_preview(event=None):
                template = SYSTEM_DEFAULTS.get("fire_pump", {}).get("description", LOREM)
                preview = template.replace("{{fp_room}}", self.fp_room_entry.get() or "{{fp_room}}")
                preview = preview.replace("{{fp_level}}", self.fp_floor_entry.get() or "{{fp_level}}")
                desc_text.delete("1.0", "end"); desc_text.insert("1.0", preview)
            self.fp_room_entry.bind("<KeyRelease>", _update_fp_desc_preview)
            self.fp_floor_entry.bind("<KeyRelease>", _update_fp_desc_preview)

        # ── Generator served systems checklist + live preview ──────────────
        if key == "generator":
            NUM_TO_TEXT_GEN = {
                1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
                6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
                11: "Eleven", 12: "Twelve",
            }

            def _update_gen_desc(event=None):
                count = self.gen_count_var.get()
                count_txt    = NUM_TO_TEXT_GEN.get(count, str(count))
                generator_s  = "generator" if count == 1 else "generators"
                generator_v  = "is" if count == 1 else "are"
                gen_serve_s  = "serves" if count == 1 else "serve"
                gen_type     = self.gen_type_var.get().capitalize()
                gen_class    = self.gen_class_var.get()
                gen_room     = self.gen_room_entry.get().strip() or "{{gen_room}}"
                gen_floor    = self.gen_floor_entry.get().strip() or "{{gen_floor}}"

                served = [GEN_DISPLAY.get(lbl, lbl) for lbl, var in self.gen_served_vars.items() if var.get()]
                if served:
                    served_list = "\n".join(f"\t\u2022  {s}" for s in served)
                else:
                    served_list = "\t\u2022  "

                if gen_class == "emergency":
                    desc_template = SYSTEM_DEFAULTS.get("generator", {}).get("description_emergency", "")
                    int_template  = SYSTEM_DEFAULTS.get("generator", {}).get("integrations_emergency", "")
                else:
                    desc_template = SYSTEM_DEFAULTS.get("generator", {}).get("description_nonemergency", "")
                    int_template  = SYSTEM_DEFAULTS.get("generator", {}).get("integrations_nonemergency", "")

                preview = desc_template
                preview = preview.replace("{{gen_count_txt}}",  count_txt)
                preview = preview.replace("{{gen_count_num}}",  str(count))
                preview = preview.replace("{{gen_type}}",       gen_type)
                preview = preview.replace("{{generator_s}}",    generator_s)
                preview = preview.replace("{{generator_verb}}", generator_v)
                preview = preview.replace("{{gen_serve_s}}",    gen_serve_s)
                preview = preview.replace("{{gen_room}}",       gen_room)
                preview = preview.replace("{{gen_floor}}",      gen_floor)
                preview = preview.replace("{{gen_served_list}}", served_list)
                desc_text.delete("1.0", "end")
                desc_text.insert("1.0", preview)

                # Update integrations preview
                it = getattr(self, "_gen_int_text_ref", None)
                if it:
                    int_preview = int_template
                    int_preview = int_preview.replace("{{generator_s}}",    generator_s)
                    int_preview = int_preview.replace("{{generator_verb}}", generator_v)
                    it.delete("1.0", "end")
                    it.insert("1.0", int_preview)

            self._update_gen_desc = _update_gen_desc
            self.gen_count_var.trace_add("write", lambda *_: (_update_gen_desc(), self._rebuild_gen_served_matrix() if hasattr(self, "_gen_served_matrix_rows") else None))
            self.gen_type_var.trace_add("write", lambda *_: _update_gen_desc())
            self.gen_class_var.trace_add("write", lambda *_: (_update_gen_desc(), self._refresh_gen_served_tab()))
            self.gen_room_entry.bind("<KeyRelease>", _update_gen_desc)
            self.gen_floor_entry.bind("<KeyRelease>", _update_gen_desc)

            self._gen_served_checkbuttons = []  # refs kept for enable/disable

            def _refresh_gen_checklist():
                previously_checked = {lbl for lbl, v in self.gen_served_vars.items() if v.get()}
                for w in self.gen_check_inner.winfo_children():
                    w.destroy()
                self.gen_served_vars.clear()
                self._gen_served_checkbuttons.clear()
                selected = [v.get() for v in self.sys_selector_vars if v.get()]
                eligible = [s for s in selected if s not in ("Generator", "Sprinkler", "Standpipe")]
                is_emergency = self.gen_class_var.get() == "emergency"

                # ── Built-in system checkboxes ────────────────────────────
                for lbl in eligible:
                    var = tk.BooleanVar(value=(lbl in previously_checked))
                    self.gen_served_vars[lbl] = var
                    cb = ttk.Checkbutton(self.gen_check_inner, text=GEN_DISPLAY.get(lbl, lbl),
                                         variable=var, command=lambda: (_update_gen_desc(), self._refresh_gen_served_tab()))
                    cb.pack(anchor="w", pady=1)
                    self._gen_served_checkbuttons.append(cb)
                    if not is_emergency:
                        cb.state(["disabled"])

                # ── Custom system rows (checkbox + label + ✕) ─────────────
                for entry in list(self.gen_custom_served):
                    lbl = entry["label"]
                    var = entry["var"]
                    # Restore checked state across rebuilds
                    if lbl in previously_checked:
                        var.set(True)
                    self.gen_served_vars[lbl] = var
                    row_f = ttk.Frame(self.gen_check_inner)
                    row_f.pack(anchor="w", fill="x", pady=1)
                    cb = ttk.Checkbutton(row_f, text=lbl, variable=var,
                                         command=lambda: (_update_gen_desc(), self._refresh_gen_served_tab()))
                    cb.pack(side="left")
                    self._gen_served_checkbuttons.append(cb)
                    if not is_emergency:
                        cb.state(["disabled"])

                    def _make_remove(e=entry, rf=row_f):
                        def _remove():
                            lbl_r = e["label"]
                            self.gen_custom_served.remove(e)
                            if lbl_r in self.gen_served_vars:
                                del self.gen_served_vars[lbl_r]
                            rf.destroy()
                            _update_gen_desc()
                            self._refresh_gen_served_tab()
                        return _remove

                    rm = ttk.Button(row_f, text="✕", width=2,
                                    command=_make_remove())
                    rm.pack(side="left", padx=(4, 0))
                    if not is_emergency:
                        rm.state(["disabled"])
                    self._gen_served_checkbuttons.append(rm)

                _update_gen_desc()
                self._refresh_gen_served_tab()

            def _update_served_state(*_):
                """Gray out served-system checkboxes and custom entry when non-emergency."""
                is_emergency = self.gen_class_var.get() == "emergency"
                for cb in self._gen_served_checkbuttons:
                    cb.state(["!disabled"] if is_emergency else ["disabled"])
                state = ["!disabled"] if is_emergency else ["disabled"]
                entry = getattr(self, "_gen_custom_entry", None)
                btn   = getattr(self, "_gen_custom_btn", None)
                if entry:
                    entry.state(state)
                if btn:
                    btn.state(state)
                self._refresh_gen_served_tab()

            self.gen_class_var.trace_add("write", _update_served_state)
            self._refresh_gen_checklist = _refresh_gen_checklist
            _refresh_gen_checklist()
            # Hook: rebuild served tab matrix whenever checklist changes
            self._gen_served_tab_refresh_hook = None  # set after tab is built

        # ── Integrations Matrix Section ────────────────────────────────────
        matrix_entries = {}

        def _insert_bullets(text_widget, content):
            """Insert content with • bullets replacing leading - characters."""
            lines = content.strip().split("\n")
            display_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith("- "):
                    line = "• " + line[2:]
                elif line.startswith("-"):
                    line = "• " + line[1:].strip()
                display_lines.append(line)
            text_widget.insert("1.0", "\n".join(display_lines))
        if key != "fire_alarm":
            ttk.Separator(content_wrap, orient="horizontal").pack(fill="x", pady=(12, 4))
            matrix_hdr = ttk.Frame(content_wrap)
            matrix_hdr.pack(anchor="w", pady=(0, 2))
            ttk.Label(matrix_hdr, text="Integrations Matrix", font=("", 9, "bold")).pack(side="left")
            ttk.Label(matrix_hdr, text="  (Sections 2 & 3)", foreground="gray", font=("", 8)).pack(side="left")
            ttk.Label(content_wrap, text=f"Fire Alarm / {label}", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))

            # Column headers
            # Container for dynamic rows (no separate header — labels are inside each row)
            rows_frame = ttk.Frame(content_wrap)
            rows_frame.pack(fill="x")
            matrix_rows = []   # list of dicts with Text widgets

            def _reorder_matrix():
                for r in matrix_rows:
                    sep_w = r.get("_sep")
                    rf    = r.get("_tp_frame")
                    if sep_w and hasattr(sep_w, "winfo_exists") and sep_w.winfo_exists():
                        sep_w.pack_forget()
                    if rf and rf.winfo_exists():
                        rf.pack_forget()
                for i, r in enumerate(matrix_rows):
                    sep_w = r.get("_sep")
                    rf    = r.get("_tp_frame")
                    if sep_w and hasattr(sep_w, "winfo_exists") and sep_w.winfo_exists():
                        if i == 0:
                            sep_w.pack_forget()
                        else:
                            sep_w.pack(fill="x", pady=(16, 8))
                    if rf and rf.winfo_exists():
                        rf.pack(fill="x", pady=(0, 6))

            def _add_matrix_row(integ="", normal="", fire="", tp_normal="", tp_fire=""):
                # Separator only between rows (not before the first)
                sep = ttk.Separator(rows_frame, orient="horizontal")
                sep.pack(fill="x", pady=(16, 8))
                if not matrix_rows:
                    sep.pack_forget()

                # Single grid frame: col0=integration(small) | col1=normal | col2=fire
                row_wrap = tk.Frame(rows_frame, bd=2, relief="flat", highlightthickness=0)
                row_wrap.pack(fill="x", pady=(0, 6))
                row_f = ttk.Frame(row_wrap)
                row_f.pack(fill="x")
                row_f.columnconfigure(0, weight=0, minsize=160)
                row_f.columnconfigure(1, weight=1, uniform="main_col")
                row_f.columnconfigure(2, weight=1, uniform="main_col")
                widgets = {}

                def _remove(rf=row_f, r=widgets):
                    if r in matrix_rows:
                        matrix_rows.remove(r)
                    rf.destroy()
                    if "_sep" in r and r["_sep"] is not None:
                        s = r["_sep"]
                        if hasattr(s, "winfo_exists") and s.winfo_exists():
                            s.destroy()
                    self.root.after(0, _refresh_scroll)

                widgets["_sep"] = sep if matrix_rows else None

                # Col 0 — Integration name + drag handle + ✕
                integ_outer = ttk.Frame(row_f)
                integ_outer.grid(row=0, column=0, rowspan=5, sticky="nwe", padx=(0, 6))

                drag_hdr = ttk.Frame(integ_outer)
                drag_hdr.pack(fill="x", pady=(0, 2))
                drag_lbl = tk.Label(drag_hdr, text="≡", foreground="#aaaaaa",
                                    cursor="sb_v_double_arrow", font=("", 13))
                drag_lbl.pack(side="left")

                _drag_state = {"start_y": None, "src_idx": None}

                def _drag_start(event, w=widgets):
                    _drag_state["start_y"] = event.y_root
                    _drag_state["src_idx"] = matrix_rows.index(w)
                    drag_lbl.configure(foreground="#4a90d9")
                    row_wrap.configure(relief="solid", bd=2,
                                       highlightbackground="#4a90d9",
                                       highlightthickness=2, bg="#dce8ff")

                def _drag_motion(event, w=widgets):
                    if _drag_state["src_idx"] is None:
                        return
                    dy = event.y_root - _drag_state["start_y"]
                    if abs(dy) < 60:
                        return
                    step = 1 if dy > 0 else -1
                    src = _drag_state["src_idx"]
                    dst = max(0, min(len(matrix_rows) - 1, src + step))
                    if dst != src:
                        matrix_rows.insert(dst, matrix_rows.pop(src))
                        _drag_state["src_idx"] = dst
                        _drag_state["start_y"] = event.y_root
                        _reorder_matrix()

                def _drag_end(event):
                    _drag_state["start_y"] = None
                    _drag_state["src_idx"] = None
                    drag_lbl.configure(foreground="#aaaaaa")
                    row_wrap.configure(relief="flat", bd=0,
                                       highlightthickness=0, bg="")

                drag_lbl.bind("<ButtonPress-1>",   _drag_start)
                drag_lbl.bind("<B1-Motion>",        _drag_motion)
                drag_lbl.bind("<ButtonRelease-1>",  _drag_end)

                ttk.Label(integ_outer, text="Integration", font=("", 8), foreground="gray").pack(anchor="w")
                integ_t = tk.Text(integ_outer, wrap="none", height=1, width=32, relief="flat", bd=1, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                integ_t.insert("1.0", integ)
                integ_t.pack(fill="x")
                ttk.Button(integ_outer, text="Remove Integration", command=_remove).pack(anchor="w", pady=(4, 0))
                widgets["integration"] = integ_t

                # Col 1 — Normal Mode description + TP
                ttk.Label(row_f, text="Normal Mode", font=("", 8), foreground="gray").grid(row=0, column=1, sticky="w", padx=(0, 4))
                normal_t = tk.Text(row_f, wrap="word", height=3, relief="flat", bd=1, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                normal_t.insert("1.0", normal)
                normal_t.grid(row=1, column=1, sticky="new", padx=(0, 4))
                attach_spellcheck(normal_t)
                enable_text_autoresize(normal_t, min_height=3, max_height=12)
                ttk.Label(row_f, text="Test Procedure — Normal Mode:", font=("", 8), foreground="gray").grid(row=2, column=1, sticky="w", padx=(0, 4), pady=(6, 0))
                tp_normal_t = tk.Text(row_f, wrap="word", height=5, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                _insert_bullets(tp_normal_t, tp_normal)
                tp_normal_t.grid(row=3, column=1, sticky="new", padx=(0, 4))
                attach_spellcheck(tp_normal_t)
                enable_text_autoresize(tp_normal_t, min_height=5, max_height=20)
                ttk.Button(row_f, text="+ New Bullet",
                           command=lambda t=tp_normal_t: (t.insert(tk.INSERT, "\n• ") if t.get("1.0", "end-1c").strip() else t.insert("1.0", "• "))
                           ).grid(row=4, column=1, sticky="w", padx=(0, 4), pady=(2, 0))
                widgets["normal_mode"] = normal_t

                # Col 2 — Fire Mode description + TP
                ttk.Label(row_f, text="Fire Mode", font=("", 8), foreground="gray").grid(row=0, column=2, sticky="w")
                fire_t = tk.Text(row_f, wrap="word", height=3, relief="flat", bd=1, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                fire_t.insert("1.0", fire)
                fire_t.grid(row=1, column=2, sticky="new")
                attach_spellcheck(fire_t)
                enable_text_autoresize(fire_t, min_height=3, max_height=12)
                ttk.Label(row_f, text="Test Procedure — Fire Mode:", font=("", 8), foreground="gray").grid(row=2, column=2, sticky="w", pady=(6, 0))
                tp_fire_t = tk.Text(row_f, wrap="word", height=5, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                _insert_bullets(tp_fire_t, tp_fire)
                tp_fire_t.grid(row=3, column=2, sticky="new")
                attach_spellcheck(tp_fire_t)
                enable_text_autoresize(tp_fire_t, min_height=5, max_height=20)
                ttk.Button(row_f, text="+ New Bullet",
                           command=lambda t=tp_fire_t: (t.insert(tk.INSERT, "\n• ") if t.get("1.0", "end-1c").strip() else t.insert("1.0", "• "))
                           ).grid(row=4, column=2, sticky="w", pady=(2, 0))
                widgets["fire_mode"] = fire_t

                widgets["tp_normal"]  = tp_normal_t
                widgets["tp_fire"]    = tp_fire_t
                widgets["_tp_frame"]  = row_wrap
                widgets["_row_wrap"]  = row_wrap

                matrix_rows.append(widgets)
                self.root.after(0, _refresh_scroll)
                return widgets

            # Add default rows from MATRIX_DEFAULTS + TP_DEFAULTS
            default_rows = MATRIX_DEFAULTS.get(key, [])
            tp_defaults   = TP_DEFAULTS.get(key, [])
            if default_rows:
                for i, row in enumerate(default_rows):
                    tp = tp_defaults[i] if i < len(tp_defaults) else ("", "")
                    _add_matrix_row(*row, tp_normal=tp[0], tp_fire=tp[1])
            else:
                _add_matrix_row()

            ttk.Button(content_wrap, text="+ Add Integration",
                       command=_add_matrix_row).pack(anchor="w", pady=(4, 0))

            matrix_entries["_rows"] = matrix_rows
            matrix_entries["_add_row"] = _add_matrix_row

        elif key == "fire_alarm":
            ttk.Separator(content_wrap, orient="horizontal").pack(fill="x", pady=(12, 4))
            fa_matrix_hdr = ttk.Frame(content_wrap)
            fa_matrix_hdr.pack(anchor="w", pady=(0, 6))
            ttk.Label(fa_matrix_hdr, text="Integrations Matrix", font=("", 9, "bold")).pack(side="left")
            ttk.Label(fa_matrix_hdr, text="  (Sections 2 & 3)", foreground="gray", font=("", 8)).pack(side="left")
            ttk.Label(content_wrap, text="Fire Alarm / Monitoring Station", font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))

            mon_rows_frame = ttk.Frame(content_wrap)
            mon_rows_frame.pack(fill="x", pady=(0, 4))
            mon_rows = []

            def _reorder_mon():
                for r in mon_rows:
                    sep_w = r.get("_sep")
                    rf    = r.get("_tp_frame")
                    if sep_w and hasattr(sep_w, "winfo_exists") and sep_w.winfo_exists():
                        sep_w.pack_forget()
                    if rf and rf.winfo_exists():
                        rf.pack_forget()
                for i, r in enumerate(mon_rows):
                    sep_w = r.get("_sep")
                    rf    = r.get("_tp_frame")
                    if sep_w and hasattr(sep_w, "winfo_exists") and sep_w.winfo_exists():
                        if i == 0:
                            sep_w.pack_forget()
                        else:
                            sep_w.pack(fill="x", pady=(16, 8))
                    if rf and rf.winfo_exists():
                        rf.pack(fill="x", pady=(0, 6))

            def _add_mon_row(integ="", normal="", fire="", tp_normal="", tp_fire=""):
                # Separator only between rows (not before the first)
                sep = ttk.Separator(mon_rows_frame, orient="horizontal")
                sep.pack(fill="x", pady=(16, 8))
                if not mon_rows:
                    sep.pack_forget()

                # Single grid frame: col0=integration(small) | col1=normal | col2=fire
                row_wrap = tk.Frame(mon_rows_frame, bd=2, relief="flat", highlightthickness=0)
                row_wrap.pack(fill="x", pady=(0, 6))
                row_f = ttk.Frame(row_wrap)
                row_f.pack(fill="x")
                row_f.columnconfigure(0, weight=0, minsize=160)
                row_f.columnconfigure(1, weight=1, uniform="main_col")
                row_f.columnconfigure(2, weight=1, uniform="main_col")
                widgets = {}

                def _remove(rf=row_f, r=widgets, rw=row_wrap):
                    if r in mon_rows:
                        mon_rows.remove(r)
                    rw.destroy()
                    if "_sep" in r and r["_sep"] is not None:
                        s = r["_sep"]
                        if hasattr(s, "winfo_exists") and s.winfo_exists():
                            s.destroy()

                widgets["_sep"] = sep if mon_rows else None

                # Col 0 — Integration name + drag handle + ✕
                integ_outer = ttk.Frame(row_f)
                integ_outer.grid(row=0, column=0, rowspan=5, sticky="nwe", padx=(0, 6))

                drag_hdr = ttk.Frame(integ_outer)
                drag_hdr.pack(fill="x", pady=(0, 2))
                drag_lbl = tk.Label(drag_hdr, text="≡", foreground="#aaaaaa",
                                    cursor="fleur", font=("", 12))
                drag_lbl.pack(side="left")

                _drag_state = {"start_y": None, "src_idx": None}

                def _drag_start(event, w=widgets):
                    _drag_state["start_y"] = event.y_root
                    _drag_state["src_idx"] = mon_rows.index(w)
                    drag_lbl.configure(foreground="#4a90d9")
                    row_wrap.configure(relief="solid", bd=2,
                                       highlightbackground="#4a90d9",
                                       highlightthickness=2, bg="#dce8ff")

                def _drag_motion(event, w=widgets):
                    if _drag_state["src_idx"] is None:
                        return
                    dy = event.y_root - _drag_state["start_y"]
                    if abs(dy) < 20:
                        return
                    src = _drag_state["src_idx"]
                    dst = src - 1 if dy < 0 else src + 1
                    if 0 <= dst < len(mon_rows):
                        mon_rows[src], mon_rows[dst] = mon_rows[dst], mon_rows[src]
                        _drag_state["src_idx"] = dst
                        _drag_state["start_y"] = event.y_root
                        _reorder_mon()

                def _drag_end(event):
                    _drag_state["start_y"] = None
                    _drag_state["src_idx"] = None
                    drag_lbl.configure(foreground="#aaaaaa")
                    row_wrap.configure(relief="flat", bd=0,
                                       highlightthickness=0, bg="")

                drag_lbl.bind("<ButtonPress-1>",   _drag_start)
                drag_lbl.bind("<B1-Motion>",        _drag_motion)
                drag_lbl.bind("<ButtonRelease-1>",  _drag_end)

                ttk.Label(integ_outer, text="Integration", font=("", 8), foreground="gray").pack(anchor="w")
                integ_t = tk.Text(integ_outer, wrap="none", height=1, width=32, relief="flat", bd=1, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                integ_t.insert("1.0", integ)
                integ_t.pack(fill="x")
                ttk.Button(integ_outer, text="Remove Integration", command=_remove).pack(anchor="w", pady=(4, 0))
                widgets["integration"] = integ_t

                # Col 1 — Normal Mode description + TP
                ttk.Label(row_f, text="Normal Mode", font=("", 8), foreground="gray").grid(row=0, column=1, sticky="w", padx=(0, 4))
                normal_t = tk.Text(row_f, wrap="word", height=3, relief="flat", bd=1, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                normal_t.insert("1.0", normal)
                normal_t.grid(row=1, column=1, sticky="new", padx=(0, 4))
                attach_spellcheck(normal_t)
                enable_text_autoresize(normal_t, min_height=3, max_height=12)
                ttk.Label(row_f, text="Test Procedure — Normal Mode:", font=("", 8), foreground="gray").grid(row=2, column=1, sticky="w", padx=(0, 4), pady=(6, 0))
                tp_normal_t = tk.Text(row_f, wrap="word", height=5, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                _insert_bullets(tp_normal_t, tp_normal)
                tp_normal_t.grid(row=3, column=1, sticky="new", padx=(0, 4))
                attach_spellcheck(tp_normal_t)
                enable_text_autoresize(tp_normal_t, min_height=5, max_height=20)
                ttk.Button(row_f, text="+ New Bullet",
                           command=lambda t=tp_normal_t: (t.insert(tk.INSERT, "\n• ") if t.get("1.0", "end-1c").strip() else t.insert("1.0", "• "))
                           ).grid(row=4, column=1, sticky="w", padx=(0, 4), pady=(2, 0))
                widgets["normal_mode"] = normal_t

                # Col 2 — Fire Mode description + TP
                ttk.Label(row_f, text="Fire Mode", font=("", 8), foreground="gray").grid(row=0, column=2, sticky="w")
                fire_t = tk.Text(row_f, wrap="word", height=3, relief="flat", bd=1, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                fire_t.insert("1.0", fire)
                fire_t.grid(row=1, column=2, sticky="new")
                attach_spellcheck(fire_t)
                enable_text_autoresize(fire_t, min_height=3, max_height=12)
                ttk.Label(row_f, text="Test Procedure — Fire Mode:", font=("", 8), foreground="gray").grid(row=2, column=2, sticky="w", pady=(6, 0))
                tp_fire_t = tk.Text(row_f, wrap="word", height=5, undo=True, maxundo=50, highlightthickness=1, highlightbackground="#aaaaaa", highlightcolor="#0078d4")
                _insert_bullets(tp_fire_t, tp_fire)
                tp_fire_t.grid(row=3, column=2, sticky="new")
                attach_spellcheck(tp_fire_t)
                enable_text_autoresize(tp_fire_t, min_height=5, max_height=20)
                ttk.Button(row_f, text="+ New Bullet",
                           command=lambda t=tp_fire_t: (t.insert(tk.INSERT, "\n• ") if t.get("1.0", "end-1c").strip() else t.insert("1.0", "• "))
                           ).grid(row=4, column=2, sticky="w", pady=(2, 0))
                widgets["fire_mode"] = fire_t

                widgets["tp_normal"]  = tp_normal_t
                widgets["tp_fire"]    = tp_fire_t
                widgets["_tp_frame"]  = row_wrap
                widgets["_row_wrap"]  = row_wrap

                mon_rows.append(widgets)
                return widgets

            mon_tp_defaults = TP_DEFAULTS.get("fire_alarm_monitoring", [])
            for i, row in enumerate(MONITORING_MATRIX_DEFAULTS):
                tp = mon_tp_defaults[i] if i < len(mon_tp_defaults) else ("", "")
                _add_mon_row(*row, tp_normal=tp[0], tp_fire=tp[1])

            ttk.Button(content_wrap, text="+ Add Integration",
                       command=_add_mon_row).pack(anchor="w", pady=(4, 0))

            matrix_entries["_mon"] = mon_rows
            matrix_entries["_add_mon_row"] = _add_mon_row
            matrix_entries["_reorder_mon"] = _reorder_mon

        # ── Elevator Actions section (between matrix and Appendix B) ─────────
        elev_actions_data = {}
        if key == "elevator":
            elev_actions_data = self._build_elevator_actions_section(content_wrap, _refresh_scroll)

        # ── Appendix B section ────────────────────────────────────────────
        appb_data = self._build_appendix_b_section(content_wrap, key, label, matrix_entries, _refresh_scroll)

        # ── sys_ui registration ────────────────────────────────────────────
        self.sys_ui[key] = {
            "present":       present_var,
            "desc_text":     desc_text,
            "int_text":      int_text,
            "matrix":        matrix_entries,
            "appb":          appb_data,
            "elev_actions":  elev_actions_data,
        }

        # Patch FA panel to use the real desc_text now that it exists
        if key == "fire_alarm" and hasattr(self, "_fa_update_desc"):
            pass  # will be wired after panel build below

        # ── Generator: update Appendix B fire desc when gen_type changes ──
        if key == "generator":
            _GEN_FIRE_TEMPLATE = (
                "Operate device (run generator, simulate failure, and close {{gen_fuel}} supply) "
                "and confirm operation and fire alarm annunciation."
            )
            def _update_gen_appb_fire(*_, _entry=appb_data.get("_fire_desc")):
                if _entry is None:
                    return
                fuel = "natural gas" if self.gen_type_var.get() == "natural gas" else "diesel fuel"
                resolved = _GEN_FIRE_TEMPLATE.replace("{{gen_fuel}}", fuel)
                _entry.delete(0, "end")
                _entry.insert(0, resolved)
            self.gen_type_var.trace_add("write", _update_gen_appb_fire)
            # Fire immediately so the entry shows the resolved value on load
            self.root.after(50, _update_gen_appb_fire)


    def _build_appendix_b_section(self, content_wrap, key, label, matrix_entries, _refresh_scroll=None):
        """
        Build the Appendix B test-result sub-section at the bottom of a system tab.
        Returns a dict: {"_rows": list_of_row_dicts, "_add_row": callable}
        Each row dict holds: {"integration": StringVar, "normal": StringVar, "fire": StringVar, "notes": Entry, "_frame": Frame}
        Normal/fire values are one of: "PASS", "FAIL", "NT"
        """
        ttk.Separator(content_wrap, orient="horizontal").pack(fill="x", pady=(16, 6))
        hdr = ttk.Frame(content_wrap)
        hdr.pack(fill="x", pady=(0, 4))
        ttk.Label(hdr, text="Appendix B — Test Results", font=("", 9, "bold")).pack(side="left")
        ttk.Label(hdr, text="  Record pass/fail for each integration test",
                  foreground="gray", font=("", 8)).pack(side="left")

        # Normal / Fire Mode description fields (full width, one line each)
        desc_frame = ttk.Frame(content_wrap)
        desc_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(desc_frame, text="Normal Mode:", foreground="gray",
                  font=("", 8)).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
        normal_desc_e = ttk.Entry(desc_frame)
        normal_desc_e.grid(row=0, column=1, sticky="we", pady=2, ipady=2)
        ttk.Label(desc_frame, text="Fire Mode:", foreground="gray",
                  font=("", 8)).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
        fire_desc_e = ttk.Entry(desc_frame)
        fire_desc_e.grid(row=1, column=1, sticky="we", pady=2, ipady=2)
        desc_frame.columnconfigure(1, weight=1)

        # All rows share ONE grid frame so columns truly align.
        # Both SW and non-SW now use the same stacked Normal/Fire layout:
        # 0=No, 1=Integration, 2=SW(sw only), 3=Normal+Fire stacked, 4=Notes, 5=Remove
        show_sw = key in ("sprinkler", "standpipe", "pre_action")
        COL_DH   = 0   # drag handle
        COL_NO   = 1
        COL_INTG = 2
        COL_SW   = 3   # only used when show_sw
        COL_NM   = 4   # stacked Normal+Fire frame (all systems)
        COL_NT   = 5
        COL_RM   = 6

        # Header frame — separate from rows_frame so column widths match row_wrap inner grids.
        # Column minsizes here must exactly mirror row_f's below (incl. COL_INTG/COL_NT/COL_RM)
        # so that fixed-column totals match and weighted columns end up the same width,
        # keeping this header aligned with the row content beneath it.
        hdr_frame = ttk.Frame(content_wrap)
        hdr_frame.pack(fill="x")
        hdr_frame.columnconfigure(COL_DH,   weight=0, minsize=36)
        hdr_frame.columnconfigure(COL_NO,   weight=0, minsize=30)
        hdr_frame.columnconfigure(COL_INTG, weight=2, minsize=140)
        if show_sw:
            hdr_frame.columnconfigure(COL_SW, weight=0, minsize=155)
        hdr_frame.columnconfigure(COL_NM, weight=0, minsize=210)
        hdr_frame.columnconfigure(COL_NT, weight=3, minsize=60)
        hdr_frame.columnconfigure(COL_RM, weight=0, minsize=40)

        ttk.Label(hdr_frame, text="No.",  font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_NO, sticky="w", padx=(4, 2), pady=(0, 2))
        ttk.Label(hdr_frame, text="System Integration", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_INTG, sticky="w", padx=(0, 6), pady=(0, 2))
        if show_sw:
            ttk.Label(hdr_frame, text="Type / No.", font=("", 8, "bold"), foreground="gray").grid(
                row=0, column=COL_SW, sticky="w", padx=(0, 6), pady=(0, 2))
        ttk.Label(hdr_frame, text="Normal / Fire Mode", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_NM, sticky="w", padx=(0, 6), pady=(0, 2))
        ttk.Label(hdr_frame, text="Notes", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_NT, sticky="w", padx=(0, 4), pady=(0, 2))

        rows_frame = tk.Frame(content_wrap)
        rows_frame.pack(fill="x")

        appb_rows = []

        def _repack_all_rows():
            """Re-pack every row_wrap in order after a reorder."""
            for i, r in enumerate(appb_rows):
                rw = r.get("_row_wrap")
                if rw and rw.winfo_exists():
                    rw.pack_forget()
            for i, r in enumerate(appb_rows):
                rw = r.get("_row_wrap")
                if rw and rw.winfo_exists():
                    rw.pack(fill="x", pady=(0, 4))
                no_lbl = r.get("_no_lbl")
                if no_lbl and no_lbl.winfo_exists():
                    no_lbl.configure(text=str(i + 1))

        def _add_appb_row(integration="", normal="", fire="", notes="", sw_type="", sw_no=""):
            idx = len(appb_rows) + 1

            widgets = {}

            # row_wrap — the border frame, identical to matrix row_wrap.
            # bd=0 to start (matches the "inactive" state in _highlight_appb_row below)
            # so row_f's width matches hdr_frame's width exactly.
            row_wrap = tk.Frame(rows_frame, bd=0, relief="flat", highlightthickness=0)
            row_wrap.pack(fill="x", pady=(0, 4))
            row_f = ttk.Frame(row_wrap)
            row_f.pack(fill="x")
            row_f.columnconfigure(COL_DH,   weight=0, minsize=36)
            row_f.columnconfigure(COL_NO,   weight=0, minsize=30)
            row_f.columnconfigure(COL_INTG, weight=2, minsize=140)
            if show_sw:
                row_f.columnconfigure(COL_SW, weight=0, minsize=155)
            row_f.columnconfigure(COL_NM, weight=0, minsize=210)
            row_f.columnconfigure(COL_NT, weight=3, minsize=60)
            row_f.columnconfigure(COL_RM, weight=0, minsize=40)
            widgets["_row_wrap"] = row_wrap
            widgets["_tp_frame"] = row_wrap  # for destroy compatibility with clear_all

            _drag_state = {"start_y": None, "src_idx": None}

            def _highlight_appb_row(w, active):
                rw = w.get("_row_wrap")
                if rw and rw.winfo_exists():
                    if active:
                        rw.configure(relief="solid", bd=2,
                                     highlightbackground="#4a90d9",
                                     highlightthickness=2, bg="#dce8ff")
                    else:
                        rw.configure(relief="flat", bd=0,
                                     highlightthickness=0,
                                     bg="#1e1e1e" if getattr(self, "_dark_mode", False) else "")
                dh = w.get("_drag_handle")
                if dh and dh.winfo_exists():
                    dh.configure(foreground="#4a90d9" if active else "#aaaaaa")

            # Drag handle
            drag_lbl = tk.Label(row_f, text="≡", foreground="#aaaaaa",
                                cursor="sb_v_double_arrow", font=("", 11))
            drag_lbl.grid(row=0, column=COL_DH, sticky="w", padx=(2, 0), pady=3)
            widgets["_drag_handle"] = drag_lbl

            def _drag_start(event, w=widgets):
                _drag_state["start_y"] = event.y_root
                _drag_state["src_idx"] = appb_rows.index(w)
                _highlight_appb_row(w, True)

            def _drag_motion(event, w=widgets):
                if _drag_state["src_idx"] is None:
                    return
                dy = event.y_root - _drag_state["start_y"]
                if abs(dy) < 40:
                    return
                step = 1 if dy > 0 else -1
                src = _drag_state["src_idx"]
                dst = max(0, min(len(appb_rows) - 1, src + step))
                if dst != src:
                    appb_rows.insert(dst, appb_rows.pop(src))
                    _drag_state["src_idx"] = dst
                    _drag_state["start_y"] = event.y_root
                    _repack_all_rows()

            def _drag_end(event):
                src_w = widgets
                _drag_state["start_y"] = None
                _drag_state["src_idx"] = None
                _highlight_appb_row(src_w, False)

            drag_lbl.bind("<ButtonPress-1>",   _drag_start)
            drag_lbl.bind("<B1-Motion>",        _drag_motion)
            drag_lbl.bind("<ButtonRelease-1>",  _drag_end)

            # No. label
            no_lbl = ttk.Label(row_f, text=str(idx), foreground="gray")
            no_lbl.grid(row=0, column=COL_NO, sticky="w", padx=(4, 2), pady=3)
            widgets["_no_lbl"] = no_lbl

            # Integration name — 2-line Text widget
            # width=1 so the widget's natural size doesn't drive COL_INTG's width
            # (it expands to fill the column via sticky="nswe"); keeps this column's
            # width consistent with hdr_frame's, which only has minsize/weight to go on.
            integ_t = tk.Text(row_f, wrap="word", height=2, width=1, relief="flat",
                              bd=1, highlightthickness=1,
                              highlightbackground="#aaaaaa", highlightcolor="#0078d4")
            integ_t.insert("1.0", integration)
            integ_t.grid(row=0, column=COL_INTG, sticky="nswe", padx=(0, 6), pady=3)
            attach_spellcheck(integ_t)
            widgets["integration"] = integ_t

            # Switch/Valve Type + Number (sprinkler & standpipe only)
            sw_type_var = tk.StringVar(value=sw_type if sw_type else "SV")
            sw_no_var   = tk.StringVar(value=sw_no)
            if show_sw:
                sw_f = ttk.Frame(row_f)
                sw_f.grid(row=0, column=COL_SW, sticky="nw", padx=(0, 6), pady=3)
                widgets["_sw_f"] = sw_f
                ttk.Label(sw_f, text="Type:", foreground="gray", font=("", 8)).grid(row=0, column=0, sticky="w")
                SW_OPTIONS = ["SV", "FS", "LP"]
                sw_cb = ttk.Combobox(sw_f, textvariable=sw_type_var, values=SW_OPTIONS, width=7)
                sw_cb.grid(row=0, column=1, sticky="w", padx=(2, 0))
                ttk.Label(sw_f, text="No.:", foreground="gray", font=("", 8)).grid(row=1, column=0, sticky="w", pady=(4,0))
                sw_no_e = ttk.Entry(sw_f, textvariable=sw_no_var, width=10)
                sw_no_e.grid(row=1, column=1, sticky="w", padx=(2, 0), pady=(4,0))
            widgets["sw_type"] = sw_type_var
            widgets["sw_no"]   = sw_no_var

            def _make_toggle_group(frame, var, options):
                btns = {}
                colors = {"PASS": "#2e7d32", "FAIL": "#c62828", "NT": "#555555"}
                def _repaint_all():
                    for v, b in btns.items():
                        active = var.get() == v
                        b.configure(
                            bg=colors.get(v, "#555555") if active else "#d0d0d0",
                            fg="white" if active else "#333333",
                            relief="flat"
                        )
                def _click(v):
                    var.set("" if var.get() == v else v)
                    _repaint_all()
                for v, txt in options:
                    b = tk.Button(frame, text=txt, padx=7, pady=2, relief="flat", bd=0,
                                  cursor="hand2", font=("", 8),
                                  command=lambda v=v: _click(v))
                    b.pack(side="left", padx=(0, 3))
                    btns[v] = b
                _repaint_all()
                return btns, _repaint_all

            nm_var = tk.StringVar(value=normal)
            fm_var = tk.StringVar(value=fire)

            # Stacked Normal / Fire frame (same layout for both SW and non-SW)
            nf_outer = ttk.Frame(row_f)
            nf_outer.grid(row=0, column=COL_NM, columnspan=1, sticky="nw", padx=(0, 6), pady=3)
            widgets["_nf_outer"] = nf_outer
            nm_f = ttk.Frame(nf_outer)
            nm_f.pack(fill="x", pady=(0, 4))
            ttk.Label(nm_f, text="Normal:", foreground="gray", font=("", 8), width=7).pack(side="left")
            nm_btns, nm_repaint = _make_toggle_group(nm_f, nm_var,
                [("PASS", "PASS"), ("FAIL", "FAIL"), ("NT", "NT")])
            fm_f = ttk.Frame(nf_outer)
            fm_f.pack(fill="x")
            ttk.Label(fm_f, text="Fire:", foreground="gray", font=("", 8), width=7).pack(side="left")
            fm_btns, fm_repaint = _make_toggle_group(fm_f, fm_var,
                [("PASS", "PASS"), ("FAIL", "FAIL"), ("NT", "NT")])

            widgets["normal"] = nm_var
            widgets["_nm_repaint"] = nm_repaint
            widgets["fire"] = fm_var
            widgets["_fm_repaint"] = fm_repaint

            # Notes entry — width=1 so it doesn't drive COL_NT's natural width (see integ_t above)
            notes_e = ttk.Entry(row_f, width=1)
            notes_e.insert(0, notes)
            notes_e.grid(row=0, column=COL_NT, sticky="we", padx=(0, 4), pady=3, ipady=2)
            widgets["notes"] = notes_e

            # Remove button
            def _remove(r=widgets):
                rw = r.get("_row_wrap")
                if rw and rw.winfo_exists():
                    rw.destroy()
                if r in appb_rows:
                    appb_rows.remove(r)
                _repack_all_rows()
                if _refresh_scroll:
                    self.root.after(0, _refresh_scroll)

            rm_btn = ttk.Button(row_f, text="✕", width=2, command=_remove)
            rm_btn.grid(row=0, column=COL_RM, padx=(0, 4), pady=3)
            widgets["_rm_btn"] = rm_btn

            appb_rows.append(widgets)
            _repack_all_rows()
            if _refresh_scroll:
                self.root.after(0, _refresh_scroll)
            return widgets

        # Seed normal/fire desc entries with defaults
        nd_default, fd_default = APPB_DESC_DEFAULTS.get(key, ("", ""))
        if nd_default:
            normal_desc_e.insert(0, nd_default)
        if fd_default:
            fire_desc_e.insert(0, fd_default)

        # Seed default Appendix B rows from APPB_DEFAULTS
        if key == "elevator":
            # Elevator rows are numbered per elevator count — seeded after tab build
            self.root.after(50, self._refresh_elevator_appb_rows)
        else:
            for name in APPB_DEFAULTS.get(key, []):
                sw_type = APPB_SW_TYPE_DEFAULTS.get(name, "") if show_sw else ""
                _add_appb_row(integration=name, normal="", fire="", sw_type=sw_type)

        btn_f = ttk.Frame(content_wrap)
        btn_f.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_f, text="+ Add Test Row", command=_add_appb_row).pack(side="left")

        return {
            "_rows":      appb_rows,
            "_add_row":   _add_appb_row,
            "_normal_desc": normal_desc_e,
            "_fire_desc":   fire_desc_e,
        }


    # ============================================================
    #   INTERCONNECTION DIAGRAM TAB
    # ============================================================


    def _build_fa_initiating_panel(self, parent, present_var, desc_text):
        """Right panel for Fire Alarm — FACP fields + initiating devices with device+area."""
        FA_DEVICE_OPTIONS = [
            "Manual Pull Stations",
            "Duct Smoke Detectors",
            "Smoke Detectors",
            "Heat Detectors",
            "Linear Heat Detectors",
            "Beam Smoke Detectors",
            "Flame Detectors",
            "Water-flow Devices",
            "Sprinkler Flow Switches",
            "Tamper Switches",
        ]

        # ── FACP Section ─────────────────────────────────────────
        ttk.Label(parent, text="Fire Alarm Control Panel",
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))

        facp_frame = ttk.Frame(parent)
        facp_frame.pack(fill="x", pady=(0, 6))

        ttk.Label(facp_frame, text="Room:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=3)
        self.facp_room_entry = ttk.Entry(facp_frame, width=36)
        self.facp_room_entry.grid(row=0, column=1, sticky="we", padx=(0, 8), pady=3)
        self._attach_entry_placeholder(self.facp_room_entry, "e.g. Main Electrical Room")

        ttk.Label(facp_frame, text="Floor:").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=3)
        self.facp_floor_entry = ttk.Entry(facp_frame, width=22)
        self.facp_floor_entry.grid(row=0, column=3, sticky="we", pady=3)
        self._attach_entry_placeholder(self.facp_floor_entry, "e.g. ground floor")

        facp_frame.columnconfigure(1, weight=1)
        facp_frame.columnconfigure(3, weight=1)

        # ── Annunciator Panel Section ─────────────────────────────
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(2, 6))

        ttk.Label(parent, text="Fire Alarm Annunciator Panel",
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))

        faap_rows_frame = ttk.Frame(parent)
        faap_rows_frame.pack(fill="x")

        self.faap_rows = []

        def _add_faap_row(room_val="", floor_val=""):
            row = {}
            row_f = ttk.Frame(faap_rows_frame)
            row_f.pack(fill="x", pady=(0, 3))
            row["frame"] = row_f

            ttk.Label(row_f, text="Room:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=3)
            room_e = ttk.Entry(row_f, width=36)
            room_e.grid(row=0, column=1, sticky="we", padx=(0, 8), pady=3)
            self._attach_entry_placeholder(room_e, "e.g. Main Lobby")
            if room_val:
                room_e.insert(0, room_val)
            row["room_entry"] = room_e

            ttk.Label(row_f, text="Floor:").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=3)
            floor_e = ttk.Entry(row_f, width=22)
            floor_e.grid(row=0, column=3, sticky="we", pady=3)
            self._attach_entry_placeholder(floor_e, "e.g. ground floor")
            if floor_val:
                floor_e.insert(0, floor_val)
            row["floor_entry"] = floor_e

            row_f.columnconfigure(1, weight=1)
            row_f.columnconfigure(3, weight=1)

            def _remove(r=row):
                r["frame"].destroy()
                if r in self.faap_rows:
                    self.faap_rows.remove(r)
                getattr(self, "_fa_update_desc", lambda: None)()

            ttk.Button(row_f, text="✕", width=3, command=_remove).grid(row=0, column=4, padx=(4, 0), pady=3)

            for w in (room_e, floor_e):
                w.bind("<KeyRelease>", lambda e: getattr(self, "_fa_update_desc", lambda: None)())

            self.faap_rows.append(row)
            getattr(self, "_fa_update_desc", lambda: None)()
            return row

        self._add_faap_row = _add_faap_row

        def _clear_faap_rows():
            for r in list(self.faap_rows):
                r["frame"].destroy()
            self.faap_rows.clear()

        self._clear_faap_rows = _clear_faap_rows

        ttk.Button(parent, text="+ Add Annunciator Panel",
                   command=lambda: _add_faap_row()).pack(anchor="w", pady=(0, 6))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(2, 8))

        # ── Initiating Devices Section ────────────────────────────
        ttk.Label(parent, text="Initiating Devices",
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))

        # Treeview: Device | Area — 5 rows tall
        cols = ("device", "area")
        self.fa_dev_tree = ttk.Treeview(parent, columns=cols, show="headings", height=5)
        self.fa_dev_tree.heading("device", text="Device")
        self.fa_dev_tree.heading("area",   text="Area")
        self.fa_dev_tree.column("device", width=200)
        self.fa_dev_tree.column("area",   width=180)
        fa_tree_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.fa_dev_tree.yview)
        self.fa_dev_tree.configure(yscrollcommand=fa_tree_scroll.set)
        self.fa_dev_tree.pack(side="top", fill="x", pady=(0, 4))

        # Entry row: dropdown + area field
        entry_frame = ttk.Frame(parent)
        entry_frame.pack(fill="x", pady=(0, 4))

        self.fa_device_var = tk.StringVar()
        ttk.Label(entry_frame, text="Device:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.fa_device_cb = ttk.Combobox(
            entry_frame, textvariable=self.fa_device_var,
            values=FA_DEVICE_OPTIONS, state="readonly"
        )
        self.fa_device_cb.grid(row=0, column=1, sticky="we", pady=2)

        ttk.Label(entry_frame, text="Area:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.fa_area_entry = ttk.Entry(entry_frame, width=40)
        self.fa_area_entry.grid(row=1, column=1, sticky="we", pady=2, ipady=4)

        entry_frame.columnconfigure(1, weight=1)

        # Internal device list (list of dicts)
        self.fa_devices = []

        def refresh_fa_tree(skip_preview=False):
            self.fa_dev_tree.delete(*self.fa_dev_tree.get_children())
            for i, d in enumerate(self.fa_devices):
                self.fa_dev_tree.insert("", "end", iid=str(i),
                                        values=(d["device"], d.get("area", "")))
            _update_dropdown()
            if not skip_preview:
                # Use the most up-to-date preview function (may be replaced by supervisory section)
                getattr(self, "_fa_update_desc", _update_desc_preview)()

        def _update_dropdown():
            used = {d["device"] for d in self.fa_devices}
            available = [opt for opt in FA_DEVICE_OPTIONS if opt not in used]
            self.fa_device_cb.configure(values=available)
            if self.fa_device_var.get() in used:
                self.fa_device_var.set("")

        def _update_desc_preview():
            """Rebuild the description text box live as devices/FACP fields change."""
            dt = getattr(self, "_fa_desc_text_ref", None)
            if dt is None:
                return
            template = SYSTEM_DEFAULTS.get("fire_alarm", {}).get("description", LOREM)
            fa_sentence = _build_fa_sentence()
            preview = template
            preview = preview.replace("{{fa_initiating_devices}}", fa_sentence)
            preview = preview.replace("{{facp_room}}",  self.facp_room_entry.get()  or "{{facp_room}}")
            preview = preview.replace("{{facp_floor}}", self.facp_floor_entry.get() or "{{facp_floor}}")
            preview = preview.replace("{{faap_sentence}}", _build_faap_sentence())
            preview = preview.replace("{{fa_notification_devices}}", _build_notification_sentence())
            dt.delete("1.0", "end")
            dt.insert("1.0", preview)

        def _build_faap_sentence():
            panels = []
            for r in self.faap_rows:
                room = r["room_entry"].get().strip() or "{{faap_room}}"
                floor = r["floor_entry"].get().strip() or "{{faap_floor}}"
                panels.append((room, floor))
            if not panels:
                return ""
            if len(panels) == 1:
                room, floor = panels[0]
                return f" The fire alarm annunciator panel is located in the {room} on the {floor} of the building."
            lines = [f"• {room} on the {floor} of the building." for room, floor in panels]
            return " Fire alarm annunciator panels are located as follows:\n" + "\n".join(lines)

        def _build_fa_sentence():
            if not self.fa_devices:
                return "manual pull stations at exits, located throughout the building"
            parts = [f"{d['device'].lower()} {d.get('area', '')}".strip()
                     for d in self.fa_devices]
            if len(parts) == 1:
                return f"{parts[0]}, located throughout the building"
            return ", ".join(parts[:-1]) + f", and {parts[-1]}, located throughout the building"

        def add_fa_device():
            device = self.fa_device_var.get().strip()
            if not device:
                return
            area = self.fa_area_entry.get().strip()
            self.fa_devices.append({"device": device, "area": area})
            self.fa_device_var.set("")
            self.fa_area_entry.delete(0, "end")
            refresh_fa_tree()

        def remove_fa_device():
            sel = self.fa_dev_tree.selection()
            if sel:
                del self.fa_devices[int(sel[0])]
                refresh_fa_tree()

        def edit_fa_device(event=None):
            sel = self.fa_dev_tree.selection()
            if not sel:
                return
            idx = int(sel[0])
            d = self.fa_devices[idx]
            self.fa_device_var.set(d["device"])
            self.fa_area_entry.delete(0, "end")
            self.fa_area_entry.insert(0, d.get("area", ""))
            del self.fa_devices[idx]
            refresh_fa_tree()

        self.fa_dev_tree.bind("<Double-1>", edit_fa_device)
        self._fa_update_desc = _update_desc_preview  # will be replaced below by supervisory section

        def _update_int_preview():
            """Rebuild integrations text box with current selected systems list."""
            LABEL_TO_NAME = {
                "Sprinkler":     "the sprinkler system",
                "Standpipe":     "the standpipe system",
                "Fire Pump":     "the fire pump",
                "Generator":     "the emergency generator",
                "Elec. Locks":   "electromagnetic locks",
                "AHU/Fan":       "air handling units",
                "Smoke Dampers": "smoke dampers",
                "Fire Shutters": "fire shutters",
                "Kitchen Hood":  "the kitchen hood suppression system",
                "Water Mist":    "the water mist system",
                "Elevator":      "the elevator recall system",
            }
            selected = [v.get() for v in self.sys_selector_vars if v.get()]
            others = [LABEL_TO_NAME.get(s, s.lower()) for s in selected if s != "Fire Alarm"]
            if others:
                if len(others) == 1:
                    fa_integrations = others[0]
                elif len(others) == 2:
                    fa_integrations = f"{others[0]} and {others[1]}"
                else:
                    fa_integrations = (
                        ", ".join(others[:-1]) + f", and {others[-1]}"
                    )
            else:
                fa_integrations = "various fire protection and life safety systems"

            first_sentence = (
                f"The fire alarm system is integrated with {fa_integrations}. "
                "Refer to individual systems for detailed description of the "
                "fire alarm integrations to each of these systems."
            )
            second_sentence = (
                "Additionally, the fire alarm system is integrated to a central monitoring "
                "station for remote monitoring of alarm, trouble, and supervisory conditions. "
                "The monitoring station connection is monitored for integrity."
            )
            int_text = getattr(self, "fa_int_text", None)
            if not int_text:
                return
            int_text.delete("1.0", "end")
            int_text.insert("1.0", f"{first_sentence}\n\n{second_sentence}")

        self._fa_update_int = _update_int_preview

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=(0, 4))
        self.fa_add_btn = ttk.Button(btn_frame, text="+ Add", command=add_fa_device)
        self.fa_rem_btn = ttk.Button(btn_frame, text="Remove", command=remove_fa_device)
        self.fa_add_btn.pack(side="left", padx=(0, 4))
        self.fa_rem_btn.pack(side="left")

        # Add default: Manual Pull Stations at exits
        self.fa_devices.append({"device": "Manual Pull Stations", "area": "at exits"})
        refresh_fa_tree(skip_preview=True)

        # ── Supervisory Devices Section ───────────────────────────
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(6, 8))
        ttk.Label(parent, text="Supervisory Devices",
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))

        sup_cols = ("device", "interconnection")
        self.fa_sup_tree = ttk.Treeview(parent, columns=sup_cols, show="headings", height=4)
        self.fa_sup_tree.heading("device",        text="Supervisory Device")
        self.fa_sup_tree.heading("interconnection", text="Interconnection Served")
        self.fa_sup_tree.column("device",          width=200)
        self.fa_sup_tree.column("interconnection", width=180)
        sup_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.fa_sup_tree.yview)
        self.fa_sup_tree.configure(yscrollcommand=sup_scroll.set)
        self.fa_sup_tree.pack(side="top", fill="x", pady=(0, 4))

        sup_entry_frame = ttk.Frame(parent)
        sup_entry_frame.pack(fill="x", pady=(0, 4))

        ttk.Label(sup_entry_frame, text="Device:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.fa_sup_device_entry = ttk.Entry(sup_entry_frame, width=40)
        self.fa_sup_device_entry.grid(row=0, column=1, sticky="we", pady=2, ipady=4)

        ttk.Label(sup_entry_frame, text="Interconnection:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.fa_sup_int_var = tk.StringVar()
        self.fa_sup_int_cb = ttk.Combobox(sup_entry_frame, textvariable=self.fa_sup_int_var, width=38)
        self.fa_sup_int_cb.grid(row=1, column=1, sticky="we", pady=2, ipady=4)

        # Map system selector labels → friendly interconnection names
        SUP_INT_LABELS = {
            "Fire Alarm":    "fire alarm system",
            "Sprinkler":     "sprinkler system",
            "Standpipe":     "standpipe system",
            "Pre-Action Sprinkler": "pre-action sprinkler system",
            "Fire Pump":     "fire pump",
            "Generator":     "generator",
            "Maglocks":      "electromagnetic locks",
            "Door Holders":  "door holders",
            "AHU/Fan":       "air handling units",
            "Smoke Dampers": "smoke dampers",
            "Fire Shutters": "fire shutters",
            "Kitchen Hood":  "kitchen hood suppression system",
            "Water Mist":    "water mist system",
            "Elevator":      "elevator",
        }

        def _refresh_sup_int_dropdown():
            selected = [v.get() for v in self.sys_selector_vars if v.get()]
            opts = [SUP_INT_LABELS.get(s, s.lower()) for s in selected]
            self.fa_sup_int_cb.configure(values=opts)

        sup_entry_frame.columnconfigure(1, weight=1)

        self.fa_supervisory_devices = []

        def refresh_sup_tree(skip_preview=False):
            self.fa_sup_tree.delete(*self.fa_sup_tree.get_children())
            for i, d in enumerate(self.fa_supervisory_devices):
                self.fa_sup_tree.insert("", "end", iid=str(i),
                                        values=(d["device"], d.get("interconnection", "")))
            if not skip_preview:
                getattr(self, "_fa_update_desc", lambda: None)()

        def _build_supervisory_sentence():
            if not self.fa_supervisory_devices:
                return ""
            parts = [
                f"{d['device'].lower()} for the {d.get('interconnection', '').lower()}".strip()
                for d in self.fa_supervisory_devices
            ]
            if len(parts) == 1:
                return parts[0]
            elif len(parts) == 2:
                return f"{parts[0]} and {parts[1]}"
            else:
                return ", ".join(parts[:-1]) + f", and {parts[-1]}"

        # Patch _update_desc_preview to also substitute supervisory devices
        def _update_desc_preview_full():
            dt = getattr(self, "_fa_desc_text_ref", None)
            if dt is None:
                return
            template = SYSTEM_DEFAULTS.get("fire_alarm", {}).get("description", LOREM)
            fa_sentence = _build_fa_sentence()
            sup_sentence = _build_supervisory_sentence()
            preview = template
            preview = preview.replace("{{fa_initiating_devices}}", fa_sentence)
            preview = preview.replace("{{fa_supervisory_devices}}", sup_sentence or "{{fa_supervisory_devices}}")
            preview = preview.replace("{{facp_room}}",  self.facp_room_entry.get()  or "{{facp_room}}")
            preview = preview.replace("{{facp_floor}}", self.facp_floor_entry.get() or "{{facp_floor}}")
            preview = preview.replace("{{faap_sentence}}", _build_faap_sentence())
            preview = preview.replace("{{fa_notification_devices}}", _build_notification_sentence())
            dt.delete("1.0", "end")
            dt.insert("1.0", preview)

        self._fa_update_desc = _update_desc_preview_full
        # Re-bind FACP entries to use the full version (FAAP rows already bind
        # to self._fa_update_desc dynamically, which now resolves here)
        for entry in (self.facp_room_entry, self.facp_floor_entry):
            entry.bind("<KeyRelease>", lambda e: _update_desc_preview_full())

        # Also make the initiating devices refresh use the full preview
        def refresh_fa_tree_full(skip_preview=False):
            self.fa_dev_tree.delete(*self.fa_dev_tree.get_children())
            for i, d in enumerate(self.fa_devices):
                self.fa_dev_tree.insert("", "end", iid=str(i),
                                        values=(d["device"], d.get("area", "")))
            _update_dropdown()
            if not skip_preview:
                _update_desc_preview_full()

        self._fa_refresh = refresh_fa_tree_full

        def add_sup_device():
            device = self.fa_sup_device_entry.get().strip()
            interconnection = self.fa_sup_int_var.get().strip()
            if not device:
                return
            self.fa_supervisory_devices.append({"device": device, "interconnection": interconnection})
            self.fa_sup_device_entry.delete(0, "end")
            self.fa_sup_int_var.set("")
            refresh_sup_tree()

        def remove_sup_device():
            sel = self.fa_sup_tree.selection()
            if sel:
                del self.fa_supervisory_devices[int(sel[0])]
                refresh_sup_tree()

        def edit_sup_device(event=None):
            sel = self.fa_sup_tree.selection()
            if not sel:
                return
            idx = int(sel[0])
            d = self.fa_supervisory_devices[idx]
            self.fa_sup_device_entry.delete(0, "end")
            self.fa_sup_device_entry.insert(0, d["device"])
            self.fa_sup_int_var.set(d.get("interconnection", ""))
            _refresh_sup_int_dropdown()
            del self.fa_supervisory_devices[idx]
            refresh_sup_tree()

        self.fa_sup_tree.bind("<Double-1>", edit_sup_device)
        self._fa_sup_refresh = refresh_sup_tree
        self._refresh_sup_int_dropdown = _refresh_sup_int_dropdown

        # Populate dropdown initially and refresh whenever combobox is opened
        _refresh_sup_int_dropdown()
        self.fa_sup_int_cb.bind("<ButtonPress-1>", lambda e: _refresh_sup_int_dropdown())

        # Default entries — shown in treeview and reflected in description preview
        self.fa_supervisory_devices.append({"device": "Monitoring valves that control the water supply", "interconnection": "sprinkler system"})
        self.fa_supervisory_devices.append({"device": "Pressure switches", "interconnection": "sprinkler system"})
        refresh_sup_tree(skip_preview=True)

        sup_btn_frame = ttk.Frame(parent)
        sup_btn_frame.pack(fill="x", pady=(0, 4))
        ttk.Button(sup_btn_frame, text="+ Add",  command=add_sup_device).pack(side="left", padx=(0, 4))
        ttk.Button(sup_btn_frame, text="Remove", command=remove_sup_device).pack(side="left")

        # ── Notification Devices Section ──────────────────────────
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(6, 8))
        ttk.Label(parent, text="Notification Devices",
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))

        notif_cols = ("device",)
        self.fa_notif_tree = ttk.Treeview(parent, columns=notif_cols, show="headings", height=3)
        self.fa_notif_tree.heading("device", text="Notification Device")
        self.fa_notif_tree.column("device", width=200)
        notif_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.fa_notif_tree.yview)
        self.fa_notif_tree.configure(yscrollcommand=notif_scroll.set)
        self.fa_notif_tree.pack(side="top", fill="x", pady=(0, 4))

        notif_entry_frame = ttk.Frame(parent)
        notif_entry_frame.pack(fill="x", pady=(0, 4))

        ttk.Label(notif_entry_frame, text="Device:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.fa_notif_device_entry = ttk.Entry(notif_entry_frame, width=40)
        self.fa_notif_device_entry.grid(row=0, column=1, sticky="we", pady=2, ipady=4)
        notif_entry_frame.columnconfigure(1, weight=1)

        self.fa_notification_devices = []

        def refresh_notif_tree(skip_preview=False):
            self.fa_notif_tree.delete(*self.fa_notif_tree.get_children())
            for i, d in enumerate(self.fa_notification_devices):
                self.fa_notif_tree.insert("", "end", iid=str(i), values=(d["device"],))
            if not skip_preview:
                getattr(self, "_fa_update_desc", lambda: None)()

        def _build_notification_sentence():
            if not self.fa_notification_devices:
                return "horns and strobes"
            parts = [d["device"].lower() for d in self.fa_notification_devices]
            if len(parts) == 1:
                return parts[0]
            elif len(parts) == 2:
                return f"{parts[0]} and {parts[1]}"
            else:
                return ", ".join(parts[:-1]) + f", and {parts[-1]}"

        def add_notif_device():
            device = self.fa_notif_device_entry.get().strip()
            if not device:
                return
            self.fa_notification_devices.append({"device": device})
            self.fa_notif_device_entry.delete(0, "end")
            refresh_notif_tree()

        def remove_notif_device():
            sel = self.fa_notif_tree.selection()
            if sel:
                del self.fa_notification_devices[int(sel[0])]
                refresh_notif_tree()

        def edit_notif_device(event=None):
            sel = self.fa_notif_tree.selection()
            if not sel:
                return
            idx = int(sel[0])
            d = self.fa_notification_devices[idx]
            self.fa_notif_device_entry.delete(0, "end")
            self.fa_notif_device_entry.insert(0, d["device"])
            del self.fa_notification_devices[idx]
            refresh_notif_tree()

        self.fa_notif_tree.bind("<Double-1>", edit_notif_device)
        self._fa_notif_refresh = refresh_notif_tree

        # Default entries — shown in treeview and reflected in description preview
        self.fa_notification_devices.append({"device": "Horns"})
        self.fa_notification_devices.append({"device": "Strobes"})
        refresh_notif_tree(skip_preview=True)

        notif_btn_frame = ttk.Frame(parent)
        notif_btn_frame.pack(fill="x", pady=(0, 4))
        ttk.Button(notif_btn_frame, text="+ Add",  command=add_notif_device).pack(side="left", padx=(0, 4))
        ttk.Button(notif_btn_frame, text="Remove", command=remove_notif_device).pack(side="left")

        # ── Drag-to-reorder for device lists ───────────────────────
        self._enable_tree_drag_reorder(self.fa_dev_tree, self.fa_devices, lambda: self._fa_refresh())
        self._enable_tree_drag_reorder(self.fa_sup_tree, self.fa_supervisory_devices, lambda: self._fa_sup_refresh())
        self._enable_tree_drag_reorder(self.fa_notif_tree, self.fa_notification_devices, refresh_notif_tree)


    def _refresh_spr_btn_styles(self):
        """Re-apply sprinkler toggle colours by calling each stored repaint fn."""
        for repaint in getattr(self, "_sprinkler_repaints", {}).values():
            try:
                repaint()
            except Exception:
                pass

    def _do_spr_btn_pass(self):
        """No-op — kept for compatibility; repaint approach needs no second pass."""
        pass

        # ---------- Action bar ----------
    def _build_elevator_actions_section(self, parent, _refresh_scroll=None):
        """Build the Elevator Actions table UI (Action | Description) with
        add/remove/drag-to-reorder rows. Inserted between the matrix and Appendix B.

        Default rows match the Word template defaults. The Primary and Alternate
        Recall descriptions auto-update when elev_primary_floor / elev_alternate_floor
        change — but only if the user has not manually edited that description cell.
        """
        # ── Section header ────────────────────────────────────────────────
        sep = ttk.Separator(parent, orient="horizontal")
        sep.pack(fill="x", pady=(10, 4))
        hdr = ttk.Frame(parent)
        hdr.pack(fill="x")
        ttk.Label(hdr, text="Elevator Actions",
                  font=("", 10, "bold")).pack(side="left")
        ttk.Label(hdr, text="  Actions performed by the elevator on fire alarm activation",
                  foreground="gray").pack(side="left")

        # Column constants
        COL_DH   = 0
        COL_NO   = 1
        COL_ACT  = 2
        COL_DESC = 3
        COL_RM   = 4

        # Shared grid frame — header row 0, data rows 1+
        grid_frame = tk.Frame(parent)
        grid_frame.pack(fill="x", pady=(4, 0))
        grid_frame.columnconfigure(COL_DH,   weight=0, minsize=22)
        grid_frame.columnconfigure(COL_NO,   weight=0, minsize=30)
        grid_frame.columnconfigure(COL_ACT,  weight=1)
        grid_frame.columnconfigure(COL_DESC, weight=3)
        grid_frame.columnconfigure(COL_RM,   weight=0, minsize=28)

        ttk.Label(grid_frame, text="No.",    font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_NO,   sticky="w", padx=(4, 2), pady=(0, 2))
        ttk.Label(grid_frame, text="Action", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_ACT,  sticky="w", padx=(0, 6), pady=(0, 2))
        ttk.Label(grid_frame, text="Operation Description", font=("", 8, "bold"), foreground="gray").grid(
            row=0, column=COL_DESC, sticky="w", padx=(0, 4), pady=(0, 2))

        _next_grow = [1]
        action_rows = []
        _drag_state = {"start_y": None, "src_idx": None}

        def _repack_all():
            for i, r in enumerate(action_rows):
                grow = i + 1
                for col_key, col_idx, kw in (
                    ("_drag_handle", COL_DH,   dict(sticky="w",   padx=(2, 0), pady=3)),
                    ("_no_lbl",      COL_NO,   dict(sticky="w",   padx=(4, 2), pady=3)),
                    ("action",       COL_ACT,  dict(sticky="nswe",padx=(0, 6), pady=3)),
                    ("desc",         COL_DESC, dict(sticky="nswe",padx=(0, 4), pady=3)),
                    ("_rm_btn",      COL_RM,   dict(padx=(0, 4),  pady=3)),
                ):
                    w = r.get(col_key)
                    if w and w.winfo_exists():
                        w.grid(row=grow, column=col_idx, **kw)
                no_lbl = r.get("_no_lbl")
                if no_lbl and no_lbl.winfo_exists():
                    no_lbl.configure(text=str(i + 1))

        def _add_action_row(action="", desc="", _auto_desc_key=None):
            """
            _auto_desc_key: one of "primary_recall" | "alternate_recall" | None.
            When set, the desc field is auto-updated from the recall floor entries
            unless the user has manually edited it.
            """
            idx  = len(action_rows) + 1
            grow = _next_grow[0]
            _next_grow[0] += 1
            widgets = {}

            # Track whether user has manually edited the description
            _user_edited = [False]

            # Drag handle
            drag_lbl = tk.Label(grid_frame, text="≡", foreground="#aaaaaa",
                                cursor="sb_v_double_arrow", font=("", 11))
            drag_lbl.grid(row=grow, column=COL_DH, sticky="w", padx=(2, 0), pady=3)
            widgets["_drag_handle"] = drag_lbl

            def _drag_start(event, w=widgets):
                _drag_state["start_y"] = event.y_root
                _drag_state["src_idx"] = action_rows.index(w)

            def _drag_motion(event, w=widgets):
                if _drag_state["src_idx"] is None:
                    return
                dy = event.y_root - _drag_state["start_y"]
                if abs(dy) < 32:
                    return
                step = 1 if dy > 0 else -1
                src = _drag_state["src_idx"]
                dst = max(0, min(len(action_rows) - 1, src + step))
                if dst != src:
                    action_rows.insert(dst, action_rows.pop(src))
                    _drag_state["src_idx"] = dst
                    _drag_state["start_y"] = event.y_root
                    _repack_all()

            def _drag_end(event):
                _drag_state["start_y"] = None
                _drag_state["src_idx"] = None

            drag_lbl.bind("<ButtonPress-1>",   _drag_start)
            drag_lbl.bind("<B1-Motion>",        _drag_motion)
            drag_lbl.bind("<ButtonRelease-1>",  _drag_end)

            # Row number label
            no_lbl = ttk.Label(grid_frame, text=str(idx), foreground="gray")
            no_lbl.grid(row=grow, column=COL_NO, sticky="w", padx=(4, 2), pady=3)
            widgets["_no_lbl"] = no_lbl

            # Action text widget
            act_t = tk.Text(grid_frame, wrap="word", height=1, relief="flat",
                            bd=1, highlightthickness=1,
                            highlightbackground="#aaaaaa", highlightcolor="#0078d4")
            act_t.insert("1.0", action)
            act_t.grid(row=grow, column=COL_ACT, sticky="nswe", padx=(0, 6), pady=3)
            attach_spellcheck(act_t)
            widgets["action"] = act_t

            # Description text widget
            desc_t = tk.Text(grid_frame, wrap="word", height=2, relief="flat",
                             bd=1, highlightthickness=1,
                             highlightbackground="#aaaaaa", highlightcolor="#0078d4")
            desc_t.insert("1.0", desc)
            desc_t.grid(row=grow, column=COL_DESC, sticky="nswe", padx=(0, 4), pady=3)
            attach_spellcheck(desc_t)
            widgets["desc"]             = desc_t
            widgets["_auto_desc_key"]   = _auto_desc_key
            widgets["_user_edited"]     = _user_edited

            def _on_desc_edit(event, _ue=_user_edited):
                _ue[0] = True
            desc_t.bind("<Key>", _on_desc_edit)

            # Remove button
            def _remove(r=widgets):
                for col_key in ("_drag_handle", "_no_lbl", "action", "desc", "_rm_btn"):
                    w = r.get(col_key)
                    if w and w.winfo_exists():
                        w.grid_remove()
                        w.destroy()
                if r in action_rows:
                    action_rows.remove(r)
                _repack_all()
                if _refresh_scroll:
                    self.root.after(0, _refresh_scroll)

            rm_btn = ttk.Button(grid_frame, text="✕", width=2, command=_remove)
            rm_btn.grid(row=grow, column=COL_RM, padx=(0, 4), pady=3)
            widgets["_rm_btn"] = rm_btn

            action_rows.append(widgets)
            if _refresh_scroll:
                self.root.after(0, _refresh_scroll)
            return widgets

        # ── Seed default rows ─────────────────────────────────────────────
        prim = getattr(self, "elev_primary_floor",  None)
        alt  = getattr(self, "elev_alternate_floor", None)
        prim_val = prim.get().strip() if prim else ""
        alt_val  = alt.get().strip()  if alt  else ""

        def _prim_desc(floor):
            f = floor or "{{elev_prim_rcl}}"
            return (
                f"Initiated for automatic fire detection activation on floor areas "
                f"other than Primary Recall Level ({f})."
            )

        def _alt_desc(floor):
            f = floor or "{{elev_prim_rcl}}"
            return (
                f"Initiated for automatic fire detection activation on the Primary "
                f"Recall Level ({f})."
            )

        DEFAULTS = [
            ("Primary Recall",        _prim_desc(prim_val), "primary_recall"),
            ("Alternate Recall",      _alt_desc(alt_val),   "alternate_recall"),
            ("Top of Shaft Alarm",
             "Initiated for automatic fire detection activation at the top of the elevator shaft.",
             None),
            ("Elevator Pit Alarm",
             "Initiated for automatic fire detection activation in the elevator shaft pit.",
             None),
        ]
        for act, desc, adk in DEFAULTS:
            _add_action_row(action=act, desc=desc, _auto_desc_key=adk)

        # ── Auto-update recall descriptions when floor fields change ──────
        def _sync_recall_descs(*_):
            pv = (getattr(self, "elev_primary_floor", None) or tk.StringVar()).get().strip()
            for r in action_rows:
                adk = r.get("_auto_desc_key")
                ue  = r.get("_user_edited", [True])
                if ue[0]:
                    continue
                dt = r.get("desc")
                if not (dt and dt.winfo_exists()):
                    continue
                if adk == "primary_recall":
                    new_text = _prim_desc(pv)
                elif adk == "alternate_recall":
                    new_text = _alt_desc(pv)   # primary floor used in both per template
                else:
                    continue
                dt.delete("1.0", "end")
                dt.insert("1.0", new_text)

        # Bind to the elevator floor entry widgets once they exist
        def _attach_recall_bindings():
            pf = getattr(self, "elev_primary_floor",  None)
            af = getattr(self, "elev_alternate_floor", None)
            if pf:
                pf.bind("<KeyRelease>", _sync_recall_descs, add="+")
            if af:
                af.bind("<KeyRelease>", _sync_recall_descs, add="+")

        self.root.after(100, _attach_recall_bindings)

        # ── Add Row button ────────────────────────────────────────────────
        btn_f = ttk.Frame(parent)
        btn_f.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_f, text="+ Add Action Row",
                   command=_add_action_row).pack(side="left")

        return {
            "_rows":    action_rows,
            "_add_row": _add_action_row,
        }

    def _refresh_elevator_appb_rows(self):
        """Rebuild elevator Appendix B rows based on current elevator count."""
        ui = self.sys_ui.get("elevator", {})
        appb = ui.get("appb", {})
        add_row = appb.get("_add_row")
        rows    = appb.get("_rows", [])
        if not add_row:
            return
        for r in list(rows):
            for wval in r.values():
                if hasattr(wval, "destroy"):
                    try: wval.destroy()
                    except Exception: pass
        rows.clear()
        count = getattr(self, "elev_count_var", None)
        try:
            count = int(count.get() if count else 1)
        except (ValueError, TypeError):
            count = 1
        for n in range(1, count + 1):
            for recall in ["Primary Recall", "Alternate Recall", "Top of Shaft", "Elevator Pit"]:
                add_row(integration=f"Elevator #{n} {recall}", normal="", fire="")