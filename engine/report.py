"""The Step 1a Screening / Roadmap report generator (docs/PRODUCT.md, ten sections; docs/FEATURES.md 1.3 to 1.9, 4.7, 6).

The report is built from the project files only. Every figure carries a numbered source; a row with no
source reads as a fact needed with what verifies it (never a guess). Client output carries fees and
ranges, never hours or rates (build brief §5). The rung sets the depth:

  screening  the ten sections, ranges only in section 8, the register, the reviewer sign-off
  roadmap    adds the program budget table and the window schedule in section 8, the planner's stamp
  plus       roadmap plus the scenario placeholders and the board summary block

HTML is the web report; the PDF is printed from it by Chrome headless when Chrome is on the machine.
"""
import datetime
import os
import re
import shutil
import subprocess
from typing import List, Optional

import jinja2

from . import fee as fee_mod, program as program_mod, review as review_mod, rules, schedule as schedule_mod, types as types_mod
from .model import Project, _yaml, CONFIDENCE

HERE = os.path.dirname(os.path.abspath(__file__))
FACT_NEEDED = "[FACT NEEDED]"
RUNGS = {
    "screening": {"title": "Entitlement Roadmap: Screen", "level": "Screen", "price": 500, "turnaround": "48 hours (two business days)",
                  "staff_hours": "one hour of planning staff review", "credit": "credited toward the Map",
                  "stamp": "Entitlement Roadmap, Screen level: model output reviewed and signed by Cox planning staff."},
    "roadmap": {"title": "Entitlement Roadmap: Map", "level": "Map", "price": 2500, "turnaround": "one week",
                "staff_hours": "four hours of senior planner review and direction", "credit": "credited toward Scenarios",
                "stamp": "Entitlement Roadmap, Map level: Cox Planning Solutions' judgment on the record, planner-reviewed."},
    "plus": {"title": "Entitlement Roadmap: Scenarios", "level": "Scenarios", "price": 5000, "turnaround": "two weeks",
             "staff_hours": "seven staff hours including a specialist desk read", "credit": "",
             "stamp": "Entitlement Roadmap, Scenarios level: Cox Planning Solutions' recommendation with a specialist read, planner-reviewed."},
}
CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Adobe Acrobat DC/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "",
]
CHECKLIST = [
    "Parcel and jurisdiction resolved correctly, including city versus county and any annexation question.",
    "Zoning, general plan and overlays match the jurisdiction's current map, not a stale layer.",
    "The stated use is classified correctly in the use table; borderline uses named and the interpretation route stated.",
    "Standards-versus-program test reads right; any variance or exception need is called out.",
    "Biology flags are plausible on the aerial; CNDDB hits within range are the right species for the habitat.",
    "Flood and ULOP status checked against the jurisdiction's own map; levee or CVFPB jurisdiction confirmed.",
    "The approval set is complete and the CEQA pathway call is defensible; a tiering document, if named, is the right one.",
    "Cost and schedule ranges pass the smell test against comparable Cox projects; confidence labels are honest.",
    "Market section figures are current and the trade area is the right shape for the use.",
    "Assumption register lists the assumptions that matter most, each with a verify-by task and cost; the upgrade recommendation is right for the scale test.",
]
STANDING_HEADER = ("For planning purposes. Not a scope of work, a fee proposal, or a commitment to perform work. "
                   "Costs and durations are planning estimates. Agency review timelines are outside our control.")
TERMS = ("We meet professional standards for planning, environmental, civil engineering, architecture, and landscape "
         "architecture work in California. We do not guarantee approvals or agency timelines. The figures here are "
         "planning estimates, not a fee proposal. Fees are set in each Task Order.")
DISCLAIMER_MAPPED = "Every constraint line is a screening indicator from mapped sources, not a determination; field confirmation is named per line."


# ---------------------------------------------------------------- sources

class Sources:
    """Numbered source list. Every figure in the report points at one entry (FEATURES 1.4)."""

    def __init__(self):
        self.items: List[dict] = []
        self._index = {}

    @staticmethod
    def label(src) -> str:
        if isinstance(src, str):
            return src
        parts = [src.get("document") or src.get("layer") or "source"]
        if src.get("sections"):
            parts.append("sections " + ", ".join(str(s) for s in src["sections"]))
        if src.get("author"):
            parts.append(src["author"])
        if src.get("revised"):
            parts.append(f"revised {src['revised']}")
        if src.get("location"):
            parts.append(src["location"])
        return ", ".join(parts)

    def ref(self, src, kind: str = "") -> Optional[int]:
        if not src:
            return None
        key = self.label(src)
        if key not in self._index:
            self.items.append({"n": len(self.items) + 1, "label": key, "kind": kind})
            self._index[key] = len(self.items)
        return self._index[key]


# ---------------------------------------------------------------- cells

def _cell(text, ref=None, confidence=None, verify=None, needed=False, extra=None):
    return {"text": text, "ref": ref, "confidence": confidence, "verify": verify, "needed": needed, "extra": extra or ""}


def _needed(verify):
    return _cell(FACT_NEEDED, verify=verify, needed=True)


def _fact_cell(p: Project, S: Sources, fact_id: str, override_text: Optional[str] = None):
    f = p.facts.get(fact_id)
    if f is None:
        return _needed(f"fact {fact_id} is not on file")
    if f.superseded:
        return _cell(f"{override_text or f.statement} (superseded by {f.superseded_by})", S.ref(f.source, "fact"), f.confidence)
    if f.stale():
        return _cell(f"{override_text or f.statement} (stale: re-establish)", S.ref(f.source, "fact"), f.confidence, verify="re-establish the fact")
    return _cell(override_text or f.statement, S.ref(f.source, "fact"), f.confidence)


def _assumption_cell(p: Project, S: Sources, aid: str, text: Optional[str] = None):
    a = p.assumptions.get(aid)
    if a is None:
        return _needed(f"assumption {aid} is not on file")
    ref = S.ref({"document": f"Cox assumption {a.id}: {a.reason}", "author": a.owner}, "assumption")
    return _cell(text or a.statement, ref, "derived", extra="assumption")


def _row_cell(p: Project, S: Sources, row: dict, text_keys=("value", "finding", "text", "result")):
    """A screen.yaml row to a cell: fact id, derived-from fact, source dict, assumption, or fact needed."""
    text = next((row[k] for k in text_keys if row.get(k)), None)
    if row.get("fact"):
        return _fact_cell(p, S, row["fact"], text)
    if row.get("assumption"):
        return _assumption_cell(p, S, row["assumption"], text)
    if row.get("derived_from"):
        base = p.facts.get(row["derived_from"])
        ref = S.ref(base.source, "fact") if base else None
        return _cell(text or FACT_NEEDED, ref, row.get("confidence", "derived"), needed=not text, verify=row.get("verify"), extra=f"derived from {row['derived_from']}")
    if text and row.get("source"):
        return _cell(text, S.ref(row["source"]), row.get("confidence", "derived"), verify=row.get("verify"))
    if text:
        return _cell(text, None, row.get("confidence"), verify=row.get("verify"), needed=False, extra="unsourced")
    return _needed(row.get("verify", "source to be named"))


# ---------------------------------------------------------------- helpers

def _money(x):
    return f"${x:,.0f}"


def _range(low, high):
    return _money(low) if low == high else f"{_money(low)} to {_money(high)}"


def _months_to_entitlement(p: Project):
    """The latest 'Months a to b' on any cost line is the planning horizon to entitlement."""
    hi = 0
    for l in p.cost_lines:
        for m in re.finditer(r"Months?\s+(\d+)\s+to\s+(\d+)", l.lands or ""):
            hi = max(hi, int(m.group(2)))
    return hi or None


def _deliv(p: Project, ref):
    try:
        return p.deliverable(ref)
    except KeyError:
        return None


def _deliv_fee(fb, d):
    if d is None:
        return None
    for r in fb.deliverables:
        if r.code == d.code:
            return r.fee_with_passthrough
    return None


def load_screen(p: Project) -> dict:
    path = os.path.join(os.path.dirname(os.path.abspath(p.canon.__class__.__module__ and __file__)), "..", "projects", p.key, "screen.yaml")
    path = os.path.normpath(path)
    return _yaml(path) if os.path.exists(path) else {}


# ---------------------------------------------------------------- build

def build(p: Project, rung: str = "screening", today: Optional[datetime.date] = None,
          ntp: Optional[datetime.date] = None, internal: bool = False) -> dict:
    if rung not in RUNGS:
        raise ValueError(f"rung must be one of {sorted(RUNGS)}")
    today = today or datetime.date.today()
    ntp = ntp or today
    S = Sources()
    sc = load_screen(p)
    fb = fee_mod.build(p)
    prog = program_mod.build(p)
    placements = schedule_mod.place(p, ntp)
    violations = rules.check(p, fb)
    report_src = sc.get("report_source")
    sections = []

    # 1. The decision in three lines
    dec = sc.get("decision", {})
    lines = []
    wb = dec.get("what_to_build")
    lines.append({"label": "WHAT TO BUILD", "cell": _row_cell(p, S, wb) if wb else _needed("the client's stated use and program, or the HBU read")})
    ha = dec.get("how_approved")
    if ha:
        c = _cell(ha["text"], None, ha.get("confidence", "derived"))
        refs = [S.ref({"document": f"Cox assumption {a}: {p.assumptions[a].reason}", "author": p.assumptions[a].owner}, "assumption")
                for a in ha.get("assumptions", []) if a in p.assumptions]
        c["ref"] = refs[0] if refs else None
        c["extra"] = "rests on " + ", ".join(ha.get("assumptions", [])) if ha.get("assumptions") else ""
        lines.append({"label": "HOW IT GETS APPROVED", "cell": c})
    else:
        lines.append({"label": "HOW IT GETS APPROVED", "cell": _needed("the approval set in section 7")})
    t = prog["total"]
    months = _months_to_entitlement(p)
    carried = p.assumptions.get(dec.get("carried_by", ""), None)
    wit = f"About {_range(t['low'], t['high'])} to entitlement"
    wit += f" over roughly {months} months from notice to proceed" if months else ""
    wit += f", assuming {carried.statement[0].lower() + carried.statement[1:].rstrip('.')}" if carried else ""
    wit += f". {t['sentence']}"
    for x in prog["exclusions"]:
        wit += f" Excluded and not yet quantifiable: {x['label'].lower()}."
    lines.append({"label": "WHAT IT TAKES", "cell": _cell(wit, S.ref({"document": "Cox program budget, computed by the model from the cost lines on file"}, "model"), "derived", extra="composition of the cost lines")})
    tp = types_mod.profile(p)
    sections.append({"n": 1, "title": "The decision in three lines", "blocks": [
        {"type": "lines", "items": lines},
        {"type": "para", "text": f"This is a {tp['name'].lower()} site ({tp['means'].rstrip('.').lower()}). {tp['drives']} CEQA expectation for the type: {tp['ceqa_expectation']}"}]})

    # 2. Property record
    rows = []
    for r in sc.get("property", {}).get("rows", []):
        rows.append([_cell(r["item"]), _row_cell(p, S, r)])
    if not rows:
        rows = [[_cell("Property record"), _needed("parcel layer and the preliminary title report")]]
    sections.append({"n": 2, "title": "Property record", "blocks": [{"type": "table", "columns": ["Item", "Record"], "rows": rows}]})

    # 3. What the rules allow
    std = [[_cell(r["standard"]), _row_cell(p, S, r)] for r in sc.get("rules", {}).get("standards", [])] or \
          [[_cell("Development standards"), _needed("the zoning district's use table and standards")]]
    lev = [[_cell(r["lever"]), _cell(r.get("test", "")), _row_cell(p, S, r)] for r in sc.get("rules", {}).get("levers", [])] or \
          [[_cell(l), _cell(""), _needed("applicability test for this site")] for l in tp["default_levers"]]
    sections.append({"n": 3, "title": "What the rules allow", "blocks": [
        {"type": "table", "columns": ["Standard", "Value"], "rows": std, "caption": "Development standards for the designation and zone"},
        {"type": "table", "columns": ["Lever", "Applicability test", "Result"], "rows": lev, "caption": "Regulatory levers that could change the envelope"}]})

    # 4. Fit
    fit = sc.get("fit", {})
    fit_rows = [[_cell("The client's program"), _row_cell(p, S, fit["client_program"]) if fit.get("client_program") else _needed("the client's stated program")],
                [_cell("Allowed by right"), _row_cell(p, S, fit["by_right"]) if fit.get("by_right") else _needed("the by-right envelope from section 3")],
                [_cell("Market read (highest and best use)"), _row_cell(p, S, fit["market"]) if fit.get("market") else _needed("Business Analyst trade-area pull and the planner's read")]]
    blocks = [{"type": "table", "columns": ["Test", "Finding"], "rows": fit_rows}]
    if fit.get("gap"):
        blocks.append({"type": "para", "text": fit["gap"]})
    blocks.append({"type": "note", "text": "This is a desktop read, not an appraisal or a market study."})
    sections.append({"n": 4, "title": "Fit: the program against the rules and the market", "blocks": blocks})

    # 5. Constraints screen
    crows = []
    for r in types_mod.ordered_constraint_rows(p, sc.get("constraints", {}).get("rows", [])):
        status = {"mapped": "Mapped", "field": "Field-confirmed", "none": "Not yet pulled"}.get(r.get("status", "none"), r.get("status", ""))
        crows.append([_cell(r["layer"]), _row_cell(p, S, r), _cell(status), _cell(r.get("implication", ""))])
    cov = types_mod.coverage(p, sc)
    for issue in cov["missing"]:
        crows.append([_cell(issue["label"]), _needed(issue["verify"]), _cell("Not yet pulled"), _cell(f"a primary issue for every {tp['name'].lower()} site")])
    if not crows:
        crows = [[_cell("Constraints"), _needed("the constraint layers"), _cell("Not yet pulled"), _cell("")]]
    sections.append({"n": 5, "title": "Constraints screen", "blocks": [
        {"type": "table", "columns": ["Layer", "Finding", "Status", "What it implies"], "rows": crows},
        {"type": "note", "text": DISCLAIMER_MAPPED}]})

    # 6. Historic aerial read
    aer = sc.get("aerial", {})
    sections.append({"n": 6, "title": "Historic aerial read", "blocks": [
        {"type": "lines", "items": [{"label": "Imagery record", "cell": _row_cell(p, S, aer) if aer.get("text") else _needed(aer.get("verify", "multi-year imagery review"))}]}]})

    # 7. The approval set
    arows = []
    federal = False
    for r in sc.get("approvals", []):
        c = _row_cell(p, S, {**r, "text": r.get("body", "")})
        federal = federal or bool(r.get("federal_nexus"))
        arows.append([_cell(r["approval"] + (" (federal nexus)" if r.get("federal_nexus") else "")), c, _cell(r.get("typical", ""))])
    if not arows:
        arows = [[_cell("Approval set"), _needed("the entitlement path from the use table and the constraint screen"), _cell("")]]
    blocks = [{"type": "table", "columns": ["Approval", "Who decides", "Typical duration"], "rows": arows}]
    if federal:
        blocks.append({"type": "para", "text": "A federal permit is in the set, so Endangered Species Act Section 7 consultation and Section 106 review ride with it. That nexus, not the County calendar, is the structural dependency that sets the schedule."})
    sections.append({"n": 7, "title": "The approval set", "blocks": blocks})

    # 8. Schedule and cost ranges
    blocks = []
    comp_rows = []
    for key, sec in prog["sections"].items():
        c = sec["composition"]
        comp_rows.append([_cell(sec["label"]), _cell(_range(c["low"], c["high"]), S.ref({"document": "Cox program budget, computed by the model from the cost lines on file"}, "model"), "derived"), _cell(c["sentence"])])
    comp_rows.append([_cell("Program cost to entitlement"), _cell(_range(t["low"], t["high"]), S.ref({"document": "Cox program budget, computed by the model from the cost lines on file"}, "model"), "derived"), _cell(t["sentence"])])
    blocks.append({"type": "table", "columns": ["Block", "Range", "Confidence"], "rows": comp_rows, "caption": "Cost ranges by block, with the confidence composition behind each"})
    for x in prog["exclusions"]:
        blocks.append({"type": "para", "text": f"Excluded, not yet quantifiable: {x['label']}. Drivers: {', '.join(x['drivers'])}. {x['why']}"})
    fees = prog.get("fees")
    if fees and fees["applicable"]:
        frows = []
        for a in fees["applicable"]:
            ref = S.ref(a["source"], "fee schedule") if a.get("source", {}).get("document") else None
            why = a["why"] + (f"; map: {a['map'].get('layer', '')} {a['map'].get('feature', '') or ''} {a['map'].get('date', '') or ''}".rstrip() if a.get("map") else "")
            frows.append([_cell(a["name"]), _cell(a["kind"]), _cell(why, ref, "published" if a.get("effective") else "pending", needed=False)])
        blocks.append({"type": "table", "columns": ["Fee schedule applying to this site", "Kind", "Why it applies"], "rows": frows,
                       "caption": "Fee schedules the parcel's location and approval set bring in (fees are priced by district, not estimated)"})
        if fees["pending"]:
            blocks.append({"type": "note", "text": "Fee lines with no adopted amount on file yet: " + "; ".join(fees["pending"]) + ". Each is in the register with what verifies it."})
    if rung in ("roadmap", "plus"):
        prow = []
        for key, sec in prog["sections"].items():
            for l in sec["lines"]:
                rng = "quote pending" if l.confidence == "pending" else _range(l.low, l.high)
                payer = {"client_direct": "client, direct", "passthrough": "Cox, at cost plus 15%", "cox": "Cox"}.get(l.payer, l.payer)
                prow.append([_cell(sec["label"].split(". ", 1)[-1]), _cell(l.label), _cell(rng, S.ref({"document": l.basis}, "basis"), l.confidence), _cell(payer), _cell(l.lands)])
        blocks.append({"type": "table", "columns": ["Block", "Item", "Range", "Who pays", "When it lands"], "rows": prow, "caption": "Program budget"})
        wrows = []
        for x in schedule_mod.critical_window_sequence(placements):
            w = p.canon.windows.get(x.window, {})
            wrows.append([_cell(x.name), _cell(w.get("name", x.window)), _cell(f"{x.opens} to {x.closes}", S.ref({"document": f"Season window canon: {w.get('basis', '')}"}, "canon"), "published"), _cell(x.flag or "")])
        if wrows:
            blocks.append({"type": "table", "columns": ["Field task", "Window", "Next open dates", "Note"], "rows": wrows, "caption": f"Season windows from a notice to proceed of {ntp.isoformat()}"})
    else:
        blocks.append({"type": "note", "text": "Line-item budget, the window schedule and the critical path are in the Roadmap."})
    sections.append({"n": 8, "title": "Schedule and cost ranges", "blocks": blocks})

    # 9. The assumption register
    reg = []
    for a in p.assumptions.values():
        d = _deliv(p, a.resolved_by) if a.resolved_by else None
        cost = _deliv_fee(fb, d)
        moves = [l.label for l in p.cost_lines if l.id in a.cost_impact]
        reg.append({"assumption": a.statement, "current": a.current or "open", "why": a.reason,
                    "verified_by": f"{d.code} {d.name}" if d else (a.resolved_by or FACT_NEEDED),
                    "cost": _money(cost) if cost is not None else "", "moves": "; ".join(moves)})
    for u in p.unquantifiable:
        for drv in u.drivers:
            ds = [ _deliv(p, r) for r in drv.get("resolved_by", []) ]
            ds = [d for d in ds if d]
            reg.append({"assumption": f"{u.label}: {drv['name']}", "current": "no figure carried", "why": "driver of an unquantifiable line",
                        "verified_by": "; ".join(f"{d.code} {d.name}" for d in ds) or FACT_NEEDED,
                        "cost": "; ".join(_money(_deliv_fee(fb, d)) for d in ds if _deliv_fee(fb, d) is not None), "moves": u.label})
    needed = []
    for s_ in sections:
        for b in s_["blocks"]:
            for r in b.get("rows", []):
                for c in r:
                    if c.get("needed"):
                        needed.append({"assumption": f"Fact needed: {r[0]['text']}", "current": "not on file", "why": "",
                                       "verified_by": c.get("verify") or "", "cost": "", "moves": f"section {s_['n']}"})
            for it in b.get("items", []):
                c = it.get("cell", {})
                if c.get("needed"):
                    needed.append({"assumption": f"Fact needed: {it['label']}", "current": "not on file", "why": "",
                                   "verified_by": c.get("verify") or "", "cost": "", "moves": f"section {s_['n']}"})
    fee_needed = []
    for l in [x for sec in prog["sections"].values() for x in sec["lines"] if x.confidence == "pending" and x.id.startswith("fee.")]:
        fee_needed.append({"assumption": f"Fee amount needed: {l.label}", "current": "pending", "why": "",
                           "verified_by": l.basis.split("verify: ")[-1] if "verify: " in l.basis else l.basis.split(". ")[-1], "cost": "", "moves": "section 8"})
    sections.append({"n": 9, "title": "The assumption register", "blocks": [
        {"type": "register", "rows": reg + needed + fee_needed, "columns": ["Assumption", "Carried as", "Why", "Verified by", "Cox fee to verify", "What it moves"]},
        {"type": "note", "text": "The fee to verify is the Cox fee for the named deliverable at the rate card, before coordination. It is the diligence list and the next proposal in one table."}]})

    # 10. Go or no-go and the three questions
    g = sc.get("go_no_go", {})
    qs = []
    for q in sc.get("questions", []):
        ds = [d for d in (_deliv(p, r) for r in q.get("resolved_by", [])) if d]
        qs.append({"q": q["q"], "by": "; ".join(f"{d.code} {d.name}" for d in ds)})
    if not qs:
        qs = [{"q": r["assumption"], "by": r["verified_by"]} for r in reg[:3]]
    st = review_mod.scale_test(p, sc)
    rung_name = {"screening": "Screen ($500)", "roadmap": "Map ($2,500)", "plus": "Scenarios ($5,000)"}
    scale_txt = f"Scale test: {rung_name[st['recommended']]}" + (f" because of {'; '.join(st['triggers'])}" if st["triggers"] else " (no trigger fired)") + "."
    if st["override"]:
        scale_txt += f" Planner's call: {rung_name[st['override']]}. {st['override_reason']}"
    scale_txt += f" {st['note']}"
    blocks = [{"type": "lines", "items": [{"label": "READ", "cell": _row_cell(p, S, {**g, "text": g.get("read")}) if g.get("read") else _needed("the planner's go or no-go read")},
                                          {"label": "RUNG", "cell": _cell(scale_txt, S.ref({"document": "Cox scale test, docs/PRICING-LADDER.md; plugin reference scale-test-and-pricing.md"}, "method"), "derived")}]},
              {"type": "questions", "items": qs}]
    sections.append({"n": 10, "title": "Go or no-go, and the three questions to answer next", "blocks": blocks})

    # next steps (FEATURES 4.7): 1b then 2, permits at 4
    to1 = p.meta.get("task_order_1", {})
    if rung == "screening":
        nxt = [f"The Map at {_money(RUNGS['roadmap']['price'])}, with this Screen's {_money(RUNGS['screening']['price'])} credited: {RUNGS['roadmap']['staff_hours']}, the highest-and-best-use read, the desktop constraints map with the candidate entitlement paths on it, the verification plan, the working session, and a scoped and priced Step 1b proposal, in one week."]
        if st["recommended"] == "plus":
            nxt.append(f"The scale test points to Scenarios at {_money(RUNGS['plus']['price'])}: a specialist desk read, a cultural records search where flagged, scenario estimates on the constraints map, a board package and a second session, in two weeks.")
    elif rung == "roadmap":
        nxt = [f"Step 1b, the surveys and data collection that confirm the constraints map in the field. The proposal that follows this Map: {to1.get('name', 'Task Order 1')} at {_money(fb.total)}, firm." if to1 else
               "Step 1b, the surveys and data collection that confirm the constraints map in the field, priced from the register above."]
        nxt.append(f"Scenarios at {_money(RUNGS['plus']['price'])} with this Map's {_money(RUNGS['roadmap']['price'])} credited, where the decision needs two or three programs estimated on the map and a board package.")
    else:
        nxt = [f"Step 1b, the surveys and data collection that confirm the constraints map in the field. The proposal that follows: {to1.get('name', 'Task Order 1')} at {_money(fb.total)}, firm." if to1 else
               "Step 1b, the surveys and data collection that confirm the constraints map in the field, priced from the register above."]
    nxt.append("Step 2 is conceptual design and alternatives, with engineering front and center: the scenarios above become designed alternatives, compared on the approvals, cost and schedule each one triggers, before anyone talks about permits.")
    nxt.append("Permit preparation and processing is Step 4, after planning and environmental review in Step 3. Compliance and monitoring is Step 5.")

    # review and sign-off
    rv = sc.get("review", {}) or {}
    items = rv.get("items", {}) or {}
    checklist = [{"n": i + 1, "text": txt, "state": items.get(i + 1, items.get(str(i + 1), ""))} for i, txt in enumerate(CHECKLIST)]
    rstate = review_mod.review_state(sc)
    reviewed = rstate["complete"]
    stamp = RUNGS[rung]["stamp"] if reviewed else ("REVIEW IN PROGRESS: not yet complete. Not for release." if rstate["reviewed"] else "MODEL OUTPUT, NOT YET STAFF-REVIEWED. Not for release.")

    meta = {
        "rung": rung, "rung_title": RUNGS[rung]["title"], "level": RUNGS[rung]["level"], "price": RUNGS[rung]["price"], "staff_hours": RUNGS[rung]["staff_hours"],
        "turnaround": RUNGS[rung]["turnaround"], "credit": RUNGS[rung]["credit"],
        "name": p.meta.get("name"), "client": p.meta.get("client"), "contact": p.meta.get("contact"),
        "address": sc.get("address", p.meta.get("name")), "apns": ", ".join(p.meta.get("parcels", [])), "acres": p.meta.get("acres"),
        "jurisdiction": ", ".join(p.meta.get("jurisdiction", [])), "date": today.isoformat(), "ntp": ntp.isoformat(),
        "development_type": tp["name"], "development_type_id": tp["id"], "uses": ", ".join(tp["uses"]),
        "scale": st, "review_summary": rstate["summary"], "review_notes": rstate["notes"],
        "stamp": stamp, "reviewed": reviewed, "reviewer": rv.get("reviewer", ""), "review_date": rv.get("date", ""),
        "standing_header": STANDING_HEADER, "terms": TERMS,
        "model_version": "cox-entitlement-model 0.1.0",
    }
    legend = [{"key": c["key"], "label": c["label"], "means": c["means"]} for c in p.canon.confidence.get("classes", [])]
    internal_block = None
    if internal:
        internal_block = {"violations": [str(v) for v in violations], "hours": fb.hours, "margin_pct": fb.margin_pct,
                          "strong_share": t["strong_share"], "sources_count": len(S.items), "facts_needed": len(needed)}
    return {"meta": meta, "sections": sections, "next_steps": nxt, "checklist": checklist, "sources": S.items,
            "legend": legend, "internal": internal_block, "facts_needed": len(needed), "fees_needed": len(fee_needed)}


# ---------------------------------------------------------------- render

def render_html(report: dict) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(HERE, "templates")), autoescape=True,
                             trim_blocks=True, lstrip_blocks=True)
    return env.get_template("report.html.j2").render(r=report)


def find_chrome() -> Optional[str]:
    for c in CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return None


def render_pdf(html_path: str, pdf_path: str) -> bool:
    chrome = find_chrome()
    if not chrome:
        return False
    url = "file://" + os.path.abspath(html_path)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
           f"--print-to-pdf={os.path.abspath(pdf_path)}", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return r.returncode == 0 and os.path.exists(pdf_path)


def write(p: Project, rung: str = "screening", out_dir: str = "out", pdf: bool = False, internal: bool = False,
          ntp: Optional[datetime.date] = None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rep = build(p, rung, ntp=ntp, internal=internal)
    html = render_html(rep)
    base = os.path.join(out_dir, f"{p.key}-{rung}" + ("-internal" if internal else ""))
    with open(base + ".html", "w") as f:
        f.write(html)
    result = {"html": base + ".html", "pdf": None, "facts_needed": rep["facts_needed"], "sources": len(rep["sources"])}
    if pdf:
        result["pdf"] = base + ".pdf" if render_pdf(base + ".html", base + ".pdf") else None
    return result
