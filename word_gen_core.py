"""
word_gen_core.py — Low-level XML/run helpers shared across all word_gen modules.
Change this file only for bugs in placeholder replacement, paragraph cloning,
or the fundamental run-level XML manipulation.
"""

import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
from copy import deepcopy
from datetime import datetime

from lxml import etree


def pick_date(entry_widget, parent):
    current = entry_widget.get().strip()
    try:
        initial = datetime.strptime(current, "%B %d, %Y")
    except ValueError:
        initial = datetime.now()
    popup = tk.Toplevel(parent)
    popup.title("Pick a Date")
    popup.resizable(False, False)
    popup.transient(parent)
    popup.grab_set()
    popup.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
    cal = Calendar(popup, selectmode="day",
                   year=initial.year, month=initial.month, day=initial.day,
                   date_pattern="y-mm-dd", font=("Arial", 10))
    cal.pack(padx=10, pady=10)

    def on_select():
        chosen = datetime.strptime(cal.get_date(), "%Y-%m-%d")
        entry_widget.delete(0, "end")
        entry_widget.insert(0, chosen.strftime("%B %d, %Y"))
        popup.destroy()

    ttk.Button(popup, text="Select", command=on_select).pack(pady=(0, 10))


# ============================================================
#   WORD GENERATION HELPERS
# ============================================================

def replace_in_paragraph(para, replacements):
    """Replace {{placeholders}} in a paragraph safely, preserving run positions.

    Placeholders may be split across runs by Word's spell-checker
    (e.g. '{{', 'building_name', '}}' in three separate runs).
    Non-text runs like <w:tab/> must stay in their original DOM position
    so tab stops are preserved. We therefore replace each placeholder
    in-place: the replacement value goes into the first run of the
    placeholder span, intermediate runs are cleared, and surrounding
    literal text in the same runs is preserved as prefix/suffix.
    Runs inside field codes (PAGE, NUMPAGES) are never touched.
    """
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W = f"{{{WNS}}}"
    p = para._p

    # Collect non-field <w:t> elements in DOM order
    t_elements = []
    field_depth = 0
    for r in p.findall(f"{W}r"):
        fld = r.find(f"{W}fldChar")
        if fld is not None:
            ftype = fld.get(f"{W}fldCharType")
            if ftype == "begin":
                field_depth += 1
            elif ftype == "end":
                field_depth -= 1
            continue
        if field_depth > 0:
            continue
        t = r.find(f"{W}t")
        if t is not None:
            t_elements.append(t)

    if not t_elements:
        return

    if "{{" not in "".join(t.text or "" for t in t_elements):
        return

    XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

    def _apply_one(key, val):
        """Find and replace all occurrences of {{key}} in-place."""
        placeholder = f"{{{{{key}}}}}"
        while True:
            full = "".join(t.text or "" for t in t_elements)
            idx = full.find(placeholder)
            if idx == -1:
                break
            end_idx = idx + len(placeholder)

            # Build position → t_element index map for current texts
            pos_map = []
            for i, t in enumerate(t_elements):
                pos_map.extend([i] * len(t.text or ""))

            # t_element indices that contain the placeholder characters
            involved = []
            for pos in range(idx, end_idx):
                if pos < len(pos_map):
                    ti = pos_map[pos]
                    if not involved or involved[-1] != ti:
                        involved.append(ti)

            if not involved:
                break

            first_ti = involved[0]
            last_ti = involved[-1]

            # Prefix: chars in first t_element before the placeholder starts
            chars_before_first = sum(len(t_elements[i].text or "") for i in range(first_ti))
            prefix = (t_elements[first_ti].text or "")[:idx - chars_before_first]

            # Suffix: chars in last t_element after the placeholder ends
            chars_before_last = sum(len(t_elements[i].text or "") for i in range(last_ti))
            suffix_start = end_idx - chars_before_last
            suffix = (t_elements[last_ti].text or "")[suffix_start:]

            # Write back
            new_first = prefix + val
            if first_ti == last_ti:
                t_elements[first_ti].text = new_first + suffix
            else:
                t_elements[first_ti].text = new_first
                for ti in involved[1:-1]:
                    t_elements[ti].text = ""
                t_elements[last_ti].text = suffix

            # Ensure leading/trailing spaces are preserved in XML
            for ti in (first_ti, last_ti):
                txt = t_elements[ti].text or ""
                if txt and (txt[0] == " " or txt[-1] == " "):
                    t_elements[ti].set(XML_SPACE, "preserve")

    for key, value in replacements.items():
        _apply_one(key, str(value) if value else "")


def replace_in_table(table, replacements):
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                replace_in_paragraph(para, replacements)


def replace_all(doc, replacements):
    for para in doc.paragraphs:
        replace_in_paragraph(para, replacements)
    for table in doc.tables:
        replace_in_table(table, replacements)
    for section in doc.sections:
        # Only access header/footer if it is explicitly linked for this section.
        # Accessing .header / .footer on a section that inherits from the previous
        # one causes python-docx to create a new blank header/footer, wiping out
        # page numbers and other inherited content.
        sect_pr = section._sectPr
        W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        has_header = sect_pr.find(f"{{{W}}}headerReference") is not None
        has_footer = sect_pr.find(f"{{{W}}}footerReference") is not None

        if has_header:
            for para in section.header.paragraphs:
                replace_in_paragraph(para, replacements)
            for table in section.header.tables:
                replace_in_table(table, replacements)
        if has_footer:
            for para in section.footer.paragraphs:
                replace_in_paragraph(para, replacements)
            for table in section.footer.tables:
                replace_in_table(table, replacements)


def _set_cell_text(cell, text):
    for para in cell.paragraphs:
        for run in para.runs:
            run.text = ""
    if cell.paragraphs:
        if cell.paragraphs[0].runs:
            cell.paragraphs[0].runs[0].text = text or ""
        else:
            cell.paragraphs[0].add_run(text or "")


def replace_placeholder_paragraph_with_paragraphs(doc, placeholder_key, paragraphs_text):
    """Replace a {{placeholder}} paragraph with multiple properly-spaced Word paragraphs."""
    placeholder_para = None
    for para in doc.paragraphs:
        if placeholder_key in para.text:
            placeholder_para = para
            break
    if placeholder_para is None:
        return
    parent = placeholder_para._element.getparent()
    placeholder_el = placeholder_para._element
    insert_idx = list(parent).index(placeholder_el)
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    offset = 0
    for i, text in enumerate(paragraphs_text):
        if i > 0 and not text.startswith("•"):
            blank_el = deepcopy(placeholder_el)
            for run in blank_el.findall(f".//{{{WNS}}}r"):
                for t in run.findall(f"{{{WNS}}}t"):
                    t.text = ""
            parent.insert(insert_idx + offset, blank_el)
            offset += 1
        new_el = deepcopy(placeholder_el)
        runs = new_el.findall(f".//{{{WNS}}}r")
        if runs:
            t_els = runs[0].findall(f"{{{WNS}}}t")
            if t_els:
                t_els[0].text = text
                t_els[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            for run in runs[1:]:
                for t in run.findall(f"{{{WNS}}}t"):
                    t.text = ""
        # Add left indent for bullet lines
        if text.startswith("•"):
            pPr = new_el.find(f"{{{WNS}}}pPr")
            if pPr is None:
                pPr = etree.SubElement(new_el, f"{{{WNS}}}pPr")
                new_el.insert(0, pPr)
            ind = pPr.find(f"{{{WNS}}}ind")
            if ind is None:
                ind = etree.SubElement(pPr, f"{{{WNS}}}ind")
            ind.set(f"{{{WNS}}}left", "360")
        parent.insert(insert_idx + offset, new_el)
        offset += 1
    parent.remove(placeholder_el)


def style_arencon_runs(doc):
    """Find every occurrence of 'Arencon Inc.' (case-insensitive) in body paragraphs
    and table cells (headers/footers excluded) and reformat the text so that:
      • 'ARENCON' is all-caps, BlairMdITC TT, 9 pt
      • 'INC.'    is all-caps, BlairMdITC TT, 7 pt

    Occurrences may be split across multiple <w:r> runs by Word's XML. The function
    joins the text of all runs in a paragraph, locates the pattern, then rewrites the
    involved runs in-place: the run that starts the match gets the prefix text, then
    two new runs (ARENCON / INC.) are inserted after it (inheriting the original rPr
    so colour/bold/etc. are preserved), and any suffix text goes into a further run.
    Intermediate runs between the first and last involved run are cleared.
    """
    import re
    from copy import deepcopy
    from lxml import etree

    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    W   = f"{{{WNS}}}"
    XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

    PATTERN = re.compile(r"arencon\s+inc\.", re.IGNORECASE)

    FONT_ARENCON = "BlairMdITC TT"
    SIZE_ARENCON = "18"   # half-points: 9 pt = 18 half-points
    FONT_INC     = "BlairMdITC TT"
    SIZE_INC     = "14"   # half-points: 7 pt = 14 half-points

    def _make_styled_run(parent_r, text, font_name, half_pt_size):
        """Clone the rPr of parent_r, override font + size, return a new <w:r>."""
        new_r = etree.Element(f"{W}r")

        # Clone existing rPr (preserves bold, colour, etc.) or create a fresh one
        orig_rPr = parent_r.find(f"{W}rPr")
        if orig_rPr is not None:
            rPr = deepcopy(orig_rPr)
        else:
            rPr = etree.Element(f"{W}rPr")
        new_r.append(rPr)

        # ── Font ────────────────────────────────────────────────────────
        rFonts = rPr.find(f"{W}rFonts")
        if rFonts is None:
            rFonts = etree.SubElement(rPr, f"{W}rFonts")
        for attr in (f"{W}ascii", f"{W}hAnsi", f"{W}cs"):
            rFonts.set(attr, font_name)

        # ── Size ────────────────────────────────────────────────────────
        sz = rPr.find(f"{W}sz")
        if sz is None:
            sz = etree.SubElement(rPr, f"{W}sz")
        sz.set(f"{W}val", half_pt_size)

        szCs = rPr.find(f"{W}szCs")
        if szCs is None:
            szCs = etree.SubElement(rPr, f"{W}szCs")
        szCs.set(f"{W}val", half_pt_size)

        # ── Text ────────────────────────────────────────────────────────
        t = etree.SubElement(new_r, f"{W}t")
        t.text = text
        if text and (text[0] == " " or text[-1] == " "):
            t.set(XML_SPACE, "preserve")

        return new_r

    def _make_plain_run(parent_r, text):
        """Clone the rPr of parent_r verbatim for prefix/suffix text."""
        new_r = etree.Element(f"{W}r")
        orig_rPr = parent_r.find(f"{W}rPr")
        if orig_rPr is not None:
            new_r.append(deepcopy(orig_rPr))
        t = etree.SubElement(new_r, f"{W}t")
        t.text = text
        if text and (text[0] == " " or text[-1] == " "):
            t.set(XML_SPACE, "preserve")
        return new_r

    def _process_paragraph(para):
        p = para._p

        # Collect (run_element, t_element) pairs — skip field-code runs
        pairs = []
        field_depth = 0
        for r in p.findall(f"{W}r"):
            fld = r.find(f"{W}fldChar")
            if fld is not None:
                ftype = fld.get(f"{W}fldCharType")
                if ftype == "begin":
                    field_depth += 1
                elif ftype == "end":
                    field_depth -= 1
                continue
            if field_depth > 0:
                continue
            t = r.find(f"{W}t")
            if t is not None:
                pairs.append((r, t))

        if not pairs:
            return

        full_text = "".join(t.text or "" for _, t in pairs)
        if not PATTERN.search(full_text):
            return

        # Process all matches in one pass (right-to-left so indices stay valid)
        matches = list(PATTERN.finditer(full_text))
        for m in reversed(matches):
            match_str = m.group(0)           # original casing, e.g. "Arencon Inc."
            idx       = m.start()
            end_idx   = m.end()

            # Determine "ARENCON" and " INC." portions from the actual match
            # (handles any whitespace between them, e.g. "Arencon  Inc.")
            space_match = re.search(r"\s+", match_str)
            if space_match:
                space_str  = space_match.group(0)
                arencon_txt = "ARENCON"
                inc_txt     = space_str + "INC."
            else:
                arencon_txt = "ARENCON"
                inc_txt     = " INC."

            # Build position → pair index map
            pos_map = []
            for i, (_, t) in enumerate(pairs):
                pos_map.extend([i] * len(t.text or ""))

            involved = []
            for pos in range(idx, end_idx):
                if pos < len(pos_map):
                    pi = pos_map[pos]
                    if not involved or involved[-1] != pi:
                        involved.append(pi)
            if not involved:
                continue

            first_pi = involved[0]
            last_pi  = involved[-1]

            first_r, first_t = pairs[first_pi]
            last_r,  last_t  = pairs[last_pi]

            chars_before_first = sum(len(pairs[i][1].text or "") for i in range(first_pi))
            prefix = (first_t.text or "")[:idx - chars_before_first]

            chars_before_last = sum(len(pairs[i][1].text or "") for i in range(last_pi))
            suffix_start = end_idx - chars_before_last
            suffix = (last_t.text or "")[suffix_start:]

            # Clear intermediate runs
            for pi in involved[1:]:
                pairs[pi][1].text = ""

            # Rewrite first run to hold only the prefix (may be empty)
            first_t.text = prefix
            if prefix and (prefix[0] == " " or prefix[-1] == " "):
                first_t.set(XML_SPACE, "preserve")

            # Insert new runs after first_r in the paragraph XML
            insert_after = first_r
            new_runs = []

            r_arencon = _make_styled_run(first_r, arencon_txt, FONT_ARENCON, SIZE_ARENCON)
            r_inc     = _make_styled_run(first_r, inc_txt,     FONT_INC,     SIZE_INC)
            new_runs.append(r_arencon)
            new_runs.append(r_inc)

            if suffix:
                r_suffix = _make_plain_run(last_r, suffix)
                new_runs.append(r_suffix)

            for i, new_r in enumerate(new_runs):
                insert_after.addnext(new_r)
                insert_after = new_r

            # Rebuild pairs list for any further (earlier) matches in this paragraph
            pairs = []
            field_depth = 0
            for r in p.findall(f"{W}r"):
                fld = r.find(f"{W}fldChar")
                if fld is not None:
                    ftype = fld.get(f"{W}fldCharType")
                    if ftype == "begin":
                        field_depth += 1
                    elif ftype == "end":
                        field_depth -= 1
                    continue
                if field_depth > 0:
                    continue
                t = r.find(f"{W}t")
                if t is not None:
                    pairs.append((r, t))

    # ── Walk body paragraphs ─────────────────────────────────────────────────
    for para in doc.paragraphs:
        _process_paragraph(para)

    # ── Walk table cells (all levels, incl. nested tables) ───────────────────
    def _walk_tables(tables):
        for table in tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        _process_paragraph(para)
                    _walk_tables(cell.tables)  # nested tables

    _walk_tables(doc.tables)
    # Headers and footers are intentionally excluded.


def remove_system_section(doc, placeholder_keys):
    """
    Remove system sections from the doc whose placeholders match placeholder_keys.
    Walks backward from each placeholder to remove its heading, labels, and blank lines.
    """
    paras = list(doc.paragraphs)
    to_remove = set()
    for i, para in enumerate(paras):
        if any(f"{{{{{k}}}}}" in para.text for k in placeholder_keys):
            to_remove.add(i)
            j = i - 1
            while j >= 0:
                p = paras[j]
                if p.text.strip() == "":
                    to_remove.add(j)
                    j -= 1
                elif p.text.strip() in (
                        "System Overview Description",
                        "System Integrations & Functional Objectives",
                        "System Integrations & Functional Objective",
                ):
                    to_remove.add(j)
                    j -= 1
                elif p.style.name == "Heading 3":
                    to_remove.add(j)
                    break
                else:
                    break
    for i in sorted(to_remove, reverse=True):
        el = paras[i]._element
        el.getparent().remove(el)