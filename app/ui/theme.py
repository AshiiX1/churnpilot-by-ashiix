"""A small, consistent light/dark design system for ttk."""
from __future__ import annotations

from tkinter import ttk

PALETTES = {
    "dark": {
        "background": "#10151F",
        "surface": "#171F2D",
        "surface_alt": "#202B3C",
        "sidebar": "#121A27",
        "text": "#F1F5F9",
        "muted": "#9AA8BA",
        "border": "#2B384A",
        "accent": "#6D8DFF",
        "accent_hover": "#87A0FF",
        "accent_text": "#FFFFFF",
        "success": "#41C99A",
        "warning": "#F3B95F",
        "danger": "#F07474",
        "tree_select": "#2D4272",
        "entry": "#111925",
    },
    "light": {
        "background": "#F4F7FB",
        "surface": "#FFFFFF",
        "surface_alt": "#EDF2F8",
        "sidebar": "#FFFFFF",
        "text": "#182230",
        "muted": "#627084",
        "border": "#DCE4EE",
        "accent": "#355FEA",
        "accent_hover": "#244AD0",
        "accent_text": "#FFFFFF",
        "success": "#16835F",
        "warning": "#99610D",
        "danger": "#B42318",
        "tree_select": "#DDE7FF",
        "entry": "#FFFFFF",
    },
}


def apply_theme(root, theme: str) -> dict[str, str]:
    name = theme if theme in PALETTES else "dark"
    colors = PALETTES[name]
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.configure(background=colors["background"])
    style.configure(".", font=("Segoe UI", 10), foreground=colors["text"], background=colors["background"])
    style.configure("TFrame", background=colors["background"])
    style.configure("App.TFrame", background=colors["background"])
    style.configure("Sidebar.TFrame", background=colors["sidebar"])
    style.configure("Content.TFrame", background=colors["background"])
    style.configure("Card.TFrame", background=colors["surface"], bordercolor=colors["border"], relief="solid", borderwidth=1)
    style.configure("Inset.TFrame", background=colors["surface_alt"])
    style.configure("TLabel", background=colors["background"], foreground=colors["text"])
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 23), background=colors["background"], foreground=colors["text"])
    style.configure("Subtitle.TLabel", font=("Segoe UI", 10), background=colors["background"], foreground=colors["muted"])
    style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 10), background=colors["surface"], foreground=colors["muted"])
    style.configure("Metric.TLabel", font=("Segoe UI Semibold", 24), background=colors["surface"], foreground=colors["text"])
    style.configure("CardBody.TLabel", background=colors["surface"], foreground=colors["text"])
    style.configure("Muted.TLabel", background=colors["background"], foreground=colors["muted"])
    style.configure("BrandFooter.TLabel", font=("Segoe UI", 8), background=colors["background"], foreground=colors["muted"])
    style.configure("MutedCard.TLabel", background=colors["surface"], foreground=colors["muted"])
    style.configure("SidebarBrand.TLabel", font=("Segoe UI Semibold", 15), background=colors["sidebar"], foreground=colors["text"])
    style.configure("SidebarHint.TLabel", font=("Segoe UI", 9), background=colors["sidebar"], foreground=colors["muted"])
    style.configure("Nav.TButton", anchor="w", padding=(14, 11), relief="flat", borderwidth=0,
                    background=colors["sidebar"], foreground=colors["muted"], font=("Segoe UI Semibold", 10))
    style.map("Nav.TButton", background=[("active", colors["surface_alt"])], foreground=[("active", colors["text"])])
    style.configure("NavActive.TButton", anchor="w", padding=(14, 11), relief="flat", borderwidth=0,
                    background=colors["accent"], foreground=colors["accent_text"], font=("Segoe UI Semibold", 10))
    style.map("NavActive.TButton", background=[("active", colors["accent_hover"])])
    style.configure("TButton", padding=(12, 8), background=colors["surface_alt"], foreground=colors["text"], bordercolor=colors["border"])
    style.map("TButton", background=[("active", colors["border"]), ("disabled", colors["surface_alt"])])
    style.configure("Accent.TButton", padding=(14, 9), background=colors["accent"], foreground=colors["accent_text"], bordercolor=colors["accent"], font=("Segoe UI Semibold", 10))
    style.map("Accent.TButton", background=[("active", colors["accent_hover"])], foreground=[("disabled", colors["muted"])])
    style.configure("Danger.TButton", padding=(12, 8), background=colors["surface"], foreground=colors["danger"], bordercolor=colors["border"])
    style.map("Danger.TButton", background=[("active", colors["surface_alt"])])
    style.configure("TEntry", padding=8, fieldbackground=colors["entry"], foreground=colors["text"], bordercolor=colors["border"])
    style.map("TEntry", fieldbackground=[("readonly", colors["surface_alt"])])
    style.configure("TCombobox", padding=7, fieldbackground=colors["entry"], background=colors["surface_alt"], foreground=colors["text"], arrowcolor=colors["muted"], bordercolor=colors["border"])
    style.map("TCombobox", fieldbackground=[("readonly", colors["entry"])], foreground=[("readonly", colors["text"])], selectbackground=[("readonly", colors["entry"])], selectforeground=[("readonly", colors["text"])])
    style.configure("TLabelframe", background=colors["surface"], foreground=colors["text"], bordercolor=colors["border"], padding=10)
    style.configure("TLabelframe.Label", background=colors["surface"], foreground=colors["text"], font=("Segoe UI Semibold", 10))
    style.configure("Treeview", background=colors["surface"], fieldbackground=colors["surface"], foreground=colors["text"], rowheight=32, bordercolor=colors["border"], relief="flat")
    style.configure("Treeview.Heading", background=colors["surface_alt"], foreground=colors["muted"], font=("Segoe UI Semibold", 9), padding=8, bordercolor=colors["border"])
    style.map("Treeview", background=[("selected", colors["tree_select"])], foreground=[("selected", colors["text"])])
    style.configure("Horizontal.TProgressbar", troughcolor=colors["surface_alt"], background=colors["accent"], bordercolor=colors["border"], lightcolor=colors["accent"], darkcolor=colors["accent"])
    style.configure("Status.TLabel", background=colors["surface_alt"], foreground=colors["muted"], padding=(8, 5), font=("Segoe UI", 9))
    style.configure("Pill.TLabel", background=colors["surface_alt"], foreground=colors["muted"], padding=(9, 4), font=("Segoe UI Semibold", 9))
    style.configure("Success.TLabel", background=colors["surface"], foreground=colors["success"], font=("Segoe UI Semibold", 11))
    style.configure("Warning.TLabel", background=colors["surface"], foreground=colors["warning"], font=("Segoe UI Semibold", 11))
    style.configure("Danger.TLabel", background=colors["surface"], foreground=colors["danger"], font=("Segoe UI Semibold", 11))
    return colors
