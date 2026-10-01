"""Confidence composition. Never emit a total without the composition behind it (build brief §5, R7)."""
from typing import Dict, List

from .model import CostLine, CONFIDENCE, STRONG


def composition(lines: List[CostLine]) -> dict:
    """Low/high totals and the share of each confidence class, plus the generated sentence."""
    by: Dict[str, dict] = {c: {"low": 0.0, "high": 0.0, "count": 0} for c in CONFIDENCE}
    for l in lines:
        by[l.confidence]["low"] += l.low; by[l.confidence]["high"] += l.high; by[l.confidence]["count"] += 1
    low = sum(v["low"] for v in by.values()); high = sum(v["high"] for v in by.values())
    mid = (low + high) / 2.0
    shares = {c: ((v["low"] + v["high"]) / 2.0 / mid if mid else 0.0) for c, v in by.items()}
    strong = sum(shares[c] for c in STRONG)
    pending = [l.label for l in lines if l.confidence == "pending"]
    sentence = (f"Firm, quoted and published lines are about {_frac(strong)} of this total; the rest is "
                f"{', '.join(c for c in ('benchmarked', 'derived', 'placeholder') if shares[c] > 0.005) or 'none'}.")
    if pending:
        sentence += f" {len(pending)} line{'s' if len(pending) != 1 else ''} carr{'y' if len(pending) != 1 else 'ies'} no figure yet: {'; '.join(pending)}."
    return {"low": low, "high": high, "by_class": by, "shares": shares, "strong_share": strong, "sentence": sentence}


def _frac(x):
    """0.21 -> 'a fifth'; falls back to a percentage."""
    table = [(0.90, "nearly all"), (0.75, "three quarters"), (0.66, "two thirds"), (0.50, "half"), (0.33, "a third"),
             (0.25, "a quarter"), (0.20, "a fifth"), (0.10, "a tenth")]
    for v, w in table:
        if abs(x - v) <= 0.04:
            return w
    return f"{x:.0%}"
