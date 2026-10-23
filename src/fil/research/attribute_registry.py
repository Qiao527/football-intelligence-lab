"""Versioned research specifications, never a player rating registry."""

import json
import re
from importlib.resources import files

VERSION = "fil-attribute-registry-1"
FIELDS = {
    "attribute_id",
    "version",
    "name",
    "football_interpretation",
    "latent_construct",
    "observable_behavior",
    "required_features",
    "opportunity_denominator",
    "data_quality_requirements",
    "confounders",
    "baselines",
    "estimation_strategy",
    "reliability_construct_tests",
    "incremental_validity_tests",
    "independent_validation_requirements",
    "falsification_criteria",
    "research_status",
}
LIST_FIELDS = {
    "required_features",
    "data_quality_requirements",
    "confounders",
    "baselines",
    "reliability_construct_tests",
    "incremental_validity_tests",
    "independent_validation_requirements",
    "falsification_criteria",
}
STATUSES = {
    "proposed",
    "descriptive",
    "exploratory",
    "independently_validated",
    "insufficient_evidence",
}


def validate(registry: dict) -> dict:
    """Reject incomplete/duplicate specifications and unsupported status labels."""
    if set(registry) != {"schema_version", "attributes"} or registry["schema_version"] != VERSION:
        raise ValueError("Unsupported attribute registry schema")
    if not isinstance(registry["attributes"], list) or not registry["attributes"]:
        raise ValueError("Nonempty attribute specifications required")
    seen = set()
    for item in registry["attributes"]:
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise ValueError("Incomplete attribute specification")
        if not isinstance(item["research_status"], str) or item["research_status"] not in STATUSES:
            raise ValueError("Incomplete attribute specification or unsupported status")
        for key, value in item.items():
            if not isinstance(value, list if key in LIST_FIELDS else str):
                raise ValueError("Attribute field type mismatch")
            if (
                not isinstance(value, (str, list))
                or not value
                or (isinstance(value, str) and not value.strip())
            ):
                raise ValueError("Nonempty text or text lists required")
            if isinstance(value, list) and any(not isinstance(v, str) or not v for v in value):
                raise ValueError("Nonempty text lists required")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", item["attribute_id"]):
            raise ValueError("Invalid attribute identifier")
        if not re.fullmatch(r"fil-[a-z0-9-]+-[1-9][0-9]*", item["version"]):
            raise ValueError("Versioned analytical definition required")
        if item["attribute_id"] in seen:
            raise ValueError("Duplicate attribute identifier")
        seen.add(item["attribute_id"])
    return registry


def load() -> dict:
    """Load packaged definitions in editable and regular installations."""
    return validate(
        json.loads(files("fil.research").joinpath("attribute_registry.json").read_text())
    )
