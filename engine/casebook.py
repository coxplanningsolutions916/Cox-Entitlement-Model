"""The casebook (docs/CASEBOOK.md): one record per project, structured so the engine can use it and a person can
read it. Facts carry sources; decisions carry a decider and a date; lessons carry the rule or benchmark they became
or the reason they stay judgment; people are named only with consent; quotables are not cleared for marketing until
someone says so. Cases publish to a team-only page, never to a client page."""
import glob
import os
from typing import Dict, List

import yaml

from .model import ROOT, ModelError

CASES = os.path.join(ROOT, "casebook")
LESSON_KINDS = {"rule", "benchmark", "playbook", "judgment", "process"}
REQUIRED = ("key", "name", "client", "jurisdiction", "development_type", "status", "summary")


def load(key: str, root: str = CASES) -> dict:
    path = os.path.join(root, f"{key}.yaml")
    if not os.path.exists(path):
        raise ModelError(f"case '{key}' not found under {root}")
    c = yaml.safe_load(open(path)) or {}
    validate(c)
    return c


def load_all(root: str = CASES) -> Dict[str, dict]:
    out = {}
    for fp in sorted(glob.glob(os.path.join(root, "*.yaml"))):
        c = yaml.safe_load(open(fp)) or {}
        validate(c)
        out[c["key"]] = c
    return out


def validate(c: dict) -> None:
    for r in REQUIRED:
        if not c.get(r):
            raise ModelError(f"case {c.get('key', '?')}: missing '{r}'")
    for i, t in enumerate(c.get("timeline", [])):
        if not (t.get("date") and t.get("event") and t.get("source")):
            raise ModelError(f"case {c['key']}: timeline[{i}] needs date, event and source")
    for i, ch in enumerate(c.get("challenges", [])):
        for k in ("id", "what", "signal", "source"):
            if not ch.get(k):
                raise ModelError(f"case {c['key']}: challenges[{i}] needs {k} (a challenge without the signal that revealed it teaches nothing)")
    for i, d in enumerate(c.get("decisions", [])):
        for k in ("call", "by", "date", "why", "source"):
            if not d.get(k):
                raise ModelError(f"case {c['key']}: decisions[{i}] needs {k}")
    ch_ids = {ch["id"] for ch in c.get("challenges", [])}
    for i, r in enumerate(c.get("resolutions", [])):
        if r.get("challenge") not in ch_ids:
            raise ModelError(f"case {c['key']}: resolutions[{i}] names unknown challenge {r.get('challenge')}")
        if not r.get("fix"):
            raise ModelError(f"case {c['key']}: resolutions[{i}] needs fix")
    for i, p in enumerate(c.get("people", [])):
        if not p.get("role"):
            raise ModelError(f"case {c['key']}: people[{i}] needs role")
        if p.get("name") and not p.get("consent"):
            raise ModelError(f"case {c['key']}: people[{i}] carries a name without consent; keep the role and drop the name, or record consent")
    for i, l in enumerate(c.get("lessons", [])):
        if l.get("kind") not in LESSON_KINDS:
            raise ModelError(f"case {c['key']}: lessons[{i}] kind must be one of {sorted(LESSON_KINDS)}")
        if l["kind"] == "rule" and not l.get("rule"):
            raise ModelError(f"case {c['key']}: lessons[{i}] is a rule lesson with no rule id (existing R-number or 'proposed R21')")
        if l["kind"] == "judgment" and not l.get("why_judgment"):
            raise ModelError(f"case {c['key']}: lessons[{i}] stays judgment: say why it cannot be a rule")
        if not l.get("lesson"):
            raise ModelError(f"case {c['key']}: lessons[{i}] needs the lesson in one sentence")
    for i, q in enumerate(c.get("quotables", [])):
        if not q.get("text"):
            raise ModelError(f"case {c['key']}: quotables[{i}] needs text")
        q.setdefault("cleared", False)
    for i, b in enumerate(c.get("benchmarks", [])):
        for k in ("metric", "value", "source"):
            if b.get(k) in (None, ""):
                raise ModelError(f"case {c['key']}: benchmarks[{i}] needs {k}")


def benchmarks(cases: Dict[str, dict]) -> List[dict]:
    out = []
    for key, c in cases.items():
        for b in c.get("benchmarks", []):
            out.append({"case": key, "jurisdiction": ", ".join(c.get("jurisdiction", [])), "development_type": c.get("development_type"), **b})
    return out


def playbook(cases: Dict[str, dict]) -> Dict[str, List[dict]]:
    """Lessons grouped by development type then by the approval or topic they tag."""
    out: Dict[str, List[dict]] = {}
    for key, c in cases.items():
        for l in c.get("lessons", []):
            out.setdefault(c.get("development_type", "any"), []).append({"case": key, **l})
    return out


def export(cases: Dict[str, dict]) -> dict:
    """Team-only export for the dashboard: full cases (names kept only where consent is recorded), the
    benchmark table and the playbook. Nothing here reaches a client page."""
    safe = {}
    for key, c in cases.items():
        cc = dict(c)
        cc["people"] = [({**p, "name": p.get("name")} if p.get("consent") else {k: v for k, v in p.items() if k != "name"}) for p in c.get("people", [])]
        safe[key] = cc
    return {"cases": safe, "benchmarks": benchmarks(cases), "playbook": playbook(cases),
            "counts": {"cases": len(cases), "challenges": sum(len(c.get("challenges", [])) for c in cases.values()),
                       "lessons": sum(len(c.get("lessons", [])) for c in cases.values()), "open_questions": sum(len(c.get("interview_questions", [])) for c in cases.values())}}


def render_text(c: dict) -> str:
    out = [f"CASE — {c['name']} ({c['client']}; {', '.join(c['jurisdiction'])}; {c['development_type']}; {c['status']})", "", c["summary"], ""]
    out.append("Timeline:")
    for t in c.get("timeline", []):
        out.append(f"  {t['date']}  {t['event']}")
    out.append(""); out.append("Challenges and resolutions:")
    res = {r["challenge"]: r for r in c.get("resolutions", [])}
    for ch in c.get("challenges", []):
        out.append(f"  [{ch['id']}] {ch['what']}")
        out.append(f"       signal: {ch['signal']}")
        if ch["id"] in res:
            out.append(f"       fix: {res[ch['id']]['fix']}")
    out.append(""); out.append("Decisions:")
    for d in c.get("decisions", []):
        out.append(f"  {d['date']}  {d['by']}: {d['call']}  — {d['why']}")
    out.append(""); out.append("Lessons:")
    for l in c.get("lessons", []):
        out.append(f"  [{l['kind']}{(' ' + l['rule']) if l.get('rule') else ''}] {l['lesson']}")
    if c.get("interview_questions"):
        out.append(""); out.append("Open for the interview:")
        for q in c["interview_questions"]:
            out.append(f"  - {q}")
    return "\n".join(out)
