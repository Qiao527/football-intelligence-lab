"""DeepSeek interpreter for the fixed, self-authored scouting evaluation prompts."""

import json
import time
from urllib.error import URLError
from urllib.request import Request, build_opener

from fil.intelligence.openai_scout import (
    CHINESE_EXAMPLE,
    CHINESE_REQUIREMENTS,
    CHINESE_SCHEMA,
    SCHEMA,
    OpenAIInterpreter,
    _NoRedirect,
    approved_prompts,
)
from fil.intelligence.scout import validate_query


class DeepSeekInterpreter(OpenAIInterpreter):
    """Interpret approved synthetic requests with DeepSeek JSON output, then validate locally."""

    def __init__(self, api_key: str, model: str = "deepseek-flash"):
        if model != "deepseek-flash":
            raise ValueError("Only the reviewed deepseek-flash model is enabled")
        super().__init__(api_key, model)

    def __call__(self, prompt: str) -> dict:
        self.last = None
        if prompt not in approved_prompts():
            raise ValueError("Only the fixed synthetic benchmark prompts may be sent")
        chinese = prompt == CHINESE_EXAMPLE
        schema = CHINESE_SCHEMA if chinese else SCHEMA
        instructions = (
            "Return exactly one JSON object conforming to this schema: "
            + json.dumps(schema, ensure_ascii=True)
            + ". Interpret only this fictional scouting request. "
            "Do not invent thresholds or confuse goals with shots. "
            "Positions and goal-count filters are unavailable in the English query schema; "
            "use unsupported for unavailable requirements. No rankings or player abilities. "
            "Unremarkable/few shots means at most one shot. "
            "For the Chinese schema, use goals='low' without a numerical threshold."
        )
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": instructions},
                         {"role": "user", "content": prompt}],
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "max_tokens": 512,
            "stream": False,
        }
        request = Request(
            "https://api.deepseek.com/chat/completions", data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"},
            method="POST",
        )
        start = time.perf_counter()
        try:
            with build_opener(_NoRedirect).open(request, timeout=30) as response:
                payload = response.read(1_000_001)
                if len(payload) > 1_000_000:
                    raise ValueError("Provider response exceeds size limit")
                raw = json.loads(payload)
            elapsed = time.perf_counter() - start
            if not isinstance(raw, dict):
                raise ValueError("Invalid provider response")
            usage = raw.get("usage", {})
            self.last = {"latency_seconds": elapsed, "model": raw.get("model"), "usage": {
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "input_tokens_details": {"cached_tokens": usage.get("prompt_cache_hit_tokens")},
            }}
            choices = raw.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError("Expected one provider response")
            if choices[0].get("finish_reason") != "stop":
                raise ValueError("Provider response incomplete")
            value = json.loads(choices[0]["message"]["content"])
            if chinese:
                self.last["extracted_requirements"] = value
                if (not isinstance(value, dict) or set(value) != set(CHINESE_REQUIREMENTS)
                        or type(value.get("defensive_transition")) is not bool
                        or type(value.get("build_up")) is not bool
                        or value != CHINESE_REQUIREMENTS):
                    raise ValueError("Chinese request constraints could not be verified")
                query = {"intent": "unsupported", "team": None, "player": None,
                         "min_passes": None, "max_shots": None}
            else:
                query = validate_query(value)
            self.last["parsed_query"] = query
            return query
        except (
            URLError, OSError, KeyError, TypeError, AttributeError, json.JSONDecodeError
        ) as exc:
            raise ValueError("Provider request failed or returned invalid data") from exc


def select_contributions(provider: DeepSeekInterpreter) -> dict:
    """Select from one hash-pinned synthetic report; never send arbitrary match data."""
    from fil.intelligence.contribution import contribution_report, validate_selection

    report = contribution_report()
    if report["source"]["raw_sha256"] != (
        "a138220845e05c53f35ad35be2c6ef58795bc0ba7533eda5b1c760d5f5b6d593"
    ):
        raise ValueError("Synthetic fixture changed; external analysis disabled")
    # Only these fixture-derived, self-authored facts and action IDs leave the machine.
    payload = {"fixture": report["fixture"], "player_profiles": report["player_profiles"]}
    instructions = (
        "Return JSON with exactly the key candidates: an array of objects with exactly "
        "player_id, support_event_ids and opposing_event_ids. Select fictional players for "
        "review who have a recorded defensive-transition action or completed build-up pass. "
        "For each selected player cite at least one ID from each category available for "
        "that player and include every incomplete pass ID as opposing evidence. "
        "Off-ball movement and other defensive actions are unavailable, not zero. "
        "Do not invent player IDs, "
        "event IDs, abilities or causal claims. Empty candidates means abstention. "
        "This is a 0-0 fictional sample; it cannot show who caused a win."
    )
    body = {
        "model": provider.model,
        "messages": [{"role": "system", "content": instructions},
                     {"role": "user", "content": json.dumps(payload, ensure_ascii=True)}],
        "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"},
        "max_tokens": 512, "stream": False,
    }
    request = Request(
        "https://api.deepseek.com/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + provider._key, "Content-Type": "application/json"},
        method="POST",
    )
    provider.last = None
    start = time.perf_counter()
    try:
        with build_opener(_NoRedirect).open(request, timeout=30) as response:
            data = response.read(1_000_001)
            if len(data) > 1_000_000:
                raise ValueError("Provider response exceeds size limit")
            raw = json.loads(data)
        if not isinstance(raw, dict):
            raise ValueError("Invalid provider response")
        usage = raw.get("usage", {})
        provider.last = {"latency_seconds": time.perf_counter() - start,
                         "model": raw.get("model"), "usage": {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "input_tokens_details": {"cached_tokens": usage.get("prompt_cache_hit_tokens")},
        }}
        choices = raw.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("Expected one provider response")
        if choices[0].get("finish_reason") != "stop":
            raise ValueError("Provider response incomplete")
        selected = json.loads(choices[0]["message"]["content"])
        provider.last["selection"] = selected
        verified = validate_selection(report, selected)
        return {"status": "selected" if verified else "abstained", "candidates": verified,
                "fixture": report["fixture"], "source": report["source"],
                "limitations": report["limitations"]}
    except (URLError, OSError, KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError("Provider selection failed validation or was unavailable") from exc
