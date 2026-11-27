from studykit import storage


def list_subjects() -> list[str]:
    """All saved subjects, sorted A to Z (ignoring upper/lower case)."""
    return sorted(storage.load()["subjects"], key=str.lower)


def add_subject(name: str) -> bool:
    """Save a subject. Returns False if it's empty or already exists."""
    name = name.strip()
    if not name:
        return False
    data = storage.load()
    if name.lower() in (s.lower() for s in data["subjects"]):
        return False
    data["subjects"].append(name)
    storage.save(data)
    return True
