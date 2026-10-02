"""Publish a project's model to the client dashboard (docs/PRICING-LADDER.md, "The client dashboard tie";
FEATURES 1.11). One JSON per project lands in the dashboard repo's roadmaps/ folder, the same way the
budgets snapshot does, and the dashboard renders it at the client's link. From Step 1b the same page
carries the client statement, so the plan and the money are one page.

The JSON is client-safe by construction: it is built from the client report (no hours, no rates) and
carries fees, ranges, confidence, the register, the change log and the next step."""
import datetime
import json
import os
from typing import Optional

from . import program as program_mod, report as report_mod, schedule as schedule_mod
from .model import Project

DEFAULT_DASH = os.path.expanduser(os.environ.get("COX_DASHBOARD", "~/code/cox-dashboard"))


def _text(cell: dict) -> str:
    if cell.get("needed"):
        return f"{report_mod.FACT_NEEDED} verified by: {cell.get('verify', '')}".strip()
    return cell.get("text", "")


def export(p: Project, rung: str = "screening", today: Optional[datetime.date] = None, ntp: Optional[datetime.date] = None) -> dict:
    today = today or datetime.date.today()
    rep = report_mod.build(p, rung, today=today, ntp=ntp)
    prog = program_mod.build(p)
    sc = report_mod.load_screen(p)
    sections = {s["n"]: s for s in rep["sections"]}

    decision = [{"label": it["label"], "text": _text(it["cell"]), "confidence": it["cell"].get("confidence")}
                for it in sections[1]["blocks"][0]["items"]]
    approvals = [{"approval": a.get("approval"), "body": a.get("body", ""), "typical": a.get("typical", ""), "federal_nexus": bool(a.get("federal_nexus"))}
                 for a in sc.get("approvals", [])]
    t = prog["total"]
    budget = {"blocks": [{"label": sec["label"], "low": sec["composition"]["low"], "high": sec["composition"]["high"],
                          "strong_share": sec["composition"]["strong_share"], "sentence": sec["composition"]["sentence"],
                          "lines": ([{"label": l.label, "low": l.low, "high": l.high, "confidence": l.confidence, "payer": l.payer, "lands": l.lands}
                                     for l in sec["lines"]] if rung != "screening" else [])}
                         for sec in prog["sections"].values()],
              "total": {"low": t["low"], "high": t["high"], "strong_share": t["strong_share"], "sentence": t["sentence"]},
              "exclusions": prog["exclusions"],
              "fee_schedules": [{"name": a["name"], "kind": a["kind"], "why": a["why"]} for a in (prog.get("fees") or {}).get("applicable", [])],
              "fees_pending": (prog.get("fees") or {}).get("pending", [])}
    windows = []
    if rung != "screening":
        ntp_d = ntp or today
        for x in schedule_mod.critical_window_sequence(schedule_mod.place(p, ntp_d)):
            w = p.canon.windows.get(x.window, {})
            windows.append({"task": x.name, "window": w.get("name", x.window), "opens": str(x.opens), "closes": str(x.closes), "note": x.flag or ""})
    register = []
    for r in sections[9]["blocks"][0]["rows"]:
        status = "pending" if r["assumption"].startswith(("Fact needed", "Fee amount needed")) else ("open" if r["current"] in ("open", "no figure carried") else "carried")
        register.append({**r, "status": status})
    change_log = []
    for f in sorted(p.facts.values(), key=lambda f: str(f.established), reverse=True):
        change_log.append({"date": str(f.established), "what": f.statement, "kind": f.kind or "fact", "confidence": f.confidence,
                           "supersedes": f.supersedes, "superseded": f.superseded})
    for c in p.conflicts:
        if c.status == "closed":
            change_log.append({"date": str(c.closed_on), "what": f"Conflict {c.number} closed: {c.title}. {c.resolution.strip()}", "kind": "conflict", "confidence": "", "supersedes": [], "superseded": False})
    change_log.sort(key=lambda x: x["date"], reverse=True)
    questions = sections[10]["blocks"][1]["items"]
    m = rep["meta"]
    return {
        "key": p.key, "name": m["name"], "client": m["client"], "contact": m["contact"], "address": m["address"], "apns": m["apns"],
        "acres": m["acres"], "jurisdiction": m["jurisdiction"], "rung": rung, "rung_title": m["rung_title"], "price": m["price"],
        "generated": today.isoformat(), "reviewed": m["reviewed"], "reviewer": m["reviewer"], "review_date": m["review_date"], "stamp": m["stamp"],
        "statement_key": p.meta.get("dashboard_key"), "status": p.meta.get("status", ""),
        "decision": decision, "go_no_go": _text(sections[10]["blocks"][0]["items"][0]["cell"]), "questions": questions,
        "approvals": approvals, "windows": windows, "budget": budget, "register": register, "change_log": change_log,
        "next_steps": rep["next_steps"], "facts_needed": rep["facts_needed"], "fees_needed": rep["fees_needed"],
        "sources": len(rep["sources"]), "model_version": m["model_version"], "standing_header": m["standing_header"], "terms": m["terms"],
    }


def write(p: Project, rung: str = "screening", dash: Optional[str] = None, today: Optional[datetime.date] = None, ntp: Optional[datetime.date] = None) -> str:
    dash = dash or DEFAULT_DASH
    out_dir = os.path.join(dash, "roadmaps")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{p.key}.json")
    with open(path, "w") as f:
        json.dump(export(p, rung, today, ntp), f, indent=1, default=str)
    return path
