"""The fee build. Operations Manual 14.3, five steps, in order (build brief §5):

1. Hours by canonical role, per deliverable.
2. Deliverable fee = sum over roles of hours × rate. Nothing loaded or rounded at the deliverable.
3. Labor subtotal.
4. Project and client coordination at 10% of LABOR. Pass-throughs are excluded from the basis.
5. Total = labor + pass-throughs (at cost plus 15%) + coordination, rounded once, at the total.

Regression fixture: Riego Rd Task Order 1 → labor 246,580; pass-through 1,725; coordination
24,658; total 273,000; 1,463 hours. If this module does not reproduce those exactly it is wrong.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import Project, Deliverable


@dataclass
class DeliverableFee:
    code: str
    name: str
    phase: str
    hours: Dict[str, float]
    fee: float                      # exact: hours × bill rate, summed over roles
    cost: Optional[float]           # internal: hours × cost rate, when cost rates exist
    passthrough_cost: float = 0.0
    passthrough_fee: float = 0.0    # cost plus markup

    @property
    def total_hours(self):
        return sum(self.hours.values())

    @property
    def fee_with_passthrough(self):
        return self.fee + self.passthrough_fee


@dataclass
class FeeBuild:
    deliverables: List[DeliverableFee]
    labor: float
    passthrough_cost: float
    passthrough_fee: float
    coordination: float
    coordination_share: float
    total_exact: float
    total: float                    # rounded once
    round_to: int
    hours: float
    hours_by_role: Dict[str, float]
    cost: Optional[float]           # internal labor cost, when cost rates exist
    notes: List[str] = field(default_factory=list)

    @property
    def margin(self):
        """Internal only. Never emitted in client output (build brief §5)."""
        if self.cost is None:
            return None
        return self.total - (self.cost + self.passthrough_cost)

    @property
    def margin_pct(self):
        m = self.margin
        return None if m is None or not self.total else m / self.total


def _cents(x):
    """Money is held to the cent. Floating-point products are rounded here so 1,500 × 1.15 is 1,725.00, not 1,724.9999."""
    return round(x + 0.0, 2)


def _round_once(value, to):
    if not to:
        return value
    return float(int((value + to / 2.0) // to) * to)


def build(project: Project, deliverables: Optional[List[Deliverable]] = None) -> FeeBuild:
    canon = project.canon
    rules = canon.fee_rules
    share = float(rules.get("coordination_share_of_labor", 0.10))
    markup = float(rules.get("passthrough_markup", 0.15))
    round_to = int(rules.get("round_total_to", 1000))
    rows, by_role = [], {}
    have_cost = all(r.cost_rate is not None for r in canon.roles.values())
    labor = cost = 0.0
    pt_cost = pt_fee = 0.0
    for dlv in (deliverables if deliverables is not None else project.deliverables):
        fee = 0.0
        c = 0.0
        for role, h in dlv.hours.items():
            r = canon.roles[role]
            fee += _cents(h * r.bill_rate)
            if have_cost:
                c += _cents(h * float(r.cost_rate))
            by_role[role] = by_role.get(role, 0.0) + h
        p_cost = sum(p.cost for p in dlv.passthroughs)
        p_fee = _cents(p_cost * (1.0 + markup))
        rows.append(DeliverableFee(code=dlv.code, name=dlv.name, phase=dlv.phase, hours=dict(dlv.hours), fee=fee,
                                   cost=(c if have_cost else None), passthrough_cost=p_cost, passthrough_fee=p_fee))
        labor += fee; cost += c; pt_cost += p_cost; pt_fee += p_fee
    coordination = _cents(labor * share)              # on labor only; pass-throughs excluded
    total_exact = _cents(labor + pt_fee + coordination)
    total = _round_once(total_exact, round_to)
    notes = []
    if total != total_exact:
        notes.append(f"Rounded once at the total, to the nearest {round_to:,}: {total_exact:,.2f} → {total:,.0f} (R12).")
    return FeeBuild(deliverables=rows, labor=labor, passthrough_cost=pt_cost, passthrough_fee=pt_fee,
                    coordination=coordination, coordination_share=share, total_exact=total_exact, total=total,
                    round_to=round_to, hours=sum(by_role.values()), hours_by_role=by_role,
                    cost=(cost if have_cost else None), notes=notes)


def payment_schedule(total: float, milestones: List[dict]) -> List[dict]:
    """Milestones run on the full fixed fee. Shares must sum to 1; amounts are rounded to the nearest
    hundred and the last milestone absorbs the rounding so the schedule sums to the total exactly."""
    shares = [float(m["share"]) for m in milestones]
    if abs(sum(shares) - 1.0) > 1e-9:
        raise ValueError(f"milestone shares sum to {sum(shares)}, not 1")
    out, running = [], 0.0
    for i, m in enumerate(milestones):
        amt = (math.floor(total * shares[i] / 100.0 + 0.5) * 100.0) if i < len(milestones) - 1 else total - running  # half-up to the hundred; the last milestone absorbs the rounding
        running += amt
        out.append({"milestone": m["milestone"], "share": shares[i], "amount": amt, "trigger": m.get("trigger", "")})
    return out


def internal_table(fb: FeeBuild, project: Project) -> str:
    """INTERNAL fee backup as text (hours and rates). Never client-facing."""
    roles = [k for k in project.canon.roles if fb.hours_by_role.get(k)]
    head = ["Code", "Deliverable"] + [project.canon.roles[k].name for k in roles] + ["Fee"]
    lines = [" | ".join(head)]
    for r in fb.deliverables:
        lines.append(" | ".join([r.code, r.name[:48]] + [f"{r.hours.get(k, 0):g}" for k in roles] + [f"{r.fee:,.0f}"]))
    lines.append(" | ".join(["", "Labor subtotal"] + [f"{fb.hours_by_role.get(k, 0):g}" for k in roles] + [f"{fb.labor:,.0f}"]))
    lines.append(f"Pass-throughs at cost plus {project.canon.fee_rules.get('passthrough_markup', 0.15):.0%}: {fb.passthrough_fee:,.0f} (cost {fb.passthrough_cost:,.0f})")
    lines.append(f"Project and client coordination at {fb.coordination_share:.0%} of labor: {fb.coordination:,.0f}")
    lines.append(f"TOTAL, ROUNDED: {fb.total:,.0f}   (exact {fb.total_exact:,.2f})   hours {fb.hours:g}")
    if fb.margin is not None:
        lines.append(f"INTERNAL margin: {fb.margin:,.0f} ({fb.margin_pct:.1%}) over loaded cost {fb.cost + fb.passthrough_cost:,.0f}")
    return "\n".join(lines)
