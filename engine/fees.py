"""Agency fees priced by location (docs/FEATURES.md 4.2a). A registry of fee schedules (canon/fees/*.yaml) scoped
to a jurisdiction, a mapped district, or an agency approval; a project's quantities (projects/<key>/fees.yaml);
and the confidence rule from the build brief: a published rate times a fact is published, times an assumption
is benchmarked, and a missing amount or quantity is pending. Generated lines land in the program budget's
agency-fee block and can replace lines typed by hand, with any difference flagged."""
import datetime
import glob
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .model import CostLine, Project, _yaml, CANON, PROJECTS, STRONG

FEES_DIR = os.path.join(CANON, "fees")
BASES = {"flat", "per_unit", "per_acre", "per_sqft", "per_impact_acre", "per_year", "per_edu", "range"}
QUANTITY_FOR = {"per_unit": "units", "per_acre": "acres", "per_sqft": "sqft", "per_impact_acre": "impact_acres",
                "per_year": "years", "per_edu": "edus"}


@dataclass
class Schedule:
    id: str
    name: str
    owner: str
    kind: str
    scope: dict
    source: dict
    lines: List[dict]
    effective: Optional[str] = None
    review_by: Optional[str] = None

    def stale(self, today: datetime.date) -> bool:
        return bool(self.review_by) and datetime.date.fromisoformat(str(self.review_by)) < today

    def scope_kind(self):
        return next(k for k in ("jurisdiction", "district", "agency") if k in self.scope)


@dataclass
class Applicability:
    schedule: Schedule
    why: str
    map_citation: Optional[dict] = None


@dataclass
class FeeResult:
    applicable: List[Applicability]
    lines: List[CostLine]
    replaced: Dict[str, str]            # generated id -> typed line id it replaces
    suppressed: Dict[str, str]          # generated id -> typed line id kept instead
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------- registry

def load_registry(root: str = FEES_DIR) -> List[Schedule]:
    out = []
    for path in sorted(glob.glob(os.path.join(root, "*.yaml"))):
        if os.path.basename(path).startswith("_"):
            continue
        for s in (_yaml(path) or {}).get("schedules", []):
            if sum(k in s.get("scope", {}) for k in ("jurisdiction", "district", "agency")) != 1:
                raise ValueError(f"schedule {s.get('id')}: scope must name exactly one of jurisdiction, district, agency")
            for l in s.get("lines", []):
                if l.get("basis") not in BASES:
                    raise ValueError(f"schedule {s['id']} line {l.get('id')}: basis must be one of {sorted(BASES)}")
                if l["basis"] == "range" and (l.get("low") is None or l.get("high") is None) and not l.get("verify"):
                    raise ValueError(f"schedule {s['id']} line {l.get('id')}: a range line needs low and high, or a verify note")
                if l["basis"] != "range" and l.get("amount") is None and not l.get("verify"):
                    raise ValueError(f"schedule {s['id']} line {l.get('id')}: no amount and no verify note (a fee line never guesses)")
            out.append(Schedule(id=s["id"], name=s["name"], owner=s.get("owner", ""), kind=s.get("kind", ""), scope=s["scope"],
                                source=s.get("source") or {}, lines=s.get("lines", []), effective=s.get("effective"), review_by=s.get("review_by")))
    return out


def load_project_fees(p: Project) -> dict:
    path = os.path.join(PROJECTS, p.key, "fees.yaml")
    return (_yaml(path) or {}) if os.path.exists(path) else {}


def load_screen_approvals(p: Project) -> List[str]:
    path = os.path.join(PROJECTS, p.key, "screen.yaml")
    sc = (_yaml(path) or {}) if os.path.exists(path) else {}
    return [a.get("approval", "") for a in sc.get("approvals", [])]


# ---------------------------------------------------------------- geometry

def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """Ray casting on [lon, lat] rings. Enough for a fee-zone test; the hosted layer answers for real."""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xint = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < xint:
                inside = not inside
    return inside


# ---------------------------------------------------------------- applicability

def applicable(p: Project, registry: List[Schedule], pf: Optional[dict] = None, approvals: Optional[List[str]] = None) -> List[Applicability]:
    pf = pf if pf is not None else load_project_fees(p)
    approvals = approvals if approvals is not None else load_screen_approvals(p)
    jur = [j.lower() for j in p.meta.get("jurisdiction", [])]
    memberships = {m["schedule"]: m for m in pf.get("memberships", [])}
    point = pf.get("point")
    out = []
    for s in registry:
        k = s.scope_kind()
        if k == "jurisdiction":
            if s.scope["jurisdiction"].lower() in jur:
                out.append(Applicability(s, f"jurisdiction {s.scope['jurisdiction']}"))
        elif k == "agency":
            key = s.scope["agency"].lower()
            hit = next((a for a in approvals if key in a.lower()), None)
            if hit:
                out.append(Applicability(s, f"approval set names {hit}"))
        elif k == "district":
            d = s.scope["district"]
            if s.id in memberships:
                m = memberships[s.id]
                if not m.get("map"):
                    raise ValueError(f"membership in {s.id} declared without a map citation (R1)")
                out.append(Applicability(s, f"declared member of {d.get('feature', s.name)}", m["map"]))
            elif point and d.get("polygon") and point_in_polygon(tuple(point), d["polygon"]):
                out.append(Applicability(s, f"parcel point inside {d.get('feature', s.name)} on layer {d.get('layer')}",
                                         {"layer": d.get("layer"), "feature": d.get("feature"), "test": "point in polygon"}))
    return out


# ---------------------------------------------------------------- pricing

def _qty(pf: dict, key: str):
    """(low, high, confidence) or None when the quantity is not on file."""
    q = (pf.get("quantities") or {}).get(key)
    if not q:
        return None
    if "value" in q:
        return float(q["value"]), float(q["value"]), q.get("confidence", "derived")
    return float(q["low"]), float(q["high"]), q.get("confidence", "derived")


def _condition_holds(p: Project, line: dict, approvals: List[str], uses: List[str]) -> Tuple[bool, str]:
    w = line.get("when") or {}
    if "approval" in w and not any(w["approval"].lower() in a.lower() for a in approvals):
        return False, f"approval set does not name {w['approval']}"
    if "assumption" in w:
        a = p.assumptions.get(w["assumption"])
        if a is None or a.current != w.get("current"):
            return False, f"{w['assumption']} is not {w.get('current')}"
    if line.get("applies_to") and uses and not set(u.lower() for u in line["applies_to"]) & set(u.lower() for u in uses):
        return False, f"applies to {', '.join(line['applies_to'])} only"
    return True, ""


def price(p: Project, apps: List[Applicability], pf: Optional[dict] = None, approvals: Optional[List[str]] = None,
          today: Optional[datetime.date] = None) -> FeeResult:
    pf = pf if pf is not None else load_project_fees(p)
    approvals = approvals if approvals is not None else load_screen_approvals(p)
    today = today or datetime.date.today()
    uses = pf.get("uses") or []
    typed = {l.id: l for l in p.cost_lines}
    reconcile = pf.get("reconcile") or {}
    keep = pf.get("keep_manual") or {}
    lines, replaced, suppressed, notes = [], {}, {}, []
    for app in apps:
        s = app.schedule
        src = dict(s.source)
        stale = s.stale(today)
        for l in s.lines:
            gid = f"{s.id}.{l['id']}"
            ok, why = _condition_holds(p, l, approvals, uses)
            if not ok:
                continue
            if gid in keep:
                suppressed[gid] = keep[gid]
                continue
            basis_txt = f"{s.name} ({s.owner}); {_srclabel(src)}"
            conf = "published"
            low = high = None
            note = l.get("note", "")
            amount_missing = (l["basis"] == "range" and (l.get("low") is None)) or (l["basis"] != "range" and l.get("amount") is None)
            if amount_missing:
                conf = "pending"
                basis_txt += f". No adopted amount on file; verify: {l.get('verify', 'the adopted schedule')}"
            elif l["basis"] == "flat":
                low = high = float(l["amount"])
            elif l["basis"] == "range":
                low, high = float(l["low"]), float(l["high"])
            else:
                qkey = QUANTITY_FOR[l["basis"]]
                if l.get("quantity"):           # the schedule fixes the quantity itself (e.g. five annual fees)
                    q = (float(l["quantity"][qkey]), float(l["quantity"][qkey]), "published")
                else:
                    q = _qty(pf, qkey)
                if q is None:
                    conf = "pending"
                    basis_txt += f". ${float(l['amount']):,.0f} {l['basis'].replace('_', ' ')}; the {qkey.replace('_', ' ')} is not yet on file"
                else:
                    ql, qh, qc = q
                    low, high = float(l["amount"]) * ql, float(l["amount"]) * qh
                    if l.get("less"):
                        low, high = max(low - float(l["less"]), 0.0), max(high - float(l["less"]), 0.0)
                    if l.get("cap"):
                        low, high = min(low, float(l["cap"])), min(high, float(l["cap"]))
                    basis_txt += f". ${float(l['amount']):,.0f} {l['basis'].replace('_', ' ')} × {ql:g}" + (f" to {qh:g}" if qh != ql else "") + f" {qkey.replace('_', ' ')}"
                    if qc not in STRONG:
                        conf = "benchmarked"
                        basis_txt += f" (the {qkey.replace('_', ' ')} is {qc}, so the fee is an application of a published rate)"
            if stale and conf == "published":
                conf = "benchmarked"
                basis_txt += f". Schedule past its review date {s.review_by}; re-confirm before relying on it"
            if note:
                basis_txt += f". {note}"
            line = CostLine(id=gid, section="agency_fees", label=l["label"], low=low or 0.0, high=high or 0.0, confidence=conf,
                            basis=basis_txt, payer="client_direct", lands=l.get("lands", ""))
            if gid in reconcile:
                tid = reconcile[gid]
                t = typed.get(tid)
                if t is not None and conf != "pending" and (round(t.low) != round(line.low) or round(t.high) != round(line.high)):
                    notes.append(f"{gid}: schedule prices {line.low:,.0f} to {line.high:,.0f}; program.yaml {tid} carries {t.low:,.0f} to {t.high:,.0f}. The typed line stands until reconciled.")
                    continue
                replaced[gid] = tid
            lines.append(line)
    return FeeResult(apps, lines, replaced, suppressed, notes)


def _srclabel(src: dict) -> str:
    parts = [src.get("document") or "source"]
    if src.get("revised"):
        parts.append(f"revised {src['revised']}")
    return ", ".join(parts)


def build(p: Project, today: Optional[datetime.date] = None, registry: Optional[List[Schedule]] = None) -> FeeResult:
    pf = load_project_fees(p)
    if not pf:
        return FeeResult([], [], {}, {}, ["no fees.yaml for this project; agency fees are the typed lines only"])
    reg = registry if registry is not None else load_registry()
    approvals = load_screen_approvals(p)
    apps = applicable(p, reg, pf, approvals)
    return price(p, apps, pf, approvals, today)


def merged_cost_lines(p: Project, fr: FeeResult) -> List[CostLine]:
    """The program's cost lines with generated fee lines replacing the typed lines they reconcile to."""
    drop = set(fr.replaced.values())
    out = [l for l in p.cost_lines if l.id not in drop]
    return out + fr.lines


def render_text(p: Project, fr: FeeResult) -> str:
    out = [f"FEE SCHEDULES APPLYING TO {p.meta.get('name')} ({', '.join(p.meta.get('jurisdiction', []))})", ""]
    for a in fr.applicable:
        out.append(f"  {a.schedule.id:36} {a.schedule.kind:14} {a.why}" + (f"  map: {a.map_citation}" if a.map_citation else ""))
    out.append("")
    out.append("PRICED LINES")
    for l in fr.lines:
        rng = "pending" if l.confidence == "pending" else (f"{l.low:,.0f}" if l.low == l.high else f"{l.low:,.0f} to {l.high:,.0f}")
        tag = f"replaces {fr.replaced[l.id]}" if l.id in fr.replaced else ""
        out.append(f"  {l.label[:58]:58} {rng:>18}  {l.confidence:<11} {tag}")
    for g, t in fr.suppressed.items():
        out.append(f"  (suppressed {g}: typed bracket {t} stands)")
    for n in fr.notes:
        out.append(f"  ! {n}")
    return "\n".join(out)
