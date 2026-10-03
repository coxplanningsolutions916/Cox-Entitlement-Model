"""Scaffold a project from the intake form (docs/FUNNEL.md, part 1). The hero form gives an address or APN, the
intent and an email; the intake page adds the contact, role, source and UTM, documents, the scale-test answers
and the order (level, paid or free). From that the model opens a project folder the rest of the engine can run:
the development type (the pilot default by jurisdiction class until the planner confirms it), the register seeded
from the type, every primary issue carried as a fact needed, the client's documents filed as sources, the order
recorded with its delivery date, and the free-screen pace applied."""
import datetime
import glob
import os
import re
from typing import Dict, List, Optional

import yaml

from .model import CANON, PROJECTS, Canon, _yaml

PILOT = os.path.join(CANON, "pilot.yaml")
LEVEL_KEY = {"screen": "screening", "screening": "screening", "map": "roadmap", "roadmap": "roadmap", "scenarios": "plus", "plus": "plus"}


def pilot() -> dict:
    return _yaml(PILOT)


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:48] or "site"


def pilot_check(jurisdiction: str) -> dict:
    cfg = pilot()
    for j in cfg["pilot"]:
        if j["jurisdiction"].lower() == (jurisdiction or "").lower():
            county = j.get("county") or j["jurisdiction"]
            regions = next((x.get("regions") for x in cfg["pilot"] if x["jurisdiction"] == county), None) or []
            return {"in_pilot": True, "kind": j["kind"], "county": county, "regions": regions}
    return {"in_pilot": False, "kind": None, "county": None, "regions": []}


def business_days(start: datetime.date, n: int) -> datetime.date:
    d = start
    while n > 0:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _orders(root: str) -> List[dict]:
    out = []
    for fp in glob.glob(os.path.join(root, "*", "intake.yaml")):
        d = _yaml(fp) or {}
        if d:
            d["_key"] = os.path.basename(os.path.dirname(fp)); out.append(d)
    return out


def free_slot(today: datetime.date, root: str = PROJECTS) -> dict:
    """Apply the free-screen cap and the monthly pace. Returns whether a free Screen is available now, the month it
    lands in, and the delivery date it would carry."""
    cfg = pilot()["free_screens"]
    orders = [o for o in _orders(root) if o.get("free")]
    used_total = len(orders)
    if used_total >= cfg["cap"]:
        return {"available": False, "reason": f"the {cfg['cap']} free Screens are taken", "used_total": used_total, "cap": cfg["cap"]}
    month = max(today, datetime.date.fromisoformat(str(cfg["starts"])))
    while True:
        ym = month.strftime("%Y-%m")
        used_month = sum(1 for o in orders if str(o.get("delivery_due", ""))[:7] == ym)
        if used_month < cfg["pace_per_month"]:
            break
        month = (month.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    start = max(today, month if month > today else today)
    due = business_days(start, pilot()["turnaround_business_days"]["screening"])
    return {"available": True, "used_total": used_total, "cap": cfg["cap"], "month": month.strftime("%Y-%m"),
            "used_month": used_month, "pace": cfg["pace_per_month"], "delivery_due": due.isoformat(), "paced": month > today}


def metrics(today: Optional[datetime.date] = None, root: str = PROJECTS) -> dict:
    today = today or datetime.date.today()
    cfg = pilot()["free_screens"]
    orders = _orders(root)
    free = [o for o in orders if o.get("free")]
    ym = today.strftime("%Y-%m")
    slot = free_slot(today, root)
    return {"free": {"cap": cfg["cap"], "used_total": len(free), "used_month": sum(1 for o in free if str(o.get("delivery_due", ""))[:7] == ym),
                     "pace": cfg["pace_per_month"], "month": ym, "next_slot": slot.get("delivery_due"), "available": slot["available"]},
            "orders": [{"key": o["_key"], "level": o.get("level"), "free": bool(o.get("free")), "ordered_at": o.get("ordered_at"),
                        "delivery_due": o.get("delivery_due"), "pilot": o.get("pilot", {}).get("in_pilot"), "role": o.get("role")} for o in orders]}


def _dump(path: str, data) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=110)


def scaffold(order: dict, today: Optional[datetime.date] = None, root: str = PROJECTS) -> dict:
    """order keys: address, apns (list), jurisdiction, intent, use, acres, name, email, company, role, phone, source,
    utm (dict or str), documents (list of {label, url}), scale (dict: parcels, resources, discretionary, board),
    level (screen|map|scenarios), free (bool), development_type (optional), ordered_at (optional)."""
    today = today or datetime.date.today()
    cfg = pilot()
    canon = Canon.load()
    level = LEVEL_KEY.get((order.get("level") or "screen").lower(), "screening")
    pc = pilot_check(order.get("jurisdiction", ""))
    dtype = order.get("development_type")
    inferred = False
    if not dtype:
        dtype = cfg["type_default"].get(pc["kind"] or "city", "infill"); inferred = True
    if dtype not in canon.types:
        raise ValueError(f"unknown development_type {dtype}")
    t = canon.types[dtype]
    key = slug(order.get("address") or (order.get("apns") or ["site"])[0])
    base = key; n = 2
    while os.path.exists(os.path.join(root, key)):
        key = f"{base}-{n}"; n += 1
    d = os.path.join(root, key); os.makedirs(d)
    ordered_at = order.get("ordered_at") or today.isoformat()
    free = bool(order.get("free")) and level == "screening"
    slot = free_slot(today, root) if free else None
    if free and not slot["available"]:
        free = False
    due = (slot["delivery_due"] if free else business_days(today, cfg["turnaround_business_days"][level]).isoformat())
    price = 0 if free else cfg["prices"][level]
    apns = [str(a) for a in (order.get("apns") or [])]
    uses = [order.get("use")] if order.get("use") else ["residential"]
    src_form = {"document": "Entitlement Roadmap intake form", "author": order.get("name") or order.get("email") or "client", "revised": ordered_at}

    _dump(os.path.join(d, "project.yaml"), {
        "key": key, "name": order.get("address") or key, "client": order.get("company") or order.get("name") or "client",
        "contact": order.get("name") or "", "development_type": dtype, "type_inferred": inferred, "uses": uses,
        "jurisdiction": [order.get("jurisdiction") or ""], "regions": pc["regions"], "parcels": apns,
        "acres": order.get("acres"), "program": order.get("intent") or "", "status": "intake",
        "board_package": bool((order.get("scale") or {}).get("board"))})
    facts = []
    if apns or order.get("address"):
        facts.append({"id": "fact.intake.parcel", "kind": "intake", "statement": f"The client identifies the site as {order.get('address') or ''}" + (f", APN {', '.join(apns)}" if apns else "") + ".",
                      "source": src_form, "established": ordered_at, "established_by": "intake", "confidence": "derived"})
    for i, doc in enumerate(order.get("documents") or [], 1):
        facts.append({"id": f"fact.intake.doc{i}", "kind": "document", "statement": f"Client supplied: {doc.get('label', 'document')}.",
                      "source": {"document": doc.get("label", "client document"), "location": doc.get("url", ""), "author": "client", "revised": ordered_at},
                      "established": ordered_at, "established_by": "intake", "confidence": "derived"})
    _dump(os.path.join(d, "facts.yaml"), {"facts": facts})
    _dump(os.path.join(d, "assumptions.yaml"), {"assumptions": [
        {"id": f"assume.seed_{i + 1}", "statement": s_, "owner": "intake", "reason": f"Standard starting assumption for a {t.name.lower()} site; the planner sets it in review.",
         "alternatives": [], "current": None} for i, s_ in enumerate(t.register_seed)]})
    for name in ("deliverables", "benchmarks", "conflicts"):
        _dump(os.path.join(d, f"{name}.yaml"), {name: []})
    _dump(os.path.join(d, "program.yaml"), {"lines": []})
    _dump(os.path.join(d, "unquantifiable.yaml"), {"lines": []})
    sc_ = order.get("scale") or {}
    screen = {
        "address": order.get("address") or key,
        "report_source": {"document": "Entitlement Roadmap intake form", "revised": ordered_at},
        "decision": {"what_to_build": {"text": order.get("intent") or "", "source": src_form, "confidence": "derived"} if order.get("intent") else None},
        "property": {"rows": [
            {"item": "Assessor parcels", "fact": "fact.intake.parcel"} if facts else {"item": "Assessor parcels", "verify": "parcel layer"},
            {"item": "Owner of record", "verify": "Assessor roll; preliminary title report"},
            {"item": "Zoning district", "verify": f"{order.get('jurisdiction', 'jurisdiction')} zoning layer"},
            {"item": "General Plan designation", "verify": f"{order.get('jurisdiction', 'jurisdiction')} General Plan land use layer"},
            {"item": "Overlays and plan areas", "verify": "overlay and specific plan layers"},
            {"item": "Habitat plan coverage", "verify": "HCP and NCCP plan-area layers with date"},
            {"item": "Williamson Act contract", "verify": "county contract map"},
            {"item": "FEMA flood zone", "verify": "FEMA NFHL panel; 200-year floodplain map"},
            {"item": "Easements of record", "verify": "preliminary title report"}]},
        "rules": {"standards": [{"standard": "Use table and development standards for the zone", "verify": f"{order.get('jurisdiction', 'jurisdiction')} development code"}],
                  "levers": [{"lever": l, "test": "", "verify": "applicability test for this site"} for l in t.default_levers]},
        "fit": {"client_program": {"text": order.get("intent") or "", "source": src_form, "confidence": "derived"} if order.get("intent") else None,
                "by_right": {"verify": "the zone's by-right envelope"}, "market": {"verify": "ArcGIS Business Analyst trade-area pull"}},
        "constraints": {"rows": [{"issue": i["id"], "layer": i["label"], "verify": i["verify"], "status": "none"} for i in t.primary_issues]},
        "aerial": {"verify": "multi-year imagery review"},
        "approvals": [],
        "questions": [{"q": s_, "resolved_by": []} for s_ in t.register_seed[:3]],
        "scale_answers": {"parcels_or_jurisdictions": sc_.get("parcels"), "mapped_resources": sc_.get("resources"), "discretionary": sc_.get("discretionary"), "board_package": sc_.get("board")},
        "review": {}}
    screen["decision"] = {k: v for k, v in screen["decision"].items() if v}
    screen["fit"] = {k: v for k, v in screen["fit"].items() if v}
    _dump(os.path.join(d, "screen.yaml"), screen)
    q = {"acres": {"value": float(order["acres"]), "source": src_form, "confidence": "derived"}} if order.get("acres") else {}
    _dump(os.path.join(d, "fees.yaml"), {"point": None, "uses": uses, "quantities": q, "memberships": [], "reconcile": {}, "keep_manual": {}})
    intake = {"key": key, "ordered_at": ordered_at, "level": level, "level_name": {"screening": "Screen", "roadmap": "Map", "plus": "Scenarios"}[level],
              "price": price, "free": free, "free_slot": slot, "delivery_due": due, "credit_applied": 0,
              "pilot": pc, "development_type": dtype, "type_inferred": inferred,
              "contact": {"name": order.get("name"), "email": order.get("email"), "company": order.get("company"), "role": order.get("role"), "phone": order.get("phone")},
              "source": order.get("source"), "utm": order.get("utm"), "documents": order.get("documents") or [], "scale_answers": sc_,
              "reviewer": None, "hooks": {}}
    _dump(os.path.join(d, "intake.yaml"), intake)
    return {"key": key, "path": d, "development_type": dtype, "type_inferred": inferred, "level": level, "price": price, "free": free,
            "delivery_due": due, "pilot": pc["in_pilot"], "free_slot": slot}


def load_intake(key: str, root: str = PROJECTS) -> dict:
    path = os.path.join(root, key, "intake.yaml")
    return (_yaml(path) or {}) if os.path.exists(path) else {}


def save_intake(key: str, data: dict, root: str = PROJECTS) -> None:
    _dump(os.path.join(root, key, "intake.yaml"), data)
