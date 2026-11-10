"""DeepSeek request/response checks use a fake transport and fictional prompts."""

import json

import pytest

from fil.intelligence import deepseek_scout
from fil.intelligence.deepseek_scout import DeepSeekInterpreter
from fil.intelligence.openai_scout import CHINESE_EXAMPLE, CHINESE_REQUIREMENTS
from fil.intelligence.scout import search


def test_deepseek_uses_bounded_synthetic_json_and_validates_response(monkeypatch):
    captured = []
    value = dict(CHINESE_REQUIREMENTS)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return json.dumps({"model": "deepseek-flash", "choices": [{"finish_reason": "stop",
                "message": {"content": json.dumps(value)}}], "usage": {
                    "prompt_tokens": 100, "completion_tokens": 20,
                    "prompt_cache_hit_tokens": 10}}).encode()

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "https://api.deepseek.com/chat/completions"
            captured.append(json.loads(request.data))
            return Response()

    monkeypatch.setattr(deepseek_scout, "build_opener", lambda *_: Opener())
    provider = DeepSeekInterpreter("fake-key")
    result = search(CHINESE_EXAMPLE, provider)
    assert result["abstention"] and not result["candidates"]
    assert provider.last["extracted_requirements"] == CHINESE_REQUIREMENTS
    assert provider.last["usage"]["input_tokens_details"]["cached_tokens"] == 10
    assert captured[0]["messages"][-1]["content"] == CHINESE_EXAMPLE
    assert captured[0]["max_tokens"] == 512 and captured[0]["thinking"]["type"] == "disabled"
    with pytest.raises(ValueError):
        provider("private unrestricted match text")
    assert len(captured) == 1
    value["goals"] = "99"
    assert search(CHINESE_EXAMPLE, provider)["interpretation_error"]


def test_deepseek_model_is_bounded():
    with pytest.raises(ValueError):
        DeepSeekInterpreter("fake-key", "unreviewed-model")


def test_contribution_model_sees_only_synthetic_and_cannot_fabricate(monkeypatch):
    sent = []
    selection = {"candidates": [{"player_id": 9101,
                                 "support_event_ids": ["demo-scout-action-001",
                                                       "demo-scout-action-002"],
                                 "opposing_event_ids": ["demo-scout-action-010"]}]}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return json.dumps({"model": "deepseek-flash", "choices": [{"finish_reason": "stop",
                "message": {"content": json.dumps(selection)}}], "usage": {
                    "prompt_tokens": 100, "completion_tokens": 20,
                    "prompt_cache_hit_tokens": 10}}).encode()

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "https://api.deepseek.com/chat/completions"
            sent.append(json.loads(request.data))
            return Response()

    monkeypatch.setattr(deepseek_scout, "build_opener", lambda *_: Opener())
    provider = DeepSeekInterpreter("fake-key")
    answer = deepseek_scout.select_contributions(provider)
    assert answer["status"] == "selected"
    assert answer["candidates"][0]["player"]["name"] == "Mara Vale"
    payload = json.loads(sent[0]["messages"][-1]["content"])
    assert payload["fixture"]["score"] == [0, 0]
    assert all(c["match_id"] == "demo-scout" for c in payload["player_profiles"])
    assert all(c["attacking_off_ball"] is None and c["defending_off_ball"] is None
               for c in payload["player_profiles"])
    selection["candidates"][0]["support_event_ids"][0] = "invented"
    with pytest.raises(ValueError):
        deepseek_scout.select_contributions(provider)
