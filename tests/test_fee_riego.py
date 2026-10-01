"""Regression fixture from the build brief §5: Riego Task Order 1 must reproduce exactly."""
from engine import fee
from engine.model import Project


def test_riego_task_order_1_reproduces_exactly():
    p = Project.load("riego-rd")
    fb = fee.build(p)
    assert fb.labor == 246580
    assert fb.passthrough_fee == 1725            # 1,500 at cost plus 15%
    assert fb.coordination == 24658              # 10% of labor, pass-throughs excluded
    assert fb.total == 273000                    # rounded once, at the total
    assert fb.hours == 1463


def test_each_deliverable_fee_is_hours_times_rate():
    p = Project.load("riego-rd")
    fb = fee.build(p)
    by_code = {r.code: r for r in fb.deliverables}
    assert by_code["1.3"].fee == 54000
    assert by_code["1.10"].fee == 18880 and by_code["1.10"].fee_with_passthrough == 20605
    assert by_code["2.2"].fee == 22200


def test_payment_schedule_sums_to_total():
    p = Project.load("riego-rd")
    fb = fee.build(p)
    ms = fee.payment_schedule(fb.total, p.meta["task_order_1"]["payment_milestones"])
    assert sum(m["amount"] for m in ms) == fb.total
    assert [m["amount"] for m in ms] == [54600, 54600, 68300, 54600, 40900]   # the workbook's payment schedule


def test_hours_by_role_match_backup():
    p = Project.load("riego-rd")
    fb = fee.build(p)
    assert fb.hours_by_role == {"principal_biologist_planner_engineer": 113, "senior_biologist": 470, "senior_planner": 176,
                                "planner": 267, "gis_analyst_cad_designer": 325, "senior_archaeologist": 64, "cultural_field_technician": 48}
