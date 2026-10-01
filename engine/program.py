"""The program budget: Cox services, consultants retained by the client, agency fees, and the
unquantifiable block as named exclusions. Totals carry their confidence composition (R7)."""
from typing import Dict

from .confidence import composition
from .model import Project

SECTIONS = [("cox_services", "A. Cox Planning Solutions professional services"),
            ("client_consultants", "B. Consultants retained separately by the client"),
            ("agency_fees", "C. Agency application and processing fees")]


def build(p: Project) -> dict:
    out: Dict[str, dict] = {}
    for key, label in SECTIONS:
        lines = [l for l in p.cost_lines if l.section == key]
        out[key] = {"label": label, "lines": lines, "composition": composition(lines)}
    all_lines = p.cost_lines
    total = composition(all_lines)
    exclusions = [{"id": u.id, "label": u.label, "why": u.why_unquantifiable.strip(),
                   "drivers": [d["name"] for d in u.drivers]} for u in p.unquantifiable]
    return {"sections": out, "total": total, "exclusions": exclusions}


def render_text(p: Project, prog: dict) -> str:
    lines = [f"PROGRAM BUDGET — {p.meta.get('name')} · {p.meta.get('client')}", ""]
    for key, sec in prog["sections"].items():
        lines.append(sec["label"])
        for l in sec["lines"]:
            rng = "quote pending" if l.confidence == "pending" else (f"{l.low:,.0f}" if l.low == l.high else f"{l.low:,.0f} to {l.high:,.0f}")
            lines.append(f"  {l.label[:70]:70} {rng:>22}  {l.confidence:<11} {('client pays direct' if l.payer == 'client_direct' else l.payer)}")
        c = sec["composition"]
        lines.append(f"  subtotal {c['low']:,.0f} to {c['high']:,.0f}  ·  {c['sentence']}")
        lines.append("")
    t = prog["total"]
    lines.append(f"PROGRAM COST TO ENTITLEMENT: {t['low']:,.0f} to {t['high']:,.0f}")
    lines.append(f"  {t['sentence']}")
    for x in prog["exclusions"]:
        lines.append(f"  EXCLUDED, NOT YET QUANTIFIABLE: {x['label']} — drivers: {', '.join(x['drivers'])}")
    return "\n".join(lines)
