"""Save all deadlines and exams to a file, and load them back (merge or replace)."""

import json
import shutil
from datetime import date, datetime
from pathlib import Path

from studykit import storage

FORMAT_NAME = "study-kit-backup"
FORMAT_VERSION = 1


class BackupError(Exception):
    """A problem the user can understand: missing file, wrong file type, bad data."""


def export_data(path) -> dict:
    """Write deadlines, exams and subjects to `path`. Returns how many of each were saved.

    Settings (theme, notifications) are not included: they belong to this computer.
    """
    path = Path(path)
    data = storage.load()
    payload = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "exported": datetime.now().isoformat(timespec="seconds"),
        "deadlines": data["deadlines"],
        "exams": data["exams"],
        "subjects": data["subjects"],
    }
    try:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as error:
        raise BackupError(f"Could not write {path.name}: {error.strerror}") from None
    return {"deadlines": len(data["deadlines"]), "exams": len(data["exams"])}


def _read(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BackupError(f"File not found: {path.name}") from None
    except OSError as error:
        raise BackupError(f"Could not open {path.name}: {error.strerror}") from None
    except ValueError:
        raise BackupError(f"{path.name} is not a readable backup file") from None
    if not isinstance(payload, dict):
        raise BackupError(f"{path.name} is not a study-kit backup")
    if "format" in payload and payload["format"] != FORMAT_NAME:
        raise BackupError(f"{path.name} is not a study-kit backup")
    if payload.get("version", FORMAT_VERSION) > FORMAT_VERSION:
        raise BackupError(f"{path.name} was made by a newer study-kit. Please update the app")
    for key in ("deadlines", "exams"):
        if not isinstance(payload.get(key, []), list):
            raise BackupError(f"{path.name} is not a study-kit backup")
    return payload


def _iso_date(value, where: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise BackupError(f"{where}: the date must look like 2026-12-01") from None


def _clean_deadline(raw, number: int) -> dict:
    where = f"Deadline {number}"
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("title"), str)
        or not raw["title"].strip()
    ):
        raise BackupError(f"{where}: it needs a title")
    subject = raw.get("subject", "")
    if not isinstance(subject, str):
        raise BackupError(f"{where}: the subject must be text")
    return {
        "title": raw["title"].strip(),
        "subject": subject.strip(),
        "due": _iso_date(raw.get("due"), where),
        "done": bool(raw.get("done", False)),
    }


def _clean_exam(raw, number: int) -> dict:
    where = f"Exam {number}"
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("subject"), str)
        or not raw["subject"].strip()
    ):
        raise BackupError(f"{where}: it needs a subject")
    topics = raw.get("topics")
    if not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
        raise BackupError(f"{where}: the topics must be a list of text")
    topics = [t.strip() for t in topics if t.strip()]
    if not topics:
        raise BackupError(f"{where}: it needs at least one topic")
    return {
        "subject": raw["subject"].strip(),
        "date": _iso_date(raw.get("date"), where),
        "topics": topics,
    }


def _deadline_key(item: dict) -> tuple:
    return (item["title"].lower(), item["subject"].lower(), item["due"])


def _exam_key(item: dict) -> tuple:
    return (item["subject"].lower(), item["date"], tuple(t.lower() for t in item["topics"]))


def _copy_current_file() -> None:
    """Keep the current data file next to itself before it is replaced."""
    path = storage.data_path()
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, path.with_name(f"{path.name}.before-import-{stamp}"))


def import_data(path, replace: bool = False) -> dict:
    """Load a backup. Merge (default) adds what is new; replace swaps everything.

    The whole file is checked first, so a bad file changes nothing.
    Returns {'deadlines': added, 'exams': added, 'skipped': duplicates left out}.
    """
    path = Path(path)
    payload = _read(path)
    new_deadlines = [_clean_deadline(r, i) for i, r in enumerate(payload.get("deadlines", []), 1)]
    new_exams = [_clean_exam(r, i) for i, r in enumerate(payload.get("exams", []), 1)]
    new_subjects = [
        s.strip() for s in payload.get("subjects", []) if isinstance(s, str) and s.strip()
    ]

    if replace:
        _copy_current_file()
    data = storage.load()
    if replace:
        data["deadlines"], data["exams"], data["subjects"] = [], [], []

    seen_deadlines = {_deadline_key(d) for d in data["deadlines"]}
    seen_exams = {_exam_key(e) for e in data["exams"]}
    added_deadlines = added_exams = skipped = 0

    for item in new_deadlines:
        if _deadline_key(item) in seen_deadlines:
            skipped += 1
            continue
        seen_deadlines.add(_deadline_key(item))
        item["id"] = max((d["id"] for d in data["deadlines"]), default=0) + 1
        data["deadlines"].append(item)
        added_deadlines += 1

    for item in new_exams:
        if _exam_key(item) in seen_exams:
            skipped += 1
            continue
        seen_exams.add(_exam_key(item))
        item["id"] = max((e["id"] for e in data["exams"]), default=0) + 1
        data["exams"].append(item)
        added_exams += 1

    known = {s.lower() for s in data["subjects"]}
    wanted = (
        new_subjects + [d["subject"] for d in new_deadlines] + [e["subject"] for e in new_exams]
    )
    for name in wanted:
        if name and name.lower() not in known:
            known.add(name.lower())
            data["subjects"].append(name)

    storage.save(data)
    return {"deadlines": added_deadlines, "exams": added_exams, "skipped": skipped}
