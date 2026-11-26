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
    "accent": "#0067c0",
    "accent_hover": "#00539a",
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
    "accent": "#2f81d6",
    "accent_hover": "#4a95e6",
    "overdue": "#ff6b6b",
    "soon": "#f0a030",
    "finished": "#8a8a8a",
}

PALETTES = {"light": LIGHT, "dark": DARK}

_current = LIGHT
_scale = 1.0


def palette() -> dict:
    """Colors of the theme that is currently applied."""
    return _current


def px(value: int) -> int:
    """Convert a size designed for a 96-DPI screen to real pixels on this screen."""
    return round(value * _scale)


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


def enable_high_dpi() -> None:
    """Tell Windows the app draws itself sharply. Must run before the first window exists."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass  # sharpness is nice to have, never a reason to crash


def apply(root, mode: str) -> str:
    """Style the whole app for the chosen mode. Returns 'light' or 'dark'."""
    import tkinter.font as tkfont
    from tkinter import ttk

    global _current, _scale
    name = resolve_name(mode, system_is_dark())
    p = PALETTES[name]
    _current = p
    _scale = root.winfo_fpixels("1i") / 96  # 1.0 at 100% Windows scale, 1.5 at 150%

    if sys.platform == "win32":
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(font_name).configure(family="Segoe UI", size=10)
    default_font = tkfont.nametofont("TkDefaultFont")
    heading_font = (default_font.actual("family"), abs(default_font.actual("size")), "bold")

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
        padding=(px(12), px(5)),
    )
    style.map("TButton", background=[("active", p["border"]), ("pressed", p["border"])])
    style.configure(
        "Accent.TButton",
        background=p["accent"],
        foreground="#ffffff",
        bordercolor=p["accent"],
        focuscolor=p["accent"],
        padding=(px(14), px(5)),
    )
    style.map(
        "Accent.TButton",
        background=[("active", p["accent_hover"]), ("pressed", p["accent_hover"])],
    )
    style.configure(
        "TCheckbutton",
        background=p["bg"],
        foreground=p["fg"],
        indicatorbackground=p["field"],
        indicatorforeground=p["fg"],
    )
    style.map("TCheckbutton", background=[("active", p["bg"])])
    style.configure(
        "TEntry",
        fieldbackground=p["field"],
        foreground=p["fg"],
        insertcolor=p["fg"],
        padding=px(4),
    )
    style.map("TEntry", fieldbackground=[("readonly", p["button"])])
    style.configure(
        "TCombobox",
        fieldbackground=p["field"],
        background=p["button"],
        foreground=p["fg"],
        arrowcolor=p["fg"],
        padding=px(4),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p["field"])],
        foreground=[("readonly", p["fg"])],
        selectbackground=[("readonly", p["field"])],
        selectforeground=[("readonly", p["fg"])],
    )
    style.configure(
        "Treeview",
        background=p["field"],
        fieldbackground=p["field"],
        foreground=p["fg"],
        rowheight=px(30),
        bordercolor=p["border"],
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
        font=heading_font,
        padding=px(6),
    )
    style.map("Treeview.Heading", background=[("active", p["border"])])
    style.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
    style.configure(
        "TNotebook.Tab", background=p["button"], foreground=p["fg"], padding=(px(16), px(7))
    )
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