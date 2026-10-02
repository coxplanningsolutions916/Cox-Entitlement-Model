"""The Step 1a / Roadmap report: ten sections, every figure sourced or flagged, the register and the sign-off present,
client output free of hours and rates (build brief §5)."""
import datetime
import re

from engine import report
from engine.model import Project


def _rep(rung="screening", internal=False):
    p = Project.load("riego-rd")
    return report.build(p, rung, today=datetime.date(2026, 10, 1), ntp=datetime.date(2026, 10, 15), internal=internal)


def _cells(rep):
    for s in rep["sections"]:
        for b in s["blocks"]:
            for row in b.get("rows", []):
                if b["type"] == "table":
                    for c in row:
                        yield s["n"], c
            for it in b.get("items", []):
                if "cell" in it:
                    yield s["n"], it["cell"]


def test_ten_sections_in_order():
    rep = _rep()
    assert [s["n"] for s in rep["sections"]] == list(range(1, 11))
    assert rep["sections"][0]["title"].startswith("The decision")
    assert rep["sections"][8]["title"] == "The assumption register"


def test_every_figure_has_a_source_or_is_flagged():
    rep = _rep()
    money = re.compile(r"\$\d")
    for n, c in _cells(rep):
        if money.search(c["text"]):
            assert c["ref"], f"section {n}: unsourced figure {c['text'][:60]}"
        if c["needed"]:
            assert c["text"] == report.FACT_NEEDED and c["verify"], f"section {n}: a fact needed must say what verifies it"


def test_register_prices_verification_from_the_fee_build():
    rep = _rep()
    reg = rep["sections"][8]["blocks"][0]["rows"]
    priced = [r for r in reg if r["cost"]]
    assert priced, "no assumption carries a fee to verify"
    ceqa = next(r for r in reg if "EIR" in r["assumption"])
    assert "4.1" in ceqa["verified_by"] and ceqa["cost"].startswith("$")
    assert any(r["assumption"].startswith("Fact needed") for r in reg)
    assert rep["facts_needed"] == sum(1 for r in reg if r["assumption"].startswith("Fact needed"))


def test_decision_line_carries_program_total_and_exclusion():
    rep = _rep()
    wit = rep["sections"][0]["blocks"][0]["items"][2]["cell"]["text"]
    assert "$1,496,239 to $2,469,182" in wit
    assert "compensatory mitigation" in wit.lower()
    assert "assuming the ceqa document is an eir" in wit.lower()


def test_client_html_has_no_hours_or_rates_and_flags_unreviewed():
    rep = _rep("roadmap")
    html = report.render_html(rep)
    assert "NOT YET STAFF-REVIEWED" in html
    assert not re.search(r"\b\d{2,4}\s*(hours|hrs|h)\b", html.replace("hours of", "x"))   # staff-hour wording is allowed, hour counts are not
    assert "$250" not in html and "/hr" not in html
    assert "Program budget" in html and "Season windows" in html
    assert "Step 2 is conceptual design" in html


def test_screening_omits_line_items_and_offers_the_roadmap():
    rep = _rep("screening")
    html = report.render_html(rep)
    assert "Program budget" not in html
    assert "Entitlement Roadmap at $2,500" in html
    assert "Staff review and sign-off" in html and html.count('class="box') == 10


def test_internal_block_only_when_asked():
    assert _rep()["internal"] is None
    i = _rep(internal=True)["internal"]
    assert i["violations"] == [] and i["hours"] == 1463 and i["margin_pct"] is not None
