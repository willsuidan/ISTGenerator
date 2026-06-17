"""
word_gen_sections.py — Test procedure section population and absent-section removal.
Change this file for bugs in TP bullet formatting, section headers, placeholder
lookup for pre-action or any other system's TP block.

pre_action is handled generically like all other systems:
  - pre_pan uses header_ph="{{stnd_integ_tp_header}}" (template reuses standpipe's placeholder)
    and table placeholders {{pre_pan_integ_tp_normal/fire}}
  - pre_sys same pattern, table placeholders {{pre_sys_integ_tp_normal/fire}}
After standpipe removes its {{stnd_integ_tp_header}} block, the remaining occurrences
belong to pre_pan then pre_sys — the generic loop finds them in document order.
"""

from copy import deepcopy
from lxml import etree

from defaults import MATRIX_DEFAULTS, TP_DEFAULTS
from constants import SYSTEMS, MONITORING_MATRIX_DEFAULTS


def populate_test_procedures(doc, data, replacements=None):
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"

    systems_data = data.get("systems", {})

    # sections: (tp_prefix, rows, header_ph_override)
    # header_ph_override — when set, overrides the default f"{{{tp_prefix}_integ_tp_header}}}"
    # normal/fire placeholders always derived as f"{{{tp_prefix}_integ_tp_normal/fire}}}"
    sections = []

    # Monitoring
    fa_sys = systems_data.get("fire_alarm", {})
    mon_rows = fa_sys.get("matrix_mon", [])
    if not mon_rows:
        mon_tp = TP_DEFAULTS.get("fire_alarm_monitoring", [])
        mon_rows = [{"integration": MONITORING_MATRIX_DEFAULTS[i][0],
                     "tp_normal": mon_tp[i][0] if i < len(mon_tp) else "",
                     "tp_fire": mon_tp[i][1] if i < len(mon_tp) else ""}
                    for i in range(len(MONITORING_MATRIX_DEFAULTS))]
    sections.append(("mon", mon_rows, None))

    for sys_info in SYSTEMS:
        key = sys_info["key"]
        if key == "fire_alarm":
            continue
        sys_d = systems_data.get(key, {})
        if not sys_d.get("present", False):
            continue
        tp_prefix = sys_info["tp_prefix"]

        if key == "pre_action":
            # pre_pan: Fire Alarm <-> Pre-Action Panel
            # Template reuses {{stnd_integ_tp_header}} — pass as override so the generic
            # loop finds it AFTER standpipe already consumed its own block.
            if sys_d.get("pre_action_panel", False):
                pap_rows_tp = sys_d.get("pap_matrix_rows", [])
                if not pap_rows_tp:
                    defaults_m = MATRIX_DEFAULTS.get("pre_action_panel", [])
                    defaults_t = TP_DEFAULTS.get("pre_action_panel", [])
                    pap_rows_tp = [{"integration": defaults_m[i][0] if i < len(defaults_m) else "",
                                    "tp_normal": defaults_t[i][0] if i < len(defaults_t) else "",
                                    "tp_fire": defaults_t[i][1] if i < len(defaults_t) else ""}
                                   for i in range(max(len(defaults_m), 1))]
                sections.append(("pre_pan", pap_rows_tp, None))
                print(f"[TP] pre_pan: {len(pap_rows_tp)} integration rows")

            # pre_sys: Pre-Action Panel <-> Pre-Action Sprinkler System
            pa_rows_tp2 = sys_d.get("matrix_rows", [])
            if not pa_rows_tp2:
                defaults_m = MATRIX_DEFAULTS.get("pre_action", [])
                defaults_t = TP_DEFAULTS.get("pre_action", [])
                pa_rows_tp2 = [{"integration": defaults_m[i][0] if i < len(defaults_m) else "",
                                "tp_normal": defaults_t[i][0] if i < len(defaults_t) else "",
                                "tp_fire": defaults_t[i][1] if i < len(defaults_t) else ""}
                               for i in range(max(len(defaults_m), 1))]
            sections.append(("pre_sys", pa_rows_tp2, None))
            print(f"[TP] pre_sys: {len(pa_rows_tp2)} integration rows")
            continue

        rows = sys_d.get("matrix_rows", [])
        if not rows:
            defaults_m = MATRIX_DEFAULTS.get(key, [])
            defaults_t = TP_DEFAULTS.get(key, [])
            rows = [{"integration": defaults_m[i][0] if i < len(defaults_m) else "",
                     "tp_normal": defaults_t[i][0] if i < len(defaults_t) else "",
                     "tp_fire": defaults_t[i][1] if i < len(defaults_t) else ""}
                    for i in range(max(len(defaults_m), 1))]
        sections.append((tp_prefix, rows, None))
        print(f"[TP] {key} ({tp_prefix}): {len(rows)} integration rows")

    def _para_full_text(para_el):
        return "".join(t.text or "" for t in para_el.findall(f".//{W}t"))

    def _replace_para_placeholder(para_el, placeholder, replacement):
        full = _para_full_text(para_el)
        if placeholder not in full:
            return False
        new_text = full.replace(placeholder, replacement)
        runs = para_el.findall(f".//{W}r")
        if runs:
            t_els = runs[0].findall(f"{W}t")
            if t_els:
                t_els[0].text = new_text
                t_els[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            for run in runs[1:]:
                for t in run.findall(f"{W}t"):
                    t.text = ""
        return True

    def _expand_cell_placeholder(cell_el, placeholder, bullet_text):
        for para_el in cell_el.findall(f".//{W}p"):
            full = _para_full_text(para_el)
            if placeholder not in full:
                continue
            parent = para_el.getparent()
            insert_idx = list(parent).index(para_el)
            first_run = para_el.find(f".//{W}r")
            rPr_source = first_run.find(f"{W}rPr") if first_run is not None else None

            lines = [l.strip() for l in bullet_text.strip().split("\n")]
            lines = [l.lstrip("- •").strip() for l in lines if l.strip()]
            if not lines:
                lines = [""]

            for i, line in enumerate(lines):
                new_p = deepcopy(para_el)
                for r in new_p.findall(f"{W}r"):
                    new_p.remove(r)
                r_el = etree.SubElement(new_p, f"{W}r")
                if rPr_source is not None:
                    r_el.insert(0, deepcopy(rPr_source))
                t_el = etree.SubElement(r_el, f"{W}t")
                t_el.text = f"\u2022  {line}" if line else ""
                t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                parent.insert(insert_idx + i, new_p)

            parent.remove(para_el)
            return True
        return False

    body = doc.element.body

    for tp_prefix, rows, header_ph_override in sections:
        header_ph = header_ph_override if header_ph_override else f"{{{{{tp_prefix}_integ_tp_header}}}}"
        normal_ph = f"{{{{{tp_prefix}_integ_tp_normal}}}}"
        fire_ph = f"{{{{{tp_prefix}_integ_tp_fire}}}}"

        body_children = list(body)

        # Find the template heading paragraph
        template_heading = None
        template_heading_idx = None
        for idx, el in enumerate(body_children):
            if el.tag == f"{W}p" and header_ph in _para_full_text(el):
                template_heading = el
                template_heading_idx = idx
                break

        if template_heading is None:
            print(f"[TP] {tp_prefix}: heading paragraph '{header_ph}' NOT FOUND — skipping")
            continue

        # The table immediately follows the heading paragraph
        template_table = (body_children[template_heading_idx + 1]
                          if template_heading_idx + 1 < len(body_children) else None)
        if template_table is None or template_table.tag != f"{W}tbl":
            print(f"[TP] {tp_prefix}: no table immediately after heading — skipping")
            continue

        # Verify the table has the expected normal/fire placeholders
        table_full = "".join(t.text or "" for t in template_table.iter(f"{W}t"))
        has_normal = normal_ph in table_full
        has_fire = fire_ph in table_full
        print(f"[TP] {tp_prefix}: found heading+table. normal_ph={normal_ph!r} in table: {has_normal}, fire_ph={fire_ph!r} in table: {has_fire}")

        insert_idx = list(body).index(template_heading)

        for i, row_data in enumerate(rows):
            header_text = row_data.get("integration", f"Integration {i + 1}")
            tp_normal = row_data.get("tp_normal", "")
            tp_fire = row_data.get("tp_fire", "")
            if replacements:
                for ph_key, val in replacements.items():
                    placeholder = f"{{{{{ph_key}}}}}"
                    if placeholder in tp_normal:
                        tp_normal = tp_normal.replace(placeholder, str(val) if val else "")
                    if placeholder in tp_fire:
                        tp_fire = tp_fire.replace(placeholder, str(val) if val else "")

            new_heading = deepcopy(template_heading)
            for para_el in new_heading.findall(f".//{W}p") or [new_heading]:
                if _replace_para_placeholder(para_el, header_ph, header_text):
                    break

            new_table = deepcopy(template_table)
            expanded_n = expanded_f = False
            for cell_el in new_table.findall(f".//{W}tc"):
                if _expand_cell_placeholder(cell_el, normal_ph, tp_normal):
                    expanded_n = True
                if _expand_cell_placeholder(cell_el, fire_ph, tp_fire):
                    expanded_f = True

            print(f"  [TP] {tp_prefix} row {i} '{header_text}': normal expanded={expanded_n}, fire expanded={expanded_f}")

            _WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            blank_p = etree.Element(f"{{{_WNS}}}p")

            body.insert(insert_idx, new_heading)
            body.insert(insert_idx + 1, new_table)
            body.insert(insert_idx + 2, blank_p)
            insert_idx += 3

        body.remove(template_heading)
        body.remove(template_table)


def _remove_absent_tp_blocks(doc, data):
    """
    Remove entire TP section blocks for systems not present in the report.
    Each section in the template has: Heading2 + blank paras + {{header}} para + table + blank paras.
    We find the Heading2 by matching the system label, then delete everything up to
    (but not including) the next Heading2 or Heading1.
    """
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"

    # gen_class display must match the heading text AFTER replace_all has run
    _gen_class_raw = data.get("systems", {}).get("generator", {}).get("gen_class", "non-emergency")
    _gen_class_display = "Emergency" if _gen_class_raw == "emergency" else "Non-Emergency"

    SECTION_HEADINGS = {
        "sprinkler": ["Fire Alarm / Sprinkler System Integrations"],
        "standpipe": ["Fire Alarm / Standpipe and Hose System Integrations"],
        # pre_action second heading uses {{preac_pan_or_fa}} — check both possible values
        "pre_action": ["Fire Alarm / Pre-Action Panel Integrations",
                       "Pre-Action Panel / Pre-Action Sprinkler System Integrations",
                       "Fire Alarm / Pre-Action Sprinkler System Integrations"],
        "fire_pump": ["Fire Alarm / Fire Pump Integrations"],
        # Generator heading includes gen_class (replaced by replace_all before this runs).
        # Always include both variants so the section is removed regardless of the
        # gen_class default when the generator is not selected at all.
        "generator": [
            f"Fire Alarm / {_gen_class_display} Generator Integrations",
            "Fire Alarm / Emergency Generator Integrations",
            "Fire Alarm / Non-Emergency Generator Integrations",
            "Emergency Generator Power Integrations",
        ],
        "maglock": ["Fire Alarm / Electromagnetic Lock Integrations"],
        "door_holders": ["Fire Alarm / Door Holder Integrations"],
        "ahu": ["Fire Alarm / Air Handling Unit Integrations"],
        "smoke_dampers": ["Fire Alarm / Smoke Damper Integrations"],
        "fire_shutters": ["Fire Alarm / Fire Shutter Integrations"],
        "kitchen_hood": ["Fire Alarm / Kitchen Hood Suppression System Integrations"],
        "water_mist":   ["Fire Alarm / Water Mist System Integrations",
                         "Fire Alarm / Water-Mist System Integrations"],
        "elevator":     ["Fire Alarm / Elevator Integrations"],
    }

    systems_data = data.get("systems", {})
    body = doc.element.body

    def _is_heading(el, levels=("Heading1", "Heading2", "Heading3")):
        pStyle = el.find(f".//{W}pStyle")
        return pStyle is not None and pStyle.get(f"{W}val") in levels

    for sys_info in SYSTEMS:
        key = sys_info["key"]
        if key == "fire_alarm":
            continue
        sys_d = systems_data.get(key, {})
        if sys_d.get("present", False):
            continue

        heading_texts = SECTION_HEADINGS.get(key, [])
        if not heading_texts:
            continue

        for heading_text in heading_texts:
            body_children = list(body)
            start_idx = None
            for idx, el in enumerate(body_children):
                if el.tag == f"{W}p" and _is_heading(el):
                    el_text = "".join(t.text or "" for t in el.findall(f".//{W}t")).strip()
                    if el_text == heading_text.strip():
                        start_idx = idx
                        break
            if start_idx is None:
                continue
            end_idx = len(body_children)
            for idx in range(start_idx + 1, len(body_children)):
                el = body_children[idx]
                if el.tag == f"{W}p" and _is_heading(el):
                    end_idx = idx
                    break
            to_remove = body_children[start_idx:end_idx]
            for el in to_remove:
                if el.getparent() is not None:
                    body.remove(el)

    # Remove "Fire Alarm / Pre-Action Panel Integrations" TP section when pre_action
    # is present but has no designated pre-action panel.
    pa_d = systems_data.get("pre_action", {})
    if pa_d.get("present", False) and not pa_d.get("pre_action_panel", False):
        body_children = list(body)
        start_idx = None
        for idx, el in enumerate(body_children):
            if el.tag == f"{W}p" and _is_heading(el):
                el_text = "".join(t.text or "" for t in el.findall(f".//{W}t")).strip()
                if el_text == "Fire Alarm / Pre-Action Panel Integrations":
                    start_idx = idx
                    break
        if start_idx is not None:
            end_idx = len(body_children)
            for idx in range(start_idx + 1, len(body_children)):
                el = body_children[idx]
                if el.tag == f"{W}p" and _is_heading(el):
                    end_idx = idx
                    break
            for el in body_children[start_idx:end_idx]:
                if el.getparent() is not None:
                    body.remove(el)
            print("[TP] Removed pre_pan TP section (no designated pre-action panel)")

    # Remove "Emergency Generator Power Integrations" TP section when generator is
    # present but non-emergency — this section only applies to emergency generators.
    gen_d = systems_data.get("generator", {})
    gen_is_nonemergency = gen_d.get("present", False) and gen_d.get("gen_class", "non-emergency") != "emergency"
    if gen_is_nonemergency:
        body_children = list(body)
        start_idx = None
        for idx, el in enumerate(body_children):
            if el.tag == f"{W}p" and _is_heading(el):
                el_text = "".join(t.text or "" for t in el.findall(f".//{W}t")).strip()
                if el_text == "Emergency Generator Power Integrations":
                    start_idx = idx
                    break
        if start_idx is not None:
            end_idx = len(body_children)
            for idx in range(start_idx + 1, len(body_children)):
                el = body_children[idx]
                if el.tag == f"{W}p" and _is_heading(el):
                    end_idx = idx
                    break
            for el in body_children[start_idx:end_idx]:
                if el.getparent() is not None:
                    body.remove(el)
            print("[TP] Removed Emergency Generator Power section (non-emergency generator)")

def expand_gen_served_tp(doc, data):
    """
    Expand {{gen_integ_tp_norm_md}} and {{gen_integ_tp_gen_md}} placeholders
    in table cells into separate bullet paragraphs — one per line.
    Must be called AFTER replace_all so the placeholders contain the joined bullet text.
    """
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"

    gen_sys = data.get("systems", {}).get("generator", {})
    emerg_rows = gen_sys.get("gen_served_matrix_rows", [])
    if not emerg_rows:
        return

    def _bullets_for(field):
        lines = []
        for r in emerg_rows:
            text = r.get(field, "").strip()
            for l in text.split("\n"):
                l = l.strip().lstrip("- •").strip()
                if l:
                    lines.append(l)
        return lines

    norm_lines = _bullets_for("tp_normal")
    fire_lines = _bullets_for("tp_fire")

    def _expand_in_cell(cell_el, placeholder, lines):
        for para_el in list(cell_el.findall(f".//{W}p")):
            full = "".join(t.text or "" for t in para_el.findall(f".//{W}t"))
            if placeholder not in full:
                continue
            parent = para_el.getparent()
            insert_idx = list(parent).index(para_el)
            first_run = para_el.find(f".//{W}r")
            rPr_source = first_run.find(f"{W}rPr") if first_run is not None else None
            for i, line in enumerate(lines if lines else [""]):
                new_p = deepcopy(para_el)
                for r in new_p.findall(f"{W}r"):
                    new_p.remove(r)
                r_el = etree.SubElement(new_p, f"{W}r")
                if rPr_source is not None:
                    r_el.insert(0, deepcopy(rPr_source))
                t_el = etree.SubElement(r_el, f"{W}t")
                t_el.text = f"•  {line}" if line else ""
                t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                parent.insert(insert_idx + i, new_p)
            parent.remove(para_el)
            return True
        return False

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                _expand_in_cell(cell._element, "__GEN_TP_NORM_EXPAND__", norm_lines)
                _expand_in_cell(cell._element, "__GEN_TP_FIRE_EXPAND__", fire_lines)

def populate_elevator_action_table(doc, data):
    """Clone the {{elevator_action}} / {{elevator_action_desc}} placeholder row
    once per entry in data["systems"]["elevator"]["elev_actions"].

    The template contains a 2-column table with a single data row:
        | {{elevator_action}} | {{elevator_action_desc}} |

    Each entry is {"action": str, "desc": str}.
    If the list is empty the placeholder row is left in place so Word
    doesn't break, but its text is cleared.
    """
    from copy import deepcopy
    from word_gen_core import replace_in_paragraph

    elev_actions = (
        data.get("systems", {})
            .get("elevator", {})
            .get("elev_actions", [])
    )

    # Locate the table containing the placeholder row
    target_table = None
    placeholder_row = None
    for table in doc.tables:
        for row in table.rows:
            row_text = "".join(cell.text for cell in row.cells)
            if "elevator_action" in row_text and "elevator_action_desc" in row_text:
                target_table = table
                placeholder_row = row
                break
        if target_table:
            break

    if target_table is None or placeholder_row is None:
        return

    if not elev_actions:
        # Clear the placeholder row rather than leaving raw {{...}} text
        replace_in_paragraph
        for cell in placeholder_row.cells:
            for para in cell.paragraphs:
                replace_in_paragraph(para, {
                    "elevator_action": "",
                    "elevator_action_desc": "",
                })
        return

    template_tr = deepcopy(placeholder_row._tr)
    placeholder_row._tr.getparent().remove(placeholder_row._tr)

    for entry in elev_actions:
        new_tr = deepcopy(template_tr)
        target_table._tbl.append(new_tr)
        for cell in target_table.rows[-1].cells:
            for para in cell.paragraphs:
                replace_in_paragraph(para, {
                    "elevator_action":      entry.get("action", ""),
                    "elevator_action_desc": entry.get("desc", ""),
                })