"""The Scenarios calculator (docs/FUNNEL.md part 3). Two or three development programs estimated on the constraints
map, not drawn: gross area, less the exclusions the map shows (wetlands, flood, setbacks, easements), less the land-use
shares for the product type (roads, drainage, parks, open space), times a density or FAR range, giving the yield, the
approvals the program would trigger, the cost and schedule ranges and the assumptions it depends on. Every parameter
is named and ranged; the planner's `scenarios:` block in screen.yaml replaces the defaults."""
import os
import re
from typing import List, Optional

import yaml

from . import mapdraft, review as review_mod
from .model import CANON, Project

SHARES = os.path.join(CANON, "land_use_shares.yaml")
SQFT_PER_ACRE = 43560
PROGRAM_RE = re.compile(r"(\d[\d,]*)\s*(?:to|-|–)\s*(\d[\d,]*)\s*(lots?|units?|dwellings?|homes?|square feet|sf)", re.I)
SINGLE_RE = re.compile(r"(\d[\d,]*)\s*(lots?|units?|dwellings?|homes?|square feet|sf)", re.I)


def shares_canon() -> dict:
    return yaml.safe_load(open(SHARES))


def parse_program(text: str):
    """'58 to 62 lots' -> (58, 62, 'lots'); '80 units' -> (80, 80, 'units'); else None."""
    m = PROGRAM_RE.search(text or "")
    if m:
        return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")), m.group(3).lower().rstrip("s") + ("s" if not m.group(3).lower().endswith("sf") else "")
    m = SINGLE_RE.search(text or "")
    if m:
        n = int(m.group(1).replace(",", "")); return n, n, m.group(2).lower().rstrip("s") + "s"
    return None


def exclusions(p: Project, screen: dict) -> List[dict]:
    """Acres the map takes off the top. From the planner's `scenarios.exclusions` list; otherwise the resource rows
    that are mapped but not yet measured are carried as named exclusions with no acreage (a fact needed)."""
    sc = screen.get("scenarios") or {}
    if sc.get("exclusions"):
        return [{**x, "acres": x.get("acres"), "measured": x.get("acres") is not None} for x in sc["exclusions"]]
    out = []
    for r in (screen.get("constraints") or {}).get("rows", []):
        hit = review_mod.resource_row(p, r)
        if hit["positive"]:
            out.append({"name": r.get("layer"), "acres": None, "measured": False, "basis": "mapped on the record; acreage waits on the delineation or the parcel-specific determination"})
    return out


def _rng(x):
    return [float(x[0]), float(x[1])] if isinstance(x, (list, tuple)) else [float(x), float(x)]


def estimate(gross_acres: float, product: str, excl: List[dict], canon: dict, density_override=None, lot: Optional[str] = None, given_yield=None) -> dict:
    prod = canon["products"][product]
    ex_lo = sum(float(e["acres"]) for e in excl if e.get("acres") is not None)
    ex_hi = ex_lo
    dev_lo, dev_hi = max(0.0, gross_acres - ex_hi), max(0.0, gross_acres - ex_lo)
    shares = prod.get("shares", {})
    share_lo = sum(_rng(v)[0] for v in shares.values()); share_hi = sum(_rng(v)[1] for v in shares.values())
    steps = [{"step": "gross site", "low": gross_acres, "high": gross_acres, "unit": "acres", "basis": "parcel record"},
             {"step": "less exclusions on the map", "low": ex_lo, "high": ex_hi, "unit": "acres", "basis": "; ".join(e["name"] for e in excl) or "none measured"},
             {"step": "developable area", "low": dev_lo, "high": dev_hi, "unit": "acres", "basis": "gross less exclusions"}]
    assumptions = [f"exclusions: {('; '.join(e['name'] + (' (' + str(e['acres']) + ' ac)' if e.get('acres') is not None else ' (acreage not yet measured)') for e in excl)) or 'none on the record'}"]
    if prod["density_basis"] == "net":
        net_lo, net_hi = dev_lo * (1 - share_hi), dev_hi * (1 - share_lo)
        steps.append({"step": "less roads, drainage, parks and other public shares", "low": share_lo, "high": share_hi, "unit": "share", "basis": ", ".join(f"{k.replace('_', ' ')} {_rng(v)[0]:.0%} to {_rng(v)[1]:.0%}" for k, v in shares.items())})
        steps.append({"step": "net developable", "low": net_lo, "high": net_hi, "unit": "acres", "basis": "developable × (1 − shares)"})
        lot = lot or prod.get("default_lot"); d = _rng(density_override or prod["lot_options"][lot])
        y_lo, y_hi = net_lo * d[0], net_hi * d[1]
        steps.append({"step": f"yield at {lot} lots", "low": y_lo, "high": y_hi, "unit": prod["unit"], "basis": f"{d[0]:g} to {d[1]:g} per net acre"})
        assumptions += [f"shares {share_lo:.0%} to {share_hi:.0%} of developable area to roads, drainage, parks and other public uses", f"{lot} lots at {d[0]:g} to {d[1]:g} per net acre"]
    elif "far" in prod:
        far = _rng(density_override or prod["far"])
        y_lo, y_hi = dev_lo * SQFT_PER_ACRE * far[0], dev_hi * SQFT_PER_ACRE * far[1]
        steps.append({"step": "building area at FAR", "low": y_lo, "high": y_hi, "unit": "square feet", "basis": f"FAR {far[0]:g} to {far[1]:g} on developable area; site shares " + ", ".join(f"{k.replace('_', ' ')} {_rng(v)[0]:.0%} to {_rng(v)[1]:.0%}" for k, v in shares.items())})
        assumptions += [f"FAR {far[0]:g} to {far[1]:g}, surface parking within the site shares"]
    else:
        d = _rng(density_override or prod["density"])
        y_lo, y_hi = dev_lo * d[0], dev_hi * d[1]
        steps.append({"step": "yield at gross density", "low": y_lo, "high": y_hi, "unit": prod["unit"], "basis": f"{d[0]:g} to {d[1]:g} per gross developable acre; site shares " + ", ".join(f"{k.replace('_', ' ')} {_rng(v)[0]:.0%} to {_rng(v)[1]:.0%}" for k, v in shares.items())})
        assumptions += [f"{d[0]:g} to {d[1]:g} dwellings per gross developable acre"]
        if prod.get("structured_parking"):
            assumptions.append("structured parking, which the market read must support")
    if given_yield:
        y_lo, y_hi = float(given_yield[0]), float(given_yield[1])
        steps.append({"step": "yield as the client states it", "low": y_lo, "high": y_hi, "unit": prod["unit"], "basis": "the client's program; implied density shown for the record"})
        if dev_hi > 0:
            assumptions.append(f"implied {y_lo / dev_hi:.2f} to {y_hi / max(dev_lo, 0.01):.2f} {prod['unit']} per developable acre")
    return {"product": product, "product_label": prod["label"], "unit": prod["unit"], "steps": steps, "yield": [round(y_lo), round(y_hi)], "assumptions": assumptions,
            "needs_map": bool(prod.get("needs_map")), "structured_parking": bool(prod.get("structured_parking")), "exclusions_measured": all(e.get("acres") is not None for e in excl) if excl else True}


def _by_right(p: Project, screen: dict, gross: float, canon: dict):
    br = (screen.get("scenarios") or {}).get("by_right_yield")
    if br:
        return {"yield": [float(br[0]), float(br[1])], "unit": (screen.get("scenarios") or {}).get("by_right_unit", "units"), "basis": (screen.get("scenarios") or {}).get("by_right_basis", "planner")}
    for f in p.facts.values():
        v = f.value or {}
        if f.kind == "designation" and v.get("min_parcel_acres"):
            n = int(gross // float(v["min_parcel_acres"]))
            return {"yield": [n, n], "unit": "lots", "basis": f"{f.statement} ({f.id})"}
    return None


def build(p: Project, screen: dict, fb, prog: dict, ntp) -> dict:
    canon = shares_canon()
    gross = float(p.meta.get("acres") or 0)
    excl = exclusions(p, screen)
    md = mapdraft.build(p, screen, fb, ntp)
    paths = {x["id"]: x for x in md["paths"]}
    pathA = paths.get("A") or next(iter(paths.values()), None)
    pathB = paths.get("B")
    t = p.development_type
    use = (p.meta.get("uses") or ["residential"])[0]
    total = prog["total"]
    planner = (screen.get("scenarios") or {}).get("programs")
    specs = planner or [{"kind": k} for k in (canon["defaults_by_type"].get(t.id, {}).get(use) or ["client_program"])]
    out = []
    client = parse_program(p.meta.get("program", ""))
    for i, spec in enumerate(specs, 1):
        kind = spec.get("kind") or spec.get("product")
        if kind == "client_program":
            product = spec.get("product") or ("rural_residential" if client and client[2] == "lots" and gross / max(client[1], 1) > 0.9 else ("single_family_subdivision" if client and client[2] == "lots" else "garden_multifamily"))
            est = estimate(gross, product, excl, canon, density_override=spec.get("density"), lot=spec.get("lot"), given_yield=client[:2] if client else None)
            name = spec.get("name") or f"S{i}. The client's program: {p.meta.get('program', '').split('(')[0].strip()}"
            path = pathA
        elif kind == "by_right":
            br = _by_right(p, screen, gross, canon)
            name = spec.get("name") or f"S{i}. By right under the current designation"
            if br:
                est = {"product": "by_right", "product_label": "By right", "unit": br["unit"], "steps": [{"step": "by-right yield", "low": br["yield"][0], "high": br["yield"][1], "unit": br["unit"], "basis": br["basis"]}],
                       "yield": [round(br["yield"][0]), round(br["yield"][1])], "assumptions": [f"by-right standard: {br['basis']}"], "needs_map": br["unit"] == "lots", "structured_parking": False, "exclusions_measured": True}
            else:
                est = {"product": "by_right", "product_label": "By right", "unit": "units", "steps": [], "yield": None, "assumptions": ["the zone's by-right density is not yet on file"], "needs_map": False, "structured_parking": False, "exclusions_measured": True, "fact_needed": "the zone's by-right density standard"}
            path = pathB
        else:
            est = estimate(gross, kind, excl, canon, density_override=spec.get("density"), lot=spec.get("lot"))
            name = spec.get("name") or f"S{i}. {canon['products'][kind]['label']}"
            path = pathA if (client is None or (est["yield"] and est["yield"][1] > 0)) else pathB
        approvals = list((path or {}).get("approvals", []))
        if est.get("needs_map") and not any("map" in a.lower() for a in approvals):
            approvals.append("Tentative subdivision or condominium map (for-sale)")
        follows_A = path is pathA
        out.append({"id": f"S{i}", "name": name, "product": est["product"], "product_label": est["product_label"], "unit": est["unit"], "yield": est["yield"], "steps": est["steps"],
                    "approvals": approvals, "ceqa": (path or {}).get("ceqa", t.ceqa_expectation), "resource_permits": (path or {}).get("resource_permits", []), "path": (path or {}).get("id"),
                    "duration_months": (path or {}).get("duration_months", t.schedule_months), "status": (path or {}).get("status", "to test"),
                    "cost": ({"low": total["low"], "high": total["high"], "basis": "the program budget on file; this scenario follows the record's path"} if follows_A and total["high"] else
                             {"low": None, "high": None, "basis": "not priced: a different path from the program on file; priced when the planner adopts it"}),
                    "assumptions": est["assumptions"] + ([f"follows path {path['id']}: {path['name']}"] if path else []) + (["exclusion acreage not yet measured: the yield is an upper bound"] if not est.get("exclusions_measured") else []),
                    "fact_needed": est.get("fact_needed"), "draft": planner is None, "market": spec.get("market", "")})
    return {"gross_acres": gross, "exclusions": excl, "programs": out, "records_search": records_search(p, screen), "parameters_confidence": canon.get("confidence", "derived"),
            "note": "Estimated on the constraints map at industry-standard land-use shares; nothing is drawn. Drawing is Step 2."}


def records_search(p: Project, screen: dict) -> dict:
    """Ordered only where the Screen flags cultural sensitivity (strategy doc v2). Results are confidential; the
    Roadmap reports what they mean and never forwards the records. A v2 follows when they return."""
    rs = screen.get("records_search") or {}
    rows = (screen.get("constraints") or {}).get("rows", [])
    cult = [r for r in rows if r.get("issue") in ("cultural", "historic") or "cultural" in str(r.get("layer", "")).lower() or "historic" in str(r.get("layer", "")).lower()]
    flagged = any((r.get("finding") or "").lower().find(w) >= 0 for r in cult for w in ("sensitiv", "recorded", "site", "resource"))
    t = p.development_type
    waters = any(review_mod.resource_row(p, r)["permits"] for r in rows)
    if rs.get("returned"):
        state = "returned"
    elif rs.get("ordered"):
        state = "ordered"
    elif flagged or (t.id in ("greenfield", "rural_resource") and waters):
        state = "recommended"
    elif not cult or all(r.get("status", "none") == "none" for r in cult):
        state = "undecided: the cultural row is not yet pulled"
    else:
        state = "not flagged"
    reason = ("the cultural row flags sensitivity" if flagged else ("undeveloped land with mapped waters: the usual signal for recorded resources along drainages" if (t.id in ("greenfield", "rural_resource") and waters) else "no flag on the record"))
    return {"state": state, "reason": reason, "ordered": rs.get("ordered"), "returned": rs.get("returned"), "finding": rs.get("finding"), "confidential": True,
            "note": "Information Center results stay confidential; the Roadmap reports what they mean and does not forward the records. A Roadmap v2 follows when they return."}


def render_text(p: Project, s: dict) -> str:
    out = [f"SCENARIOS — {p.meta.get('name')} ({p.development_type.name}, {s['gross_acres']:g} acres)", ""]
    for e in s["exclusions"]:
        out.append(f"  exclusion: {e['name']}  {e['acres'] if e.get('acres') is not None else 'acreage not measured'}")
    for x in s["programs"]:
        y = f"{x['yield'][0]:,} to {x['yield'][1]:,} {x['unit']}" if x["yield"] else f"[FACT NEEDED: {x.get('fact_needed')}]"
        out.append(f"\n{x['name']}  [{x['product_label']}]  yield {y}  path {x['path']} ({x['status']})  {x['duration_months'][0]} to {x['duration_months'][1]} months")
        for st in x["steps"]:
            unit = st["unit"]; lo, hi = st["low"], st["high"]
            val = f"{lo:.0%} to {hi:.0%}" if unit == "share" else (f"{lo:,.1f} to {hi:,.1f} {unit}" if unit == "acres" else f"{lo:,.0f} to {hi:,.0f} {unit}")
            out.append(f"    {st['step']:52} {val:>28}   {st['basis'][:70]}")
        out.append(f"    approvals: {'; '.join(x['approvals'])}")
        out.append(f"    cost: " + (f"${x['cost']['low']:,.0f} to ${x['cost']['high']:,.0f}" if x["cost"]["low"] else x["cost"]["basis"]))
        out.append(f"    assumptions: {'; '.join(x['assumptions'])}")
    rs = s["records_search"]
    out.append(f"\nCultural records search: {rs['state']} ({rs['reason']})")
    return "\n".join(out)
