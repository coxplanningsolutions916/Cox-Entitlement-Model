"""Chart data for the client page (docs/DASHBOARD-DESIGN.md): months per cost line, task-order milestones,
the investment burn-up series, and the mitigation resolution gates. Pure data; the dashboard draws it.
Every month is counted from the notice to proceed; every derived month says so."""
import datetime
import re
from typing import List, Optional

from . import schedule as schedule_mod
from .model import Project

MONTHS_RE = re.compile(r"Months?\s+(\d+)\s+to\s+(\d+)")
CODE_RE = re.compile(r"(\d+\.\d+)(?:\s+through\s+(\d+\.\d+))?")


def months_of(lands: str):
    """'Months 15 to 30' -> (15, 30); anything else -> None."""
    m = MONTHS_RE.search(lands or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _month_index(d: datetime.date, ntp: datetime.date) -> int:
    return max(0, round((d - ntp).days / 30.4))


def deliverable_months(p: Project, ntp: datetime.date, horizon_months: int = 12) -> dict:
    """Month (from NTP) at which each deliverable lands: the close of its season window when it has one
    (published), else a derived place inside the task-order horizon from its sequence step."""
    placements = {x.code: x for x in schedule_mod.place(p, ntp)}
    steps = [d.sequence_step for d in p.deliverables if d.sequence_step]
    max_step = max(steps) if steps else 1
    out = {}
    for d in p.deliverables:
        x = placements.get(d.code)
        if x and x.closes:
            out[d.code] = {"month": _month_index(x.closes, ntp), "basis": "window close", "confidence": "published", "date": x.closes.isoformat()}
        else:
            step = d.sequence_step or max_step
            out[d.code] = {"month": max(1, round(horizon_months * step / max_step)), "basis": "sequence step", "confidence": "derived", "date": None}
    return out


def _codes(text: str) -> List[str]:
    out = []
    for a, b in CODE_RE.findall(text or ""):
        if b:
            pa, sa = a.split("."); pb, sb = b.split(".")
            if pa == pb:
                out += [f"{pa}.{i}" for i in range(int(sa), int(sb) + 1)]
            else:
                out += [a, b]
        else:
            out.append(a)
    return out


def milestones(p: Project, ntp: datetime.date, total_fee: float) -> List[dict]:
    """The task order's payment milestones placed in months by the deliverables that trigger them."""
    to = p.meta.get("task_order_1") or {}
    ms = to.get("payment_milestones") or []
    if not ms:
        return []
    span = months_of(next((l.lands for l in p.cost_lines if l.id == "line.to1"), "")) or (1, 12)
    dm = deliverable_months(p, ntp, span[1])
    out = []
    for i, m in enumerate(ms):
        codes = [c for c in _codes(m.get("trigger", "")) if c in dm]
        if i == 0 and not codes:
            month, basis, conf = 0, "execution", "firm"
        elif codes:
            month = max(dm[c]["month"] for c in codes)
            conf = "published" if all(dm[c]["confidence"] == "published" for c in codes) else "derived"
            basis = "triggered by " + ", ".join(codes)
        else:
            month, basis, conf = span[1], "end of task order", "derived"
        out.append({"label": m["milestone"], "month": month, "share": m.get("share"), "amount": round(total_fee * float(m.get("share", 0))),
                    "trigger": m.get("trigger", ""), "basis": basis, "confidence": conf})
    return out


def line_spans(prog: dict) -> List[dict]:
    """Every cost line with its months, for the Gantt and the burn-up."""
    out = []
    for key, sec in prog["sections"].items():
        for l in sec["lines"]:
            mo = months_of(l.lands)
            out.append({"id": l.id, "label": l.label, "block": key, "low": l.low, "high": l.high, "confidence": l.confidence,
                        "payer": l.payer, "start": mo[0] if mo else None, "end": mo[1] if mo else None, "lands": l.lands})
    return out


def burnup(spans: List[dict], horizon: Optional[int] = None) -> dict:
    """Cumulative low and high by month for lines with months; the firm line separately; lines with no months
    reported as unscheduled rather than guessed onto the curve."""
    dated = [s for s in spans if s["start"] is not None and s["confidence"] != "pending"]
    H = horizon or max([s["end"] for s in dated] + [12])
    low = [0.0] * (H + 1); high = [0.0] * (H + 1); firm = [0.0] * (H + 1)
    for s in dated:
        a, b = max(0, s["start"] - 1), max(s["start"], s["end"])
        n = max(1, b - a)
        for m in range(a + 1, b + 1):
            if m <= H:
                low[m] += s["low"] / n; high[m] += s["high"] / n
                if s["confidence"] == "firm":
                    firm[m] += s["low"] / n
    for m in range(1, H + 1):
        low[m] += low[m - 1]; high[m] += high[m - 1]; firm[m] += firm[m - 1]
    unsched = [s for s in spans if s["start"] is None and s["confidence"] != "pending"]
    return {"horizon": H, "low": [round(x) for x in low], "high": [round(x) for x in high], "firm": [round(x) for x in firm],
            "unscheduled_low": round(sum(s["low"] for s in unsched)), "unscheduled_high": round(sum(s["high"] for s in unsched)),
            "unscheduled_count": len(unsched)}


def period_bars(spans: List[dict], horizon: int, period: int = 6) -> List[dict]:
    """Stacked bars per period split by who pays (midpoint of each line's range spread over its months)."""
    n = (horizon + period - 1) // period
    bars = [{"from": i * period + 1, "to": min((i + 1) * period, horizon), "cox": 0.0, "client_direct": 0.0, "passthrough": 0.0} for i in range(n)]
    for s in spans:
        if s["start"] is None or s["confidence"] == "pending":
            continue
        a, b = max(1, s["start"]), max(s["start"], s["end"])
        mid = (s["low"] + s["high"]) / 2.0 / max(1, b - a + 1)
        for m in range(a, b + 1):
            i = min(n - 1, (m - 1) // period)
            bars[i][s["payer"] if s["payer"] in bars[i] else "cox"] += mid
    for b in bars:
        for k in ("cox", "client_direct", "passthrough"):
            b[k] = round(b[k])
    return bars


def mitigation_gates(p: Project, ntp: datetime.date) -> List[dict]:
    """Each unquantifiable line as a cone: the gates (resolving deliverables, in month order) at which the
    figure moves from no figure, to a benchmarked range, to a quote, to a firm number."""
    dm = deliverable_months(p, ntp)
    out = []
    for u in p.unquantifiable:
        gates = {}
        for drv in u.drivers:
            for ref in drv.get("resolved_by", []):
                try:
                    d = p.deliverable(ref)
                except KeyError:
                    continue
                g = gates.setdefault(d.code, {"code": d.code, "label": d.name, "month": dm[d.code]["month"], "date": dm[d.code]["date"],
                                             "confidence": dm[d.code]["confidence"], "drivers": []})
                g["drivers"].append(drv["name"])
        ordered = sorted(gates.values(), key=lambda g: g["month"])
        states = ["range, benchmarked", "quoted", "firm"]
        for i, g in enumerate(ordered):
            g["state_after"] = states[min(i, len(states) - 1)] if i < len(ordered) - 1 else "firm"
        refs = []
        for rid in u.reference_costs:
            b = p.benchmarks.get(rid)
            if b:
                refs.append({"label": b.label, "value": b.value, "unit": b.unit, "status": b.status, "source": b.source})
        out.append({"id": u.id, "label": u.label, "state": "no figure carried", "why": u.why_unquantifiable.strip(),
                    "drivers": [{"name": d["name"], "resolved_by": d.get("resolved_by", []), "status": "open"} for d in u.drivers],
                    "gates": ordered, "reference_costs": refs,
                    "withdrawn": u.withdrawn_estimates})
    return out
