"""Custom widgets: a rounded, smooth button and a hover highlight for tables.

The standard ttk buttons can't have rounded corners, so `Button` draws its own shape.
The shape is a small picture made here in pure Python (no extra packages), with soft
edges, so the corners do not look jagged.

Speed: pictures are shared between buttons and made once per size and color, a button
only changes its picture when something really changed, and the pictures have no
transparency (see-through pictures are slow to draw in Tk on Windows).
"""

import base64
import os
import struct
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
import weakref
import zlib
from functools import lru_cache
from math import hypot

from studykit import theme

HOVER_TAG = "hover"

# style name -> (palette key for normal / hover / pressed, text color or None for the theme text)
_STYLES = {
    "TButton": ("button", "button_hover", "button_pressed", None),
    "Accent.TButton": ("accent", "accent_hover", "accent_pressed", "#ffffff"),
    "Success.TButton": ("success", "success_hover", "success_pressed", "#ffffff"),
    "Danger.TButton": ("danger", "danger_hover", "danger_pressed", "#ffffff"),
}

_buttons: "weakref.WeakSet[RoundButton]" = weakref.WeakSet()


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _rgb(color: str) -> tuple:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))


@lru_cache(maxsize=256)
def rounded_png(width: int, height: int, radius: int, color: str, background: str) -> bytes:
    """A PNG picture of a filled rounded rectangle on a flat background.

    `color` and `background` are '#rrggbb'. The corners are soft (anti-aliased): they fade from
    `color` into `background`. The picture has no transparency on purpose: drawing see-through
    pictures is slow in Tk on Windows, and the button always sits on the same background.
    """
    fill, back = _rgb(color), _rgb(background)
    radius = max(0, min(radius, width // 2, height // 2))
    solid = bytes(fill)
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # PNG row filter: none
        y_center = y + 0.5
        dy = max(radius - y_center, y_center - (height - radius), 0)
        if dy == 0:
            rows += solid * width  # a row without corners: one color all the way
            continue
        left = []
        for x in range(radius):
            coverage = min(max(radius - hypot(radius - (x + 0.5), dy) + 0.5, 0.0), 1.0)
            left.append(bytes(round(back[i] + (fill[i] - back[i]) * coverage) for i in range(3)))
        rows += b"".join(left) + solid * (width - 2 * radius) + b"".join(reversed(left))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(rows), 1))
        + _chunk(b"IEND", b"")
    )


_photos: dict = {}  # pictures shared by all buttons: (w, h, radius, color, background) -> picture


def _photo(master, width, height, radius, color, background):
    key = (width, height, radius, color, background)
    image = _photos.get(key)
    if image is None:
        if len(_photos) > 200:  # window was resized a lot: forget old sizes
            _photos.clear()
        png = rounded_png(width, height, radius, color, background)
        image = tk.PhotoImage(master=master, data=base64.b64encode(png))
        _photos[key] = image
    return image


class RoundButton(tk.Canvas):
    """A rounded button. Used like ttk.Button: Button(parent, text=..., style=..., command=...).

    Styles: 'TButton' (grey, the default), 'Accent.TButton', 'Success.TButton', 'Danger.TButton'.
    `configure(state='disabled')` / `configure(state='normal')` work like on a ttk button.
    """

    def __init__(self, parent, text="", command=None, style="TButton", width=None, state="normal"):
        self._text = text
        self._command = command
        self._style = style if style in _STYLES else "TButton"
        self._state = state
        self._hover = False
        self._pressed = False
        self._focused = False
        self._drawn = None  # what is on screen now, so we never draw the same thing twice
        self._image = None  # keeps the current picture alive

        self._font = tkfont.nametofont("TkDefaultFont")
        pad_x, pad_y = theme.px(16), theme.px(8)
        text_width = self._font.measure(text)
        if width:  # like ttk: a minimum width counted in characters
            text_width = max(text_width, width * self._font.measure("0"))
        self._width = text_width + 2 * pad_x
        self._height = self._font.metrics("linespace") + 2 * pad_y

        super().__init__(
            parent,
            width=self._width,
            height=self._height,
            highlightthickness=0,
            borderwidth=0,
            takefocus=True,
        )
        self._image_item = self.create_image(0, 0, anchor="nw")
        self._text_item = self.create_text(0, 0, anchor="center", font=self._font)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", lambda event: self._set(focused=True))
        self.bind("<FocusOut>", lambda event: self._set(focused=False))
        self.bind("<Return>", self._on_key)
        self.bind("<space>", self._on_key)
        self.bind("<Configure>", lambda event: self.redraw())
        _buttons.add(self)
        self.restyle()

    # ----- same names as ttk.Button -----

    def configure(self, cnf=None, **options):
        if cnf is None and not options:
            return super().configure()
        options = dict(cnf or {}, **options)
        changed = False
        if "state" in options:
            self._state = options.pop("state")
            changed = True
        if "text" in options:
            self._text = options.pop("text")
            changed = True
        if "command" in options:
            self._command = options.pop("command")
        if options:
            super().configure(**options)
        if changed:
            self.restyle()

    config = configure

    def invoke(self):
        if self._state != "disabled" and self._command:
            self._command()

    # ----- drawing -----

    def restyle(self):
        """Pick up the current theme colors and draw again."""
        self._drawn = None
        super().configure(bg=theme.palette()["bg"], cursor=self._cursor())
        self.redraw()

    def _cursor(self) -> str:
        return "" if self._state == "disabled" else "hand2"

    def _set(self, **flags):
        changed = False
        for name, value in flags.items():
            if getattr(self, f"_{name}") != value:
                setattr(self, f"_{name}", value)
                changed = True
        if changed:
            self.redraw()

    def redraw(self):
        palette = theme.palette()
        normal, hover, pressed, text_color = _STYLES[self._style]
        if self._state == "disabled":
            fill, text_color = palette["button"], palette["muted"]
        else:
            text_color = text_color or palette["fg"]
            if self._pressed:
                fill = palette[pressed]
            elif self._hover or self._focused:
                fill = palette[hover]
            else:
                fill = palette[normal]

        width = self.winfo_width() if self.winfo_width() > 1 else self._width
        height = self.winfo_height() if self.winfo_height() > 1 else self._height
        state = (fill, text_color, width, height, self._text, palette["bg"])
        if state == self._drawn:
            return
        self._drawn = state

        radius = min(theme.px(8), height // 2)
        self._image = _photo(self, width, height, radius, fill, palette["bg"])
        self.itemconfigure(self._image_item, image=self._image)
        self.coords(self._text_item, width / 2, height / 2)
        self.itemconfigure(self._text_item, text=self._text, fill=text_color)

    # ----- mouse and keyboard -----

    def _on_enter(self, event):
        self._set(hover=True)

    def _on_leave(self, event):
        self._set(hover=False, pressed=False)

    def _on_press(self, event):
        if self._state != "disabled":
            self._set(pressed=True)

    def _on_release(self, event):
        was_pressed = self._pressed
        self._set(pressed=False)
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        if was_pressed and inside:
            self.invoke()

    def _on_key(self, event):
        self.invoke()
        return "break"


def Button(parent, **options):  # noqa: N802 - used like a class: Button(parent, text=...)
    """A rounded button. Set STUDYKIT_PLAIN_BUTTONS=1 to get the plain Windows-style ones."""
    if os.environ.get("STUDYKIT_PLAIN_BUTTONS"):
        return ttk.Button(parent, **options)
    return RoundButton(parent, **options)


def restyle_all_buttons() -> None:
    """Call after the theme changed, so every open button gets the new colors."""
    for button in list(_buttons):
        try:
            if button.winfo_exists():
                button.restyle()
        except tk.TclError:
            pass


class RowHover:
    """Highlights the table row under the mouse (never the selected row).

    The color comes from a tag called HOVER_TAG: set it with
    `tree.tag_configure(HOVER_TAG, background=...)`.
    """

    def __init__(self, tree):
        self.tree = tree
        self.item = ""
        tree.bind("<Motion>", self.on_motion, add="+")
        tree.bind("<Leave>", self.on_leave, add="+")
        tree.bind("<<TreeviewSelect>>", self.on_leave, add="+")

    def _tags(self, item) -> list:
        tags = self.tree.item(item, "tags") or ()
        if isinstance(tags, str):
            tags = tags.split()
        return list(tags)

    def clear(self):
        if self.item and self.tree.exists(self.item):
            tags = [tag for tag in self._tags(self.item) if tag != HOVER_TAG]
            self.tree.item(self.item, tags=tags)
        self.item = ""

    def on_motion(self, event):
        item = self.tree.identify_row(event.y)
        if item == self.item:
            return
        self.clear()
        if item and item not in self.tree.selection():
            self.tree.item(item, tags=self._tags(item) + [HOVER_TAG])
            self.item = item

    def on_leave(self, event=None):
        self.clear()
