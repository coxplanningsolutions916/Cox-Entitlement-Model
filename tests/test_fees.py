"""The fee engine: schedules scoped by jurisdiction, district or agency; the confidence rule; reconciliation with typed lines."""
import datetime

from engine import fees, program
from engine.model import CostLine, Project

TODAY = datetime.date(2026, 10, 1)


def test_registry_loads_and_every_line_has_amount_or_verify():
    reg = fees.load_registry()
    ids = {s.id for s in reg}
    assert {"fee.rwqcb_cv.section_401", "fee.sutter.processing", "fee.sutter.impact"} <= ids
    for s in reg:
        for l in s.lines:
            assert l.get("amount") is not None or l.get("low") is not None or l.get("verify")


def test_riego_schedules_apply_by_jurisdiction_and_approval_set():
    p = Project.load("riego-rd")
    fr = fees.build(p, today=TODAY)
    why = {a.schedule.id: a.why for a in fr.applicable}
    assert why["fee.sutter.processing"].startswith("jurisdiction")
    assert "401" in why["fee.rwqcb_cv.section_401"]
    assert "fee.cdfw.section_2081" in why and "fee.usace.section_404" in why


def test_riego_generated_lines_reproduce_the_typed_program_lines():
    p = Project.load("riego-rd")
    fr = fees.build(p, today=TODAY)
    assert fr.notes == [], fr.notes                       # every reconciled line matches the 21 Sept program
    by = {l.id: l for l in fr.lines}
    assert by["fee.sutter.processing.gpa"].low == 9911 and by["fee.sutter.processing.gpa"].confidence == "published"
    assert by["fee.cdfw.section_1602.notification"].high == 24720
    assert by["fee.rwqcb_cv.section_401.annual"].low == 17700          # 3,540 × 5 years
    assert fr.suppressed == {"fee.rwqcb_cv.section_401.project_fee": "line.rwqcb_project_fee"}
    assert len(fr.replaced) == 10


def test_missing_quantity_and_missing_amount_price_as_pending():
    p = Project.load("riego-rd")
    fr = fees.build(p, today=TODAY)
    by = {l.id: l for l in fr.lines}
    assert by["fee.sutter.impact.transportation"].confidence == "pending"       # amount not on file
    assert "verify" in by["fee.sutter.impact.transportation"].basis
    assert "fee.rwqcb_cv.section_401.project_fee" not in by                     # suppressed, typed bracket stands


def test_published_rate_times_assumed_quantity_is_benchmarked_and_stale_schedule_downgrades():
    p = Project.load("riego-rd")
    reg = [fees.Schedule(id="fee.test.park", name="Test park fee", owner="Test", kind="park", scope={"jurisdiction": "Sutter County"},
                         source={"document": "test resolution", "revised": "2026-01-01"}, effective="2026-01-01", review_by="2027-01-01",
                         lines=[{"id": "park", "label": "Park fee", "basis": "per_unit", "amount": 1000, "applies_to": ["residential"]},
                                {"id": "drain", "label": "Drainage", "basis": "per_acre", "amount": 10}]),
           fees.Schedule(id="fee.test.old", name="Old schedule", owner="Test", kind="facility", scope={"jurisdiction": "Sutter County"},
                         source={"document": "old", "revised": "2020-01-01"}, effective="2020-01-01", review_by="2021-01-01",
                         lines=[{"id": "f", "label": "Old flat fee", "basis": "flat", "amount": 500}])]
    fr = fees.build(p, today=TODAY, registry=reg)
    by = {l.id: l for l in fr.lines}
    assert (by["fee.test.park.park"].low, by["fee.test.park.park"].high) == (58000, 62000)
    assert by["fee.test.park.park"].confidence == "benchmarked"       # units are the client's concept, not a fact
    assert by["fee.test.park.drain"].confidence == "published" and by["fee.test.park.drain"].low == 1601.6
    assert by["fee.test.old.f"].confidence == "benchmarked" and "review date" in by["fee.test.old.f"].basis


def test_district_membership_by_declared_map_or_point_in_polygon():
    p = Project.load("riego-rd")
    sq = [[-121.6, 38.9], [-121.5, 38.9], [-121.5, 39.0], [-121.6, 39.0]]
    reg = [fees.Schedule(id="fee.test.zone", name="Zone Z", owner="Test", kind="drainage",
                         scope={"district": {"layer": "test_zones", "feature": "Z", "polygon": sq}},
                         source={"document": "test"}, effective="2026-01-01", review_by="2027-01-01",
                         lines=[{"id": "d", "label": "Zone fee", "basis": "per_acre", "amount": 100}])]
    inside = {"point": [-121.55, 38.95], "quantities": {"acres": {"value": 10, "confidence": "published"}}}
    outside = {"point": [-121.7, 38.95], "quantities": {"acres": {"value": 10, "confidence": "published"}}}
    assert [a.schedule.id for a in fees.applicable(p, reg, inside, [])] == ["fee.test.zone"]
    assert fees.applicable(p, reg, outside, []) == []
    declared = {"memberships": [{"schedule": "fee.test.zone", "map": {"layer": "test_zones", "date": "2026-01-01"}}], "quantities": {}}
    a = fees.applicable(p, reg, declared, [])
    assert a and a[0].map_citation["layer"] == "test_zones"
    try:
        fees.applicable(p, reg, {"memberships": [{"schedule": "fee.test.zone"}]}, [])
        assert False, "membership without a map must be refused (R1)"
    except ValueError:
        pass


def test_program_budget_merges_generated_fee_lines_without_double_counting():
    p = Project.load("riego-rd")
    prog = program.build(p)
    ids = [l.id for l in prog["sections"]["agency_fees"]["lines"]]
    assert "line.fee_gpa" not in ids and "fee.sutter.processing.gpa" in ids
    assert "line.rwqcb_project_fee" in ids                                   # the kept bracket
    assert ids.count("fee.sutter.processing.gpa") == 1
    assert prog["total"]["low"] == 1496239 and prog["total"]["high"] == 2469182   # the reproduced lines move nothing
    assert len(prog["fees"]["pending"]) == 6
