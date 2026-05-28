"""
word_gen_contacts.py — Contractor, notification, signature, and occupancy table population.
Change this file for bugs in the people/occupancy tables in the Word document.
"""

from copy import deepcopy
from lxml import etree

from word_gen_core import replace_in_paragraph


def populate_contacts_table(doc, contractors):
    """Table: role | company | phone — all 3 in the same row."""
    contacts_table = None
    placeholder_row = None
    for table in doc.tables:
        for row in table.rows:
            row_text = "".join(cell.text for cell in row.cells)
            if ("contractor_role" in row_text and "contractor_company" in row_text
                    and "contractor_phone" in row_text):
                contacts_table = table
                placeholder_row = row
                break
        if contacts_table:
            break
    if contacts_table is None or placeholder_row is None:
        return
    template_tr = deepcopy(placeholder_row._tr)
    placeholder_row._tr.getparent().remove(placeholder_row._tr)
    for c in contractors:
        new_tr = deepcopy(template_tr)
        contacts_table._tbl.append(new_tr)
        for cell in contacts_table.rows[-1].cells:
            for para in cell.paragraphs:
                replace_in_paragraph(para, {
                    "contractor_role": c.get("role", ""),
                    "contractor_company": c.get("company", ""),
                    "contractor_phone": c.get("phone", ""),
                })


def populate_notifications_table(doc, contractors):
    """Notifications table: 'role – company' | phone — same row, no contractor_name."""
    notif_table = None
    placeholder_row = None
    for table in doc.tables:
        for row in table.rows:
            row_text = "".join(cell.text for cell in row.cells)
            if ("contractor_role" in row_text and "contractor_phone" in row_text
                    and "contractor_name" not in row_text
                    and "contractor_company" in row_text):
                notif_table = table
                placeholder_row = row
                break
        if notif_table:
            break
    if notif_table is None or placeholder_row is None:
        return
    template_tr = deepcopy(placeholder_row._tr)
    placeholder_row._tr.getparent().remove(placeholder_row._tr)
    for c in contractors:
        new_tr = deepcopy(template_tr)
        notif_table._tbl.append(new_tr)
        for cell in notif_table.rows[-1].cells:
            for para in cell.paragraphs:
                replace_in_paragraph(para, {
                    "contractor_role": c.get("role", ""),
                    "contractor_company": c.get("company", ""),
                    "contractor_phone": c.get("phone", ""),
                })


def populate_signatures_table(doc, contractors):
    """
    Two signature tables:
      Table A — 1 row: contractor_role | contractor_company | contractor_name (all in same row)
      Table B — 3-row group per contractor:
                  row 0: contractor_role (merged) | Company: | contractor_company
                  row 1: (merged)                 | Name:    | contractor_name
                  row 2: (merged)                 | Signature: | blank | Date: | blank
    """
    for table in doc.tables:
        full_text = "".join(cell.text for row in table.rows for cell in row.cells)
        if "contractor_role" not in full_text or "contractor_name" not in full_text:
            continue

        # Find which row starts the contractor group
        start_idx = None
        for idx, row in enumerate(table.rows):
            row_text = "".join(cell.text for cell in row.cells)
            if "contractor_role" in row_text:
                start_idx = idx
                break
        if start_idx is None:
            continue

        # Determine group size: 1 row if contractor_name is in same row, else 3 rows
        start_row_text = "".join(cell.text for cell in table.rows[start_idx].cells)
        rows_in_group = 1 if "contractor_name" in start_row_text else 3

        # Copy template rows
        group_trs = [
            deepcopy(table.rows[start_idx + i]._tr)
            for i in range(rows_in_group)
            if start_idx + i < len(table.rows)
        ]

        # Remove template rows in reverse order
        for i in range(rows_in_group - 1, -1, -1):
            tr = table.rows[start_idx + i]._tr
            tr.getparent().remove(tr)

        # Insert one group per contractor
        for c in contractors:
            replacements = {
                "contractor_role": c.get("role", ""),
                "contractor_company": c.get("company", ""),
                "contractor_name": c.get("name", ""),
            }
            for template_tr in group_trs:
                new_tr = deepcopy(template_tr)
                table._tbl.append(new_tr)
                for cell in table.rows[-1].cells:
                    for para in cell.paragraphs:
                        replace_in_paragraph(para, replacements)


def populate_occupancies_table(doc, occupancies):
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"

    placeholder_para = None
    for para in doc.paragraphs:
        if "occ_type" in para.text and "occ_description" in para.text:
            placeholder_para = para
            break
    if placeholder_para is None:
        return

    if not occupancies:
        replace_in_paragraph(placeholder_para, {"occ_type": "", "occ_description": ""})
        return

    # Detect tab_prefix BEFORE replace_in_paragraph collapses all runs into one.
    # Add one extra tab to compensate for the "Occupancies: " label width.
    tab_prefix = ""
    for run in placeholder_para.runs:
        if "{{" in run.text:
            break
        if "\t" in run.text:
            tab_prefix += run.text
    tab_prefix += "\t"

    replace_in_paragraph(placeholder_para, {
        "occ_type": occupancies[0].get("occ_type", ""),
        "occ_description": occupancies[0].get("occ_description", ""),
    })

    if len(occupancies) == 1:
        return

    placeholder_el = placeholder_para._element
    parent = placeholder_el.getparent()
    insert_idx = list(parent).index(placeholder_el) + 1

    orig_runs = placeholder_el.findall(f".//{W}r")
    rPr_source = orig_runs[0].find(f"{W}rPr") if orig_runs else None

    for i, occ in enumerate(occupancies[1:]):
        occ_type = occ.get("occ_type", "")
        occ_desc = occ.get("occ_description", "")
        content = f"{occ_type} \u2014 {occ_desc}" if occ_desc else occ_type

        new_el = deepcopy(placeholder_el)
        for r in list(new_el.findall(f".//{W}r")):
            r.getparent().remove(r)

        def _make_run(text):
            r_el = etree.SubElement(new_el, f"{W}r")
            if rPr_source is not None:
                r_el.insert(0, deepcopy(rPr_source))
            t_el = etree.SubElement(r_el, f"{W}t")
            t_el.text = text
            t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            return r_el

        _make_run(tab_prefix)
        _make_run(content)
        parent.insert(insert_idx + i, new_el)