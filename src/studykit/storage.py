import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


def data_path() -> Path:
    """Where the data file lives. Can be overridden for tests."""
    custom = os.environ.get("STUDYKIT_DATA")
    if custom:
        return Path(custom)
    return Path.home() / ".studykit" / "data.json"


def _back_up_broken_file(path: Path) -> None:
    """Rename an unreadable data file so it is kept for inspection, not overwritten."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        os.replace(path, backup)
    except OSError:
        pass  # if even the rename fails, still start with empty data


def load() -> dict:
    """Read all data. Missing parts are filled in, so old data files keep working.

    If the file is damaged (not valid JSON), it is renamed to data.json.corrupt-<time>
    and the app starts with empty data instead of crashing.
    """
    path = data_path()
    data = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except ValueError:  # includes JSONDecodeError and UnicodeDecodeError
            data = None
        if not isinstance(data, dict):  # damaged, or not a JSON object
            _back_up_broken_file(path)
            data = {}
    for key in ("deadlines", "exams", "subjects"):
        data.setdefault(key, [])
    data.setdefault("settings", {})
    return data


def save(data: dict) -> None:
    """Write all data safely: write a temp file first, then swap it in.

    If the program or the PC stops in the middle, the old data file is still intact.
    """
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, path)  # atomic: the file is either the old one or the new one
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
