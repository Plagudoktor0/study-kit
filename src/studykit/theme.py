import sys

from studykit import storage

MODES = ("system", "light", "dark")

# Colors. Layers, from the back to the front:
#   bg      the window
#   field   panels: the table, the summary cards, text boxes
#   input   text fields and dropdowns (the deepest layer in the dark theme)
# Dark theme borders are invisible on purpose: the layers separate things, not outlines.
LIGHT = {
    "bg": "#f3f3f3",
    "fg": "#1e1e1e",
    "field": "#ffffff",
    "input": "#ffffff",
    "outline": "#bdbdbd",  # thin edge of text fields (invisible in the dark theme)
    "button": "#e1e1e1",
    "button_hover": "#d3d3d3",
    "button_pressed": "#c4c4c4",
    "border": "#d9d9d9",
    "select": "#0078d4",
    "select_fg": "#ffffff",
    "accent": "#0067c0",
    "accent_hover": "#00539a",
    "accent_pressed": "#004278",
    "success": "#2e7d32",
    "success_hover": "#256628",
    "success_pressed": "#1d521f",
    "danger": "#c0392b",
    "danger_hover": "#a53024",
    "danger_pressed": "#8a281e",
    "overdue": "#c0392b",
    "soon": "#d68910",
    "finished": "#7f8c8d",
    "muted": "#6b6b6b",
}

DARK = {
    "bg": "#313338",
    "fg": "#dbdee1",
    "field": "#2b2d31",
    "input": "#1e1f22",
    "outline": "#1e1f22",
    "button": "#4e5058",
    "button_hover": "#5f626b",
    "button_pressed": "#42444b",
    "border": "#2b2d31",
    "select": "#404249",
    "select_fg": "#ffffff",
    "accent": "#5865f2",
    "accent_hover": "#4752c4",
    "accent_pressed": "#3c45a5",
    "success": "#248046",
    "success_hover": "#1a6334",
    "success_pressed": "#154f2a",
    "danger": "#da373c",
    "danger_hover": "#a12828",
    "danger_pressed": "#8a2222",
    "overdue": "#f23f43",
    "soon": "#f0b232",
    "finished": "#80848e",
    "muted": "#949ba4",
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
    """True if the operating system is set to dark mode for apps."""
    if sys.platform == "darwin":
        import subprocess

        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
            )
        except OSError:
            return False
        return result.stdout.strip() == "Dark"
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
    _scale = root.winfo_fpixels("1i") / 96 if sys.platform == "win32" else 1.0

    if sys.platform == "win32":
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(font_name).configure(family="Segoe UI", size=10)
    default_font = tkfont.nametofont("TkDefaultFont")
    heading_font = (default_font.actual("family"), abs(default_font.actual("size")), "bold")

    style = ttk.Style(root)
    style.theme_use("clam")

    # Flat look: every border and 3D edge gets the color of what is behind it,
    # so nothing is outlined unless we say so. `flat(color)` is that setting.
    def flat(color):
        return {"bordercolor": color, "lightcolor": color, "darkcolor": color}

    def flat_map(**states):
        """Same as flat(), but with a different color per widget state."""
        result = {"bordercolor": [], "lightcolor": [], "darkcolor": []}
        for state, color in states.items():
            for key in result:
                result[key].append((state, color))
        return result

    style.configure(
        ".",
        background=p["bg"],
        foreground=p["fg"],
        fieldbackground=p["input"],
        troughcolor=p["input"],
        focuscolor=p["bg"],
        borderwidth=0,
        **flat(p["bg"]),
    )

    def button(name, base, hover, pressed, fg="#ffffff"):
        style.configure(
            name,
            background=base,
            foreground=fg,
            focuscolor=base,
            focusthickness=0,
            borderwidth=0,
            relief="flat",
            padding=(px(14), px(6)),
            **flat(base),
        )
        states = {"disabled": p["button"], "pressed": pressed, "active": hover}
        style.map(
            name,
            background=[(state, color) for state, color in states.items()],
            foreground=[("disabled", p["muted"])],
            **flat_map(**states),
        )

    button("TButton", p["button"], p["button_hover"], p["button_pressed"], fg=p["fg"])
    button("Accent.TButton", p["accent"], p["accent_hover"], p["accent_pressed"])
    button("Success.TButton", p["success"], p["success_hover"], p["success_pressed"])
    button("Danger.TButton", p["danger"], p["danger_hover"], p["danger_pressed"])

    style.configure(
        "TCheckbutton",
        background=p["bg"],
        foreground=p["fg"],
        indicatorbackground=p["input"],
        indicatorforeground=p["fg"],
        indicatormargin=(0, 0, px(6), 0),
        upperbordercolor=p["muted"],
        lowerbordercolor=p["muted"],
        focuscolor=p["bg"],
    )
    style.map(
        "TCheckbutton",
        background=[("active", p["bg"])],
        indicatorbackground=[("selected", p["accent"]), ("active", p["field"])],
        indicatorforeground=[("selected", "#ffffff")],
        upperbordercolor=[("selected", p["accent"])],
        lowerbordercolor=[("selected", p["accent"])],
    )

    # text fields: no edge in the dark theme, a thin one in the light theme, accent when typing
    field_edge = {"bordercolor": p["outline"], "lightcolor": p["input"], "darkcolor": p["input"]}
    focus_edge = {
        "bordercolor": [("focus", p["accent"])],
        "lightcolor": [("focus", p["accent"])],
        "darkcolor": [("focus", p["accent"])],
    }
    style.configure(
        "TEntry",
        fieldbackground=p["input"],
        foreground=p["fg"],
        insertcolor=p["fg"],
        padding=px(6),
        borderwidth=1,
        **field_edge,
    )
    style.map("TEntry", fieldbackground=[("readonly", p["input"])], **focus_edge)
    style.configure(
        "TCombobox",
        fieldbackground=p["input"],
        background=p["input"],
        foreground=p["fg"],
        arrowcolor=p["muted"],
        arrowsize=px(14),
        padding=px(6),
        borderwidth=1,
        **field_edge,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p["input"])],
        background=[("active", p["input"]), ("readonly", p["input"])],
        foreground=[("readonly", p["fg"])],
        arrowcolor=[("active", p["fg"])],
        selectbackground=[("readonly", p["input"])],
        selectforeground=[("readonly", p["fg"])],
        **focus_edge,
    )

    # the table
    style.configure(
        "Treeview",
        background=p["field"],
        fieldbackground=p["field"],
        foreground=p["fg"],
        rowheight=px(34),
        borderwidth=0,
        **flat(p["field"]),
    )
    style.map(
        "Treeview",
        background=[("selected", p["select"])],
        foreground=[("selected", p["select_fg"])],
    )
    style.configure(
        "Treeview.Heading",
        background=p["bg"],
        foreground=p["muted"],
        relief="flat",
        borderwidth=0,
        font=heading_font,
        padding=(px(8), px(8)),
        **flat(p["bg"]),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", p["bg"])],
        foreground=[("active", p["fg"])],
    )

    # tabs: the selected tab melts into the page, the others are a darker strip
    style.configure(
        "TNotebook",
        background=p["bg"],
        borderwidth=0,
        tabmargins=(px(10), px(8), px(10), 0),
        **flat(p["bg"]),
    )
    style.configure(
        "TNotebook.Tab",
        background=p["field"],
        foreground=p["muted"],
        padding=(px(18), px(8)),
        borderwidth=0,
        focuscolor=p["bg"],
        **flat(p["field"]),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", p["bg"]), ("active", p["button"])],
        foreground=[("selected", p["fg"]), ("active", p["fg"])],
        **flat_map(selected=p["bg"], active=p["button"]),
    )

    style.configure(
        "Horizontal.TProgressbar",
        background=p["accent"],
        troughcolor=p["input"],
        thickness=px(8),
        borderwidth=0,
        **flat(p["accent"]),
    )
    for orient in ("Vertical", "Horizontal"):
        style.configure(
            f"{orient}.TScrollbar",
            background=p["button"],
            troughcolor=p["bg"],
            arrowcolor=p["muted"],
            gripcount=0,
            borderwidth=0,
            **flat(p["button"]),
        )
        style.map(
            f"{orient}.TScrollbar",
            background=[("active", p["button_hover"])],
            **flat_map(active=p["button_hover"]),
        )

    # dashboard cards, headings, empty-state hints
    family = default_font.actual("family")
    size = abs(default_font.actual("size"))
    style.configure(
        "CardValue.TLabel",
        background=p["field"],
        foreground=p["fg"],
        font=(family, size * 2, "bold"),
    )
    style.configure("Danger.CardValue.TLabel", foreground=p["overdue"])
    style.configure("Warn.CardValue.TLabel", foreground=p["soon"])
    style.configure("Quiet.CardValue.TLabel", foreground=p["finished"])
    style.configure("CardCaption.TLabel", background=p["field"], foreground=p["muted"])
    style.configure("Empty.TLabel", background=p["field"], foreground=p["muted"])
    style.configure("Heading.TLabel", font=(family, size + 1, "bold"))

    # plain tk widgets (windows, text boxes, dropdown lists) use the option database
    root.configure(bg=p["bg"])
    root.option_add("*Toplevel.background", p["bg"])
    root.option_add("*Text.background", p["field"])
    root.option_add("*Text.foreground", p["fg"])
    root.option_add("*Text.insertBackground", p["fg"])
    root.option_add("*Text.selectBackground", p["select"])
    root.option_add("*Text.selectForeground", p["select_fg"])
    root.option_add("*TCombobox*Listbox.background", p["input"])
    root.option_add("*TCombobox*Listbox.foreground", p["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["select"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["select_fg"])
    return name
