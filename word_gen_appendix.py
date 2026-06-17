"""
word_gen_appendix.py — Appendix B (IST Protocols with results) and Appendix C
(blank IST form) table population, plus the pre-generation template-row saver.
Change this file for bugs in AppB/C section headers, row numbering, checkbox
state, or pre-action row handling.

pre_action is handled as TWO fully dynamic sections (pre_pan + pre_sys),
identical in mechanism to sprinkler, standpipe, etc.
  pre_pan: Fire Alarm / Pre-Action Panel   — uses pap_appb_rows
  pre_sys: Pre-Action Panel / Pre-Action Sprinkler System — uses appb_rows
"""

from copy import deepcopy
from lxml import etree

from defaults import APPB_DESC_DEFAULTS
from constants import SYSTEMS


def populate_appendix_b_table(doc, data):
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"

    systems_data = data.get("systems", {})

    # Locate the IST Protocols table
    appb_table = None
    for table in doc.tables:
        full = " ".join(c.text for row in table.rows for c in row.cells)
        if "Integrated Systems Testing Protocols" in full and "mon_itp" in full:
            appb_table = table
            break
    if appb_table is None:
        print("[AppB] ERROR: table not found (mon_itp not in any table after replace_all)")
        return

    tbl_el = appb_table._tbl
    all_rows = list(appb_table.rows)
    if len(all_rows) < 5:
        print(f"[AppB] ERROR: only {len(all_rows)} rows — too few")
        return

    print(f"[AppB] found table with {len(all_rows)} rows")

    # Save template rows for cloning BEFORE deleting data rows.
    # Row 3 = section header template, Row 4 = data row (no sw), Row 6 = data row (sw/sprinkler)
    template_section_tr = deepcopy(all_rows[3]._tr)
    template_data_tr    = deepcopy(all_rows[4]._tr)
    template_data_tr_sw = deepcopy(all_rows[6]._tr) if len(all_rows) > 6 else deepcopy(all_rows[4]._tr)

    for row in all_rows[3:]:
        tbl_el.remove(row._tr)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _set_cell_plain_text(tc, text):
        paras = tc.findall(f"{W}p")
        if not paras:
            return
        p = paras[0]
        for child in list(p):
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag in ("r", "sdt", "hyperlink", "ins", "del"):
                p.remove(child)
        r_el = etree.SubElement(p, f"{W}r")
        t_el = etree.SubElement(r_el, f"{W}t")
        t_el.text = text or ""
        if text:
            t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    def _make_section_header_row(section_label, sys_label, normal_desc, fire_desc,
                                 full_header=None):
        """
        Clone the template section-header row.
        full_header: if provided, used verbatim as the bold first line
                     (for pre_sys which has a non-standard title format).
        Otherwise builds: "{section_label}: {sys_label} / Fire Alarm Integrations:"
        """
        new_tr = deepcopy(template_section_tr)
        tcs = new_tr.findall(f".//{W}tc")
        if not tcs:
            return new_tr
        paras = tcs[0].findall(f"{W}p")
        header_text = full_header if full_header else f"{section_label}: {sys_label} / Fire Alarm Integrations:"
        normal_text = f"Normal Mode: {normal_desc}"
        fire_text   = f"Fire Mode: {fire_desc}"

        def _set_para_text(p, txt, bold=False):
            for child in list(p):
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag in ("r", "sdt", "hyperlink"):
                    p.remove(child)
            r_el = etree.SubElement(p, f"{W}r")
            if bold:
                rPr = etree.SubElement(r_el, f"{W}rPr")
                etree.SubElement(rPr, f"{W}b")
            t_el = etree.SubElement(r_el, f"{W}t")
            t_el.text = txt
            t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

        if len(paras) >= 3:
            _set_para_text(paras[0], header_text, bold=True)
            _set_para_text(paras[1], normal_text)
            _set_para_text(paras[2], fire_text)
        elif paras:
            _set_para_text(paras[0], f"{header_text}\n{normal_text}\n{fire_text}", bold=True)
        return new_tr

    def _set_checkbox_state(sdt_el, checked):
        content = sdt_el.find(f"{W}sdtContent")
        if content is None:
            return
        for r in content.findall(f".//{W}r"):
            for t in r.findall(f"{W}t"):
                t.text = "\u2612" if checked else "\u2610"

    def _make_data_row(row_num, integration_name, normal_result, fire_result,
                       notes_text, sw_type="", sw_no="", has_sw=False):
        new_tr = deepcopy(template_data_tr_sw if has_sw else template_data_tr)
        tcs = new_tr.findall(f".//{W}tc")
        if len(tcs) < 5:
            return new_tr

        _set_cell_plain_text(tcs[0], str(row_num))

        lines = [l for l in integration_name.split("\n") if l.strip()] or [integration_name]
        _set_cell_plain_text(tcs[1], lines[0])
        for extra_line in lines[1:]:
            paras1 = tcs[1].findall(f"{W}p")
            if paras1:
                new_p = deepcopy(paras1[0])
                for r in new_p.findall(f".//{W}r"):
                    for t in r.findall(f"{W}t"):
                        t.text = extra_line
                tcs[1].append(new_p)

        if has_sw:
            type_str = sw_type.strip() if sw_type else ""
            no_str   = sw_no.strip()   if sw_no   else ""
            sw_reps = [
                ("{{sprk_itp_sw_type}}",  f"{type_str} No:"),
                ("{{stand_itp_sw_type}}", f"{type_str} No:"),
                ("{{sprk_itp_sw_no}}",    no_str),
                ("{{stand_itp_sw_no}}",   no_str),
            ]
            for p_el in list(tcs[2].findall(f"{W}p")) + list(tcs[3].findall(f"{W}p")):
                all_runs = p_el.findall(f".//{W}r")
                if not all_runs:
                    continue
                joined = "".join(t.text or "" for r in all_runs for t in r.findall(f"{W}t"))
                replaced = joined
                for ph, val in sw_reps:
                    replaced = replaced.replace(ph, val)
                if replaced == joined:
                    continue
                t_els_r0 = all_runs[0].findall(f"{W}t")
                if t_els_r0:
                    t_els_r0[0].text = replaced
                    t_els_r0[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                    for t in t_els_r0[1:]:
                        all_runs[0].remove(t)
                p_el_parent = all_runs[0].getparent()
                for r in all_runs[1:]:
                    if r.getparent() is p_el_parent:
                        p_el_parent.remove(r)
            cb_paras = tcs[3].findall(f"{W}p")[1:3]
        else:
            cb_paras = tcs[3].findall(f"{W}p")

        for para_idx, result in enumerate([normal_result, fire_result]):
            if para_idx >= len(cb_paras):
                break
            sdts = cb_paras[para_idx].findall(f"{W}sdt")
            if len(sdts) < 3:
                continue
            _set_checkbox_state(sdts[0], result == "PASS")
            _set_checkbox_state(sdts[1], result == "FAIL")
            _set_checkbox_state(sdts[2], result == "NT")

        _set_cell_plain_text(tcs[4], notes_text)

        for tc in tcs:
            paras = tc.findall(f"{W}p")
            for p in reversed(paras[1:]):
                if "".join(t.text or "" for t in p.findall(f".//{W}t")).strip() == "" \
                        and not p.findall(f".//{W}sdt"):
                    tc.remove(p)
                else:
                    break
        return new_tr

    # ── Section labels ──────────────────────────────────────────────────────────
    _gen_class_raw_b = systems_data.get("generator", {}).get("gen_class", "non-emergency")
    _gen_class_display_b = "Emergency" if _gen_class_raw_b == "emergency" else "Non-Emergency"

    SYS_LABELS = {
        "fire_alarm":   "Monitoring Station",
        "sprinkler":    "Sprinkler System",
        "standpipe":    "Standpipe System",
        "fire_pump":    "Fire Pump",
        "generator":    f"{_gen_class_display_b} Generator",
        "maglock":      "Electromagnetic Lock",
        "door_holders": "Door Holder",
        "ahu":          "Air Handling Unit",
        "smoke_dampers":"Smoke Dampers",
        "fire_shutters":"Fire Shutter",
        "kitchen_hood": "Kitchen Hood Suppression System",
        "elevator":     "Elevator",
    }

    # ── Build a flat ordered list of sections to generate ──────────────────────
    # pre_action expands to TWO entries (pre_pan + pre_sys) so section numbers
    # are assigned sequentially with no offset arithmetic needed.
    present_keys = ["fire_alarm"] + [
        sys_info["key"] for sys_info in SYSTEMS
        if sys_info["key"] != "fire_alarm"
           and systems_data.get(sys_info["key"], {}).get("present", False)
    ]

    # ordered_sections: list of dicts describing each section to emit
    ordered_sections = []
    sec_num = 1
    pa_sys = systems_data.get("pre_action", {})
    preac_pan_or_fa = ("Pre-Action Panel"
                       if pa_sys.get("pre_action_panel", False)
                       else "Fire Alarm")

    for key in present_keys:
        sys_d = systems_data.get(key, {})
        if key == "pre_action":
            # pre_pan only exists when a designated pre-action panel is present
            if sys_d.get("pre_action_panel", False):
                pap_nd = sys_d.get("pap_appb_normal_desc", "").strip() or \
                         APPB_DESC_DEFAULTS.get("pre_action_panel", ("", ""))[0]
                pap_fd = sys_d.get("pap_appb_fire_desc", "").strip() or \
                         APPB_DESC_DEFAULTS.get("pre_action_panel", ("", ""))[1]
                ordered_sections.append({
                    "sec_num":    sec_num,
                    "key":        "pre_pan",
                    "appb_rows":  sys_d.get("pap_appb_rows", []),
                    "normal_desc": pap_nd,
                    "fire_desc":   pap_fd,
                    "full_header": f"ITP Section 3.{sec_num}: Pre-Action Panel / Fire Alarm Integrations:",
                    "has_sw":      False,
                })
                sec_num += 1
            # pre_sys section
            pa_nd = sys_d.get("appb_normal_desc", "").strip() or \
                    APPB_DESC_DEFAULTS.get("pre_action", ("", ""))[0]
            pa_fd = sys_d.get("appb_fire_desc", "").strip() or \
                    APPB_DESC_DEFAULTS.get("pre_action", ("", ""))[1]
            ordered_sections.append({
                "sec_num":    sec_num,
                "key":        "pre_sys",
                "appb_rows":  sys_d.get("appb_rows", []),
                "normal_desc": pa_nd,
                "fire_desc":   pa_fd,
                "full_header": f"ITP Section 3.{sec_num}: Pre-Action Sprinkler System / {preac_pan_or_fa} Integrations:",
                "has_sw":      True,
            })
            sec_num += 1
        else:
            ordered_sections.append({
                "sec_num":    sec_num,
                "key":        key,
                "appb_rows":  sys_d.get("appb_rows" if key != "fire_alarm" else "appb_rows", []),
                "normal_desc": None,  # computed below
                "fire_desc":   None,
                "full_header": None,
                "has_sw":      key in ("sprinkler", "standpipe"),
            })
            sec_num += 1

    global_row_num = 1

    for sec in ordered_sections:
        key       = sec["key"]
        appb_rows = sec["appb_rows"]
        sys_d     = systems_data.get(key, {}) if key not in ("pre_pan", "pre_sys") \
                    else systems_data.get("fire_alarm" if key == "fire_alarm" else "pre_action", {})
        if key == "fire_alarm":
            sys_d = systems_data.get("fire_alarm", {})
            appb_rows = sys_d.get("appb_rows", [])

        if not appb_rows:
            print(f"[AppB] sec 3.{sec['sec_num']} ({key}): no appb_rows — skipping data rows")
            continue

        section_label = f"ITP Section 3.{sec['sec_num']}"

        # Resolve normal/fire desc
        normal_desc = sec["normal_desc"]
        fire_desc   = sec["fire_desc"]
        if normal_desc is None or fire_desc is None:
            real_sys_d = systems_data.get(key, {})
            nd = real_sys_d.get("appb_normal_desc", "").strip()
            fd = real_sys_d.get("appb_fire_desc",   "").strip()
            if not nd or not fd:
                matrix_rows = real_sys_d.get("matrix_mon" if key == "fire_alarm" else "matrix_rows", [])
                if matrix_rows:
                    nd = nd or matrix_rows[0].get("normal_mode", "")[:150]
                    fd = fd or matrix_rows[0].get("fire_mode",   "")[:150]
                else:
                    nd = nd or "Review system installation and confirm normal operation."
                    fd = fd or "Cause associated condition and confirm correct system response."
            normal_desc = nd
            fire_desc   = fd

        print(f"[AppB] sec 3.{sec['sec_num']} ({key}): {len(appb_rows)} rows, has_sw={sec['has_sw']}")

        tbl_el.append(_make_section_header_row(
            section_label,
            SYS_LABELS.get(key, key),
            normal_desc[:150],
            fire_desc[:150],
            full_header=sec["full_header"],
        ))

        for row_data in appb_rows:
            data_tr = _make_data_row(
                row_num=global_row_num,
                integration_name=row_data.get("integration", ""),
                normal_result=row_data.get("normal", ""),
                fire_result=row_data.get("fire", ""),
                notes_text=row_data.get("notes", ""),
                sw_type=row_data.get("sw_type", ""),
                sw_no=row_data.get("sw_no", ""),
                has_sw=sec["has_sw"],
            )
            tbl_el.append(data_tr)
            global_row_num += 1

    # ── Emergency Generator Power Integrations ────────────────────────────────
    gen_sys_d   = systems_data.get("generator", {})
    gen_present = gen_sys_d.get("present", False)
    gen_class   = gen_sys_d.get("gen_class", "non-emergency")
    served_labels = gen_sys_d.get("gen_served", [])

    GEN_DISPLAY_36 = {
        "Fire Alarm":   "Fire Alarm System", "Fire Pump":  "Fire Pump",
        "Maglocks":     "Electromagnetic Locks", "Door Holders": "Door Holders",
        "AHU/Fan":      "Air Handling Units",    "Smoke Dampers": "Smoke Dampers",
        "Fire Shutters":"Fire Shutters",          "Kitchen Hood":  "Kitchen Hood Suppression System",
        "Elevator":     "Elevator",
    }

    if gen_present and gen_class == "emergency" and served_labels:
        gen_count = gen_sys_d.get("gen_count", 1)
        gen_type  = gen_sys_d.get("gen_type", "diesel").lower()
        _conns_key  = "generator_conns_diesel" if gen_type == "diesel" else "generator_conns_natural_gas"
        _nd, _fd    = APPB_DESC_DEFAULTS.get(_conns_key, ("", ""))
        gen_sec_num = sec_num
        print(f"[AppB] Emergency gen power section: 3.{gen_sec_num}")
        tbl_el.append(_make_section_header_row(
            f"ITP Section 3.{gen_sec_num}",
            "Emergency Generator Power Integrations",
            _nd[:150], _fd[:150],
            full_header=f"ITP Section 3.{gen_sec_num}: Emergency Generator Power Integrations:",
        ))
        for gen_num in range(1, gen_count + 1):
            tbl_el.append(_make_data_row(global_row_num, f"Generator #{gen_num} Startup", "", "", "", has_sw=False))
            global_row_num += 1
            for lbl in served_labels:
                device_name = GEN_DISPLAY_36.get(lbl, lbl)
                tbl_el.append(_make_data_row(global_row_num,
                                             f"Generator #{gen_num} {device_name} Emergency Power",
                                             "", "", "", has_sw=False))
                global_row_num += 1


def populate_appendix_c_table(doc, data, template_rows=None):
    """Appendix C — blank integrated testing form (same structure as B, no results)."""

    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"

    systems_data = data.get("systems", {})

    # Locate the Appendix C IST table (3rd table after paragraph "Appendix C")
    appc_table = None
    body = doc.element.body
    found_appc = False
    tables_after = 0
    for elem in list(body):
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "p":
            txt = "".join(t.text or "" for t in elem.iter(f"{{{WNS}}}t")).strip()
            if txt == "Appendix C":
                found_appc = True
        elif tag == "tbl" and found_appc:
            tables_after += 1
            if tables_after == 3:
                for t in doc.tables:
                    if t._tbl is elem:
                        appc_table = t
                        break
                break
    if appc_table is None:
        print("[AppC] ERROR: table not found")
        return

    tbl_el  = appc_table._tbl
    all_rows = list(appc_table.rows)
    if len(all_rows) < 5:
        return

    print(f"[AppC] found table with {len(all_rows)} rows")

    # Template rows — use pre-saved (pre-replace_all) rows when available
    if template_rows:
        template_section_tr = deepcopy(template_rows["section_tr"])
        template_data_tr    = deepcopy(template_rows["data_tr"])
        template_data_tr_sw = deepcopy(template_rows["data_tr_sw"])
    else:
        template_section_tr = deepcopy(all_rows[3]._tr)
        template_data_tr    = deepcopy(all_rows[4]._tr)
        template_data_tr_sw = deepcopy(all_rows[6]._tr) if len(all_rows) > 6 else deepcopy(all_rows[4]._tr)

    for row in all_rows[3:]:
        tbl_el.remove(row._tr)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _set_cell_text(tc, text):
        paras = tc.findall(f"{W}p")
        if not paras:
            return
        p = paras[0]
        for child in list(p):
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag in ("r", "sdt", "hyperlink", "ins", "del"):
                p.remove(child)
        r_el = etree.SubElement(p, f"{W}r")
        t_el = etree.SubElement(r_el, f"{W}t")
        t_el.text = text or ""
        if text:
            t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    def _make_section_header(section_label, sys_label, normal_desc, fire_desc,
                             full_header=None):
        new_tr = deepcopy(template_section_tr)
        tcs = new_tr.findall(f".//{W}tc")
        if not tcs:
            return new_tr
        paras = tcs[0].findall(f"{W}p")
        header_text = full_header if full_header else f"{section_label}: {sys_label} / Fire Alarm Integrations:"
        normal_text = f"Normal Mode: {normal_desc}"
        fire_text   = f"Fire Mode: {fire_desc}"

        def _set_para(p, txt, bold=False):
            for child in list(p):
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag in ("r", "sdt", "hyperlink"):
                    p.remove(child)
            r_el = etree.SubElement(p, f"{W}r")
            if bold:
                rPr = etree.SubElement(r_el, f"{W}rPr")
                etree.SubElement(rPr, f"{W}b")
            t_el = etree.SubElement(r_el, f"{W}t")
            t_el.text = txt
            t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

        if len(paras) >= 3:
            _set_para(paras[0], header_text, bold=True)
            _set_para(paras[1], normal_text)
            _set_para(paras[2], fire_text)
        elif paras:
            _set_para(paras[0], f"{header_text}\n{normal_text}\n{fire_text}", bold=True)
        return new_tr

    def _make_data_row_c(row_num, integration_name, has_sw=False, sw_type="", sw_no=""):
        new_tr = deepcopy(template_data_tr_sw if has_sw else template_data_tr)
        tcs = new_tr.findall(f".//{W}tc")
        if not tcs:
            return new_tr

        _set_cell_text(tcs[0], str(row_num))
        _set_cell_text(tcs[1], integration_name)

        if has_sw and len(tcs) > 2:
            sw_reps = [
                ("{{sprk_itp_sw_type}}",  f"{sw_type} No:" if sw_type else "SV No:"),
                ("{{stand_itp_sw_type}}", f"{sw_type} No:" if sw_type else "SV No:"),
                ("{{sprk_itp_sw_no}}",    sw_no),
                ("{{stand_itp_sw_no}}",   sw_no),
            ]
            for tc in [tcs[2], tcs[3]]:
                for p_el in tc.findall(f"{W}p"):
                    all_runs = p_el.findall(f".//{W}r")
                    if not all_runs:
                        continue
                    joined = "".join(t.text or "" for r in all_runs for t in r.findall(f"{W}t"))
                    replaced = joined
                    for ph, val in sw_reps:
                        replaced = replaced.replace(ph, val)
                    if replaced == joined:
                        continue
                    t_els = all_runs[0].findall(f"{W}t")
                    if t_els:
                        t_els[0].text = replaced
                        t_els[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        for t in t_els[1:]:
                            all_runs[0].remove(t)
                    for r in all_runs[1:]:
                        for t in r.findall(f"{W}t"):
                            t.text = ""

        # All checkboxes unchecked
        for tc in tcs[2:]:
            for sdt in tc.findall(f".//{W}sdt"):
                content_el = sdt.find(f"{W}sdtContent")
                if content_el is None:
                    continue
                for t in content_el.findall(f".//{W}t"):
                    if t.text in ("\u2612", "\u2611"):
                        t.text = "\u2610"

        # Clear notes cell
        if len(tcs) >= 5:
            for p in tcs[-1].findall(f"{W}p"):
                for r in p.findall(f"{W}r"):
                    for t in r.findall(f"{W}t"):
                        t.text = ""

        return new_tr

    # ── Build sections (same flat-list approach as AppB) ──────────────────────
    present_keys = ["fire_alarm"] + [
        sys_info["key"] for sys_info in SYSTEMS
        if sys_info["key"] != "fire_alarm"
           and systems_data.get(sys_info["key"], {}).get("present", False)
    ]

    pa_sys = systems_data.get("pre_action", {})
    preac_pan_or_fa = ("Pre-Action Panel"
                       if pa_sys.get("pre_action_panel", False)
                       else "Fire Alarm")

    _gen_class_raw_c = systems_data.get("generator", {}).get("gen_class", "non-emergency")
    _gen_class_display_c = "Emergency" if _gen_class_raw_c == "emergency" else "Non-Emergency"

    SYS_LABELS_C = {
        "fire_alarm":   "Monitoring Station",   "sprinkler":    "Sprinkler System",
        "standpipe":    "Standpipe System",      "fire_pump":    "Fire Pump",
        "generator":    f"{_gen_class_display_c} Generator",   "maglock":      "Electromagnetic Lock",
        "door_holders": "Door Holder",           "ahu":          "Air Handling Unit",
        "smoke_dampers":"Smoke Dampers",         "fire_shutters":"Fire Shutter",
        "kitchen_hood": "Kitchen Hood Suppression System", "elevator": "Elevator",
    }

    ordered_sections = []
    sec_num = 1
    for key in present_keys:
        sys_d = systems_data.get(key, {})
        if key == "pre_action":
            if sys_d.get("pre_action_panel", False):
                pap_nd = sys_d.get("pap_appb_normal_desc", "").strip() or \
                         APPB_DESC_DEFAULTS.get("pre_action_panel", ("", ""))[0]
                pap_fd = sys_d.get("pap_appb_fire_desc", "").strip() or \
                         APPB_DESC_DEFAULTS.get("pre_action_panel", ("", ""))[1]
                ordered_sections.append({
                    "sec_num": sec_num, "key": "pre_pan",
                    "appb_rows": sys_d.get("pap_appb_rows", []),
                    "normal_desc": pap_nd, "fire_desc": pap_fd,
                    "full_header": f"ITP Section 3.{sec_num}: Pre-Action Panel / Fire Alarm Integrations:",
                    "has_sw": False,
                })
                sec_num += 1
            pa_nd = sys_d.get("appb_normal_desc", "").strip() or \
                    APPB_DESC_DEFAULTS.get("pre_action", ("", ""))[0]
            pa_fd = sys_d.get("appb_fire_desc", "").strip() or \
                    APPB_DESC_DEFAULTS.get("pre_action", ("", ""))[1]
            ordered_sections.append({
                "sec_num": sec_num, "key": "pre_sys",
                "appb_rows": sys_d.get("appb_rows", []),
                "normal_desc": pa_nd, "fire_desc": pa_fd,
                "full_header": f"ITP Section 3.{sec_num}: Pre-Action Sprinkler System / {preac_pan_or_fa} Integrations:",
                "has_sw": True,
            })
            sec_num += 1
        else:
            ordered_sections.append({
                "sec_num": sec_num, "key": key,
                "appb_rows": sys_d.get("appb_rows", []),
                "normal_desc": None, "fire_desc": None,
                "full_header": None,
                "has_sw": key in ("sprinkler", "standpipe"),
            })
            sec_num += 1

    global_row_num = 1

    for sec in ordered_sections:
        key       = sec["key"]
        appb_rows = sec["appb_rows"]
        if not appb_rows:
            continue

        section_label = f"ITP Section 3.{sec['sec_num']}"
        normal_desc   = sec["normal_desc"]
        fire_desc     = sec["fire_desc"]
        if normal_desc is None or fire_desc is None:
            real_sys_d = systems_data.get(key, {})
            nd = real_sys_d.get("appb_normal_desc", "").strip()
            fd = real_sys_d.get("appb_fire_desc",   "").strip()
            if not nd or not fd:
                matrix_rows = real_sys_d.get("matrix_mon" if key == "fire_alarm" else "matrix_rows", [])
                nd = nd or (matrix_rows[0].get("normal_mode", "")[:150] if matrix_rows else
                            "Review system installation and confirm normal operation.")
                fd = fd or (matrix_rows[0].get("fire_mode",   "")[:150] if matrix_rows else
                            "Cause associated condition and confirm correct system response.")
            normal_desc, fire_desc = nd, fd

        tbl_el.append(_make_section_header(
            section_label, SYS_LABELS_C.get(key, key),
            normal_desc[:150], fire_desc[:150],
            full_header=sec["full_header"],
        ))

        for row_data in appb_rows:
            tbl_el.append(_make_data_row_c(
                global_row_num, row_data.get("integration", ""),
                has_sw=sec["has_sw"],
                sw_type=row_data.get("sw_type", ""),
                sw_no=row_data.get("sw_no", ""),
            ))
            global_row_num += 1

    # Emergency generator
    gen_sys_d   = systems_data.get("generator", {})
    gen_present = gen_sys_d.get("present", False)
    gen_class   = gen_sys_d.get("gen_class", "non-emergency")
    served_labels = gen_sys_d.get("gen_served", [])
    GEN_DISPLAY_C = {
        "Fire Alarm":"Fire Alarm System","Fire Pump":"Fire Pump",
        "Maglocks":"Electromagnetic Locks","Door Holders":"Door Holders",
        "AHU/Fan":"Air Handling Units","Smoke Dampers":"Smoke Dampers",
        "Fire Shutters":"Fire Shutters","Kitchen Hood":"Kitchen Hood Suppression System",
        "Elevator":"Elevator",
    }
    if gen_present and gen_class == "emergency" and served_labels:
        gen_count = gen_sys_d.get("gen_count", 1)
        gen_type  = gen_sys_d.get("gen_type", "diesel").lower()
        _conns_key = "generator_conns_diesel" if gen_type == "diesel" else "generator_conns_natural_gas"
        _nd, _fd   = APPB_DESC_DEFAULTS.get(_conns_key, ("", ""))
        tbl_el.append(_make_section_header(
            f"ITP Section 3.{sec_num}",
            "Emergency Generator Power Integrations",
            _nd[:150], _fd[:150],
            full_header=f"ITP Section 3.{sec_num}: Emergency Generator Power Integrations:",
        ))
        for gen_num in range(1, gen_count + 1):
            tbl_el.append(_make_data_row_c(global_row_num, f"Generator #{gen_num} Startup"))
            global_row_num += 1
            for lbl in served_labels:
                device_name = GEN_DISPLAY_C.get(lbl, lbl)
                tbl_el.append(_make_data_row_c(
                    global_row_num, f"Generator #{gen_num} {device_name} Emergency Power"))
                global_row_num += 1


def _save_appc_template_rows(doc):
    """
    Save deepcopies of Appendix C template rows BEFORE replace_all runs,
    so the sw placeholder text ({{stand_itp_sw_type}} etc.) is still intact.
    Returns dict with keys: section_tr, data_tr, data_tr_sw
    """
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"
    body = doc.element.body
    body_elements = list(body)
    found_appc_heading = False
    tables_after = 0
    for elem in body_elements:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "p":
            text = "".join(t.text or "" for t in elem.iter(f"{W}t")).strip()
            if text == "Appendix C":
                found_appc_heading = True
        elif tag == "tbl" and found_appc_heading:
            tables_after += 1
            if tables_after == 3:
                rows = elem.findall(f".//{W}tr")
                if len(rows) >= 7:
                    return {
                        "section_tr":  deepcopy(rows[3]),
                        "data_tr":     deepcopy(rows[4]),
                        "data_tr_sw":  deepcopy(rows[6]),
                    }
                elif len(rows) >= 5:
                    return {
                        "section_tr": deepcopy(rows[3]),
                        "data_tr":    deepcopy(rows[4]),
                        "data_tr_sw": deepcopy(rows[4]),
                    }
    return {}