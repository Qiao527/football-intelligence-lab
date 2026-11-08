"""Local Match Intelligence retains the research score reconciler."""

from fil.intelligence.report_core import CLAIM_STANDARDS, LIMITATIONS, native, weight
from fil.intelligence.report_core import analyze as _analyze
from fil.intelligence.report_core import validate as _validate
from fil.research.eligibility import ordered_score


def validate(raw: list[dict], metadata: dict) -> dict:
    """Validate a local source with the existing full score reconciler."""
    return _validate(raw, metadata, ordered_score)


def analyze(raw: list[dict], metadata: dict, identity: dict, *, period=None, team=None) -> dict:
    """Analyze a local source with the existing full score reconciler."""
    return _analyze(
        raw, metadata, identity, period=period, team=team, score_reconciler=ordered_score
    )


__all__ = ["CLAIM_STANDARDS", "LIMITATIONS", "analyze", "native", "validate", "weight"]
