"""The strategy rules (build brief §7) as independently testable predicates. Each returns a list of
Violation records; an empty list means the rule holds. HARD rules block generation; the rest warn.
The Riego evidence lives in the docstrings so the intent survives the implementation."""
from dataclasses import dataclass
from typing import List

from .model import Project, SCOPE_STATUS

HARD = {"R1", "R5", "R6", "R11", "R13", "R18"}


@dataclass
class Violation:
    rule: str
    record: str
    message: str
    hard: bool

    def __str__(self):
        return f"[{self.rule}{' HARD' if self.hard else ''}] {self.record}: {self.message}"


def r1_membership_needs_map(p: Project) -> List[Violation]:
    """A plan or program membership claim requires a map or GIS citation with a source and date before any
    framework rests on it. Riego: two delivered membership claims (NBHCP, SPSP) were wrong."""
    out = []
    for f in p.facts.values():
        if f.kind == "membership" and not f.superseded:
            mc = f.map_citation or {}
            if not (mc.get("date") and (mc.get("figure") or mc.get("layer") or mc.get("map"))):
                out.append(Violation("R1", f.id, "membership claim without a map or GIS citation carrying a source and date; no coverage, fee, tiering or precedent logic may rest on it", True))
    return out


def r5_unquantifiable_carry_no_number(p: Project) -> List[Violation]:
    """Where the inputs that set a cost do not exist, the line is unquantifiable: drivers and reference costs,
    never a bracket. Riego withdrew its mitigation bracket on exactly this reasoning."""
    out = []
    for u in p.unquantifiable:
        for d in u.drivers:
            if not d.get("resolved_by"):
                out.append(Violation("R5", u.id, f"driver '{d.get('name')}' names nothing that resolves it", True))
    labels = {u.label.lower() for u in p.unquantifiable}
    for l in p.cost_lines:
        if l.label.lower() in labels:
            out.append(Violation("R5", l.id, "a cost line duplicates an unquantifiable line with a number", True))
    return out


def r6_benchmark_applicability(p: Project) -> List[Violation]:
    """A benchmark is usable only where its applicability conditions hold against this project."""
    out = []
    juris = set(p.meta.get("jurisdiction") or []) | set(p.meta.get("regions") or [])   # county plus the regions it sits in
    acres = float(p.meta.get("acres") or 0)
    for b in p.benchmarks.values():
        if b.status == "rejected":
            continue
        a = b.applicability or {}
        if a.get("jurisdiction") and not (set(a["jurisdiction"]) & juris):
            out.append(Violation("R6", b.id, f"jurisdiction {a['jurisdiction']} does not include {sorted(juris)}", True))
        if a.get("max_project_acres") and acres > float(a["max_project_acres"]):
            out.append(Violation("R6", b.id, f"project is {acres:g} acres; benchmark applies up to {a['max_project_acres']}", True))
    return out


def r7_every_dollar_has_confidence(p: Project) -> List[Violation]:
    return [Violation("R7", l.id, "cost line without confidence or basis", False)
            for l in p.cost_lines if not l.confidence or not l.basis]


def r11_discussed_is_not_authorized(p: Project) -> List[Violation]:
    """Scope status is an enum; nothing is 'started' or later without an executed authority record."""
    out = []
    for d in p.deliverables:
        if SCOPE_STATUS.index(d.status) >= SCOPE_STATUS.index("started"):
            a = d.authority or {}
            if not (a.get("document") and a.get("executed")):
                out.append(Violation("R11", d.id, f"status '{d.status}' without an executed authority record (document + executed date)", True))
    return out


def r12_round_once(p: Project, fee_build) -> List[Violation]:
    """No deliverable carries a rounded or loaded figure; the fee is exactly hours × rate."""
    out = []
    for r in fee_build.deliverables:
        d = p.deliverable(r.code)
        exact = sum(h * p.canon.roles[k].bill_rate for k, h in d.hours.items())
        if abs(exact - r.fee) > 0.005:
            out.append(Violation("R12", d.id, f"deliverable fee {r.fee} is not hours × rate ({exact})", False))
    return out


def r13_quarantine(p: Project, text: str) -> List[Violation]:
    """Superseded source text is quarantined: a draft containing a quarantined term is rejected."""
    out = []
    low = (text or "").lower()
    for f in p.facts.values():
        if f.superseded:
            for term in f.quarantined_terms:
                if term.lower() in low:
                    out.append(Violation("R13", f.id, f"draft contains quarantined language '{term}' from a superseded source", True))
    return out


def r18_local_rule_confirmed(p: Project) -> List[Violation]:
    """Confirm the current local rule before applying any statewide standard; a stale local-rule fact misprices."""
    out = []
    for f in p.facts.values():
        if f.kind == "local_rule" and not f.superseded and f.stale():
            out.append(Violation("R18", f.id, "local rule fact is past its TTL; confirm the current rule before relying on it", True))
    return out


def r19_type_coverage(p: Project) -> List[Violation]:
    """The screen must address every primary issue of the project's development type, or carry it as a fact
    needed. A greenfield screen with no aquatic row, or an infill screen with no neighbor row, is incomplete."""
    import os
    from .model import PROJECTS, _yaml
    from . import types as types_mod
    path = os.path.join(PROJECTS, p.key, "screen.yaml")
    screen = (_yaml(path) or {}) if os.path.exists(path) else {}
    out = []
    if not screen:
        return out
    for issue in types_mod.coverage(p, screen)["missing"]:
        out.append(Violation("R19", f"{p.key}:{issue['id']}", f"{p.development_type.name} screen does not address '{issue['label']}' (carried as a fact needed; verify: {issue['verify']})", False))
    return out


def r20_rung_matches_scale_test(p: Project) -> List[Violation]:
    """A Roadmap sold below the rung the scale test recommends needs the planner's written reason."""
    from . import review as review_mod
    st = review_mod.scale_test(p)
    out = []
    if st["override"] and review_mod.RUNG_ORDER.index(st["override"]) < review_mod.RUNG_ORDER.index(st["recommended"]) and not st["override_reason"]:
        out.append(Violation("R20", p.key, f"rung override to {st['override']} below the scale test's {st['recommended']} without a reason", True))
    return out


def check(p: Project, fee_build=None, draft_text: str = "") -> List[Violation]:
    v = []
    v += r1_membership_needs_map(p)
    v += r5_unquantifiable_carry_no_number(p)
    v += r6_benchmark_applicability(p)
    v += r7_every_dollar_has_confidence(p)
    v += r11_discussed_is_not_authorized(p)
    if fee_build is not None:
        v += r12_round_once(p, fee_build)
    if draft_text:
        v += r13_quarantine(p, draft_text)
    v += r18_local_rule_confirmed(p)
    v += r19_type_coverage(p)
    v += r20_rung_matches_scale_test(p)
    return v
