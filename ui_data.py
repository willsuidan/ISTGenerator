"""
ui_data.py — DataMixin: data gather/populate, report generation UI, contractors, clear_all.
"""

import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from defaults import (
    SYSTEM_DEFAULTS, MATRIX_DEFAULTS, TP_DEFAULTS, APPB_DEFAULTS, APPB_DESC_DEFAULTS,
    NOTIFICATION_DEFAULTS, format_weeks_notice,
    PPE_DEFAULTS, SPECIAL_HAZARDS_DEFAULT, TEAM_COMMUNICATIONS_DEFAULT, OCCUPANT_NOTIFICATION_DEFAULT,
)
from constants import SYSTEMS, MONITORING_MATRIX_DEFAULTS, CONTACT_TYPES, LOREM
import importlib.util
_PIL_AVAILABLE = importlib.util.find_spec("PIL") is not None

from word_gen import generate_report
from spellcheck import get_user_words, load_user_words



def _refresh_fields_via_word(path):
    """
    Open the document in a hidden Word instance, update all fields
    (including page numbers), then save and close.
    Falls back silently if win32com is not available.
    """
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        try:
            doc = word.Documents.Open(os.path.abspath(path))
            doc.Fields.Update()
            for section in doc.Sections:
                for hdr in section.Headers:
                    hdr.Range.Fields.Update()
                for ftr in section.Footers:
                    ftr.Range.Fields.Update()
            doc.Save()
            doc.Close(False)
        finally:
            word.Quit()
            pythoncom.CoUninitialize()
    except Exception:
        pass  # win32com not available or Word not installed — silently skip


class DataMixin:
    """Mixin providing data gather/populate, save/load, report generation UI."""
    def _gather_data(self):
        scope = self.scope_entry.get().strip() if self.scope_var.get() == "limited" else ""
        selected_labels = {v.get() for v in self.sys_selector_vars if v.get()}
        systems_data = {}
        for sys_info in SYSTEMS:
            key = sys_info["key"]
            ui  = self.sys_ui[key]
            sys_entry = {
                "present":      sys_info["label"] in selected_labels,
                "description":  ui["desc_text"].get("1.0", "end-1c"),
                "integrations": ui["int_text"].get("1.0", "end-1c"),
            }
            # Collect matrix data — always save, even if defaults
            matrix = ui.get("matrix", {})

            def _read_matrix_row(r):
                """Safely read a matrix row dict into serialisable data."""
                out = {}
                for f in ("integration", "normal_mode", "fire_mode"):
                    widget = r.get(f)
                    out[f] = widget.get("1.0", "end-1c") if widget else ""
                for f in ("tp_normal", "tp_fire"):
                    widget = r.get(f)
                    raw = widget.get("1.0", "end-1c") if widget else ""
                    out[f] = raw.replace("• ", "- ")
                return out

            if key == "fire_alarm":
                sys_entry["matrix_mon"] = [
                    _read_matrix_row(r) for r in matrix.get("_mon", [])
                ]
            else:
                sys_entry["matrix_rows"] = [
                    _read_matrix_row(r) for r in matrix.get("_rows", [])
                ]
            if key == "fire_alarm":
                sys_entry["fa_initiating_devices"]   = list(self.fa_devices)
                sys_entry["fa_supervisory_devices"]  = list(getattr(self, "fa_supervisory_devices", []))
                sys_entry["fa_notification_devices"] = list(getattr(self, "fa_notification_devices", []))
                sys_entry["facp_room"]  = self.facp_room_entry.get().strip()
                sys_entry["facp_floor"] = self.facp_floor_entry.get().strip()
                sys_entry["faap_panels"] = [
                    {"room": r["room_entry"].get().strip(), "floor": r["floor_entry"].get().strip()}
                    for r in getattr(self, "faap_rows", [])
                ]
            if key == "fire_pump":
                sys_entry["fp_room"]  = self.fp_room_entry.get().strip()
                sys_entry["fp_floor"] = self.fp_floor_entry.get().strip()
            if key == "pre_action":
                sys_entry["pre_action_panel"] = getattr(self, "pre_action_panel_var", tk.BooleanVar()).get()
                sys_entry["pre_action_subtypes"] = {
                    s: v.get() for s, v in getattr(self, "_pre_action_subtype_vars", {}).items()
                }
                sys_entry["pa_protected_areas"] = list(getattr(self, "pa_protected_areas", []))
                sys_entry["pa_valve_locations"]  = list(getattr(self, "pa_valve_locations",  []))
                sys_entry["pap_matrix_rows"] = [
                    {
                        "integration": r["integration"].get("1.0", "end-1c").strip(),
                        "normal_mode": r["normal_mode"].get("1.0", "end-1c").strip(),
                        "fire_mode":   r["fire_mode"].get("1.0", "end-1c").strip(),
                        "tp_normal":   r["tp_normal"].get("1.0", "end-1c").strip(),
                        "tp_fire":     r["tp_fire"].get("1.0", "end-1c").strip(),
                    }
                    for r in getattr(self, "_pap_matrix_rows", [])
                ]
                sys_entry["pap_appb_rows"] = [
                    {
                        "integration": r["integration"].get("1.0", "end-1c").strip(),
                        "normal":  r["normal"].get(),
                        "fire":    r["fire"].get(),
                        "notes":   r["notes"].get().strip(),
                        "sw_type": r.get("sw_type", tk.StringVar()).get(),
                        "sw_no":   r.get("sw_no",   tk.StringVar()).get(),
                    }
                    for r in getattr(self, "_pap_appb_rows", [])
                ]
                nd = getattr(self, "_pap_appb_normal_desc_e", None)
                fd = getattr(self, "_pap_appb_fire_desc_e",   None)
                sys_entry["pap_appb_normal_desc"] = nd.get() if nd else ""
                sys_entry["pap_appb_fire_desc"]   = fd.get() if fd else ""
            if key == "generator":
                sys_entry["gen_type"]   = self.gen_type_var.get()
                sys_entry["gen_class"]  = self.gen_class_var.get()
                sys_entry["gen_room"]   = self.gen_room_entry.get().strip()
                sys_entry["gen_floor"]  = self.gen_floor_entry.get().strip()
                sys_entry["gen_count"]  = self.gen_count_var.get()
                sys_entry["gen_served"] = [lbl for lbl, v in self.gen_served_vars.items() if v.get()]
                sys_entry["gen_custom_served"] = [
                    {"label": c["label"], "checked": c["var"].get()}
                    for c in getattr(self, "gen_custom_served", [])
                ]
                # Save generator served systems matrix rows
                sys_entry["gen_served_matrix_rows"] = [
                    _read_matrix_row(r) for r in getattr(self, "_gen_served_matrix_rows", [])
                ]
                # Save generator served systems Appendix B rows
                gs_appb_saved = []
                for r in getattr(self, "_gs_appb_rows", []):
                    integ_w = r.get("integration")
                    gs_appb_saved.append({
                        "integration": integ_w.get("1.0","end-1c") if integ_w else "",
                        "normal": r["normal"].get() if "normal" in r else "",
                        "fire":   r["fire"].get()   if "fire"   in r else "",
                        "notes":  r["notes"].get()  if hasattr(r.get("notes"), "get") else "",
                    })
                sys_entry["gs_appb_rows"]    = gs_appb_saved
                nd_w = getattr(self, "_gs_normal_desc_e", None)
                fd_w = getattr(self, "_gs_fire_desc_e",   None)
                sys_entry["gs_normal_desc"] = nd_w.get() if nd_w else ""
                sys_entry["gs_fire_desc"]   = fd_w.get() if fd_w else ""
            if key == "elevator":
                sys_entry["elev_count"]         = self.elev_count_var.get()
                sys_entry["elev_primary_floor"]  = self.elev_primary_floor.get().strip()
                sys_entry["elev_alternate_floor"] = self.elev_alternate_floor.get().strip()
                # Gather elevator action rows
                ea_data = self.sys_ui.get("elevator", {}).get("elev_actions", {})
                ea_rows = ea_data.get("_rows", [])
                elev_actions = []
                for r in ea_rows:
                    act_w  = r.get("action")
                    desc_w = r.get("desc")
                    act  = act_w.get("1.0",  "end-1c").strip() if act_w  else ""
                    desc = desc_w.get("1.0", "end-1c").strip() if desc_w else ""
                    elev_actions.append({
                        "action": act,
                        "desc":   desc,
                        "_auto_desc_key": r.get("_auto_desc_key"),
                        "_user_edited":   r.get("_user_edited", [False])[0],
                    })
                sys_entry["elev_actions"] = elev_actions
            if key == "sprinkler":
                sys_entry["sprinkler_subtypes"] = {s: v.get() for s, v in self._sprinkler_subtype_vars.items()}
                sys_entry["sprk_valve_locations"] = list(getattr(self, "sprk_valve_locations", []))
            if key == "standpipe":
                sys_entry["stnd_valve_locations"] = list(getattr(self, "stnd_valve_locations", []))
            if key == "water_mist":
                sys_entry["wm_protected_areas"] = list(getattr(self, "wm_protected_areas", []))
            # Appendix B rows
            appb = ui.get("appb", {})
            appb_saved = []
            nd_widget = appb.get("_normal_desc")
            fd_widget = appb.get("_fire_desc")
            for r in appb.get("_rows", []):
                appb_saved.append({
                    "integration": r["integration"].get("1.0", "end-1c"),
                    "sw_type":     r["sw_type"].get() if "sw_type" in r else "",
                    "sw_no":       r["sw_no"].get()   if "sw_no"   in r else "",
                    "normal":      r["normal"].get(),
                    "fire":        r["fire"].get(),
                    "notes":       r["notes"].get(),
                })
            sys_entry["appb_rows"] = appb_saved
            sys_entry["appb_normal_desc"] = nd_widget.get() if nd_widget else ""
            sys_entry["appb_fire_desc"]   = fd_widget.get() if fd_widget else ""
            systems_data[key] = sys_entry
        return {
            "project_info":         {k: (e.get() if not isinstance(e, ttk.Combobox) else e.get()) for k, e in self.project_fields.items()},
            "building_description": self.building_desc_text.get("1.0", "end-1c"),
            "building_scope":       scope,
            "building_scope_type":  self.scope_var.get(),
            "selected_systems":     [v.get() for v in self.sys_selector_vars if v.get()],
            "occupancies":          self._get_occupancies(),
            "contractors":          self.contractors,
            "systems":              systems_data,
            "diagram":              self._diag_get_state(),
            "template_path":        self.template_path.get(),
            "diagram_png_path":     getattr(self, "_diag_selected_png", None) or "",
            "output_path":          self.output_path.get(),
            "user_dictionary":      get_user_words(),
            "ist_notes":            [t.get("1.0", "end-1c") for t in getattr(self, "ist_notes", [])],
            "forms_documentation":  getattr(self, "_forms_doc_text", None) and self._forms_doc_text.get("1.0", "end-1c") or "",
            "personnel_safety": {
                "noti_to_participants":   self._noti_participants_text.get("1.0", "end-1c"),
                "participant_wks_notice": self.participant_wks_notice_var.get(),
                "noti_to_occupants":      self._noti_occupants_text.get("1.0", "end-1c"),
                "occupant_hrs_notice":    self.occupant_hrs_notice_var.get(),
                "prop_notice_example":    self._prop_notice_text.get("1.0", "end-1c"),
                "building_phase":         self.building_phase_var.get(),
                "ppe_required":           self.ppe_required_var.get(),
                "ppe_items":              list(self.ppe_items),
                "safety_protocols":       self._safety_protocols_text.get("1.0", "end-1c"),
                "special_hazards":        self._special_hazards_text.get("1.0", "end-1c"),
                "team_communications":    self._team_communications_text.get("1.0", "end-1c"),
                "occupant_notification":  self._occupant_notification_text.get("1.0", "end-1c"),
            },
        }

    def _populate_from_data(self, data):
        # Restore user dictionary words saved with this file
        load_user_words(data.get("user_dictionary", []))

        for key, widget in self.project_fields.items():
            value = data.get("project_info", {}).get(key, "")
            if isinstance(widget, ttk.Combobox):
                widget.set(value)
            else:
                widget.delete(0, "end")
                widget.insert(0, value)

        scope_type = data.get("building_scope_type", "entire")
        self.scope_var.set(scope_type)
        self.scope_entry.configure(state="normal")
        self.scope_entry.delete(0, "end")
        self.scope_entry.insert(0, data.get("building_scope", ""))
        if scope_type != "limited":
            self.scope_entry.configure(state="disabled")

        self.building_desc_text.delete("1.0", "end")
        self.building_desc_text.insert("1.0", data.get("building_description", ""))

        # Restore system selectors — clear existing rows first
        for widget in self.sys_selector_inner.winfo_children():
            widget.destroy()
        self.sys_selector_vars = []
        # Re-add locked FA row
        fa_row = ttk.Frame(self.sys_selector_inner)
        fa_row.pack(fill="x", pady=2)
        ttk.Label(fa_row, text="Fire Alarm", anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 6))
        fa_var = tk.StringVar(value="Fire Alarm")
        self.sys_selector_vars = [fa_var]
        # Add other selected systems
        for label in data.get("selected_systems", []):
            if label != "Fire Alarm":
                self._add_system_selector_row(value=label)

        # Rebuild the generator served systems checklist now that selectors are restored
        if hasattr(self, "_refresh_gen_checklist"):
            self._refresh_gen_checklist()

        for widget in self.occ_inner.winfo_children():
            widget.destroy()
        self.occ_vars = []
        saved_occs = data.get("occupancies", [])
        if saved_occs:
            for occ in saved_occs:
                val  = occ.get("occ_type", "")
                desc = occ.get("occ_description", "")
                self._add_occupancy_row(value=f"{val} - {desc}" if desc else val)
        else:
            self._add_occupancy_row()

        self.contractors = data.get("contractors", [])
        self._refresh_contact_tree()

        # Restore IST notes
        for t in list(getattr(self, "ist_notes", [])):
            try: t.master.destroy()
            except Exception: pass
        if hasattr(self, "ist_notes"):
            self.ist_notes.clear()
        saved_notes = data.get("ist_notes", [])
        add_note = getattr(self, "_add_ist_note", None)
        if add_note:
            notes_to_load = saved_notes if saved_notes else [""] * 5
            for text in notes_to_load:
                add_note(text)

        # Restore Personnel Safety / Notifications data
        ps = data.get("personnel_safety", {})
        if ps:
            self.participant_wks_notice_var.set(
                ps.get("participant_wks_notice", NOTIFICATION_DEFAULTS["participant_wks_notice"]))
            self.occupant_hrs_notice_var.set(
                ps.get("occupant_hrs_notice", NOTIFICATION_DEFAULTS["occupant_hrs_notice"]))
            self._noti_participants_text.delete("1.0", "end")
            self._noti_participants_text.insert("1.0", ps.get("noti_to_participants",
                NOTIFICATION_DEFAULTS["noti_to_participants"].replace(
                    "{{participant_wks_notice}}", format_weeks_notice(self.participant_wks_notice_var.get()))))
            self._noti_occupants_text.delete("1.0", "end")
            self._noti_occupants_text.insert("1.0", ps.get("noti_to_occupants",
                NOTIFICATION_DEFAULTS["noti_to_occupants"].replace(
                    "{{occupant_hrs_notice}}", str(self.occupant_hrs_notice_var.get()))))
            self._prop_notice_text.delete("1.0", "end")
            self._prop_notice_text.insert("1.0", ps.get("prop_notice_example",
                NOTIFICATION_DEFAULTS["prop_notice_example"]))

            # Personnel Safety section (5.1-5.4)
            self.building_phase_var.set(ps.get("building_phase", "occupied"))
            self.ppe_required_var.set(ps.get("ppe_required", True))
            self.ppe_items = list(ps.get("ppe_items", PPE_DEFAULTS))
            if hasattr(self, "_refresh_ppe_tree"):
                self._refresh_ppe_tree()
            if hasattr(self, "_update_safety_protocols"):
                self._update_safety_protocols()
            saved_sp = ps.get("safety_protocols", "").strip()
            if saved_sp:
                self._safety_protocols_text.delete("1.0", "end")
                self._safety_protocols_text.insert("1.0", ps.get("safety_protocols"))

            self._special_hazards_text.delete("1.0", "end")
            self._special_hazards_text.insert("1.0", ps.get("special_hazards", SPECIAL_HAZARDS_DEFAULT))
            self._team_communications_text.delete("1.0", "end")
            self._team_communications_text.insert("1.0", ps.get("team_communications", TEAM_COMMUNICATIONS_DEFAULT))
            self._occupant_notification_text.delete("1.0", "end")
            self._occupant_notification_text.insert("1.0", ps.get("occupant_notification", OCCUPANT_NOTIFICATION_DEFAULT))

        fd_widget = getattr(self, "_forms_doc_text", None)
        if fd_widget:
            fd_widget.delete("1.0", "end")
            fd_widget.insert("1.0", data.get("forms_documentation", ""))

        systems_data = data.get("systems", {})
        for sys_info in SYSTEMS:
            key = sys_info["key"]
            ui  = self.sys_ui[key]
            sys = systems_data.get(key, {})
            ui["present"].set(True)
            for w_key, t_key in [("desc_text", "description"), ("int_text", "integrations")]:
                w = ui[w_key]
                default_val = SYSTEM_DEFAULTS.get(key, {}).get(t_key, LOREM)
                w.delete("1.0", "end")
                w.insert("1.0", sys.get(t_key, default_val))
            # Restore matrix data
            # Always restore from saved data (even defaults), using a safe
            # teardown that destroys only the top-level row/tp frames so we
            # never double-destroy child widgets.
            matrix = ui.get("matrix", {})

            def _clear_rows(row_list):
                """Destroy UI frames for each row and empty the list."""
                for r in list(row_list):
                    # _tp_frame is now the same as the main row_f — just destroy it once
                    frame = r.get("_tp_frame")
                    if frame and frame.winfo_exists():
                        frame.destroy()
                    # Also destroy any separator
                    sep = r.get("_sep")
                    if sep and hasattr(sep, "winfo_exists") and sep.winfo_exists():
                        sep.destroy()
                row_list.clear()

            if key == "fire_alarm":
                saved_mon = sys.get("matrix_mon", [])
                add_mon = matrix.get("_add_mon_row")
                existing_mon = matrix.get("_mon", [])
                _clear_rows(existing_mon)
                if add_mon:
                    for row_data in saved_mon:
                        add_mon(row_data.get("integration", ""),
                                row_data.get("normal_mode", ""),
                                row_data.get("fire_mode", ""),
                                row_data.get("tp_normal", ""),
                                row_data.get("tp_fire", ""))
            else:
                saved_rows = sys.get("matrix_rows", [])
                add_row = matrix.get("_add_row")
                existing_rows = matrix.get("_rows", [])
                _clear_rows(existing_rows)
                if add_row:
                    for row_data in saved_rows:
                        add_row(row_data.get("integration", ""),
                                row_data.get("normal_mode", ""),
                                row_data.get("fire_mode", ""),
                                row_data.get("tp_normal", ""),
                                row_data.get("tp_fire", ""))
            if key == "fire_alarm":
                self.fa_devices.clear()
                self.fa_devices.extend(sys.get("fa_initiating_devices", [
                    {"device": "Manual Pull Stations", "area": "at exits"}
                ]))
                self._fa_refresh(skip_preview=True)
                # Supervisory devices
                sup_devs = getattr(self, "fa_supervisory_devices", None)
                if sup_devs is not None:
                    sup_devs.clear()
                    sup_devs.extend(sys.get("fa_supervisory_devices", []))
                    self._fa_sup_refresh(skip_preview=True)
                # Notification devices
                notif_devs = getattr(self, "fa_notification_devices", None)
                if notif_devs is not None:
                    notif_devs.clear()
                    notif_devs.extend(sys.get("fa_notification_devices", [
                        {"device": "Horns"}, {"device": "Strobes"}
                    ]))
                    self._fa_notif_refresh(skip_preview=True)
                for entry, saved_key in [
                    (self.facp_room_entry,  "facp_room"),
                    (self.facp_floor_entry, "facp_floor"),
                ]:
                    entry.delete(0, "end")
                    entry.insert(0, sys.get(saved_key, ""))
                self._clear_faap_rows()
                for panel in sys.get("faap_panels", []):
                    self._add_faap_row(panel.get("room", ""), panel.get("floor", ""))
            if key == "sprinkler" and self._sprinkler_subtype_vars:
                saved_subtypes = sys.get("sprinkler_subtypes", {})
                # Support old list format
                if isinstance(saved_subtypes, list):
                    saved_subtypes = {s: True for s in saved_subtypes}
                # Empty dict (old save) — default Wet Pipe on
                if not saved_subtypes:
                    saved_subtypes = {"Wet Pipe": True}
                for subtype, var in self._sprinkler_subtype_vars.items():
                    var.set(bool(saved_subtypes.get(subtype, False)))
                # Repaint buttons and refresh description text to match
                for subtype, repaint in getattr(self, "_sprinkler_repaints", {}).items():
                    repaint()
                if hasattr(self, "_sprinkler_refresh_text"):
                    self._sprinkler_refresh_text()
                spr_vlv = getattr(self, "sprk_valve_locations", None)
                if spr_vlv is not None:
                    spr_vlv.clear()
                    spr_vlv.extend(sys.get("sprk_valve_locations", []))
                    if hasattr(self, "_refresh_spr_vlv_tree"): self._refresh_spr_vlv_tree()
                    if hasattr(self, "_sprinkler_refresh_text"): self._sprinkler_refresh_text()
            if key == "standpipe":
                stnd_vlv = getattr(self, "stnd_valve_locations", None)
                if stnd_vlv is not None:
                    stnd_vlv.clear()
                    stnd_vlv.extend(sys.get("stnd_valve_locations", []))
                    if hasattr(self, "_refresh_stnd_vlv_tree"): self._refresh_stnd_vlv_tree()
                    if hasattr(self, "_standpipe_refresh_text"): self._standpipe_refresh_text()
            if key == "water_mist":
                wm_areas = getattr(self, "wm_protected_areas", None)
                if wm_areas is not None:
                    wm_areas.clear()
                    wm_areas.extend(sys.get("wm_protected_areas", []))
                    if hasattr(self, "_refresh_wm_area_tree"): self._refresh_wm_area_tree()
                    if hasattr(self, "_watermist_refresh_text"): self._watermist_refresh_text()
            if key == "fire_pump":
                self.fp_room_entry.delete(0, "end"); self.fp_room_entry.insert(0, sys.get("fp_room", ""))
                self.fp_floor_entry.delete(0, "end"); self.fp_floor_entry.insert(0, sys.get("fp_floor", ""))
            if key == "pre_action":
                has_panel = sys.get("pre_action_panel", False)
                pap_var = getattr(self, "pre_action_panel_var", None)
                if pap_var is not None:
                    pap_var.set(has_panel)
                saved_pa_subtypes = sys.get("pre_action_subtypes", {})
                for s, v in getattr(self, "_pre_action_subtype_vars", {}).items():
                    v.set(saved_pa_subtypes.get(s, s == "Pre-Action (Single Interlock)"))
                for repaint in getattr(self, "_pre_action_subtype_repaints", {}).values():
                    repaint()
                pa = getattr(self, "pa_protected_areas", None)
                if pa is not None:
                    pa.clear()
                    pa.extend(sys.get("pa_protected_areas", []))
                    if hasattr(self, "_refresh_pa_tree"): self._refresh_pa_tree()
                cv = getattr(self, "pa_valve_locations", None)
                if cv is not None:
                    cv.clear()
                    cv.extend(sys.get("pa_valve_locations", []))
                    if hasattr(self, "_refresh_cv_tree"): self._refresh_cv_tree()
                # Restore pre_action panel matrix rows
                pap_matrix_rows = getattr(self, "_pap_matrix_rows", [])
                add_pap = getattr(self, "_add_pap_matrix_row", None)
                if add_pap is not None:
                    for row_f in list(pap_matrix_rows):
                        frame = row_f.get("_tp_frame")
                        if frame and frame.winfo_exists():
                            frame.destroy()
                        sep = row_f.get("_sep")
                        if sep and hasattr(sep, "winfo_exists") and sep.winfo_exists():
                            sep.destroy()
                    pap_matrix_rows.clear()
                    for row_data in sys.get("pap_matrix_rows", []):
                        add_pap(row_data.get("integration",""), row_data.get("normal_mode",""),
                                row_data.get("fire_mode",""), row_data.get("tp_normal",""),
                                row_data.get("tp_fire",""))
                # Restore pre_action panel Appendix B rows
                pap_appb_rows = getattr(self, "_pap_appb_rows", [])
                add_pap_appb = getattr(self, "_add_pap_appb_row", None)
                if add_pap_appb is not None:
                    for r in list(pap_appb_rows):
                        for w in r.values():
                            if hasattr(w, "destroy"):
                                try: w.destroy()
                                except Exception: pass
                    pap_appb_rows.clear()
                    for row_data in sys.get("pap_appb_rows", []):
                        add_pap_appb(row_data.get("integration",""), row_data.get("normal",""),
                                     row_data.get("fire",""), row_data.get("notes",""),
                                     row_data.get("sw_type",""), row_data.get("sw_no",""))
                nd_e = getattr(self, "_pap_appb_normal_desc_e", None)
                fd_e = getattr(self, "_pap_appb_fire_desc_e",   None)
                if nd_e:
                    nd_e.delete(0, "end"); nd_e.insert(0, sys.get("pap_appb_normal_desc", ""))
                if fd_e:
                    fd_e.delete(0, "end"); fd_e.insert(0, sys.get("pap_appb_fire_desc", ""))
                if has_panel and hasattr(self, "_refresh_pre_action_panel_tab"):
                    self._refresh_pre_action_panel_tab()
                # Refresh live description preview with restored data
                if hasattr(self, "_update_preac_desc"):
                    self.root.after(50, self._update_preac_desc)
            if key == "generator":
                # Suppress gen served matrix rebuild while we restore saved data
                self._loading_gen_served = True
                self.gen_count_var.set(sys.get("gen_count", 1))
                self.gen_type_var.set(sys.get("gen_type", "diesel"))
                self.gen_class_var.set(sys.get("gen_class", "non-emergency"))
                self.gen_room_entry.delete(0, "end"); self.gen_room_entry.insert(0, sys.get("gen_room", ""))
                self.gen_floor_entry.delete(0, "end"); self.gen_floor_entry.insert(0, sys.get("gen_floor", ""))
                # Restore custom served systems first so checklist rebuild includes them
                saved_custom = sys.get("gen_custom_served", [])
                custom_list = getattr(self, "gen_custom_served", [])
                custom_list.clear()
                import tkinter as tk_mod
                for c in saved_custom:
                    lbl = c.get("label", "")
                    if lbl:
                        var = tk_mod.BooleanVar(value=c.get("checked", True))
                        custom_list.append({"label": lbl, "var": var})
                if hasattr(self, "_refresh_gen_checklist"):
                    self._refresh_gen_checklist()
                saved_served = set(sys.get("gen_served", []))
                for lbl, var in self.gen_served_vars.items():
                    var.set(lbl in saved_served)
                if hasattr(self, "_update_gen_desc"):
                    self._update_gen_desc()
                # Show the served systems tab without triggering matrix rebuild
                def _show_served_tab():
                    tab_id = getattr(self, "_gen_served_tab_id", None)
                    if not tab_id:
                        return
                    gen_class = getattr(self, "gen_class_var", None)
                    if gen_class and gen_class.get() == "emergency":
                        try:
                            if self.notebook.tab(tab_id, "state") == "hidden":
                                self.notebook.add(tab_id, text="Generator Served Systems")
                        except Exception:
                            pass
                    # Always reorder after showing to ensure correct position
                    if hasattr(self, "_reorder_tabs"):
                        self._reorder_tabs()
                self.root.after(50, _show_served_tab)
                # Restore gen served matrix rows (override the auto-added defaults)
                saved_gsm = sys.get("gen_served_matrix_rows", [])
                if saved_gsm:
                    gsm_rows = getattr(self, "_gen_served_matrix_rows", [])
                    add_gsm  = getattr(self, "_add_gen_served_row", None)
                    for r in list(gsm_rows):
                        frame = r.get("_tp_frame")
                        if frame and frame.winfo_exists(): frame.destroy()
                        sep = r.get("_sep")
                        if sep and hasattr(sep, "winfo_exists") and sep.winfo_exists(): sep.destroy()
                    gsm_rows.clear()
                    if add_gsm:
                        for rd in saved_gsm:
                            add_gsm(integ=rd.get("integration",""), normal=rd.get("normal_mode",""),
                                    fire=rd.get("fire_mode",""), tp_normal=rd.get("tp_normal",""),
                                    tp_fire=rd.get("tp_fire",""))
                # Restore Appendix B rows for gen served tab
                saved_gs_appb = sys.get("gs_appb_rows", [])
                add_gs_appb   = getattr(self, "_add_gs_appb_row", None)
                gs_appb_list  = getattr(self, "_gs_appb_rows", [])
                for r in list(gs_appb_list):
                    for wval in r.values():
                        if hasattr(wval, "destroy"):
                            try: wval.destroy()
                            except Exception: pass
                gs_appb_list.clear()
                if add_gs_appb:
                    for rd in saved_gs_appb:
                        add_gs_appb(integration=rd.get("integration",""),
                                    normal=rd.get("normal",""), fire=rd.get("fire",""),
                                    notes=rd.get("notes",""))
                nd_w2 = getattr(self, "_gs_normal_desc_e", None)
                fd_w2 = getattr(self, "_gs_fire_desc_e",   None)
                if nd_w2:
                    nd_w2.delete(0,"end")
                    nd_w2.insert(0, sys.get("gs_normal_desc", APPB_DESC_DEFAULTS.get("generator", ("", ""))[0]))
                if fd_w2:
                    fd_w2.delete(0,"end")
                    fd_w2.insert(0, sys.get("gs_fire_desc", APPB_DESC_DEFAULTS.get("generator", ("", ""))[1]))
                # Done loading — allow gen served matrix to rebuild normally again
                self._loading_gen_served = False
            if key == "elevator":
                self.elev_count_var.set(sys.get("elev_count", 1))
                self.elev_primary_floor.delete(0, "end"); self.elev_primary_floor.insert(0, sys.get("elev_primary_floor", ""))
                self.elev_alternate_floor.delete(0, "end"); self.elev_alternate_floor.insert(0, sys.get("elev_alternate_floor", ""))
                if hasattr(self, "_update_elev_preview"):
                    self._update_elev_preview()
                # Restore elevator action rows
                ea_data    = ui.get("elev_actions", {})
                add_ea_row = ea_data.get("_add_row")
                ea_rows_ui = ea_data.get("_rows", [])
                saved_ea   = sys.get("elev_actions", [])
                if add_ea_row and saved_ea:
                    # Clear existing default rows
                    for r in list(ea_rows_ui):
                        for col_key in ("_drag_handle", "_no_lbl", "action", "desc", "_rm_btn"):
                            w = r.get(col_key)
                            if w and hasattr(w, "winfo_exists") and w.winfo_exists():
                                try: w.destroy()
                                except Exception: pass
                    ea_rows_ui.clear()
                    for entry in saved_ea:
                        r = add_ea_row(
                            action=entry.get("action", ""),
                            desc=entry.get("desc", ""),
                            _auto_desc_key=entry.get("_auto_desc_key"),
                        )
                        if r:
                            ue = entry.get("_user_edited", False)
                            r.get("_user_edited", [False])[0] = ue
            # Restore Appendix B rows
            appb = ui.get("appb", {})
            add_appb = appb.get("_add_row")
            existing_appb = appb.get("_rows", [])
            # Clear existing rows
            for r in list(existing_appb):
                for wval in r.values():
                    if hasattr(wval, "destroy"):
                        try: wval.destroy()
                        except Exception: pass
            existing_appb.clear()
            # Restore desc fields — fall back to APPB_DESC_DEFAULTS if not saved
            nd_w = appb.get("_normal_desc")
            fd_w = appb.get("_fire_desc")
            nd_default, fd_default = APPB_DESC_DEFAULTS.get(key, ("", ""))
            if nd_w:
                nd_w.delete(0, "end")
                nd_w.insert(0, sys.get("appb_normal_desc", "") or nd_default)
            if fd_w:
                fd_w.delete(0, "end")
                fd_w.insert(0, sys.get("appb_fire_desc", "") or fd_default)
            if add_appb:
                for rd in sys.get("appb_rows", []):
                    add_appb(
                        integration=rd.get("integration", ""),
                        sw_type=rd.get("sw_type", ""),
                        sw_no=rd.get("sw_no", ""),
                        normal=rd.get("normal", "PASS"),
                        fire=rd.get("fire", "PASS"),
                        notes=rd.get("notes", ""),
                    )

        # Restore diagram state
        if "diagram" in data:
            self._diag_set_state(data["diagram"])

        # Restore template path
        saved_template = data.get("template_path", "")
        if saved_template and os.path.exists(saved_template):
            self.template_path.set(saved_template)

        # Restore diagram PNG path
        saved_png = data.get("diagram_png_path", "")
        if saved_png and os.path.exists(saved_png):
            self._diag_selected_png = saved_png
            if hasattr(self, "_diag_png_path_var"):
                self._diag_png_path_var.set(saved_png)

        # Restore output path
        saved_output = data.get("output_path", "")
        if saved_output:
            self.output_path.set(saved_output)

        # Ensure all tabs are in the correct order after load
        if hasattr(self, "_reorder_tabs"):
            self.root.after(100, self._reorder_tabs)

    # ============================================================
    #   GENERATE
    # ============================================================


    def generate_report_ui(self):
        template = self.template_path.get()
        if not template:
            messagebox.showwarning("No Template", "Please select a Word template first.")
            return
        # Use saved output path as default, or ask
        default_output = self.output_path.get()
        if default_output:
            output_path = default_output
        else:
            output_path = filedialog.asksaveasfilename(
                title="Save Generated Report As", defaultextension=".docx",
                filetypes=[("Word documents", "*.docx"), ("All files", "*.*")])
        if not output_path:
            return
        # Save the chosen path back
        self.output_path.set(output_path)
        try:
            data = self._gather_data()
            # Use user-selected PNG if available, otherwise auto-export from canvas
            diag_png = None
            selected = getattr(self, "_diag_selected_png", None)
            if selected and os.path.exists(selected):
                diag_png = selected
            elif _PIL_AVAILABLE:
                try:
                    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    tmp.close()
                    self._diag_export_to_path(tmp.name)
                    diag_png = tmp.name
                except Exception:
                    pass
            data["diagram_png"] = diag_png
            generate_report(data, template, output_path)
            # Use win32com to open Word invisibly, update all fields, and save
            # This is the only reliable way to fix page numbers after generation
            _refresh_fields_via_word(output_path)
            messagebox.showinfo("Success", f"Report generated!\n\n{output_path}")
            if messagebox.askyesno("Open File?", "Open the report now?"):
                os.startfile(output_path)
        except Exception as e:
            messagebox.showerror("Generation Error", f"Could not generate report:\n\n{e}")

    # ============================================================
    #   CONTACTS
    # ============================================================

    def open_add_contact(self):
        self._open_contact_dialog()

    def _open_contact_dialog(self, existing=None, index=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Contact" if existing is None else "Edit Contact")
        dialog.geometry("480x240")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Role:").grid(row=0, column=0, sticky="w", pady=5)
        role_var = tk.StringVar(value=existing.get("role", "") if existing else "")
        ttk.Combobox(frame, textvariable=role_var, values=CONTACT_TYPES, width=42).grid(
            row=0, column=1, pady=5, sticky="we")

        for i, (lbl_text, field) in enumerate([
            ("Company:", "company"), ("Phone:", "phone"), ("Name:", "name")
        ], start=1):
            ttk.Label(frame, text=lbl_text).grid(row=i, column=0, sticky="w", pady=5)
            e = ttk.Entry(frame, width=45)
            e.grid(row=i, column=1, pady=5, sticky="we")
            if existing:
                e.insert(0, existing.get(field, ""))
            frame.__dict__[f"_{field}_entry"] = e

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)

        def save():
            d = {
                "role":    role_var.get().strip(),
                "company": frame._company_entry.get().strip(),
                "phone":   frame._phone_entry.get().strip(),
                "name":    frame._name_entry.get().strip(),
            }
            if index is not None:
                self.contractors[index] = d
            else:
                self.contractors.append(d)
            self._refresh_contact_tree()
            dialog.destroy()

        ttk.Button(btn_frame, text="Save",   command=save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
        frame.columnconfigure(1, weight=1)

    def _refresh_contact_tree(self):
        self.contact_tree.delete(*self.contact_tree.get_children())
        for i, c in enumerate(self.contractors):
            self.contact_tree.insert("", "end", iid=str(i),
                values=(c.get("role",""), c.get("company",""),
                        c.get("phone",""), c.get("name","")))

    def edit_contact(self):
        sel = self.contact_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select a contact to edit.")
            return
        self._open_contact_dialog(existing=self.contractors[int(sel[0])], index=int(sel[0]))

    def delete_contact(self):
        sel = self.contact_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select a contact to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this contact?"):
            del self.contractors[int(sel[0])]
            self._refresh_contact_tree()

    # ============================================================
    #   CLEAR ALL
    # ============================================================

    def clear_all(self):
        if not messagebox.askyesno("Confirm Clear", "Clear all data? This cannot be undone."):
            return
        for widget in self.project_fields.values():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, "end")
        self.project_fields["date"].insert(0, datetime.now().strftime("%B %d, %Y"))
        self.project_fields["project_description"].insert(
            0, "Fire Protection Systems Integrated Systems Testing Plan")
        self.project_fields["prepared_by_role"].insert(0, "Fire Protection Consultant")
        self.project_fields["reviewed_by_role"].insert(0, "Principal")
        self.scope_var.set("entire")
        self.scope_entry.configure(state="normal")
        self.scope_entry.delete(0, "end")
        self.scope_entry.configure(state="disabled")
        self.building_desc_text.delete("1.0", "end")
        self._update_building_description()
        # Clear system selectors and hide all system tabs
        for widget in self.sys_selector_inner.winfo_children():
            widget.destroy()
        self.sys_selector_vars = []
        for sys_info in SYSTEMS:
            tab_id = self.sys_tab_frames.get(sys_info["key"])
            if tab_id:
                self.notebook.hide(tab_id)
        # Re-add locked FA row and show FA tab
        fa_row = ttk.Frame(self.sys_selector_inner)
        fa_row.pack(fill="x", pady=2)
        ttk.Label(fa_row, text="Fire Alarm", anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 6))
        fa_var = tk.StringVar(value="Fire Alarm")
        self.sys_selector_vars = [fa_var]
        fa_tab_id = self.sys_tab_frames.get("fire_alarm")
        if fa_tab_id:
            self.notebook.add(fa_tab_id, text="Fire Alarm")
            self.sys_ui["fire_alarm"]["present"].set(True)
        for widget in self.occ_inner.winfo_children():
            widget.destroy()
        self.occ_vars = []
        self._add_occupancy_row()
        # Reset IST notes to 5 blank rows
        for t in list(getattr(self, "ist_notes", [])):
            try: t.master.destroy()
            except Exception: pass
        if hasattr(self, "ist_notes"):
            self.ist_notes.clear()
        add_note = getattr(self, "_add_ist_note", None)
        if add_note:
            for _ in range(5):
                add_note()

        # Reset Personnel Safety / Notifications to defaults
        self.participant_wks_notice_var.set(NOTIFICATION_DEFAULTS["participant_wks_notice"])
        self.occupant_hrs_notice_var.set(NOTIFICATION_DEFAULTS["occupant_hrs_notice"])
        if hasattr(self, "_update_noti_participants"):
            self._update_noti_participants()
        if hasattr(self, "_update_noti_occupants"):
            self._update_noti_occupants()
        self._prop_notice_text.delete("1.0", "end")
        self._prop_notice_text.insert("1.0", NOTIFICATION_DEFAULTS["prop_notice_example"])

        # Reset Personnel Safety (5.1-5.4) to defaults
        self.building_phase_var.set("occupied")
        self.ppe_required_var.set(True)
        self.ppe_items = list(PPE_DEFAULTS)
        if hasattr(self, "_refresh_ppe_tree"):
            self._refresh_ppe_tree()
        if hasattr(self, "_update_ppe_state"):
            self._update_ppe_state()
        if hasattr(self, "_update_safety_protocols"):
            self._update_safety_protocols()
        self._special_hazards_text.delete("1.0", "end")
        self._special_hazards_text.insert("1.0", SPECIAL_HAZARDS_DEFAULT)
        self._team_communications_text.delete("1.0", "end")
        self._team_communications_text.insert("1.0", TEAM_COMMUNICATIONS_DEFAULT)
        self._occupant_notification_text.delete("1.0", "end")
        self._occupant_notification_text.insert("1.0", OCCUPANT_NOTIFICATION_DEFAULT)

        self.contractors = [
            {"role": "Owner/Owner's Representative", "company": "", "name": "", "phone": ""},
            {"role": "Fire Protection Engineer", "company": "ARENCON Inc.", "name": "", "phone": "905-615-1774"},
            {"role": "Integrated Testing Coordinator", "company": "ARENCON Inc.", "name": "", "phone": "905-615-1774"},
        ]
        self._refresh_contact_tree()
        for sys_info in SYSTEMS:
            key = sys_info["key"]
            ui  = self.sys_ui[key]
            ui["present"].set(True)
            for w_key, d_key in [("desc_text", "description"), ("int_text", "integrations")]:
                w = ui[w_key]
                w.delete("1.0", "end")
                w.insert("1.0", SYSTEM_DEFAULTS.get(key, {}).get(d_key, LOREM))
            # Reset matrix to defaults using safe teardown
            matrix = ui.get("matrix", {})

            def _clear_rows_reset(row_list):
                for r in list(row_list):
                    frame = r.get("_tp_frame")
                    if frame and frame.winfo_exists():
                        frame.destroy()
                    sep = r.get("_sep")
                    if sep and hasattr(sep, "winfo_exists") and sep.winfo_exists():
                        sep.destroy()
                row_list.clear()

            if key == "fire_alarm":
                add_mon = matrix.get("_add_mon_row")
                existing_mon = matrix.get("_mon", [])
                _clear_rows_reset(existing_mon)
                if add_mon:
                    mon_tp_defaults = TP_DEFAULTS.get("fire_alarm_monitoring", [])
                    for i, row in enumerate(MONITORING_MATRIX_DEFAULTS):
                        tp = mon_tp_defaults[i] if i < len(mon_tp_defaults) else ("", "")
                        add_mon(*row, tp_normal=tp[0], tp_fire=tp[1])
            else:
                add_row = matrix.get("_add_row")
                existing_rows = matrix.get("_rows", [])
                _clear_rows_reset(existing_rows)
                if add_row:
                    default_rows = MATRIX_DEFAULTS.get(key, [])
                    tp_defaults = TP_DEFAULTS.get(key, [])
                    for i, row in enumerate(default_rows):
                        tp = tp_defaults[i] if i < len(tp_defaults) else ("", "")
                        add_row(*row, tp_normal=tp[0], tp_fire=tp[1])
            if key == "fire_alarm":
                self.fa_devices.clear()
                self.fa_devices.append({"device": "Manual Pull Stations", "area": "at exits"})
                sup_devs = getattr(self, "fa_supervisory_devices", None)
                if sup_devs is not None:
                    sup_devs.clear()
                    self._fa_sup_refresh(skip_preview=True)
                notif_devs = getattr(self, "fa_notification_devices", None)
                if notif_devs is not None:
                    notif_devs.clear()
                    self._fa_notif_refresh(skip_preview=True)
                self._fa_refresh()
                for entry in (self.facp_room_entry, self.facp_floor_entry):
                    entry.delete(0, "end")
                self._clear_faap_rows()
            if key == "sprinkler" and self._sprinkler_subtype_vars:
                for subtype, var in self._sprinkler_subtype_vars.items():
                    var.set(subtype == "Wet Pipe")
                for subtype, repaint in getattr(self, "_sprinkler_repaints", {}).items():
                    repaint()
                if hasattr(self, "_sprinkler_refresh_text"):
                    self._sprinkler_refresh_text()
            if key == "standpipe":
                stnd_vlv = getattr(self, "stnd_valve_locations", None)
                if stnd_vlv is not None:
                    stnd_vlv.clear()
                    if hasattr(self, "_refresh_stnd_vlv_tree"): self._refresh_stnd_vlv_tree()
                    if hasattr(self, "_standpipe_refresh_text"): self._standpipe_refresh_text()
            if key == "water_mist":
                wm_areas = getattr(self, "wm_protected_areas", None)
                if wm_areas is not None:
                    wm_areas.clear()
                    if hasattr(self, "_refresh_wm_area_tree"): self._refresh_wm_area_tree()
                    if hasattr(self, "_watermist_refresh_text"): self._watermist_refresh_text()
            if key == "fire_pump":
                self.fp_room_entry.delete(0, "end"); self.fp_floor_entry.delete(0, "end")
            if key == "generator":
                self.gen_count_var.set(1)
                self.gen_type_var.set("diesel")
                self.gen_class_var.set("non-emergency")
                self.gen_room_entry.delete(0, "end"); self.gen_floor_entry.delete(0, "end")
                for var in self.gen_served_vars.values():
                    var.set(False)
                if hasattr(self, "_update_gen_desc"):
                    self._update_gen_desc()
                if hasattr(self, "_refresh_gen_served_tab"):
                    self._refresh_gen_served_tab()
            if key == "elevator":
                self.elev_count_var.set(1)
                self.elev_primary_floor.delete(0, "end")
                self.elev_alternate_floor.delete(0, "end")
            # Reset Appendix B to defaults
            appb = ui.get("appb", {})
            add_appb = appb.get("_add_row")
            existing_appb = appb.get("_rows", [])
            for r in list(existing_appb):
                for wval in r.values():
                    if hasattr(wval, "destroy"):
                        try: wval.destroy()
                        except Exception: pass
            existing_appb.clear()
            nd_w2 = appb.get("_normal_desc")
            fd_w2 = appb.get("_fire_desc")
            if nd_w2: nd_w2.delete(0, "end")
            if fd_w2: fd_w2.delete(0, "end")
            if add_appb:
                if key == "elevator":
                    self._refresh_elevator_appb_rows()
                else:
                    for name in APPB_DEFAULTS.get(key, []):
                        add_appb(integration=name, normal="", fire="")
        self.current_data_file.set("")


# ============================================================
#   ENTRY POINT
# ============================================================