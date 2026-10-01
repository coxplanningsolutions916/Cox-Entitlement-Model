import datetime

import pytest

from engine import fee, rules, schedule, program
from engine.model import Project, ModelError


def test_riego_passes_hard_rules():
    p = Project.load("riego-rd")
    v = rules.check(p, fee.build(p))
    assert not [x for x in v if x.hard], [str(x) for x in v]


def test_r1_blocks_membership_without_map():
    p = Project.load("riego-rd")
    f = p.facts["fact.nbhcp.boundary"]; f.map_citation = None
    assert any(x.rule == "R1" for x in rules.r1_membership_needs_map(p))


def test_r13_rejects_quarantined_language():
    p = Project.load("riego-rd")
    v = rules.r13_quarantine(p, "The project is covered under the per acre fee of the Conservancy.")
    assert v and all(x.hard for x in v)
    assert not rules.r13_quarantine(p, "The parcels are outside the Natomas Basin HCP plan area.")


def test_r6_rejected_benchmark_is_skipped_and_wrong_jurisdiction_fails():
    p = Project.load("riego-rd")
    p.benchmarks["bench.swha_land"].status = "candidate"
    v = rules.r6_benchmark_applicability(p)
    assert any("jurisdiction" in x.message for x in v) and any("acres" in x.message for x in v)


def test_r11_started_requires_authority():
    p = Project.load("riego-rd")
    p.deliverables[0].status = "started"
    assert rules.r11_discussed_is_not_authorized(p)
    p.deliverables[0].authority = {"document": "Task Order 1", "executed": "2026-10-15"}
    assert not rules.r11_discussed_is_not_authorized(p)


def test_unquantifiable_line_refuses_a_number(tmp_path):
    import shutil, os
    src = os.path.join(os.path.dirname(__file__), "..", "projects", "riego-rd")
    dst = tmp_path / "riego-rd"; shutil.copytree(src, dst)
    (dst / "unquantifiable.yaml").write_text("lines:\n  - id: unq.x\n    label: X\n    why_unquantifiable: y\n    low: 1\n    drivers: [{name: a, resolved_by: [b]}]\n")
    with pytest.raises(ModelError):
        Project.load("riego-rd", root=str(tmp_path))


def test_unknown_role_is_rejected(tmp_path):
    import shutil, os
    src = os.path.join(os.path.dirname(__file__), "..", "projects", "riego-rd")
    dst = tmp_path / "riego-rd"; shutil.copytree(src, dst)
    (dst / "deliverables.yaml").write_text("deliverables:\n  - {id: d, code: '9.9', name: n, phase: '01 Assessment', hours: {Sr. Biologist: 1}}\n")
    with pytest.raises(ModelError):
        Project.load("riego-rd", root=str(tmp_path))


def test_schedule_places_delineation_in_spring_window():
    p = Project.load("riego-rd")
    pl = schedule.place(p, datetime.date(2026, 10, 15))
    d = next(x for x in pl if x.code == "1.3")
    assert d.opens == datetime.date(2027, 2, 15) and d.closes == datetime.date(2027, 5, 15)
    fall = next(x for x in pl if x.code == "1.0")
    assert fall.opens == datetime.date(2026, 10, 15) and fall.closes == datetime.date(2026, 11, 30)
    assert any("1.9" in g["codes"] for g in schedule.mobilizations(p, pl))


def test_program_total_names_mitigation_as_exclusion():
    p = Project.load("riego-rd")
    prog = program.build(p)
    assert prog["total"]["low"] == 1496239 and prog["total"]["high"] == 2469182
    assert any("mitigation" in x["label"].lower() for x in prog["exclusions"])
    assert "fifth" in prog["total"]["sentence"] or "%" in prog["total"]["sentence"]
