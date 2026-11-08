"""Model boundary tests use a fake HTTP response; no provider is contacted."""

import json

import pytest

from fil.intelligence import openai_scout
from fil.intelligence.openai_scout import OpenAIInterpreter
from fil.intelligence.scout import check_interpretation, interpret, search


def test_paraphrase_and_independent_guard():
    text = "Find footballers who contribute to defensive transitions and build-up"
    query = interpret("Find players who contribute to defensive transitions and build-up")
    assert interpret(text)["intent"] == "unsupported"
    answer = search(text, lambda _: query)
    assert answer["interpretation_mode"] == "provider"
    assert {c["name"] for c in answer["candidates"]} == {"Mara Vale", "Tess Rowe"}
    with pytest.raises(ValueError):
        check_interpretation("Find Linden Rovers players with at least 3 passes",
                             {**query, "intent": "passes", "team": None})
    assert search("Find fast players with passes", lambda _: query)["abstention"]
    assert search("Find footballers who contribute to defensive transitions and build-up",
                  lambda _: {**query, "invented": "event"})["abstention"]


def test_provider_sends_only_approved_synthetic_prompt(monkeypatch):
    text = "Find footballers who contribute to defensive transitions and build-up"
    query = interpret("Find players who contribute to defensive transitions and build-up")
    sent = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return json.dumps({"status": "completed", "model": "mock-model",
                               "output": [{"type": "message", "content": [
                                   {"type": "output_text", "text": json.dumps(query)}]}],
                               "usage": {"input_tokens": 20, "output_tokens": 10}}).encode()

    def fake_open(request, timeout):
        sent.append(json.loads(request.data))
        assert request.full_url == "https://api.openai.com/v1/responses"
        assert timeout == 30
        return FakeResponse()

    class FakeOpener:
        open = staticmethod(fake_open)

    monkeypatch.setattr(openai_scout, "build_opener", lambda *_: FakeOpener())
    provider = OpenAIInterpreter("fake-key", "mock-model")
    assert provider(text) == query
    assert sent[0]["input"] == text and sent[0]["store"] is False
    assert "demo-scout-action" not in json.dumps(sent[0])
    assert provider.last["usage"]["input_tokens"] == 20
    with pytest.raises(ValueError):
        provider("unapproved private research text")
    assert len(sent) == 1


def test_modified_benchmark_disables_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(openai_scout, "ROOT", tmp_path)
    target = tmp_path / "docs/benchmarks/scout-copilot"
    target.mkdir(parents=True)
    (target / "cases.json").write_text("[]")
    with pytest.raises(ValueError, match="changed"):
        openai_scout.approved_prompts()


def test_bad_provider_output_and_transport_fail_closed(monkeypatch):
    text = "Find footballers who contribute to defensive transitions and build-up"

    class BadResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return b'{"status":"completed","output":[{"type":"message","content":[' \
                b'{"type":"output_text","text":"not json"}]}]}'

    class FakeOpener:
        open = staticmethod(lambda *args, **kwargs: BadResponse())

    monkeypatch.setattr(openai_scout, "build_opener", lambda *_: FakeOpener())
    result = search(text, OpenAIInterpreter("fake-key", "mock-model"))
    assert result["abstention"] and not result["candidates"]
    assert result["interpretation_error"]

    def no_connection(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(openai_scout, "build_opener", lambda *_: type(
        "FailedOpener", (), {"open": staticmethod(no_connection)}
    )())
    result = search(text, OpenAIInterpreter("fake-key", "mock-model"))
    assert result["abstention"] and result["interpretation_error"]


def test_redirects_are_not_followed():
    handler = openai_scout._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://other.invalid") is None


def test_approved_chinese_example_abstains_without_positions_or_goal_filter():
    text = "帮我找几个进球不多，但在防守转换和进攻组织方面表现活跃的中场。"
    assert text in openai_scout.approved_prompts()
    proposed = {"intent": "transition_buildup", "team": None, "player": None,
                "min_passes": None, "max_shots": 1}
    result = search(text, lambda _: proposed)
    assert result["abstention"] and not result["candidates"]


def test_chinese_example_extracts_constraints_then_abstains(monkeypatch):
    sent = []
    requirements = dict(openai_scout.CHINESE_REQUIREMENTS)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return json.dumps({"status": "completed", "model": "mock-model",
                               "output": [{"type": "message", "content": [
                                   {"type": "output_text", "text": json.dumps(requirements)}]}],
                               "usage": {"input_tokens": 10, "output_tokens": 10}}).encode()

    class FakeOpener:
        def open(self, request, timeout):
            sent.append(json.loads(request.data))
            return FakeResponse()

    monkeypatch.setattr(openai_scout, "build_opener", lambda *_: FakeOpener())
    provider = OpenAIInterpreter("fake-key", "mock-model")
    result = search(openai_scout.CHINESE_EXAMPLE, provider)
    assert provider.last["extracted_requirements"] == requirements
    assert result["abstention"] and not result["candidates"]
    assert sent[0]["input"] == openai_scout.CHINESE_EXAMPLE
    assert sent[0]["text"]["format"]["schema"] == openai_scout.CHINESE_SCHEMA
    requirements["position"] = None
    result = search(openai_scout.CHINESE_EXAMPLE, provider)
    assert result["abstention"] and result["interpretation_error"]
