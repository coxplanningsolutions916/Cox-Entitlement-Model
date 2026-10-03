"""Part 2: the Map-level drafts."""
import datetime
import os

from engine import fee, mapdraft, publish, report
from engine.model import Project
from engine.report import load_screen

NTP = datetime.date(2026, 10, 15)


def _m(key):
    p = Project.load(key)
    return p, mapdraft.build(p, load_screen(p), fee.build(p), NTP)


def test_constraint_manifest_tags_every_issue_and_exports(tmp_path):
    p, m = _m("lemon-hill")
    tags = {l["status"] for l in m["layers"]}
    assert tags <= {"mapped", "field-verified", "not yet pulled"} and m["legend"]["field"] == 0      # nothing is field-verified before Step 1b
    assert any(l["issue"] == "historic" and l["status"] == "not yet pulled" for l in m["layers"])    # the uncovered primary issue is in the manifest
    files = mapdraft.export_manifest(p, m["layers"], str(tmp_path))
    assert os.path.exists(files["csv"]) and os.path.exists(files["json"])
    assert open(files["csv"]).read().count("\n") == len(m["layers"]) + 1


def test_candidate_paths_never_choose_and_rule_out_with_a_reason():
    p, m = _m("lemon-hill")
    ids = {x["id"]: x for x in m["paths"]}
    assert ids["A"]["status"] == "open" and "Rezone" in ids["A"]["name"] and all(x["draft"] for x in m["paths"])
    assert ids["B"]["status"] == "ruled out" and "Rezone" in ids["B"]["why_ruled_out"]
    assert ids["C"]["status"] == "to test" and "SB 35" in ids["C"]["name"]
    assert ids["A"]["resource_permits"] == []                                                    # no mapped waters on the Lemon Hill record
    r, rm_ = _m("riego-rd")
    rids = {x["id"]: x for x in rm_["paths"]}
    assert rids["A"]["resource_permits"] and rids["D"]["name"].startswith("Specific plan") and "C" not in rids
    assert all("duration_months" in x and x["confirms"] for x in rm_["paths"])


def test_hbu_uses_the_planner_rows_when_present_else_a_draft():
    _, lm = _m("lemon-hill"); _, rm_ = _m("riego-rd")
    assert not lm["hbu"]["draft"] and [r["rank"] for r in lm["hbu"]["rows"]] == [1, 2, 3, 4]
    assert rm_["hbu"]["draft"] and rm_["hbu"]["rows"][0]["rank"] == "to rank"


def test_verification_plan_is_ordered_priced_and_prices_step_1b():
    p, m = _m("riego-rd")
    plan = m["plan"]
    months = [e["month"] for e in plan if e["month"] is not None]
    assert months == sorted(months) and plan[0]["fee"] and plan[0]["settles"]
    assert any(e["code"] == "1.3" and "Compensatory mitigation" in " ".join(e["moves"]) for e in plan)
    assert m["step1b"]["fee"] == 273000 and m["step1b"]["confidence"] == "firm"


def test_map_blocks_appear_only_at_map_and_scenarios_rungs():
    p = Project.load("lemon-hill")
    scr = report.build(p, "screening", today=datetime.date(2026, 10, 3), ntp=NTP)
    mp = report.build(p, "roadmap", today=datetime.date(2026, 10, 3), ntp=NTP)
    assert "candidate paths" not in scr["sections"][6]["title"] and "candidate paths" in mp["sections"][6]["title"]
    html = report.render_html(mp)
    assert "Candidate entitlement paths" in html and "Verification plan" in html and "layer manifest" in html and "Highest and best use" in html
    d = publish.export(p, "roadmap", today=datetime.date(2026, 10, 3), ntp=NTP)
    assert d["map"]["legend"]["pending"] >= 1 and len(d["map"]["paths"]) >= 3
    assert publish.export(p, "screening", today=datetime.date(2026, 10, 3))["map"] is None
