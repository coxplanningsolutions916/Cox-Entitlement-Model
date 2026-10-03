"""Map-level drafts (docs/FUNNEL.md part 2). The Map ($2,500, one week) is the planner's judgment on the record;
the model drafts, the planner corrects and signs. Four drafts:

  constraint_layers   the desktop constraints map as a layer manifest: every constraint with its finding, status
                      (mapped, field-verified, not yet pulled), source and confidence, exported for the ArcGIS template
  candidate_paths     the entitlement paths still open on that map, the approvals each would trigger and in what
                      order, the CEQA pathway, what would confirm or rule each out; never a chosen path
  hbu                 the permissible uses ranked against the market read
  verification_plan   the field surveys and studies that would confirm the map, in order, priced from the fee build

Everything is a draft and says so; the planner's edits live in screen.yaml (paths:, hbu:) and win over the generator."""
import csv
import json
import os
from typing import List, Optional

from . import charts, review as review_mod, types as types_mod
from .model import Project

ISSUE_LAYERS = {  # the GIS layers that stand behind each primary issue, for the manifest
    "aquatic": ["NWI wetlands", "NHD streams", "CARI", "vernal pool complexes"], "species": ["CNDDB occurrences (1 and 5 mi)", "USFWS critical habitat", "IPaC species list"],
    "hcp": ["HCP and NCCP plan areas and fee zones"], "ag": ["Williamson Act contracts", "FMMP farmland"], "flood": ["FEMA NFHL", "200-year floodplain and ULOP", "CVFPB jurisdiction"],
    "services": ["sewer and water service areas", "spheres of influence", "urban services boundary"], "vehicle": ["zoning", "General Plan", "specific plan areas"],
    "nexus": ["USACE jurisdiction (from the delineation)"], "cultural": ["historic resources inventory"], "mitigation": [],
    "compatibility": ["adjacent zoning and uses", "building heights"], "density_parking": ["zoning standards", "transit stops and corridors"],
    "levers": ["transit priority areas", "housing element sites", "AB 2011 corridors"], "utilities": ["sewer and water mains", "service areas"],
    "site_history": ["historic aerials", "EnviroStor and GeoTracker sites"], "trees": ["tree canopy", "heritage tree inventory"], "noise_air": ["noise contours", "major roads and rail"],
    "historic": ["historic districts and listed resources"], "traffic": ["VMT screening map", "transit priority areas"], "ceqa": ["master EIR tiering area"],
}
DISCRETIONARY = review_mod.DISCRETIONARY


def _short(name: str) -> str:
    return name.split(" (")[0].split(":")[0].strip()


# ---------------------------------------------------------------- constraints map manifest

def constraint_layers(p: Project, screen: dict) -> List[dict]:
    t = p.development_type
    rows = types_mod.ordered_constraint_rows(p, (screen.get("constraints") or {}).get("rows", []))
    out = []
    covered = set()
    for r in rows:
        issue = r.get("issue") or next((i["id"] for i in t.primary_issues if types_mod.covers(r, i)), None)
        covered.add(issue)
        finding, src, conf = r.get("finding"), r.get("source"), r.get("confidence")
        if r.get("fact") and r["fact"] in p.facts:
            f = p.facts[r["fact"]]; finding = finding or f.statement; src = f.source; conf = f.confidence
        elif r.get("assumption") and r["assumption"] in p.assumptions:
            a = p.assumptions[r["assumption"]]; finding = finding or a.statement; src = {"document": f"Cox assumption {a.id}"}; conf = "derived"
        status = {"mapped": "mapped", "field": "field-verified"}.get(r.get("status"), "not yet pulled")
        gis = list(ISSUE_LAYERS.get(issue, []))
        low = (str(r.get("layer", "")) + " " + str(finding or "")).lower()
        for words, extra in ((("wetland", "aquatic", "waters", "stream"), ["NWI wetlands", "NHD streams", "CARI"]), (("flood", "zone ae"), ["FEMA NFHL", "200-year floodplain and ULOP"]),
                             (("cnddb", "species", "habitat"), ["CNDDB occurrences (1 and 5 mi)", "USFWS critical habitat"]), (("tree", "nesting"), ["tree canopy", "heritage tree inventory"])):
            if any(w in low for w in words):
                gis += [x for x in extra if x not in gis]
        out.append({"issue": issue, "layer": r.get("layer"), "gis_layers": gis, "finding": finding or "", "status": status,
                    "verify": r.get("verify", ""), "implication": r.get("implication", ""), "confidence": conf or ("pending" if status == "not yet pulled" else "derived"),
                    "source": src.get("document") if isinstance(src, dict) else (src or "")})
    for i in t.primary_issues:
        if i["id"] not in covered:
            out.append({"issue": i["id"], "layer": i["label"], "gis_layers": ISSUE_LAYERS.get(i["id"], []), "finding": "", "status": "not yet pulled",
                        "verify": i["verify"], "implication": f"primary issue for every {t.name.lower()} site", "confidence": "pending", "source": ""})
    return out


def export_manifest(p: Project, layers: List[dict], out_dir: str = "out") -> dict:
    """CSV and JSON for the ArcGIS template (Suzanne, task 20516205): one row per constraint, the layers behind it, the tag."""
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, f"{p.key}-constraints-manifest")
    with open(base + ".csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["issue", "layer", "gis_layers", "status", "confidence", "finding", "implication", "verify", "source"])
        for l in layers:
            w.writerow([l["issue"], l["layer"], "; ".join(l["gis_layers"]), l["status"], l["confidence"], l["finding"], l["implication"], l["verify"], l["source"]])
    fees = {}
    try:
        from .model import PROJECTS, _yaml
        fp = os.path.join(PROJECTS, p.key, "fees.yaml"); fees = _yaml(fp) or {} if os.path.exists(fp) else {}
    except Exception:
        pass
    geo = {"type": "FeatureCollection", "features": []}
    if fees.get("point"):
        geo["features"].append({"type": "Feature", "geometry": {"type": "Point", "coordinates": fees["point"]},
                                "properties": {"key": p.key, "name": p.meta.get("name"), "parcels": p.meta.get("parcels"), "jurisdiction": p.meta.get("jurisdiction")}})
    with open(base + ".json", "w") as f:
        json.dump({"project": p.key, "development_type": p.development_type.id, "layers": layers, "site": geo}, f, indent=1)
    return {"csv": base + ".csv", "json": base + ".json"}


# ---------------------------------------------------------------- candidate paths

def _ceqa_options(p: Project):
    a = p.assumptions.get("assume.ceqa_pathway")
    if a and a.alternatives:
        return a.alternatives, a.current
    return [], None


def candidate_paths(p: Project, screen: dict) -> List[dict]:
    """Rule-based draft. The planner may replace it with screen.yaml `paths:`."""
    if screen.get("paths"):
        return [{**x, "basis": x.get("basis", "planner"), "draft": False} for x in screen["paths"]]
    t = p.development_type
    st = review_mod.scale_test(p, screen)
    resources = [x for x in st["triggers"] if x.startswith("mapped resource")]
    permit_rows = [r for r in (screen.get("constraints") or {}).get("rows", []) if review_mod.resource_row(p, r)["permits"]]
    approvals = [a.get("approval", "") for a in screen.get("approvals") or []]
    named_disc = [a for a in approvals if any(w in a.lower() for w in DISCRETIONARY)]
    ceqa_alts, ceqa_now = _ceqa_options(p)
    hum = lambda k: str(k).replace("_", " ").replace("class32", "Class 32").replace("mnd", "MND").replace("eir", "EIR").replace("is ", "IS/")
    ceqa_txt = (f"{hum(ceqa_now) if ceqa_now else 'to be set'}; alternatives: {', '.join(hum(x) for x in ceqa_alts)}" if ceqa_alts else t.ceqa_expectation)
    resource_permits = ["Section 404 and 401", "Fish and Game Code 1602", "CESA 2081 or ESA Section 7"] if permit_rows else []
    lo, hi = (t.schedule_months or [12, 24])
    paths = []
    # Path A: as the record frames it
    if approvals:
        paths.append({"id": "A", "name": "As the record frames it: " + " + ".join(_short(a) for a in approvals[:4]) + ("" if len(approvals) <= 4 else " + …"),
                      "approvals": approvals, "ceqa": ceqa_txt, "resource_permits": resource_permits, "status": "open",
                      "duration_months": [lo, hi], "confirms": ["the jurisdiction's pre-application confirms the vehicle", "the CEQA pathway holds against the checklist"] +
                      (["the delineation of record sets the resource permits"] if permit_rows else []), "rules_out": ["a mapped feature that forces an EIR where an exemption or MND was assumed"] if not permit_rows else ["impact acreage the alternatives test cannot avoid"],
                      "basis": "the approvals on file and the CEQA assumption", "draft": True})
    # Path B: by right
    by_right = (screen.get("fit") or {}).get("by_right") or {}
    br_text = (by_right.get("text") or "").lower()
    br_ok = by_right.get("ok")
    if br_ok is None:
        br_ok = not named_disc and not any(w in br_text for w in ("needs the rezone", "rezone", "amendment"))
    paths.append({"id": "B", "name": "By right under the current zone, with design review", "approvals": ["Site plan and design review"] + (["Ministerial permits only"] if br_ok else []),
                  "ceqa": "Class 32 infill exemption or ministerial (no CEQA)" if t.id in ("infill", "redevelopment") else "exemption or MND for the by-right program",
                  "resource_permits": resource_permits, "status": "open" if br_ok else "ruled out",
                  "duration_months": [3, 9], "confirms": ["the program fits the zone's use table and standards", "no discretionary approval is required"],
                  "rules_out": ["the program exceeds the by-right envelope"], "why_ruled_out": (f"the record names {', '.join(_short(a) for a in named_disc[:2])}: the program exceeds what the zone allows by right" if named_disc else ("the fit section says the program needs a rezone" if not br_ok else "")),
                  "basis": "the fit test against the current zone", "draft": True})
    # Path C: ministerial state path (infill residential)
    if t.id in ("infill", "redevelopment") and "residential" in (p.meta.get("uses") or []):
        paths.append({"id": "C", "name": "Ministerial under SB 35 / SB 423 (or AB 2011 on a commercial corridor)", "approvals": ["Ministerial approval with objective standards", "Design review limited to objective standards"],
                      "ceqa": "none (ministerial)", "resource_permits": resource_permits, "status": "to test",
                      "duration_months": [4, 10], "confirms": ["the jurisdiction's RHNA progress makes SB 35 or SB 423 available", "the site meets the statute's site criteria", "the affordability share the owner will carry", "zoning allows residential (after any rezone, the path reopens)"],
                      "rules_out": ["agricultural or non-residential zoning", "an affordability share the project cannot carry"], "basis": "the type's default levers", "draft": True})
    # Path D: the alternative vehicle
    if t.id == "greenfield":
        paths.append({"id": "D", "name": "Specific plan (or specific plan amendment) in place of a stand-alone General Plan amendment and rezone", "approvals": ["Specific plan or amendment", "Tentative subdivision map", "Development agreement (optional)"],
                      "ceqa": "EIR on the specific plan, with project-level tiering later", "resource_permits": resource_permits, "status": "to test",
                      "duration_months": [lo + 6, hi + 12], "confirms": ["the County's appetite for a plan-level entitlement", "a financing plan for backbone infrastructure", "whether neighbouring land joins"],
                      "rules_out": ["a site too small to carry plan-level infrastructure", "a County preference for the amendment-and-rezone route"], "basis": "the type's typical approvals", "draft": True})
    elif t.id in ("infill", "redevelopment") and named_disc:
        paths.append({"id": "D", "name": "Planned unit development or overlay in place of a straight rezone", "approvals": ["PUD or overlay designation", "Site plan and design review", "Density bonus where it helps"],
                      "ceqa": ceqa_txt, "resource_permits": resource_permits, "status": "to test",
                      "duration_months": [lo, hi], "confirms": ["the code offers a PUD or overlay route", "the trade the City would want for it"], "rules_out": ["a code without the tool", "a Council preference for the plain rezone"], "basis": "the type's typical approvals", "draft": True})
    elif t.id == "rural_resource":
        paths.append({"id": "D", "name": "Use permit under the agricultural zone (Williamson Act compatible use)", "approvals": ["Conditional use permit", "Williamson Act compatibility finding"],
                      "ceqa": "MND", "resource_permits": resource_permits, "status": "to test", "duration_months": [lo, hi],
                      "confirms": ["the use is on the County's compatible-use list", "water and septic feasibility"], "rules_out": ["an incompatible use under the contract"], "basis": "the type's typical approvals", "draft": True})
    for x in paths:
        x["triggers"] = resources + ([f"discretionary: {', '.join(_short(a) for a in named_disc[:3])}"] if named_disc and x["id"] == "A" else [])
    return paths


# ---------------------------------------------------------------- HBU ranking

def hbu(p: Project, screen: dict) -> dict:
    rows = screen.get("hbu") or []
    market = (screen.get("fit") or {}).get("market") or {}
    if rows:
        return {"rows": rows, "draft": False, "note": "Ranked by the planner against the market read."}
    use = (p.meta.get("uses") or ["residential"])[0]
    return {"rows": [{"use": f"{use.title()} as the client proposes ({p.meta.get('program', '')})", "permissible": "see the fit test and the candidate paths", "market": market.get("text") or "market read not yet in hand", "rank": "to rank", "basis": "intake"}],
            "draft": True, "note": "The ranking waits on the Business Analyst pull and the planner's read; the rows above are placeholders from the intake."}


# ---------------------------------------------------------------- verification plan

def verification_plan(p: Project, fb, ntp) -> List[dict]:
    """What would confirm the map, in order: each assumption's resolving deliverable with its fee, month and window;
    facts needed grouped under the deliverable or the data pull that supplies them."""
    span = charts.months_of(next((l.lands for l in p.cost_lines if l.id == "line.to1"), "")) or (1, 12)
    dm = charts.deliverable_months(p, ntp, span[1])
    by_deliv = {}
    for a in p.assumptions.values():
        d = None
        if a.resolved_by:
            try:
                d = p.deliverable(a.resolved_by)
            except KeyError:
                d = None
        key = d.code if d else "unassigned"
        e = by_deliv.setdefault(key, {"code": key, "name": d.name if d else "No deliverable named yet", "fee": None, "month": dm.get(d.code, {}).get("month") if d else None,
                                       "window": None, "settles": [], "moves": set(), "field_work": bool(d and d.field_work)})
        e["settles"].append(a.statement)
        for l in p.cost_lines:
            if l.id in a.cost_impact:
                e["moves"].add(l.label)
    for u in p.unquantifiable:
        for drv in u.drivers:
            for ref in drv.get("resolved_by", []):
                try:
                    d = p.deliverable(ref)
                except KeyError:
                    continue
                e = by_deliv.setdefault(d.code, {"code": d.code, "name": d.name, "fee": None, "month": dm.get(d.code, {}).get("month"), "window": None, "settles": [], "moves": set(), "field_work": d.field_work})
                e["settles"].append(f"{u.label}: {drv['name']}")
                e["moves"].add(u.label)
    for r in fb.deliverables:
        if r.code in by_deliv:
            by_deliv[r.code]["fee"] = r.fee_with_passthrough
    for d in p.deliverables:
        if d.code in by_deliv and d.window:
            w = p.canon.windows.get(d.window, {}); by_deliv[d.code]["window"] = w.get("name", d.window)
    plan = sorted(by_deliv.values(), key=lambda e: (e["month"] is None, e["month"] or 0, -len(e["moves"])))
    for i, e in enumerate(plan, 1):
        e["step"] = i; e["moves"] = sorted(e["moves"])
    return plan


def step1b_scope(p: Project, fb, plan: List[dict]) -> dict:
    to = p.meta.get("task_order_1") or {}
    if to:
        return {"name": to.get("name"), "fee": fb.total, "confidence": "firm", "basis": "the task order on file, priced by the fee build"}
    fee = sum(e["fee"] or 0 for e in plan if e["fee"])
    return {"name": "Step 1b: the surveys and studies in the verification plan", "fee": round(fee / 1000) * 1000 if fee else None, "confidence": "derived",
            "basis": "the sum of the resolving deliverables at the rate card, before coordination; a task order sets the firm figure"}


def build(p: Project, screen: dict, fb, ntp) -> dict:
    layers = constraint_layers(p, screen)
    plan = verification_plan(p, fb, ntp)
    return {"layers": layers, "paths": candidate_paths(p, screen), "hbu": hbu(p, screen), "plan": plan, "step1b": step1b_scope(p, fb, plan),
            "legend": {"mapped": sum(1 for l in layers if l["status"] == "mapped"), "field": sum(1 for l in layers if l["status"] == "field-verified"),
                       "pending": sum(1 for l in layers if l["status"] == "not yet pulled")}}


def render_text(p: Project, m: dict) -> str:
    out = [f"MAP DRAFTS — {p.meta.get('name')} ({p.development_type.name})", "", "Constraints map manifest:"]
    for l in m["layers"]:
        out.append(f"  [{l['status']:14}] {l['layer'][:44]:44} {(l['finding'] or l['verify'])[:60]}")
    out.append(""); out.append("Candidate entitlement paths (draft; never a chosen path):")
    for x in m["paths"]:
        out.append(f"  {x['id']}. {x['name']}  [{x['status']}]  {x['duration_months'][0]} to {x['duration_months'][1]} months")
        out.append(f"      approvals: {'; '.join(x['approvals'])}")
        out.append(f"      CEQA: {x['ceqa']}" + (f"; resource permits: {', '.join(x['resource_permits'])}" if x['resource_permits'] else ""))
        out.append(f"      confirms: {'; '.join(x['confirms'])}")
        if x.get("why_ruled_out"): out.append(f"      ruled out because: {x['why_ruled_out']}")
    out.append(""); out.append("Verification plan:")
    for e in m["plan"]:
        out.append(f"  {e['step']}. {e['code']} {e['name'][:48]:48} month {e['month']}  fee {('$' + format(e['fee'], ',.0f')) if e['fee'] else 'n/a':>10}  settles: {len(e['settles'])}  moves: {', '.join(e['moves'])[:60]}")
    s1 = m["step1b"]
    out.append(""); out.append(f"Step 1b scope: {s1['name']} — {('$' + format(s1['fee'], ',.0f')) if s1['fee'] else 'unpriced'} ({s1['confidence']}; {s1['basis']})")
    return "\n".join(out)
