"""The dashboard JSON: client-safe, complete, serializable."""
import datetime
import json

from engine import publish
from engine.model import Project


def test_export_is_client_safe_and_complete():
    p = Project.load("riego-rd")
    d = publish.export(p, "roadmap", today=datetime.date(2026, 10, 1), ntp=datetime.date(2026, 10, 15))
    s = json.dumps(d, default=str)
    assert "hours_by_role" not in s and "bill_rate" not in s and "cost_rate" not in s
    assert [x["label"] for x in d["decision"]] == ["WHAT TO BUILD", "HOW IT GETS APPROVED", "WHAT IT TAKES"]
    assert d["budget"]["total"]["low"] == 1496239 and d["budget"]["exclusions"][0]["label"] == "Compensatory mitigation"
    assert any(a["federal_nexus"] for a in d["approvals"]) and d["windows"]
    assert {r["status"] for r in d["register"]} >= {"open", "pending"}
    assert d["change_log"][0]["date"] >= d["change_log"][-1]["date"]
    assert d["next_steps"][1].startswith("Step 2 is conceptual design")
    assert d["fees_needed"] == 6 and d["facts_needed"] == 12


def test_screening_export_has_no_line_items_or_windows():
    p = Project.load("riego-rd")
    d = publish.export(p, "screening", today=datetime.date(2026, 10, 1))
    assert all(b["lines"] == [] for b in d["budget"]["blocks"]) and d["windows"] == []
    assert d["price"] == 500 and "Map at $2,500" in d["next_steps"][0]
