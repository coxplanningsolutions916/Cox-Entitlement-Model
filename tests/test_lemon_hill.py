"""Lemon Hill: the genericity test. A second site, a different type, a task order built under the old method."""
import datetime

from engine import fee, program, publish, report, rules
from engine.model import Project


def test_fee_build_prices_the_april_hours_under_om_14_3():
    p = Project.load("lemon-hill")
    fb = fee.build(p)
    assert fb.labor == 19737.5 and fb.passthrough_fee == 2185 and fb.coordination == 1973.75
    assert fb.total == 24000 and fb.hours == 121.5
    assert p.meta["task_order_1"]["proposal_of_record"]["fee"] == 23200      # the delta is documented, not hidden
    ms = fee.payment_schedule(fb.total, p.meta["task_order_1"]["payment_milestones"])
    assert [m["amount"] for m in ms] == [9600, 9600, 4800]


def test_rules_surface_the_real_gaps():
    p = Project.load("lemon-hill")
    v = rules.check(p, fee.build(p))
    hard = [x for x in v if x.hard]
    assert [x.rule for x in hard] == ["R1"] and "sshcp" in hard[0].record     # the Roadmap's HCP claim needs a map citation
    assert any(x.rule == "R19" for x in v)


def test_program_total_matches_the_roadmap_figure():
    p = Project.load("lemon-hill")
    t = program.build(p)["total"]
    assert t["low"] == 160000 and t["high"] == 160000          # 24,000 firm + the Roadmap's 136,000 balance; fees pending
    assert program.build(p)["exclusions"][0]["label"].startswith("Resource evaluation")


def test_report_and_publish_run_for_an_infill_site():
    p = Project.load("lemon-hill")
    rep = report.build(p, "roadmap", today=datetime.date(2026, 10, 2), ntp=datetime.date(2026, 10, 15))
    assert [s["n"] for s in rep["sections"]] == list(range(1, 11))
    assert rep["meta"]["development_type"] == "Infill"
    assert "infill site" in rep["sections"][0]["blocks"][1]["text"]
    rows = rep["sections"][4]["blocks"][0]["rows"]
    assert rows[0][0]["text"].startswith("Neighbors")                      # type order: compatibility first
    assert any(r[0]["text"] == "Historic and cultural resources" and r[1]["needed"] for r in rows)
    html = report.render_html(rep)
    assert "Infill" in html and "Season windows" not in html               # no window-constrained deliverables on an infill site
    d = publish.export(p, "roadmap", today=datetime.date(2026, 10, 2), ntp=datetime.date(2026, 10, 15))
    assert d["development_type"]["id"] == "infill" and d["type_coverage"]["missing"] == ["Historic and cultural resources"]
    assert d["chart"]["months_to_entitlement"] == 24 and d["chart"]["mitigation"][0]["gates"]
