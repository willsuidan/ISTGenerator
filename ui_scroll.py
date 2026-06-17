"""
ui_scroll.py — Shared helpers for mouse-wheel scrolling and auto-resizing
Text widgets across the app's scrollable tabs.
"""

import tkinter as tk
from tkinter import ttk


def _scroll_step(event):
    """Return +1/-1 scroll step (in 'units') for a mousewheel/button event."""
    if getattr(event, "num", None) == 4:
        return -1
    if getattr(event, "num", None) == 5:
        return 1
    # Windows/macOS <MouseWheel>: event.delta is +/-120 (or multiples)
    return -1 if event.delta > 0 else 1


# All canvases registered via bind_mousewheel(). A single bind_all handler
# (bound once) dispatches each wheel event to whichever registered canvas is
# an ancestor of the widget under the pointer.
_registered_canvases = []
_global_handler_bound = False


def _find_target_canvas(widget):
    w = widget
    while w is not None:
        if w in _registered_canvases:
            return w
        w = getattr(w, "master", None)
    return None


def _on_global_wheel(event):
    canvas = _find_target_canvas(event.widget)
    if canvas is None:
        return None  # pointer isn't over any registered scrollable canvas

    # Walk from the widget under the pointer up to `canvas`, looking for a
    # Text/Treeview that has its own scrollable overflow. If found and not
    # yet at its top/bottom boundary, let it scroll itself. Otherwise (no
    # overflow, or already at the boundary) scroll the outer canvas instead.
    w = event.widget
    while w is not None and w is not canvas:
        if isinstance(w, (tk.Text, ttk.Treeview)):
            try:
                top, bottom = w.yview()
            except (tk.TclError, ValueError, TypeError):
                top, bottom = 0.0, 1.0
            if bottom - top < 0.999:
                step = _scroll_step(event)
                if step < 0 and top <= 0.0:
                    break  # already at top — fall through to canvas
                if step > 0 and bottom >= 1.0:
                    break  # already at bottom — fall through to canvas
                return None  # let the widget's own binding scroll it
            break  # no overflow in this widget — fall through to canvas
        w = getattr(w, "master", None)

    canvas.yview_scroll(_scroll_step(event), "units")
    return "break"


def bind_mousewheel(canvas):
    """
    Enable mouse-wheel scrolling for a vertically-scrollable Canvas while the
    pointer is anywhere over it (including child widgets).

    Text/Treeview descendants that have their own scrollable content keep
    scrolling themselves; once they hit their top/bottom the scroll passes
    through and scrolls `canvas` instead. Nested scrollable canvases (e.g. a
    smaller canvas inside a tab) take precedence over their containing
    canvas, since they're encountered first when walking up from the
    pointer's widget.
    """
    global _global_handler_bound

    if canvas not in _registered_canvases:
        _registered_canvases.append(canvas)

    if not _global_handler_bound:
        canvas.bind_all("<MouseWheel>", _on_global_wheel)
        canvas.bind_all("<Button-4>", _on_global_wheel)
        canvas.bind_all("<Button-5>", _on_global_wheel)
        _global_handler_bound = True

    def _on_destroy(_event=None):
        if canvas in _registered_canvases:
            _registered_canvases.remove(canvas)

    canvas.bind("<Destroy>", _on_destroy, add="+")


def enable_text_autoresize(text_widget, min_height=3, max_height=15):
    """
    Make a tk.Text widget grow/shrink its `height` (in display lines) to fit
    its content, clamped to [min_height, max_height]. Updates live as the
    user types, pastes, or the content is changed programmatically
    (insert/delete both raise <<Modified>>).
    """

    def _resize(_event=None):
        if not text_widget.winfo_exists():
            return
        result = text_widget.count("1.0", "end", "displaylines")
        lines = result[0] if result else 1
        lines = max(min_height, min(max_height, lines))
        if int(text_widget.cget("height")) != lines:
            text_widget.configure(height=lines)
        text_widget.edit_modified(False)

    def _on_configure(event):
        # The widget's pixel width (and thus how the text wraps into display
        # lines) is only known once the surrounding layout has settled, which
        # happens after the initial after_idle resize. Recompute whenever the
        # widget's width changes; height-only changes (e.g. our own resize)
        # are ignored to avoid feedback loops.
        last = getattr(text_widget, "_autoresize_last_width", None)
        if event.width != last:
            text_widget._autoresize_last_width = event.width
            _resize()

    text_widget.bind("<<Modified>>", _resize)
    text_widget.bind("<Configure>", _on_configure)
    text_widget.after_idle(_resize)
    return _resize
