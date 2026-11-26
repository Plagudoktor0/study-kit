import pytest

from studykit import theme


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def test_explicit_modes_ignore_the_system():
    assert theme.resolve_name("dark", system_dark=False) == "dark"
    assert theme.resolve_name("light", system_dark=True) == "light"


def test_system_mode_follows_the_system():
    assert theme.resolve_name("system", system_dark=True) == "dark"
    assert theme.resolve_name("system", system_dark=False) == "light"


def test_unknown_mode_behaves_like_system():
    assert theme.resolve_name("neon", system_dark=True) == "dark"


def test_mode_defaults_to_system():
    assert theme.get_mode() == "system"


def test_set_and_get_mode():
    theme.set_mode("dark")
    assert theme.get_mode() == "dark"


def test_invalid_mode_is_ignored():
    theme.set_mode("neon")
    assert theme.get_mode() == "system"


def test_both_palettes_have_the_same_keys():
    assert theme.LIGHT.keys() == theme.DARK.keys()

def test_px_scales_with_the_screen(monkeypatch):
    monkeypatch.setattr(theme, "_scale", 1.5)
    assert theme.px(100) == 150
    monkeypatch.setattr(theme, "_scale", 1.0)
    assert theme.px(100) == 100    