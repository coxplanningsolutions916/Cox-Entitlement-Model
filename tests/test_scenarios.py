"""Part 3: the Scenarios calculator, the records-search flag and the board package."""
import datetime
import os

from engine import fee, mapdraft, program, publish, report, scenarios
from engine.model import Project
from engine.report import load_screen

NTP = datetime.date(2026, 10, 15)


def _s(key):
    p = Project.load(key)
    return p, scenarios.build(p, load_screen(p), fee.build(p), program.build(p), NTP)


def test_program_parsing():
    assert scenarios.parse_program("Residential, 58 to 62 lots (client concept)") == (58, 62, "lots")
    assert scenarios.parse_program("roughly 175 to 210 units") == (175, 210, "units")
    assert scenarios.parse_program("80 units") == (80, 80, "units") and scenarios.parse_program("a warehouse") is None


def test_lemon_hill_scenarios_from_the_market_read():
    p, s = _s("lemon-hill")
    ids = {x["id"]: x for x in s["programs"]}
    assert ids["S1"]["yield"] == [175, 210] and ids["S1"]["path"] == "A" and ids["S1"]["cost"]["low"] == 160000
    assert ids["S2"]["product"] == "tuck_under_multifamily" and ids["S2"]["yield"] == [120, 180]          # 6.0 ac × 20 to 30
    assert ids["S3"]["product"] == "townhomes_attached" and any("map" in a.lower() for a in ids["S3"]["approvals"])   # for-sale needs a map
    assert all(x["draft"] for x in s["programs"]) and s["records_search"]["state"].startswith("undecided")


def test_riego_scenarios_including_by_right_from_the_designation_fact():
    p, s = _s("riego-rd")
    ids = {x["id"]: x for x in s["programs"]}
    assert ids["S1"]["yield"] == [58, 62] and ids["S1"]["product"] == "rural_residential"
    assert ids["S2"]["product"] == "single_family_subdivision" and 400 <= ids["S2"]["yield"][0] <= 500 and 650 <= ids["S2"]["yield"][1] <= 760
    assert ids["S3"]["product"] == "by_right" and ids["S3"]["yield"] == [2, 2] and ids["S3"]["path"] == "B"
    assert ids["S1"]["resource_permits"] and any("not yet measured" in a for a in ids["S1"]["assumptions"])
    assert s["records_search"]["state"] == "recommended"                                                   # greenfield with mapped waters


def test_estimate_arithmetic_is_transparent():
    canon = scenarios.shares_canon()
    e = scenarios.estimate(10.0, "single_family_subdivision", [{"name": "wetland", "acres": 1.0}], canon)
    steps = {s["step"]: s for s in e["steps"]}
    assert steps["developable area"]["low"] == 9.0
    assert abs(steps["net developable"]["low"] - 9.0 * (1 - 0.55)) < 1e-6 and abs(steps["net developable"]["high"] - 9.0 * (1 - 0.35)) < 1e-6
    assert e["yield"] == [round(9.0 * 0.45 * 6.0), round(9.0 * 0.65 * 7.0)] and e["exclusions_measured"]


def test_plus_report_carries_scenarios_and_board_package(tmp_path):
    p = Project.load("riego-rd")
    rep = report.build(p, "plus", today=datetime.date(2026, 10, 3), ntp=NTP)
    assert "scenarios" in rep["sections"][3]["title"] and any(b.get("caption", "").startswith("Scenarios estimated") for b in rep["sections"][3]["blocks"])
    assert any(it["label"] == "RECORDS SEARCH" for b in rep["sections"][4]["blocks"] if b["type"] == "lines" for it in b["items"])
    res = report.write(p, "plus", str(tmp_path), pdf=False)
    assert os.path.exists(res["board"]["summary"]) and os.path.exists(res["board"]["deck"])
    html = open(res["board"]["summary"]).read()
    assert "Board summary" in html and "S1." in html and "hours" not in html.split("Board summary")[1][:4000].lower().replace("business days", "")
    d = publish.export(p, "plus", today=datetime.date(2026, 10, 3), ntp=NTP)
    assert d["scenarios"]["programs"][2]["product"] == "by_right"
    assert publish.export(p, "roadmap", today=datetime.date(2026, 10, 3), ntp=NTP)["scenarios"] is None
