"""Reusable visual components and lightweight tooltips."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class MetricCard(ttk.Frame):
    def __init__(self, master, title: str, value: str, subtitle: str = "", accent: str | None = None):
        super().__init__(master, style="Card.TFrame", padding=(16, 14))
        self.grid_columnconfigure(0, weight=1)
        self.title_label = ttk.Label(self, text=title.upper(), style="CardTitle.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.value_label = ttk.Label(self, text=value, style="Metric.TLabel")
        self.value_label.grid(row=1, column=0, sticky="w", pady=(9, 3))
        self.subtitle_label = ttk.Label(self, text=subtitle, style="MutedCard.TLabel", wraplength=250)
        self.subtitle_label.grid(row=2, column=0, sticky="w")
        self._accent = accent
        if accent:
            self.configure(padding=(16, 14))

    def set_values(self, value: str, subtitle: str | None = None) -> None:
        self.value_label.configure(text=value)
        if subtitle is not None:
            self.subtitle_label.configure(text=subtitle)


class ToolTip:
    """Small delayed tooltip, using Tk's event loop only."""
    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel_schedule()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self) -> None:
        if self._window or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._window = tk.Toplevel(self.widget)
        self._window.wm_overrideredirect(True)
        self._window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self._window,
            text=self.text,
            justify="left",
            background="#202B3C",
            foreground="#F1F5F9",
            padx=10,
            pady=7,
            font=("Segoe UI", 9),
            relief="solid",
            borderwidth=1,
        )
        label.pack()

    def _cancel_schedule(self) -> None:
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _hide(self, _event=None) -> None:
        self._cancel_schedule()
        if self._window:
            try:
                self._window.destroy()
            except tk.TclError:
                pass
            self._window = None
