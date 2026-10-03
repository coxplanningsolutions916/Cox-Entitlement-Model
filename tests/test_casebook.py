import copy

import pytest

from engine import casebook
from engine.model import ModelError


def test_grant_line_case_loads_and_is_complete():
    c = casebook.load("grant-line-rd")
    assert c["development_type"] == "redevelopment" and len(c["challenges"]) == 9 and len(c["decisions"]) == 7
    res = {r["challenge"] for r in c["resolutions"]}
    assert res == {ch["id"] for ch in c["challenges"]}
    assert all(not p.get("name") for p in c["people"])                       # no names without consent
    assert all(q["cleared"] is False for q in c["quotables"])                 # nothing cleared for marketing yet
    kinds = {l["kind"] for l in c["lessons"]}
    assert {"rule", "playbook", "judgment", "benchmark", "process"} <= kinds
    assert any(l.get("rule") == "proposed R21" for l in c["lessons"])


def test_validation_refuses_unsourced_and_unconsented_records():
    c = casebook.load("grant-line-rd")
    bad = copy.deepcopy(c); bad["challenges"][0].pop("source")
    with pytest.raises(ModelError):
        casebook.validate(bad)
    bad = copy.deepcopy(c); bad["people"][0]["name"] = "Someone"
    with pytest.raises(ModelError):
        casebook.validate(bad)
    bad = copy.deepcopy(c); bad["lessons"][0] = {"kind": "rule", "lesson": "x"}
    with pytest.raises(ModelError):
        casebook.validate(bad)


def test_export_builds_benchmarks_and_playbook():
    e = casebook.export(casebook.load_all())
    assert e["counts"]["cases"] >= 1
    assert any(b["metric"].startswith("CUP major") and b["value"] == 8800 for b in e["benchmarks"])
    assert "redevelopment" in e["playbook"] and any(l["kind"] == "playbook" for l in e["playbook"]["redevelopment"])
