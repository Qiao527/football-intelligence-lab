"""Review records preserve prior judgments and reject malformed local files."""

import json

import pytest

from fil.research.review_annotations import save_review


def test_review_append_and_invalid_file_safety(tmp_path):
    path = tmp_path / "review.json"
    save_review(path, {"reviewer": "TEST_ONLY_A", "answer": "No"})
    save_review(path, {"reviewer": "TEST_ONLY_B", "answer": "Yes"})
    assert [x["answer"] for x in json.loads(path.read_text())] == ["No", "Yes"]
    path.write_text("{}")
    with pytest.raises(ValueError):
        save_review(path, {"reviewer": "TEST_ONLY"})
    assert path.read_text() == "{}"
