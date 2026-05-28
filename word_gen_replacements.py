"""
word_gen_replacements.py — Builds the {{placeholder}} -> value dict for the Word template.
Change this file when adding, renaming, or fixing a template placeholder variable.
No docx XML manipulation lives here — pure data transformation.
"""

from defaults import (
    SYSTEM_DEFAULTS, APPB_DESC_DEFAULTS, MATRIX_DEFAULTS, TP_DEFAULTS,
    GEN_SERVED_NORMAL, GEN_SERVED_GENMODE, GEN_SERVED_TP_NORMAL, GEN_SERVED_TP_GENMODE,
)
from constants import SYSTEMS, MONITORING_MATRIX_DEFAULTS


def build_replacements(data):
    pi = data.get("project_info", {})
    fa_sys = data.get("systems", {}).get("fire_alarm", {})

    # FACP/FAAP from fire alarm system data
    facp_room = fa_sys.get("facp_room", "")
    facp_floor = fa_sys.get("facp_floor", "")
    faap_room = fa_sys.get("faap_room", "")
    faap_floor = fa_sys.get("faap_floor", "")

    # Build initiating devices sentence
    fa_devices = fa_sys.get("fa_initiating_devices", [])
    if fa_devices:
        parts = [f"{d['device'].lower()} {d.get('area', '')}".strip()
                 for d in fa_devices]
        if len(parts) == 1:
            fa_sentence = f"{parts[0]}, located throughout the building"
        else:
            fa_sentence = ", ".join(parts[:-1]) + f", and {parts[-1]}, located throughout the building"
    else:
        fa_sentence = "manual pull stations at exits, located throughout the building"

    # Build supervisory devices sentence: "X for the Y, Z for the W, and ..."
    fa_sup_devices = fa_sys.get("fa_supervisory_devices", [])
    if fa_sup_devices:
        sup_parts = [
            f"{d['device'].lower()} for the {d.get('interconnection', '').lower()}".strip()
            for d in fa_sup_devices
        ]
        if len(sup_parts) == 1:
            fa_supervisory_sentence = sup_parts[0]
        elif len(sup_parts) == 2:
            fa_supervisory_sentence = f"{sup_parts[0]} and {sup_parts[1]}"
        else:
            fa_supervisory_sentence = ", ".join(sup_parts[:-1]) + f", and {sup_parts[-1]}"
    else:
        fa_supervisory_sentence = ""

    # Build fa_integrations from selected_systems list
    LABEL_TO_NAME = {
        "Sprinkler": "the sprinkler system",
        "Standpipe": "the standpipe system",
        "Fire Pump": "the fire pump",
        "Generator": "the emergency generator",
        "Maglocks": "electromagnetic locks",
        "Door Holders": "door holders",
        "AHU/Fan": "air handling units",
        "Smoke Dampers": "smoke dampers",
        "Fire Shutters": "fire shutters",
        "Kitchen Hood": "the kitchen hood suppression system",
        "Water Mist": "the water mist system",
        "Elevator": "the elevator recall system",
    }
    selected_systems = data.get("selected_systems", [])
    others = [LABEL_TO_NAME.get(s, s.lower()) for s in selected_systems if s != "Fire Alarm"]
    if others:
        if len(others) == 1:
            fa_integrations = others[0]
        elif len(others) == 2:
            fa_integrations = f"{others[0]} and {others[1]}"
        else:
            fa_integrations = ", ".join(others[:-1]) + f", and {others[-1]}"
    else:
        fa_integrations = "various fire protection and life safety systems"

    # Build matrix placeholder replacements
    systems_data = data.get("systems", {})
    matrix_replacements = {}

    # Monitoring station matrix — stored under fire_alarm
    fa_matrix_mon = systems_data.get("fire_alarm", {}).get("matrix_mon", [])
    if fa_matrix_mon:
        matrix_replacements["mon_integ"] = "\n".join(
            r.get("integration", "") for r in fa_matrix_mon if r.get("integration", "").strip())
        matrix_replacements["mon_integ_normal_mode"] = "\n".join(
            r.get("normal_mode", "") for r in fa_matrix_mon if r.get("normal_mode", "").strip())
        matrix_replacements["mon_integ_fire_mode"] = "\n".join(
            r.get("fire_mode", "") for r in fa_matrix_mon if r.get("fire_mode", "").strip())
    else:
        defs = MONITORING_MATRIX_DEFAULTS
        matrix_replacements["mon_integ"] = "\n".join(r[0] for r in defs)
        matrix_replacements["mon_integ_normal_mode"] = "\n".join(r[1] for r in defs)
        matrix_replacements["mon_integ_fire_mode"] = "\n".join(r[2] for r in defs)

    # Per-system matrix values — combine multiple rows
    for sys_info in SYSTEMS:
        prefix = sys_info.get("matrix_prefix")
        if not prefix:
            continue
        key = sys_info["key"]
        sys_d = systems_data.get(key, {})
        rows = sys_d.get("matrix_rows", [])
        default_rows = MATRIX_DEFAULTS.get(key, [])
        source_rows = rows if rows else [{"integration": r[0], "normal_mode": r[1], "fire_mode": r[2]} for r in
                                         default_rows]
        matrix_replacements[f"{prefix}_integ"] = " / ".join(
            r.get("integration", "").strip() for r in source_rows if r.get("integration", "").strip())
        matrix_replacements[f"{prefix}_integ_normal_mode"] = "\n".join(
            r.get("normal_mode", "").strip() for r in source_rows if r.get("normal_mode", "").strip())
        matrix_replacements[f"{prefix}_integ_fire_mode"] = "\n".join(
            r.get("fire_mode", "").strip() for r in source_rows if r.get("fire_mode", "").strip())

    replacements = {
        "project description": pi.get("project_description", ""),
        "project_description": pi.get("project_description", ""),
        "project_number": pi.get("project_number", ""),
        "iteration": pi.get("version", ""),
        "date": pi.get("date", ""),
        "prep_name": pi.get("prepared_by", ""),
        "prep_quals": pi.get("prepared_by_quals", ""),
        "prep_role": pi.get("prepared_by_role", "Fire Protection Consultant"),
        "rev_name": pi.get("reviewed_by", ""),
        "rev_quals": pi.get("reviewed_by_quals", ""),
        "rev_role": pi.get("reviewed_by_role", "Principal"),
        "building_name": pi.get("building_name", ""),
        "building_address": pi.get("address", ""),
        "building_city": pi.get("building_city", ""),
        "building_province": pi.get("building_province", ""),
        "ag_storeys": pi.get("ag_storeys", ""),
        "bg_storeys": pi.get("bg_storeys", ""),
        "construction_type": pi.get("construction_type", ""),
        "client_company": pi.get("client_company", ""),
        "client_address": pi.get("client_address", ""),
        "client_city": pi.get("client_city", ""),
        "client_province": pi.get("client_province", ""),
        "client_postal": pi.get("client_postal", ""),
        "building_scope": data.get("building_scope", ""),
        "facp_room": facp_room,
        "facp_floor": facp_floor,
        "faap_room": faap_room,
        "faap_floor": faap_floor,
        "fa_initiating_devices": fa_sentence,
        "fa_supervisory_devices": fa_supervisory_sentence,
        "fa_integrations": fa_integrations,
        "fp_room": systems_data.get("fire_pump", {}).get("fp_room", ""),
        "fp_level": systems_data.get("fire_pump", {}).get("fp_floor", ""),
        "gen_room": systems_data.get("generator", {}).get("gen_room", ""),
        "gen_floor": systems_data.get("generator", {}).get("gen_floor", ""),
    }

    # Shared number-to-text map
    NUM_TO_TEXT = {
        1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
        6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
        11: "Eleven", 12: "Twelve",
    }

    # Generator placeholders
    gen_sys = systems_data.get("generator", {})
    gen_count = gen_sys.get("gen_count", 1)
    replacements["gen_count_txt"] = NUM_TO_TEXT.get(gen_count, str(gen_count))
    replacements["gen_count_num"] = str(gen_count)
    replacements["gen_type"] = gen_sys.get("gen_type", "").capitalize()
    # {{gen_class}} is used in AppB/C section headers — must be human-readable
    _gen_class_raw = gen_sys.get("gen_class", "non-emergency")
    replacements["gen_class"] = "Emergency" if _gen_class_raw == "emergency" else "Non-Emergency"
    replacements["generator_s"] = "generator" if gen_count == 1 else "generators"
    replacements["generator_verb"] = "is" if gen_count == 1 else "are"
    replacements["gen_serve_s"] = "serves" if gen_count == 1 else "serve"
    served_labels = gen_sys.get("gen_served", [])
    replacements["system_s"] = "system" if len(served_labels) == 1 else "systems"
    GEN_DISPLAY_BR = {
        "Fire Pump": "Fire Pump", "Maglocks": "Electromagnetic Locks",
        "Door Holders": "Door Holders", "AHU/Fan": "Air Handling Units",
        "Smoke Dampers": "Smoke Dampers", "Fire Shutters": "Fire Shutters",
        "Kitchen Hood": "Kitchen Hood Suppression System", "Elevator": "Elevator",
    }
    # gen_served_list is expanded as separate paragraphs in expand_gen_served_system
    replacements["gen_served_list"] = ""  # placeholder — actual expansion done post replace_all

    # Generator served systems TP (Normal Mode / Generator Mode) — feeds table 8 in template
    emerg_rows = gen_sys.get("gen_served_matrix_rows", [])
    if emerg_rows:
        def _bullets(text):
            lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
            return "\n".join(f"•  {l.lstrip('- •').strip()}" for l in lines)

        replacements["gen_integ_tp_norm_md"] = "\n".join(
            _bullets(r.get("tp_normal", "")) for r in emerg_rows if r.get("tp_normal", "").strip())
        replacements["gen_integ_tp_gen_md"] = "\n".join(
            _bullets(r.get("tp_fire", "")) for r in emerg_rows if r.get("tp_fire", "").strip())
    else:
        replacements["gen_integ_tp_norm_md"] = ""
        replacements["gen_integ_tp_gen_md"] = ""

    # Emergency generator served systems ITP (Appendix B section 3.6)
    gs_appb = gen_sys.get("gs_appb_rows", [])
    gs_nd = gen_sys.get("gs_normal_desc", APPB_DESC_DEFAULTS.get("generator", ("", ""))[0])
    gs_fd = gen_sys.get("gs_fire_desc", APPB_DESC_DEFAULTS.get("generator", ("", ""))[1])
    if gs_appb:
        replacements["emerg_gen_itp_test"] = " / ".join(
            r.get("integration", "").strip() for r in gs_appb if r.get("integration", "").strip())
        replacements["emerg_gen_normal_mode_itp_desc"] = gs_nd
        replacements["emerg_gen_fire_mode_itp_desc"] = gs_fd
        replacements["emerg_gen_itp_notes"] = " / ".join(
            r.get("notes", "").strip() for r in gs_appb if r.get("notes", "").strip())
    else:
        replacements["emerg_gen_itp_test"] = ""
        replacements["emerg_gen_normal_mode_itp_desc"] = ""
        replacements["emerg_gen_fire_mode_itp_desc"] = ""
        replacements["emerg_gen_itp_notes"] = ""

    # Appendix B Section 3.6 — Emergency Generator Power Integrations header placeholders
    # The template row uses {{gen_conns_normal_mode_itp_desc}} and {{gen_conns _fire_mode_itp_desc}}
    # (note: there is a literal space before _fire in the template placeholder name).
    _gen_type_val = gen_sys.get("gen_type", "diesel").lower()
    _is_emergency = gen_sys.get("gen_class", "non-emergency") == "emergency"
    _served_labels = gen_sys.get("gen_served", [])
    if _is_emergency and _served_labels:
        _conns_key = "generator_conns_diesel" if _gen_type_val == "diesel" else "generator_conns_natural_gas"
        _conns_desc = APPB_DESC_DEFAULTS.get(_conns_key, ("", ""))
        replacements["gen_conns_normal_mode_itp_desc"] = _conns_desc[0]
        replacements["gen_conns _fire_mode_itp_desc"] = _conns_desc[1]  # space intentional — matches template typo
    else:
        replacements["gen_conns_normal_mode_itp_desc"] = ""
        replacements["gen_conns _fire_mode_itp_desc"] = ""

    # Generator connected systems matrix placeholders
    GEN_CON_LABEL_MAP = {
        "Fire Alarm": "gen_con_fa",
        "Fire Pump": "gen_con_fpmp",
        "Maglocks": "gen_con_mglck",
        "Door Holders": "gen_con_dhldr",
        "AHU/Fan": "gen_con_ahu",
        "Smoke Dampers": "gen_con_sdmpr",
        "Fire Shutters": "gen_con_fshtr",
        "Kitchen Hood": "gen_con_ktchn",
        "Water Mist": "gen_con_watmst",
        "Elevator": "gen_con_elev",
    }
    gen_served_rows = gen_sys.get("gen_served_matrix_rows", [])
    # Build lookup by served system label
    served_row_lookup = {}
    for r in gen_served_rows:
        integ = r.get("integration", "").strip()
        served_row_lookup[integ] = r
    # GEN_DISPLAY for lookup
    GEN_DISPLAY_CON = {
        "Fire Alarm": "Fire Alarm System", "Fire Pump": "Fire Pump",
        "Maglocks": "Electromagnetic Locks", "Door Holders": "Door Holders",
        "AHU/Fan": "Air Handling Units", "Smoke Dampers": "Smoke Dampers",
        "Fire Shutters": "Fire Shutters", "Kitchen Hood": "Kitchen Hood Suppression System",
        "Water Mist": "Water Mist System",
        "Elevator": "Elevators",
    }
    for lbl, prefix in GEN_CON_LABEL_MAP.items():
        display_name = GEN_DISPLAY_CON.get(lbl, lbl)
        row = served_row_lookup.get(display_name, {})
        replacements[f"{prefix}_normal_mode"] = row.get("normal_mode", "").strip()
        replacements[f"{prefix}_fire_mode"] = row.get("fire_mode", "").strip()

    # Elevator placeholders
    elev_sys = systems_data.get("elevator", {})
    elev_count = elev_sys.get("elev_count", 1)
    replacements["elev_count_txt"] = NUM_TO_TEXT.get(elev_count, str(elev_count))
    replacements["elev_count_num"] = str(elev_count)
    replacements["elevator_s"] = "elevator" if elev_count == 1 else "elevators"
    replacements["elevator_verb"] = "is" if elev_count == 1 else "are"
    replacements["elev_prim_rcl"] = elev_sys.get("elev_primary_floor", "")
    replacements["elev_alt_rcl"] = elev_sys.get("elev_alternate_floor", "")
    # Sprinkler field replacements
    spr_sys = systems_data.get("sprinkler", {})
    # {{sprk_type}}: human-readable type label from selected subtypes
    _spr_subtypes = spr_sys.get("sprinkler_subtypes", {})
    _spr_type_labels = {"Wet Pipe": "wet-pipe", "Dry Pipe": "dry-pipe"}
    _spr_order = [s for s in ("Wet Pipe", "Dry Pipe") if _spr_subtypes.get(s, s == "Wet Pipe")]
    if len(_spr_order) == 1:
        replacements["sprk_type"] = _spr_type_labels.get(_spr_order[0], _spr_order[0].lower())
    elif len(_spr_order) == 2:
        replacements["sprk_type"] = f"{_spr_type_labels[_spr_order[0]]} and {_spr_type_labels[_spr_order[1]]}"
    else:
        replacements["sprk_type"] = "wet-pipe"
    # {{sprk_vlv_locs}}: bulleted list of valve locations
    _spr_vlv = spr_sys.get("sprk_valve_locations", [])
    if _spr_vlv:
        replacements["sprk_vlv_locs"] = "\n".join(f"\t\u2022  {v}" for v in _spr_vlv)
    else:
        replacements["sprk_vlv_locs"] = ""

    # Sprinkler field replacements
    spr_sys = systems_data.get("sprinkler", {})
    _spr_subtypes = spr_sys.get("sprinkler_subtypes", {})
    _spr_order = [s for s in ("Wet Pipe", "Dry Pipe") if _spr_subtypes.get(s, s == "Wet Pipe")]
    _spr_labels = {"Wet Pipe": "wet-pipe", "Dry Pipe": "dry-pipe"}
    if len(_spr_order) == 1:
        replacements["sprk_type"] = _spr_labels.get(_spr_order[0], _spr_order[0].lower())
    elif len(_spr_order) == 2:
        replacements["sprk_type"] = f"{_spr_labels[_spr_order[0]]} and {_spr_labels[_spr_order[1]]}"
    else:
        replacements["sprk_type"] = "wet-pipe"
    _spr_vlv = spr_sys.get("sprk_valve_locations", [])
    replacements["sprk_vlv_locs"] = ("\n".join(f"\t\u2022  {v}" for v in _spr_vlv) if _spr_vlv else "")

    # Pre-Action Sprinkler field replacements
    pa_sys = systems_data.get("pre_action", {})
    _pa_areas = pa_sys.get("pa_protected_areas", [])
    replacements["pa_protected_areas"] = ", ".join(_pa_areas)
    # Build preac_protec_areas string and verb for Word doc
    if len(_pa_areas) == 1:
        replacements["preac_protec_areas"] = _pa_areas[0]
        replacements["preac_area_verb"] = "is"
    elif len(_pa_areas) == 2:
        replacements["preac_protec_areas"] = f"{_pa_areas[0]} and {_pa_areas[1]}"
        replacements["preac_area_verb"] = "are"
    elif len(_pa_areas) > 2:
        replacements["preac_protec_areas"] = ", ".join(_pa_areas[:-1]) + f", and {_pa_areas[-1]}"
        replacements["preac_area_verb"] = "are"
    else:
        replacements["preac_protec_areas"] = ""
        replacements["preac_area_verb"] = "is"
    replacements["pa_valve_locations"] = ", ".join(pa_sys.get("pa_valve_locations", []))

    # {{preac_pan_or_fa}}: 'Pre-Action Panel' when a designated panel is present, else 'Fire Alarm'
    _has_panel = pa_sys.get("pre_action_panel", False)
    replacements["preac_pan_or_fa"] = "Pre-Action Panel" if _has_panel else "Fire Alarm"

    # Water mist protected areas + verb
    wm_sys = systems_data.get("water_mist", {})
    _wm_areas = wm_sys.get("wm_protected_areas", [])
    if len(_wm_areas) == 1:
        replacements["watmist_protec_area"] = _wm_areas[0]
        replacements["watmist_area_verb"] = "is"
    elif len(_wm_areas) == 2:
        replacements["watmist_protec_area"] = f"{_wm_areas[0]} and {_wm_areas[1]}"
        replacements["watmist_area_verb"] = "are"
    elif len(_wm_areas) > 2:
        replacements["watmist_protec_area"] = ", ".join(_wm_areas[:-1]) + f", and {_wm_areas[-1]}"
        replacements["watmist_area_verb"] = "are"
    else:
        replacements["watmist_protec_area"] = ""
        replacements["watmist_area_verb"] = "is"

    # pre_pan / pre_sys matrix + ITP desc + gen_con placeholders
    # (pre_pan = Fire Alarm <-> Pre-Action Panel; pre_sys = Panel <-> Pre-Action Sprinkler)
    _pa_rows = pa_sys.get("matrix_rows", [])
    if not _pa_rows:
        _pa_rows = [{"integration": r[0], "normal_mode": r[1], "fire_mode": r[2]}
                    for r in MATRIX_DEFAULTS.get("pre_action", [])]
    _pap_rows = pa_sys.get("pap_matrix_rows", [])
    if not _pap_rows:
        _pap_rows = [{"integration": r[0], "normal_mode": r[1], "fire_mode": r[2]}
                     for r in MATRIX_DEFAULTS.get("pre_action_panel", [])]
    replacements["pre_pan_integ"] = " / ".join(
        r.get("integration", "").strip() for r in _pap_rows if r.get("integration", "").strip())
    replacements["pre_pan_normal_mode"] = "\n".join(
        r.get("normal_mode", "").strip() for r in _pap_rows if r.get("normal_mode", "").strip())
    replacements["pre_pan_fire_mode"] = "\n".join(
        r.get("fire_mode", "").strip() for r in _pap_rows if r.get("fire_mode", "").strip())
    replacements["pre_sys_integ"] = " / ".join(
        r.get("integration", "").strip() for r in _pa_rows if r.get("integration", "").strip())
    replacements["pre_sys_normal_mode"] = "\n".join(
        r.get("normal_mode", "").strip() for r in _pa_rows if r.get("normal_mode", "").strip())
    replacements["pre_sys_fire_mode"] = "\n".join(
        r.get("fire_mode", "").strip() for r in _pa_rows if r.get("fire_mode", "").strip())
    # Appendix B ITP description placeholders
    _appb_pap = APPB_DESC_DEFAULTS.get("pre_action_panel", ("", ""))
    _appb_pa = APPB_DESC_DEFAULTS.get("pre_action", ("", ""))
    replacements["pre_pan_normal_mode_itp_desc"] = pa_sys.get("pap_appb_normal_desc", "").strip() or _appb_pap[0]
    replacements["pre_pan_fire_mode_itp_desc"] = pa_sys.get("pap_appb_fire_desc", "").strip() or _appb_pap[1]
    replacements["pre_sys_normal_mode_itp_desc"] = pa_sys.get("appb_normal_desc", "").strip() or _appb_pa[0]
    replacements["pre_sys_fire_mode_itp_desc"] = pa_sys.get("appb_fire_desc", "").strip() or _appb_pa[1]
    # Generator emergency power for pre_pan and pre_sys rows
    _gen_con = {r.get("integration", "").strip(): r
                for r in systems_data.get("generator", {}).get("gen_served_matrix_rows", [])}
    _ppan = _gen_con.get("Pre-Action Sprinkler System Panel", {})
    _psys = _gen_con.get("Pre-Action Sprinkler System", {})
    replacements["gen_con_pre_pan_normal_mode"] = _ppan.get("normal_mode", "").strip()
    replacements["gen_con_pre_pan_fire_mode"] = _ppan.get("fire_mode", "").strip()
    replacements["gen_con_pre_sys_normal_mode"] = _psys.get("normal_mode", "").strip()
    replacements["gen_con_pre_sys_fire_mode"] = _psys.get("fire_mode", "").strip()

    return replacements