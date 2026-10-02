"""The program budget: Cox services, consultants retained by the client, agency fees, and the
unquantifiable block as named exclusions. Totals carry their confidence composition (R7)."""
from typing import Dict

from .confidence import composition
from .model import Project
from . import fees as fees_mod

SECTIONS = [("cox_services", "A. Cox Planning Solutions professional services"),
            ("client_consultants", "B. Consultants retained separately by the client"),
            ("agency_fees", "C. Agency application and processing fees")]


def build(p: Project, with_fees: bool = True) -> dict:
    """The program budget. With fees, the fee engine's generated agency lines replace the typed lines they
    reconcile to and add pending lines for every fee family the schedules name but cannot yet price."""
    fr = fees_mod.build(p) if with_fees else None
    all_lines = fees_mod.merged_cost_lines(p, fr) if fr else list(p.cost_lines)
    out: Dict[str, dict] = {}
    for key, label in SECTIONS:
        lines = [l for l in all_lines if l.section == key]
        out[key] = {"label": label, "lines": lines, "composition": composition(lines)}
    total = composition(all_lines)
    exclusions = [{"id": u.id, "label": u.label, "why": u.why_unquantifiable.strip(),
                   "drivers": [d["name"] for d in u.drivers]} for u in p.unquantifiable]
    fee_block = None
    if fr:
        fee_block = {"applicable": [{"id": a.schedule.id, "name": a.schedule.name, "owner": a.schedule.owner, "kind": a.schedule.kind,
                                     "why": a.why, "map": a.map_citation, "source": a.schedule.source, "effective": a.schedule.effective}
                                    for a in fr.applicable],
                     "replaced": fr.replaced, "suppressed": fr.suppressed, "notes": fr.notes,
                     "pending": [l.label for l in fr.lines if l.confidence == "pending"]}
    return {"sections": out, "total": total, "exclusions": exclusions, "fees": fee_block}


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
