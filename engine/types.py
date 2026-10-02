"""Development-type profile and coverage: what a greenfield or infill screen must cover, and which of the
type's primary issues the screen on file does not yet address (those become fact-needed rows)."""
from typing import List

from .model import Project


def profile(p: Project) -> dict:
    t = p.development_type
    return {"id": t.id, "name": t.name, "means": t.means, "drives": t.drives, "ceqa_expectation": t.ceqa_expectation,
            "schedule_months": t.schedule_months, "uses": p.meta.get("uses", []), "signals": t.signals,
            "primary_issues": [{"id": i["id"], "label": i["label"]} for i in t.primary_issues],
            "default_levers": t.default_levers, "typical_approvals": t.typical_approvals, "register_seed": t.register_seed,
            "fee_families": t.fee_families,
            "report_emphasis": t.report_emphasis}


def _row_text(row: dict) -> str:
    return " ".join(str(row.get(k, "")) for k in ("issue", "layer", "finding", "implication", "lever", "approval", "standard", "item")).lower()


def covers(row: dict, issue: dict) -> bool:
    if row.get("issue") == issue["id"]:
        return True
    txt = _row_text(row)
    return any(str(k).lower() in txt for k in issue.get("keywords", []))


def coverage(p: Project, screen: dict) -> dict:
    """Which primary issues the screen's constraint, lever, approval and property rows cover, and which are missing."""
    rows = list((screen.get("constraints") or {}).get("rows", [])) + list((screen.get("rules") or {}).get("levers", [])) \
        + list(screen.get("approvals") or []) + list((screen.get("property") or {}).get("rows", []))
    covered, missing = [], []
    for issue in p.development_type.primary_issues:
        (covered if any(covers(r, issue) for r in rows) else missing).append(issue)
    return {"covered": covered, "missing": missing}


def ordered_constraint_rows(p: Project, rows: List[dict]) -> List[dict]:
    """Constraint rows in the type's issue order, uncategorised rows after."""
    issues = p.development_type.primary_issues
    def rank(r):
        for i, issue in enumerate(issues):
            if covers(r, issue):
                return i
        return len(issues)
    return sorted(rows, key=rank)
