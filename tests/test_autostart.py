import sys

from studykit import autostart


def test_command_for_frozen_exe(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\study-kit.exe")
    assert autostart.command() == r'"C:\Apps\study-kit.exe"'


def test_command_from_source_uses_pythonw(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\proj\.venv\Scripts\python.exe")
    cmd = autostart.command()
    assert "pythonw.exe" in cmd
    assert cmd.endswith("-m studykit.gui")
