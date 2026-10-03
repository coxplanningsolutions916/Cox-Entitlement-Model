"""The scale test and the planner's review."""
import datetime
import os
import shutil

from engine import review, report, rules
from engine.model import Project


def test_scale_test_fires_on_riego_and_lemon_hill_for_the_right_reasons():
    r = review.scale_test(Project.load("riego-rd"))
    assert r["recommended"] == "plus"
    assert any("mapped resource" in t for t in r["triggers"]) and any("discretionary" in t for t in r["triggers"])
    l = review.scale_test(Project.load("lemon-hill"))
    assert l["recommended"] == "plus"
    assert [t for t in l["triggers"] if t.startswith("discretionary")] and not [t for t in l["triggers"] if "jurisdiction" in t]
    res = [t for t in l["triggers"] if "mapped resource" in t]
    assert res == ["mapped resource: Flood: Morrison Creek corridor"]       # adjacent Zone AE counts; "no aquatic features" and "outside the HCP" do not
    assert not any("Habitat conservation plan" in t for t in r["triggers"])  # Riego is outside the NBHCP: not a trigger


def test_review_writes_the_block_and_clears_the_stamp(tmp_path):
    src = os.path.join(os.path.dirname(__file__), "..", "projects", "lemon-hill")
    dst = tmp_path / "lemon-hill"; shutil.copytree(src, dst)
    p = Project.load("lemon-hill", root=str(tmp_path))
    review.PROJECTS_BACKUP = review.PROJECTS
    review.PROJECTS = str(tmp_path)
    try:
        items = {n: "ok" for n in range(1, 11)}; items[9] = "trade area should be 10 minutes, not 15, for this product"
        block = review.record_review(p, "Chris Cox", items, "2026-10-03", "roadmap", "Two adjacent parcels in one ownership and a routine rezone; the Roadmap covers it.", "Clean infill site; density is the decision.")
        assert block["rung_override"] == "roadmap"
        text = (dst / "screen.yaml").read_text()
        assert text.count("\nreview:") == 1 and "Chris Cox" in text and "review: {}" not in text
        sc = review.load_screen(p)
        st = review.review_state(sc)
        assert st["complete"] and st["notes"] == {9: items[9]}
        s = review.scale_test(p, sc)
        assert s["recommended"] == "plus" and s["effective"] == "roadmap"
        # the override needs a reason (R20)
        sc["review"]["override_reason"] = ""
        (dst / "screen.yaml").write_text(text.replace(block["override_reason"], ""))
        p2 = Project.load("lemon-hill", root=str(tmp_path))
        assert any(x.rule == "R20" and x.hard for x in rules.r20_rung_matches_scale_test(p2))
    finally:
        review.PROJECTS = review.PROJECTS_BACKUP


def test_report_carries_the_rung_line_and_the_incomplete_stamp():
    p = Project.load("lemon-hill")
    rep = report.build(p, "roadmap", today=datetime.date(2026, 10, 3), ntp=datetime.date(2026, 10, 15))
    rung = rep["sections"][9]["blocks"][0]["items"][1]["cell"]["text"]
    assert rung.startswith("Scale test: Roadmap Plus") and "Rezone" in rung
    assert rep["meta"]["stamp"].startswith("MODEL OUTPUT")
