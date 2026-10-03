"""The planner's review and the scale test (docs/PRICING-LADDER.md; plugin reference scale-test-and-pricing.md).

Scale test, answered by the model where it can and confirmed by the planner: a Roadmap Plus when the site spans
more than one jurisdiction, carries mapped waters, wetlands, flood hazard or listed-species habitat on or adjacent,
needs a discretionary entitlement, or the client needs a board package. An assemblage of adjacent parcels in one
ownership counts as one site. The planner may override the rung with a reason; the override prints on the report.

Review: the ten-item checklist (report.CHECKLIST) with a reviewer and a date, written into the project's
screen.yaml. Until it exists the report carries the red unreviewed stamp and must not go out."""
import datetime
import os
import re
from typing import Dict, List, Optional

import yaml

from . import types as types_mod
from .model import PROJECTS, Project, _yaml

DISCRETIONARY = ("rezone", "general plan amendment", "specific plan", "use permit", "conditional use", "variance",
                 "annexation", "planned development", "tentative map", "subdivision map", "development agreement")
RESOURCE_ISSUES = {"aquatic", "species", "hcp", "flood", "nexus", "mitigation"}
RESOURCE_WORDS = ("wetland", "vernal", "aquatic", "waters", "species", "habitat", "flood", "zone ae", "creek", "stream", "cnddb")
RUNG_ORDER = ["screening", "roadmap", "plus"]


def screen_path(p: Project) -> str:
    return os.path.join(PROJECTS, p.key, "screen.yaml")


def load_screen(p: Project) -> dict:
    path = screen_path(p)
    return (_yaml(path) or {}) if os.path.exists(path) else {}


WATERS_SPECIES_ISSUES = {"aquatic", "species", "hcp", "nexus", "mitigation"}
WATERS_SPECIES_WORDS = ("wetland", "vernal", "aquatic", "waters", "species", "habitat", "stream", "cnddb")
NEGATIVE_WORDS = ("no features", "none visible", "no aquatic", "show no ", "outside the", "outside ", "does not affect", "no streams", "no ponding")


def resource_row(p: Project, r: dict) -> dict:
    """Is this constraint row a positive, mapped resource finding? And is it the kind (waters, wetlands, species, habitat)
    that brings resource permits, as opposed to a flood zone, which sizes the Roadmap but not the permit stack?"""
    issue = r.get("issue")
    extra = ""
    if r.get("fact") and r["fact"] in p.facts:
        extra = p.facts[r["fact"]].statement
    elif r.get("assumption") and r["assumption"] in p.assumptions:
        extra = p.assumptions[r["assumption"]].statement
    txt = " ".join([str(r.get(k, "")) for k in ("layer", "finding")] + [extra]).lower()
    is_resource = issue in RESOURCE_ISSUES or any(w in txt for w in RESOURCE_WORDS)
    has_finding = bool(r.get("finding") or r.get("fact") or r.get("assumption"))
    negative = any(w in txt for w in NEGATIVE_WORDS)
    positive = bool(is_resource and has_finding and r.get("status") in ("mapped", "field") and not negative)
    permits = positive and (issue in WATERS_SPECIES_ISSUES or any(w in txt for w in WATERS_SPECIES_WORDS))
    return {"positive": positive, "permits": permits, "issue": issue}


def scale_test(p: Project, screen: Optional[dict] = None) -> dict:
    screen = screen if screen is not None else load_screen(p)
    triggers: List[str] = []
    jur = p.meta.get("jurisdiction") or []
    if len(jur) > 1:
        triggers.append(f"parcels in {len(jur)} jurisdictions")
    sites = p.meta.get("sites") or 1
    if sites > 1:
        triggers.append(f"{sites} separate sites")
    # mapped resources: a constraint row on a resource issue with a mapped/field status and a positive finding
    for r in (screen.get("constraints") or {}).get("rows", []):
        hit = resource_row(p, r)
        if hit["positive"]:
            triggers.append(f"mapped resource: {r.get('layer')}")
    for a in screen.get("approvals") or []:
        name = (a.get("approval") or "").lower()
        if any(w in name for w in DISCRETIONARY):
            triggers.append(f"discretionary entitlement: {a.get('approval')}")
    if p.meta.get("board_package"):
        triggers.append("client needs a board package")
    recommended = "plus" if triggers else "roadmap"
    rv = screen.get("review") or {}
    override = rv.get("rung_override")
    return {"recommended": recommended, "triggers": triggers, "override": override, "override_reason": rv.get("override_reason"),
            "effective": override or recommended,
            "note": ("The Step 1a Screening is always the first rung; the test sizes the Roadmap that follows."
                     + (" Two or more adjacent parcels in one ownership count as one site." if len(p.meta.get("parcels") or []) > 1 else ""))}


def _dump_block(d: dict) -> str:
    return yaml.safe_dump({"review": d}, sort_keys=False, allow_unicode=True, width=120)


def record_review(p: Project, reviewer: str, items: Dict[int, str], date: Optional[str] = None,
                  rung_override: Optional[str] = None, override_reason: Optional[str] = None, summary: str = "") -> dict:
    """Write the review block into screen.yaml (replacing any existing top-level review block)."""
    if rung_override and rung_override not in RUNG_ORDER:
        raise ValueError(f"rung_override must be one of {RUNG_ORDER}")
    if rung_override and not override_reason:
        raise ValueError("a rung override needs a reason; it prints on the report")
    date = date or datetime.date.today().isoformat()
    block = {"reviewer": reviewer, "date": date, "items": {int(k): v for k, v in sorted(items.items(), key=lambda kv: int(kv[0]))}}
    if summary:
        block["summary"] = summary
    if rung_override:
        block["rung_override"] = rung_override
        block["override_reason"] = override_reason
    path = screen_path(p)
    text = open(path).read() if os.path.exists(path) else ""
    text = re.sub(r"(?ms)^review:.*?(?=^\S|\Z)", "", text).rstrip() + "\n\n" + _dump_block(block)
    with open(path, "w") as f:
        f.write(text)
    return block


def record_corrections(p: Project, corrections: List[dict], reviewer: str, date: Optional[str] = None) -> str:
    """Append the planner's corrections to the draft (section, field, from, to, reason) to corrections.yaml. The
    register is what the model learns from and what the dashboard counts as the error rate per Screen."""
    date = date or datetime.date.today().isoformat()
    path = os.path.join(PROJECTS, p.key, "corrections.yaml")
    existing = (_yaml(path) or {}).get("corrections", []) if os.path.exists(path) else []
    for c in corrections:
        existing.append({"date": date, "reviewer": reviewer, **c})
    with open(path, "w") as f:
        yaml.safe_dump({"corrections": existing}, f, sort_keys=False, allow_unicode=True, width=120)
    return path


def parse_fix(text: str) -> dict:
    """'section|field|from|to|reason' -> dict (pipes inside values are not supported; keep reasons short)."""
    parts = [x.strip() for x in text.split("|")]
    while len(parts) < 5:
        parts.append("")
    return {"section": parts[0], "field": parts[1], "from": parts[2], "to": parts[3], "reason": parts[4]}


def correction_metrics(root: str = PROJECTS, today: Optional[datetime.date] = None, days: int = 30) -> dict:
    import glob
    today = today or datetime.date.today()
    since = (today - datetime.timedelta(days=days)).isoformat()
    reviewed, corrections, by_section = 0, 0, {}
    for sp in glob.glob(os.path.join(root, "*", "screen.yaml")):
        sc = _yaml(sp) or {}
        rv = sc.get("review") or {}
        if rv.get("reviewer") and str(rv.get("date", "")) >= since:
            reviewed += 1
        cp = os.path.join(os.path.dirname(sp), "corrections.yaml")
        if os.path.exists(cp):
            for c in (_yaml(cp) or {}).get("corrections", []):
                if str(c.get("date", "")) >= since:
                    corrections += 1
                    by_section[str(c.get("section"))] = by_section.get(str(c.get("section")), 0) + 1
    return {"days": days, "screens_reviewed": reviewed, "corrections": corrections,
            "per_screen": round(corrections / reviewed, 2) if reviewed else None, "by_section": by_section}


def review_state(screen: dict) -> dict:
    rv = screen.get("review") or {}
    items = rv.get("items") or {}
    oks = sum(1 for v in items.values() if v == "ok")
    notes = {k: v for k, v in items.items() if v and v != "ok"}
    return {"reviewed": bool(rv.get("reviewer")), "reviewer": rv.get("reviewer", ""), "date": rv.get("date", ""),
            "ok": oks, "notes": notes, "summary": rv.get("summary", ""), "complete": bool(rv.get("reviewer")) and len(items) >= 10}
