"""
spellcheck.py — Real-time spell checking for tk.Text widgets.

Usage:
    from spellcheck import attach_spellcheck
    attach_spellcheck(some_text_widget)

Words are checked on every keystroke with a short debounce.
Misspelled words are underlined in red. Right-click shows suggestions.
Domain-specific fire protection terms are whitelisted so they never flag.
"""

import re
import tkinter as tk
from tkinter import ttk
from spellchecker import SpellChecker

# ── Domain whitelist ────────────────────────────────────────────────────────
# All lowercase — checked case-insensitively.
DOMAIN_WORDS = {
    # Acronyms & abbreviations
    "facp", "faap", "fap", "ahu", "hvac", "mfl", "nfpa", "ufc", "ulc", "csa",
    "obc", "onc", "ofc", "ifc", "ibc", "ul", "fm", "os", "psi", "gpm", "hp",
    "kw", "kwh", "lps", "lpm", "afff", "co", "co2", "halon", "novec",
    "esfr", "cmda", "ocr", "ist", "itp", "tp", "fp", "fa", "sv", "fs", "lp",
    "fps", "nr", "nt", "n", "v", "vdc", "vac", "hz",
    # Fire protection systems & components
    "sprinkler", "sprinklers", "standpipe", "standpipes", "maglocks", "maglock",
    "firepump", "firepumps", "riser", "risers", "annunciator", "annunciators",
    "annunciation", "supervisory", "annunciating", "initiating", "addressable",
    "dialer", "dialers", "enunciator", "enunciators", "firetruck", "preaction",
    "deluge", "suppression", "tamper", "waterflow", "jockey", "churn",
    "backflow", "preventer", "preaction", "pre-action", "subtype",
    # Building & occupancy terms
    "occupancy", "occupancies", "egress", "atrium", "atriums", "stairwell",
    "stairwells", "vestibule", "vestibules", "plenum", "plenums", "penthouse",
    "mezzanine", "mezzanines", "soffit", "soffits", "fascia",
    # Electrical & mechanical
    "breaker", "breakers", "conduit", "conduits", "wireway", "wireways",
    "raceway", "raceways", "plenum-rated", "thermostat", "thermostats",
    "louver", "louvers", "intake", "interlocked", "interlock", "interlocks",
    # General technical
    "pdf", "docx", "xlsx", "csv", "ui", "gui", "api", "url", "ip",
    # Names / proper nouns common in reports
    "arencon", "caplink", "fenmar", "morrison", "kidde", "siemens", "notifier",
    "simplex", "edwards", "honeywell", "gamewell", "bosch", "hochiki",
    "System", "systems",
}

_spell = SpellChecker()
_spell.word_frequency.load_words(DOMAIN_WORDS)

# Snapshot of built-in words — used to diff user additions on save
_BUILTIN_DOMAIN_WORDS = frozenset(DOMAIN_WORDS)

# Debounce delay in ms
_DEBOUNCE_MS = 400


def _is_ignorable(word):
    """Return True for words that should never be flagged."""
    w = word.lower().strip("''-")
    if not w:
        return True
    # All-caps acronym (2+ chars): FACP, AHU, OS&Y, etc.
    if re.match(r'^[A-Z0-9&/_-]{1,8}$', word):
        return True
    # Numbers, measurements: 175PSI, 30s, 6", etc.
    if re.match(r'^[\d.,/]+[a-zA-Z"\']*$', word):
        return True
    # Placeholder style: {{something}}
    if '{{' in word or '}}' in word:
        return True
    # Bullet characters
    if word in ('•', '–', '—', '-'):
        return True
    # Single characters
    if len(w) <= 1:
        return True
    # In domain whitelist
    if w in DOMAIN_WORDS:
        return True
    return False


def _check_widget(widget):
    """Re-run spell check on the entire widget content."""
    widget.tag_remove("misspelled", "1.0", "end")
    content = widget.get("1.0", "end-1c")
    # Tokenise — split on whitespace and punctuation, keep apostrophes within words
    for match in re.finditer(r"[A-Za-z''-]+", content):
        word = match.group()
        if _is_ignorable(word):
            continue
        if _spell.unknown([word.lower().strip("''-")]):
            # Convert character offset to tkinter line.col index
            start_off = match.start()
            end_off = match.end()
            start_idx = f"1.0 + {start_off} chars"
            end_idx = f"1.0 + {end_off} chars"
            widget.tag_add("misspelled", start_idx, end_idx)


def _show_suggestions(event, widget):
    """Right-click context menu with spelling suggestions."""
    # Find which misspelled word was clicked
    idx = widget.index(f"@{event.x},{event.y}")
    ranges = widget.tag_ranges("misspelled")
    clicked_word = None
    clicked_start = clicked_end = None
    for i in range(0, len(ranges), 2):
        start, end = ranges[i], ranges[i + 1]
        if widget.compare(start, "<=", idx) and widget.compare(idx, "<=", end):
            clicked_word = widget.get(start, end)
            clicked_start, clicked_end = start, end
            break

    menu = tk.Menu(widget, tearoff=0)
    if clicked_word:
        candidates = list(_spell.candidates(clicked_word.lower()) or [])
        candidates = [c for c in candidates if c.lower() != clicked_word.lower()][:6]
        if candidates:
            for c in candidates:
                display = c.capitalize() if clicked_word[0].isupper() else c
                menu.add_command(
                    label=display,
                    command=lambda w=widget, s=clicked_start, e=clicked_end, r=display:
                        (w.delete(s, e), w.insert(s, r))
                )
            menu.add_separator()
        menu.add_command(
            label=f'Add "{clicked_word}" to dictionary',
            command=lambda word=clicked_word, w=widget: _add_to_dict(word, w)
        )
        menu.add_separator()

    menu.add_command(label="Cut",   command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy",  command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
    menu.tk_popup(event.x_root, event.y_root)


def _add_to_dict(word, widget):
    """Add a word to the session dictionary and re-check."""
    DOMAIN_WORDS.add(word.lower())
    _spell.word_frequency.load_words([word.lower()])
    _check_widget(widget)


# ── Persistence helpers (called by ui_data.py on save/load) ─────────────────

def get_user_words():
    """Return the list of user-added words to save into the data file."""
    return sorted(DOMAIN_WORDS - _BUILTIN_DOMAIN_WORDS)


def load_user_words(words):
    """Load a list of saved user words back into the dictionary on file open."""
    for w in words:
        w = w.lower().strip()
        if w:
            DOMAIN_WORDS.add(w)
            _spell.word_frequency.load_words([w])


def attach_spellcheck(widget):
    """
    Attach real-time spell checking to a tk.Text widget.
    Call once after the widget is created.
    """
    # Red underline tag
    widget.tag_configure("misspelled", underline=True, foreground="red")

    _timer = [None]

    def _schedule_check(event=None):
        if _timer[0]:
            widget.after_cancel(_timer[0])
        _timer[0] = widget.after(_DEBOUNCE_MS, lambda: _check_widget(widget))

    widget.bind("<KeyRelease>", _schedule_check, add="+")
    widget.bind("<Button-3>", lambda e: _show_suggestions(e, widget), add="+")

    # Initial check (e.g. when loading from file)
    widget.after(100, lambda: _check_widget(widget))