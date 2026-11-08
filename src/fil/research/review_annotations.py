"""Append local review records while preserving previous judgments."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def save_review(path: Path, record: dict[str, Any]) -> None:
    """Atomically replace one local file after adding a record to its existing list."""
    previous = json.loads(path.read_text()) if path.exists() else []
    if not isinstance(previous, list):
        raise ValueError("Review file has an unexpected format")
    previous.append(record)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, delete=False, encoding="utf-8"
        ) as tmp:
            temp_name = tmp.name
            json.dump(previous, tmp, indent=2)
            tmp.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
