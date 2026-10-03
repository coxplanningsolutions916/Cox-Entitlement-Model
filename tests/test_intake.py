"""Part 1: scaffold from the intake form, the free-screen pace, the hooks' payloads, the correction register, the metrics."""
import datetime
import json
import os

import pytest

from engine import hooks, intake, publish, report, review
from engine.model import Project

ORDER = {"address": "1234 Example Ave, Elk Grove", "apns": ["121-0010-001"], "jurisdiction": "City of Elk Grove", "intent": "Garden apartments, about 80 units",
         "use": "residential", "acres": 3.2, "name": "Jane Developer", "email": "jane@example.com", "company": "Example Homes LLC", "role": "developer",
         "phone": "916-555-0100", "source": "Google Ads", "utm": {"utm_source": "google", "utm_campaign": "roadmap"},
         "documents": [{"label": "Preliminary title report", "url": "https://drive.google.com/x"}],
         "scale": {"parcels": "1", "resources": "unknown", "discretionary": "no", "board": False}, "level": "screen", "free": True}
TODAY = datetime.date(2026, 11, 2)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, "PROJECTS", str(tmp_path)); monkeypatch.setattr(hooks, "PROJECTS", str(tmp_path)); monkeypatch.setattr(review, "PROJECTS", str(tmp_path))
    return str(tmp_path)


def test_scaffold_is_a_loadable_project_the_engine_can_report_on(root):
    r = intake.scaffold(ORDER, TODAY, root)
    assert r["key"] == "1234-example-ave-elk-grove" and r["development_type"] == "infill" and r["type_inferred"] and r["pilot"]
    assert r["free"] and r["price"] == 0 and r["delivery_due"] == "2026-11-04"      # two business days
    p = Project.load(r["key"], root=root)
    assert p.development_type.id == "infill" and len(p.assumptions) == 6 and "fact.intake.parcel" in p.facts and "fact.intake.doc1" in p.facts
    rep = report.build(p, "screening", today=TODAY)
    assert [s["n"] for s in rep["sections"]] == list(range(1, 11))
    rows = rep["sections"][4]["blocks"][0]["rows"]
    assert len(rows) == 11 and all(r_[1]["needed"] for r_ in rows)                 # every infill issue carried as a fact needed
    assert rep["meta"]["stamp"].startswith("MODEL OUTPUT")
    assert rep["sections"][9]["blocks"][0]["items"][1]["cell"]["text"].startswith("Scale test: Map")


def test_outside_pilot_and_explicit_type(root):
    r = intake.scaffold({**ORDER, "jurisdiction": "City of Davis", "development_type": "redevelopment", "free": False, "level": "map"}, TODAY, root)
    assert not r["pilot"] and r["development_type"] == "redevelopment" and not r["type_inferred"] and r["price"] == 2500 and r["delivery_due"] == "2026-11-09"
    assert "outside-pilot" in hooks.automator_order(r["key"], root=root)["contact"]["tags"]


def test_free_screens_are_paced_and_capped(root, monkeypatch):
    cfg = intake.pilot()
    monkeypatch.setattr(intake, "pilot", lambda: {**cfg, "free_screens": {"cap": 3, "pace_per_month": 2, "starts": "2026-10-30"}})
    a = intake.scaffold({**ORDER, "address": "1 A St"}, TODAY, root); b = intake.scaffold({**ORDER, "address": "2 B St"}, TODAY, root)
    c = intake.scaffold({**ORDER, "address": "3 C St"}, TODAY, root)
    assert a["free"] and b["free"] and c["free"] and c["free_slot"]["paced"] and c["delivery_due"].startswith("2026-12")
    d = intake.scaffold({**ORDER, "address": "4 D St"}, TODAY, root)
    assert not d["free"] and d["price"] == 500                                          # cap reached: the order is a paid Screen
    m = intake.metrics(TODAY, root)
    assert m["free"]["used_total"] == 3 and m["free"]["available"] is False


def test_hooks_dry_run_payloads_and_qbo_request(root):
    r = intake.scaffold(ORDER, TODAY, root)
    o = hooks.automator_order(r["key"], root=root)
    assert o["dry_run"] and o["opportunity"]["stage"] == "Roadmap Requested" and o["opportunity"]["monetaryValue"] == 0
    assert set(o["contact"]["tags"]) == {"roadmap-screen", "free-screen"} and "utm_campaign=roadmap" in o["note"]
    t = hooks.productive_review_task(r["key"], root=root)
    assert t["dry_run"] and t["assignee_id"] in ("1218809", "1339861") and t["due_date"] == "2026-11-04" and "engine review" in t["description"]
    q = hooks.qbo_request(r["key"], root=root)
    assert q["line"]["product_id"] == 85 and q["line"]["amount"] == 0 and "Free Screen" in q["memo"]
    assert intake.load_intake(r["key"], root)["hooks"]["qbo_request"]["line"]["amount"] == 0
    d = hooks.automator_delivered(r["key"], root=root)
    assert d["dry_run"] and d["stage"] == "Roadmap Delivered"
    path = hooks.delivery_email(r["key"], root=root, out_dir=os.path.join(root, "out"))
    assert "the Map at $2,500 with your $500 Screen credited" in open(path).read()


def test_corrections_register_and_metrics(root):
    r = intake.scaffold(ORDER, TODAY, root)
    p = Project.load(r["key"], root=root)
    review.record_review(p, "Chris Cox", {n: "ok" for n in range(1, 11)}, "2026-11-03")
    review.record_corrections(p, [review.parse_fix("5|constraints.flood|not yet pulled|Zone X per NFHL panel 06067C0245H|parcel check"),
                                  review.parse_fix("3|levers.AB 2097||within half a mile of the Elk Grove transit center|measured")], "Chris Cox", "2026-11-03")
    m = review.correction_metrics(root, datetime.date(2026, 11, 5))
    assert m["screens_reviewed"] == 1 and m["corrections"] == 2 and m["per_screen"] == 2.0 and m["by_section"] == {"5": 1, "3": 1}


def test_publish_all_writes_metrics(root, tmp_path, monkeypatch):
    import engine.publish as pub
    monkeypatch.setattr(pub, "DEFAULT_DASH", str(tmp_path / "dash"))
    path = pub.write_metrics(today=TODAY)
    m = json.load(open(path))
    assert m["free"]["cap"] == 100 and "corrections" in m and m["generated"] == "2026-11-02"
