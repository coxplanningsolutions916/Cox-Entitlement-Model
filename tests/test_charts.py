import datetime

from engine import charts, program, publish
from engine.model import Project

NTP = datetime.date(2026, 10, 15)


def test_months_parse_and_spans():
    assert charts.months_of("Months 15 to 30.") == (15, 30)
    assert charts.months_of("At application.") is None
    p = Project.load("riego-rd")
    spans = charts.line_spans(program.build(p))
    to1 = next(s for s in spans if s["id"] == "line.to1")
    assert (to1["start"], to1["end"]) == (1, 12) and to1["confidence"] == "firm"


def test_burnup_is_cumulative_and_ends_at_the_scheduled_total():
    p = Project.load("riego-rd")
    spans = charts.line_spans(program.build(p))
    bu = charts.burnup(spans)
    assert bu["horizon"] == 36
    assert all(bu["low"][i] <= bu["low"][i + 1] for i in range(36))
    dated_low = sum(s["low"] for s in spans if s["start"] is not None and s["confidence"] != "pending")
    assert abs(bu["low"][36] - dated_low) <= 2
    assert bu["firm"][12] == 273000 and bu["firm"][36] == 273000
    assert bu["unscheduled_count"] > 0            # agency fees 'at application' are reported, not guessed onto the curve


def test_milestones_land_in_months_with_their_basis():
    p = Project.load("riego-rd")
    ms = charts.milestones(p, NTP, 273000)
    assert [m["amount"] for m in ms] == [54600, 54600, 68250, 54600, 40950]
    assert ms[0]["month"] == 0 and ms[0]["confidence"] == "firm"
    delin = next(m for m in ms if "Delineation" in m["label"])
    assert delin["basis"] == "triggered by 1.3" and delin["confidence"] == "published" and 5 <= delin["month"] <= 8
    assert all(m["month"] <= 12 for m in ms)


def test_mitigation_gates_in_month_order_with_states():
    p = Project.load("riego-rd")
    g = charts.mitigation_gates(p, NTP)[0]
    assert g["state"] == "no figure carried" and len(g["drivers"]) == 4
    months = [x["month"] for x in g["gates"]]
    assert months == sorted(months) and g["gates"][-1]["state_after"] == "firm"
    assert any(r["status"] == "rejected" for r in g["reference_costs"])


def test_publish_carries_chart_data():
    p = Project.load("riego-rd")
    d = publish.export(p, "roadmap", today=datetime.date(2026, 10, 1), ntp=NTP)
    c = d["chart"]
    assert c["months_to_entitlement"] == 36 and len(c["period_bars"]) == 6 and c["mitigation"]
    assert c["register_counts"]["open"] + c["register_counts"]["pending"] == len(d["register"])
    assert d["next_fee"]["amount"] == 273000
