import json
import os
from pathlib import Path


def data_path() -> Path:
    """Where the data file lives. Can be overridden for tests."""
    custom = os.environ.get("STUDYKIT_DATA")
    if custom:
        return Path(custom)
    return Path.home() / ".studykit" / "data.json"


def load() -> dict:
    """Read all data. Missing parts are filled in, so old data files keep working."""
    path = data_path()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    for key in ("deadlines", "exams", "subjects"):
        data.setdefault(key, [])
    data.setdefault("settings", {})
    return data


def save(data: dict) -> None:
    """Write all data to the file, creating the folder if needed."""
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
