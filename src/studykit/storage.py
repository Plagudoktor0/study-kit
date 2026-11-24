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
    """Read all data. If the file doesn't exist yet, return an empty structure."""
    path = data_path()
    if not path.exists():
        return {"deadlines": [], "exams": []}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save(data: dict) -> None:
    """Write all data to the file, creating the folder if needed."""
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)