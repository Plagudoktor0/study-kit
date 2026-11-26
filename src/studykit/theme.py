import sys

from studykit import storage

MODES = ("system", "light", "dark")

LIGHT = {
    "bg": "#f3f3f3",
    "fg": "#1e1e1e",
    "field": "#ffffff",
    "button": "#e1e1e1",
    "border": "#b8b8b8",
    "select": "#0078d4",
    "select_fg": "#ffffff",
    "overdue": "#c0392b",
    "soon": "#d68910",
    "finished": "#7f8c8d",
}

DARK = {
    "bg": "#1e1e1e",
    "fg": "#e6e6e6",
    "field": "#2b2b2b",
    "button": "#3a3a3a",
    "border": "#5a5a5a",
    "select": "#0a64ad",
    "select_fg": "#ffffff",
    "overdue": "#ff6b6b",
    "soon": "#f0a030",
    "finished": "#8a8a8a",
}

PALETTES = {"light": LIGHT, "dark": DARK}

_current = LIGHT


def palette() -> dict:
    """Colors of the theme that is currently applied."""
    return _current


def get_mode() -> str:
    mode = storage.load()["settings"].get("theme", "system")
    return mode if mode in MODES else "system"


def set_mode(mode: str) -> None:
    if mode not in MODES:
        return
    data = storage.load()
    data["settings"]["theme"] = mode
    storage.save(data)


def system_is_dark() -> bool:
    """True if Windows is set to dark mode for apps."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except OSError:
        return False


def resolve_name(mode: str, system_dark: bool) -> str:
    """Turn a mode ('system', 'light', 'dark') into 'light' or 'dark'."""
    if mode == "dark":
        return "dark"
    if mode == "light":
        return "light"
    return "dark" if system_dark else "light"


def apply(root, mode: str) -> str:
    """Style the whole app for the chosen mode. Returns 'light' or 'dark'."""
    from tkinter import ttk

    global _current
    name = resolve_name(mode, system_is_dark())
    p = PALETTES[name]
    _current = p

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=p["bg"],
        foreground=p["fg"],
        fieldbackground=p["field"],
        bordercolor=p["border"],
        troughcolor=p["button"],
    )
    style.configure(
        "TButton",
        background=p["button"],
        foreground=p["fg"],
        bordercolor=p["border"],
        focuscolor=p["button"],
        padding=(8, 3),
    )
    style.map("TButton", background=[("active", p["border"]), ("pressed", p["border"])])
    style.configure(
        "TCheckbutton",
        background=p["bg"],
        foreground=p["fg"],
        indicatorbackground=p["field"],
        indicatorforeground=p["fg"],
    )
    style.map("TCheckbutton", background=[("active", p["bg"])])
    style.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"], insertcolor=p["fg"])
    style.map("TEntry", fieldbackground=[("readonly", p["button"])])
    style.configure(
        "TCombobox",
        fieldbackground=p["field"],
        background=p["button"],
        foreground=p["fg"],
        arrowcolor=p["fg"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p["field"])],
        foreground=[("readonly", p["fg"])],
        selectbackground=[("readonly", p["field"])],
        selectforeground=[("readonly", p["fg"])],
    )
    style.configure(
        "Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"]
    )
    style.map(
        "Treeview",
        background=[("selected", p["select"])],
        foreground=[("selected", p["select_fg"])],
    )
    style.configure(
        "Treeview.Heading",
        background=p["button"],
        foreground=p["fg"],
        bordercolor=p["border"],
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", p["border"])])
    style.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
    style.configure("TNotebook.Tab", background=p["button"], foreground=p["fg"], padding=(12, 4))
    style.map(
        "TNotebook.Tab",
        background=[("selected", p["bg"])],
        foreground=[("selected", p["fg"])],
    )

    # plain tk widgets (windows, text boxes, dropdown lists) use the option database
    root.configure(bg=p["bg"])
    root.option_add("*Toplevel.background", p["bg"])
    root.option_add("*Text.background", p["field"])
    root.option_add("*Text.foreground", p["fg"])
    root.option_add("*Text.insertBackground", p["fg"])
    root.option_add("*Text.selectBackground", p["select"])
    root.option_add("*Text.selectForeground", p["select_fg"])
    root.option_add("*TCombobox*Listbox.background", p["field"])
    root.option_add("*TCombobox*Listbox.foreground", p["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["select"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["select_fg"])
    return name