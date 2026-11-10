"""Opt-in OpenAI interpreter, restricted to fixed self-authored benchmark prompts.

No events, credentials or unrestricted user input enter the prompt. No provider call is
made until the caller explicitly invokes this adapter with a matching synthetic case.
"""

import hashlib
import json
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fil.intelligence.scout import INTENTS, KEYS, PLAYERS, TEAMS, validate_query


def _repository_root(
    module_file: Path | None = None, cwd: Path | None = None
) -> Path:
    """Locate the checkout that owns the reviewed benchmark files."""
    module = Path(module_file if module_file is not None else __file__).resolve()
    working = Path(cwd if cwd is not None else Path.cwd()).resolve()
    for candidate in (*module.parents, working):
        if (candidate / "docs" / "benchmarks" / "scout-copilot" / "cases.json").is_file():
            return candidate
    return module.parents[3]


ROOT = _repository_root()
APPROVED = {
    "cases.json": "4339eb6f9f407ec830270dbdd7a0167875c7df54400da0a120ff41de4379ab2c",
    "heldout.json": "a5d1b1bde2b9dec29d900b36197637fdcd30efae5b7364533af01dca78191368",
    "chinese_example.json": "a91d6a57c4212a644bcdf70130f2e9e0fbc77ebc3da882635023e384eabfb336",
}
SCHEMA = {
    "type": "object", "additionalProperties": False, "required": sorted(KEYS),
    "properties": {
        "intent": {"type": "string", "enum": sorted(INTENTS)},
        "team": {"type": ["string", "null"], "enum": [*sorted(TEAMS), None]},
        "player": {"type": ["string", "null"], "enum": [*sorted(PLAYERS), None]},
        "min_passes": {"type": ["integer", "null"]},
        "max_shots": {"type": ["integer", "null"]},
    },
}


CHINESE_EXAMPLE = "帮我找几个进球不多，但在防守转换和进攻组织方面表现活跃的中场。"
CHINESE_REQUIREMENTS = {
    "position": "midfield", "goals": "low", "defensive_transition": True, "build_up": True,
}
CHINESE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": sorted(CHINESE_REQUIREMENTS),
    "properties": {
        "position": {"type": ["string", "null"], "enum": ["midfield", None]},
        "goals": {"type": ["string", "null"], "enum": ["low", None]},
        "defensive_transition": {"type": "boolean"},
        "build_up": {"type": "boolean"},
    },
}


def approved_prompts() -> set[str]:
    """Verify exact, reviewed synthetic files before allowing any external request."""
    allowed = set()
    for name, expected in APPROVED.items():
        data = (ROOT / "docs/benchmarks/scout-copilot" / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Synthetic benchmark changed; external access disabled")
        allowed.update(case["prompt"] for case in json.loads(data))
    return allowed


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenAIInterpreter:
    """Responses API structured output interpreter; pass explicitly to ``search``."""

    def __init__(self, api_key: str, model: str):
        if not api_key or not model:
            raise ValueError("A key and explicit model are required")
        self._key = api_key
        self.model = model
        self.last = None

    def __call__(self, prompt: str) -> dict:
        self.last = None
        if prompt not in approved_prompts():
            raise ValueError("Only the fixed synthetic benchmark prompts may be sent")
        chinese = prompt == CHINESE_EXAMPLE
        instructions = (
            "Extract the requested constraints from the fictional scouting request. "
            "Do not infer a numeric threshold for low goals or substitute shots for goals."
        ) if chinese else (
                "Convert this fictional scouting request to the given schema. "
                "Only recorded transition, build-up passes, passes, shots and player actions "
                "are supported. Use unsupported or comparison for unobservable or comparative "
                "requests. Never omit requested constraints. Null means not requested. "
                "Unremarkable/few shots means at most one shot. No rankings or abilities. "
                "Positions and goal-count filters are unavailable: use unsupported for those "
                "requests, including non-English requests; do not replace goals with shots."
            )
        body = {
            "model": self.model, "store": False, "instructions": instructions,
            "input": prompt,
            "text": {"format": {"type": "json_schema", "name": "scouting_query",
                                 "strict": True, "schema": CHINESE_SCHEMA if chinese else SCHEMA}},
        }
        request = Request(
            "https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
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
            if not isinstance(raw, dict) or raw.get("status") != "completed":
                raise ValueError("Provider response incomplete")
            content = [part["text"] for item in raw.get("output", [])
                       if item.get("type") == "message" for part in item.get("content", [])
                       if part.get("type") == "output_text"]
            if len(content) != 1:
                raise ValueError("Provider did not return one structured response")
            usage = raw.get("usage", {})
            self.last = {"latency_seconds": elapsed, "usage": usage, "model": raw.get("model")}
            value = json.loads(content[0])
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
