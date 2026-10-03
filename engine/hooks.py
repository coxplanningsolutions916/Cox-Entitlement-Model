"""The hooks around an order (docs/FUNNEL.md, part 1): Automator opportunity at Roadmap Requested with level, value,
source, UTM and the free-screen tag; the Productive review task on the reviewer rota; the QuickBooks invoice request
(or the $0 record); Roadmap Delivered and the delivery email on sign-off. Every hook runs dry by default and returns
the payload it would send; `live=True` sends it. The API clients are the ones the firm already runs
(~/code/cox-productive-tools: ghl_client.py, productive_client.py), found through COX_TOOLS or the default path."""
import datetime
import hashlib
import hmac
import os
import sys
from typing import Optional

from . import intake as intake_mod
from .model import PROJECTS

TOOLS = os.path.expanduser(os.environ.get("COX_TOOLS", "~/code/cox-productive-tools"))


def _clients():
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(TOOLS, ".env"))
        load_dotenv(os.path.join(os.path.expanduser("~/code/cox-automator-mcp"), ".env"))
    except ImportError:
        pass
    import ghl_client as gc  # noqa
    import productive_client as pc  # noqa
    return gc, pc


def _cfg():
    return intake_mod.pilot()


def dashboard_link(key: str) -> Optional[str]:
    """The client's /r/ link needs the dashboard's SHARE_SECRET; without it the Client links page is the place to copy it."""
    secret = os.environ.get("SHARE_SECRET")
    if not secret:
        return None
    tok = hmac.new(secret.encode(), ("rm:" + key).encode(), hashlib.sha256).hexdigest()[:20]
    return f"{_cfg()['dashboard_url']}/r/{tok}"


def _opp_name(it: dict) -> str:
    return f"Entitlement Roadmap ({it['level_name']}) — {it.get('key')}"


# ---------------------------------------------------------------- Automator

def _pipeline(gc, s, loc, cfg):
    pls = gc.get_json(s, "/opportunities/pipelines", params={"locationId": loc}).get("pipelines", [])
    pl = next((p for p in pls if p.get("id") == cfg.get("pipeline_id")), None) or \
         next((p for p in pls if p.get("name", "").lower() == cfg.get("pipeline", "").lower()), None)
    if not pl:
        raise RuntimeError(f"Sales pipeline not found by id {cfg.get('pipeline_id')} or name {cfg.get('pipeline')}")
    return pl

def automator_order(key: str, live: bool = False, root: str = PROJECTS) -> dict:
    it = intake_mod.load_intake(key, root)
    c = it.get("contact") or {}
    cfg = _cfg()["automator"]
    utm = it.get("utm") if isinstance(it.get("utm"), str) else " ".join(f"{k}={v}" for k, v in (it.get("utm") or {}).items())
    tags = [f"roadmap-{it['level_name'].lower()}"] + (["free-screen"] if it.get("free") else []) + ([] if (it.get("pilot") or {}).get("in_pilot") else ["outside-pilot"])
    contact = {"firstName": (c.get("name") or "").split(" ")[0], "lastName": " ".join((c.get("name") or "").split(" ")[1:]),
               "email": c.get("email"), "phone": c.get("phone"), "companyName": c.get("company"), "source": it.get("source"), "tags": tags}
    opportunity = {"pipeline": cfg["pipeline"], "stage": cfg["requested_stage"], "name": _opp_name(it), "monetaryValue": it.get("price", 0),
                   "source": it.get("source"), "status": "open"}
    note = (f"Entitlement Roadmap order: {it['level_name']} at ${it.get('price', 0):,}" + (" (free Screen)" if it.get("free") else "") +
            f"; delivery due {it.get('delivery_due')}; role {c.get('role')}; UTM {utm or 'none'}; documents {len(it.get('documents') or [])}; "
            f"scale answers {it.get('scale_answers')}; project key {key}.")
    payload = {"contact": {k: v for k, v in contact.items() if v}, "opportunity": opportunity, "note": note}
    if not live:
        return {"dry_run": True, **payload}
    gc, _ = _clients()
    s = gc.make_session(); loc = gc.location_id()
    body = {"locationId": loc, **{k: v for k, v in contact.items() if v and k != "tags"}}
    try:
        r = gc.post_json(s, "/contacts/", body); cid = (r.get("contact") or r).get("id")
    except Exception as e:  # duplicate → GHL returns the existing id in meta
        import json as _json
        meta = {}
        try:
            meta = _json.loads(getattr(e, "body", "{}")).get("meta") or {}
        except Exception:
            pass
        cid = meta.get("contactId")
        if not cid:
            raise
    pl = _pipeline(gc, s, loc, cfg)
    st = next((x for x in pl.get("stages", []) if x.get("name", "").lower() == cfg["requested_stage"].lower()), None)
    if not st:
        raise RuntimeError(f"stage {cfg['requested_stage']} not found in {cfg['pipeline']}")
    ob = {"pipelineId": pl["id"], "pipelineStageId": st["id"], "contactId": cid, "name": opportunity["name"], "status": "open",
          "locationId": loc, "monetaryValue": opportunity["monetaryValue"]}
    if it.get("source"):
        ob["source"] = it["source"]
    o = gc.post_json(s, "/opportunities/", ob); oid = (o.get("opportunity") or o).get("id")
    gc.post_json(s, f"/contacts/{cid}/notes", {"body": note})
    if tags:
        try:
            gc.post_json(s, f"/contacts/{cid}/tags", {"tags": tags})
        except Exception:
            pass
    it.setdefault("hooks", {})["automator"] = {"contact_id": cid, "opportunity_id": oid, "stage": cfg["requested_stage"], "at": datetime.datetime.now().isoformat(timespec="seconds")}
    intake_mod.save_intake(key, it, root)
    return {"dry_run": False, "contact_id": cid, "opportunity_id": oid, **payload}


def automator_delivered(key: str, live: bool = False, root: str = PROJECTS) -> dict:
    it = intake_mod.load_intake(key, root)
    cfg = _cfg()["automator"]
    link = dashboard_link(key) or f"{_cfg()['dashboard_url']}/links (Client links page: copy the roadmap link)"
    note = f"Entitlement Roadmap {it.get('level_name')} delivered; reviewed by {it.get('reviewer') or 'planner'}; dashboard {link}."
    payload = {"stage": cfg["delivered_stage"], "note": note, "opportunity_id": (it.get("hooks") or {}).get("automator", {}).get("opportunity_id")}
    if not live:
        return {"dry_run": True, **payload}
    if not payload["opportunity_id"]:
        raise RuntimeError("no Automator opportunity recorded for this order; run automator_order first")
    gc, _ = _clients()
    s = gc.make_session(); loc = gc.location_id()
    pl = _pipeline(gc, s, loc, cfg)
    st = next((x for x in pl.get("stages", []) if x.get("name", "").lower() == cfg["delivered_stage"].lower()), None)
    if not st:
        raise RuntimeError(f"stage {cfg['delivered_stage']} not found in the Sales pipeline")
    gc.put_json(s, f"/opportunities/{payload['opportunity_id']}", {"pipelineStageId": st["id"]})
    cid = it["hooks"]["automator"].get("contact_id")
    if cid:
        gc.post_json(s, f"/contacts/{cid}/notes", {"body": note})
    it["hooks"]["automator"]["stage"] = cfg["delivered_stage"]; it["hooks"]["automator"]["delivered_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    intake_mod.save_intake(key, it, root)
    return {"dry_run": False, **payload}


# ---------------------------------------------------------------- Productive review task

def productive_review_task(key: str, live: bool = False, root: str = PROJECTS) -> dict:
    it = intake_mod.load_intake(key, root)
    cfg = _cfg()
    n = len([o for o in intake_mod._orders(root)])
    reviewer = cfg["reviewers"][(n - 1) % len(cfg["reviewers"])] if cfg["reviewers"] else None
    title = f"Review the {it.get('level_name')} for {it.get('key')} by {it.get('delivery_due')}"
    body = (f"<p>Model draft ready for the planner's review. Run the review and the stamp clears:</p>"
            f"<pre>cd ~/code/cox-entitlement-model && source .venv/bin/activate && python -m engine review {key} --reviewer \"&lt;you&gt;\" --ok 1,2,3,4,5,6,7,8,9,10 [--note n=\"...\"] [--fix \"section|field|from|to|reason\"]</pre>"
            f"<p>Then: <code>python -m engine report {key} --rung {it.get('level')} --pdf</code>, <code>python -m engine publish {key} --rung {it.get('level')}</code>, "
            f"<code>python -m engine hooks {key} delivered --live</code>. Level {it.get('level_name')}, {'free Screen' if it.get('free') else '$' + format(it.get('price', 0), ',')}, "
            f"type {it.get('development_type')}{' (inferred: confirm in item 1)' if it.get('type_inferred') else ''}, pilot {'yes' if (it.get('pilot') or {}).get('in_pilot') else 'NO'}.</p>")
    payload = {"project_id": cfg["productive"]["review_project"], "list_name": cfg["productive"]["review_list_name"], "assignee_id": reviewer,
               "due_date": it.get("delivery_due"), "title": title, "description": body}
    if not live:
        return {"dry_run": True, **payload}
    _, pc = _clients()
    s = pc.make_session()
    lists = list(pc.get_all(s, "/task_lists", params={"filter[project_id]": payload["project_id"], "page[size]": 200}))
    tl = next((x for x in lists if (x["attributes"].get("name") or "") == payload["list_name"]), None)
    if not tl:
        tl = pc.post(s, "/task_lists", {"data": {"type": "task_lists", "attributes": {"name": payload["list_name"]},
                                                 "relationships": {"project": {"data": {"type": "projects", "id": payload["project_id"]}}}}})["data"]
    t = pc.post(s, "/tasks", {"data": {"type": "tasks", "attributes": {"title": title[:140], "description": body, "due_date": payload["due_date"]},
                                        "relationships": {"project": {"data": {"type": "projects", "id": payload["project_id"]}},
                                                          "task_list": {"data": {"type": "task_lists", "id": tl["id"]}},
                                                          **({"assignee": {"data": {"type": "people", "id": reviewer}}} if reviewer else {})}}})["data"]
    it.setdefault("hooks", {})["productive_review_task"] = t["id"]; it["reviewer_id"] = reviewer
    intake_mod.save_intake(key, it, root)
    return {"dry_run": False, "task_id": t["id"], **payload}


# ---------------------------------------------------------------- QuickBooks

def qbo_request(key: str, root: str = PROJECTS) -> dict:
    """The invoice (or $0 record) as the request the SOP's QuickBooks step sends: product 85 '01 Assessment', one line,
    the level and address in the description, no card fee unless asked. Returned for the operator or the QBO connector."""
    it = intake_mod.load_intake(key, root)
    cfg = _cfg()["qbo"]
    c = it.get("contact") or {}
    amount = max(0, int(it.get("price", 0)) - int(it.get("credit_applied") or 0))
    req = {"customer": {"name": c.get("company") or c.get("name"), "email": c.get("email")},
           "line": {"product_id": cfg["product_id"], "item": cfg["item"], "description": f"Entitlement Roadmap — {it.get('level_name')} — {it.get('key')}", "amount": amount, "taxable": False},
           "memo": ("Free Screen (launch offer), $0 record" if it.get("free") else "Payment due on order; work starts on payment per the Roadmap SOP") + (f"; credit applied ${it.get('credit_applied'):,}" if it.get("credit_applied") else ""),
           "send_to": c.get("email")}
    it.setdefault("hooks", {})["qbo_request"] = req
    intake_mod.save_intake(key, it, root)
    return req


# ---------------------------------------------------------------- delivery email

def delivery_email(key: str, root: str = PROJECTS, out_dir: str = "out") -> str:
    it = intake_mod.load_intake(key, root)
    cfg = _cfg()
    c = it.get("contact") or {}
    link = dashboard_link(key) or "<dashboard link from the Client links page>"
    level = it.get("level")
    nxt = {"screening": f"the Map at ${cfg['prices']['roadmap']:,} with your ${cfg['credits']['roadmap']:,} Screen credited: a planner's corrections, the highest-and-best-use ranking, the desktop constraints map with the candidate entitlement paths, the verification plan, a one-hour working session and a scoped and priced Step 1b, in one week",
           "roadmap": f"Scenarios at ${cfg['prices']['plus']:,} with your ${cfg['credits']['plus']:,} Map credited: a specialist desk read, a cultural records search where flagged, two or three development programs estimated on the map, a board package and a second session, in two weeks; or the Step 1b proposal in the report, the surveys that confirm the map in the field",
           "plus": "the Step 1b proposal in the report: the surveys and data collection that confirm the constraints map in the field, then Step 2 conceptual design with engineering front and center"}[level]
    text = f"""Subject: Your Entitlement Roadmap ({it.get('level_name')}) for {it.get('key')}

{c.get('name') or 'Hello'},

Your Entitlement Roadmap at the {it.get('level_name')} level is ready. It was reviewed and signed by {it.get('reviewer') or 'a Cox planner'} before it reached you.

Your dashboard: {link}
The page is the living version: it updates as the project moves. The PDF attached is today's snapshot.

What it says, in three lines, is on page one. The assumption register lists what each figure rests on, what verifies it and what that costs.

Next, if you want it: {nxt}.

Book the working session or a call: {cfg['dashboard_url'].replace('cox-dashboard.onrender.com', 'coxplanningsolutions.com')}/roadmap (or reply to this email).

Chris Cox
Principal Planner, Cox Planning Solutions
"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{key}-delivery.md")
    with open(path, "w") as f:
        f.write(text)
    return path
