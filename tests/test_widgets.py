import struct
import zlib

from studykit import widgets


class Picture:
    """Reads back a PNG made by rounded_png (8-bit RGB, no row filters)."""

    def __init__(self, png: bytes):
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        position, data = 8, b""
        while position < len(png):
            (length,) = struct.unpack(">I", png[position : position + 4])
            kind = png[position + 4 : position + 8]
            body = png[position + 8 : position + 8 + length]
            if kind == b"IHDR":
                self.width, self.height = struct.unpack(">II", body[:8])
                assert body[8:10] == bytes([8, 2])  # 8 bits per channel, RGB
            elif kind == b"IDAT":
                data += body
            position += 12 + length
        self.raw = zlib.decompress(data)

    def pixel(self, x, y):
        start = y * (self.width * 3 + 1) + 1 + x * 3
        return tuple(self.raw[start : start + 3])


BACK = "#313338"
BACK_RGB = (0x31, 0x33, 0x38)
FILL_RGB = (0x58, 0x65, 0xF2)


def picture(width, height, radius, color="#5865f2", background=BACK) -> Picture:
    return Picture(widgets.rounded_png(width, height, radius, color, background))


def test_rounded_png_is_a_valid_picture_with_the_right_size():
    image = picture(60, 30, 8)
    assert (image.width, image.height) == (60, 30)


def test_rounded_png_corners_show_the_background_and_middle_is_solid():
    image = picture(60, 30, 8)
    assert image.pixel(0, 0) == BACK_RGB  # the very corner is cut away
    assert image.pixel(59, 29) == BACK_RGB
    assert image.pixel(30, 15) == FILL_RGB
    assert image.pixel(30, 0) == FILL_RGB  # straight edges stay solid
    assert image.pixel(0, 15) == FILL_RGB


def test_rounded_png_corners_are_symmetric():
    image = picture(60, 30, 8)
    for x in range(8):
        for y in range(8):
            assert image.pixel(x, y) == image.pixel(59 - x, y)
            assert image.pixel(x, y) == image.pixel(x, 29 - y)


def test_rounded_png_has_soft_edges():
    image = picture(60, 30, 8)
    mixed = [
        image.pixel(x, y)
        for x in range(8)
        for y in range(8)
        if image.pixel(x, y) not in (BACK_RGB, FILL_RGB)
    ]
    assert mixed  # some pixels are a blend of the fill and the background


def test_rounded_png_radius_is_limited_to_half_the_height():
    image = picture(40, 10, 99)
    assert (image.width, image.height) == (40, 10)


def test_rounded_png_with_no_radius_is_all_one_color():
    image = picture(20, 10, 0)
    assert {image.pixel(x, y) for x in range(20) for y in range(10)} == {FILL_RGB}


class FakeTree:
    """The few Treeview methods RowHover uses."""

    def __init__(self, rows):
        self.rows = {name: tuple(tags) for name, tags in rows.items()}
        self.selected = ()
        self.row_at = {}
        self.bindings = {}

    def bind(self, sequence, func, add=None):
        self.bindings[sequence] = func

    def identify_row(self, y):
        return self.row_at.get(y, "")

    def selection(self):
        return self.selected

    def exists(self, item):
        return item in self.rows

    def item(self, item, option=None, tags=None):
        if tags is not None:
            self.rows[item] = tuple(tags)
            return None
        return self.rows[item]


class Event:
    def __init__(self, y):
        self.y = y


def make_hover():
    tree = FakeTree({"a": ("overdue",), "b": (), "c": ("finished",)})
    tree.row_at = {10: "a", 40: "b", 70: "c"}
    return tree, widgets.RowHover(tree)


def test_hover_adds_the_tag_and_keeps_the_other_tags():
    tree, hover = make_hover()
    hover.on_motion(Event(10))
    assert tree.rows["a"] == ("overdue", widgets.HOVER_TAG)


def test_hover_moves_with_the_mouse():
    tree, hover = make_hover()
    hover.on_motion(Event(10))
    hover.on_motion(Event(40))
    assert tree.rows["a"] == ("overdue",)
    assert tree.rows["b"] == (widgets.HOVER_TAG,)


def test_hover_is_removed_when_the_mouse_leaves():
    tree, hover = make_hover()
    hover.on_motion(Event(70))
    hover.on_leave()
    assert tree.rows["c"] == ("finished",)


def test_selected_row_is_not_highlighted():
    tree, hover = make_hover()
    tree.selected = ("b",)
    hover.on_motion(Event(40))
    assert tree.rows["b"] == ()


def test_hover_survives_a_row_that_was_deleted():
    tree, hover = make_hover()
    hover.on_motion(Event(10))
    del tree.rows["a"]
    hover.on_motion(Event(40))  # must not crash
    assert tree.rows["b"] == (widgets.HOVER_TAG,)


def test_hover_over_empty_space_clears_the_highlight():
    tree, hover = make_hover()
    hover.on_motion(Event(10))
    hover.on_motion(Event(999))
    assert tree.rows["a"] == ("overdue",)
