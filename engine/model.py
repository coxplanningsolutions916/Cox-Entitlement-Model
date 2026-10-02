"""Domain types and YAML loading. Facts, assumptions, deliverables, cost lines, unquantifiable
lines, benchmarks and conflicts are different types and never blur (build brief §2, §4).

Every loader validates what the brief says the engine must enforce: a fact needs a source,
an established date and a confidence class; a role key must be one of the canonical strings;
an unquantifiable line must carry no number; a benchmark carries its applicability conditions.
"""
import datetime
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CANON = os.path.join(ROOT, "canon")
PROJECTS = os.path.join(ROOT, "projects")

CONFIDENCE = ["firm", "quoted", "published", "benchmarked", "derived", "placeholder", "pending"]
STRONG = {"firm", "quoted", "published"}
PAYERS = {"cox", "client_direct", "passthrough"}
SCOPE_STATUS = ["proposed", "discussed", "authorized", "started", "delivered", "superseded"]


class ModelError(ValueError):
    """Raised when a record violates a structural rule. The message names the record and the rule."""


def _yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


# ---------------------------------------------------------------- canon

@dataclass
class Role:
    key: str
    name: str
    bill_rate: float
    cost_rate: Optional[float] = None
    note: str = ""


class DevelopmentType:
    """A land-context type from canon/development_types.yaml (greenfield, infill, ...)."""
    def __init__(self, d: dict):
        self.id = d["id"]; self.name = d["name"]; self.means = d.get("means", ""); self.drives = d.get("drives", "")
        self.signals = d.get("signals", []); self.ceqa_expectation = d.get("ceqa_expectation", "")
        self.schedule_months = d.get("schedule_months", []); self.primary_issues = d.get("primary_issues", [])
        self.default_levers = d.get("default_levers", []); self.typical_approvals = d.get("typical_approvals", [])
        self.fee_families = d.get("fee_families", []); self.register_seed = d.get("register_seed", [])
        self.report_emphasis = d.get("report_emphasis", "")


@dataclass
class Canon:
    roles: Dict[str, Role]
    fee_rules: dict
    windows: Dict[str, dict]
    confidence: dict

    types: Dict[str, "DevelopmentType"] = field(default_factory=dict)
    uses: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, root=CANON):
        r = _yaml(os.path.join(root, "roles.yaml"))
        roles = {x["key"]: Role(x["key"], x["name"], float(x["bill_rate"]), x.get("cost_rate"), x.get("note", ""))
                 for x in r.get("roles", [])}
        w = _yaml(os.path.join(root, "windows.yaml"))
        windows = {x["id"]: x for x in w.get("windows", [])}
        tpath = os.path.join(root, "development_types.yaml")
        t = _yaml(tpath) if os.path.exists(tpath) else {}
        types = {x["id"]: DevelopmentType(x) for x in t.get("types", [])}
        return cls(roles=roles, fee_rules=r.get("fee_rules", {}), windows=windows,
                   confidence=_yaml(os.path.join(root, "confidence.yaml")), types=types, uses=t.get("uses", []))


# ---------------------------------------------------------------- records

@dataclass
class Fact:
    id: str
    statement: str
    source: dict
    established: str
    confidence: str
    value: Optional[dict] = None
    established_by: str = ""
    ttl_days: Optional[int] = None
    supersedes: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    quarantined_terms: List[str] = field(default_factory=list)
    kind: str = ""          # e.g. "membership" (rule R1)
    map_citation: Optional[dict] = None

    @property
    def superseded(self):
        return bool(self.superseded_by)

    def stale(self, today=None):
        if not self.ttl_days:
            return False
        today = today or datetime.date.today()
        return (today - datetime.date.fromisoformat(str(self.established)[:10])).days > self.ttl_days


@dataclass
class Assumption:
    id: str
    statement: str
    owner: str
    reason: str
    alternatives: List[str] = field(default_factory=list)
    current: Optional[str] = None
    resolved_by: Optional[str] = None
    cost_impact: List[str] = field(default_factory=list)
    schedule_impact: List[str] = field(default_factory=list)


@dataclass
class Passthrough:
    label: str
    cost: float                # Cox's cost; the fee carries cost plus the canon markup


@dataclass
class Deliverable:
    id: str
    code: str
    name: str
    phase: str
    hours: Dict[str, float]
    sequence_step: Optional[int] = None
    window: Optional[str] = None
    field_work: bool = False
    gates: List[str] = field(default_factory=list)
    resolves: List[str] = field(default_factory=list)
    passthroughs: List[Passthrough] = field(default_factory=list)
    status: str = "proposed"
    authority: Optional[dict] = None      # the executed authority record, when status is started+
    what_it_produces: str = ""

    @property
    def total_hours(self):
        return sum(self.hours.values())


@dataclass
class CostLine:
    id: str
    section: str
    label: str
    low: float
    high: float
    confidence: str
    basis: str
    payer: str = "cox"
    driven_by: List[str] = field(default_factory=list)
    lands: str = ""


@dataclass
class UnquantifiableLine:
    id: str
    label: str
    why_unquantifiable: str
    drivers: List[dict] = field(default_factory=list)
    reference_costs: List[str] = field(default_factory=list)
    withdrawn_estimates: List[dict] = field(default_factory=list)


@dataclass
class Benchmark:
    id: str
    label: str
    value: float
    unit: str
    source: str
    applicability: dict = field(default_factory=dict)
    status: str = "candidate"
    rejected_on: Optional[str] = None
    rejected_because: str = ""


@dataclass
class Conflict:
    number: int
    title: str
    status: str
    resolution: str = ""
    closed_on: Optional[str] = None
    closed_by: Optional[str] = None
    sources_in_conflict: List[dict] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    reversal_policy: str = "escalate"


@dataclass
class Project:
    key: str
    meta: dict
    facts: Dict[str, Fact]
    assumptions: Dict[str, Assumption]
    deliverables: List[Deliverable]
    cost_lines: List[CostLine]
    unquantifiable: List[UnquantifiableLine]
    benchmarks: Dict[str, Benchmark]
    conflicts: List[Conflict]
    canon: Canon

    # ------------------------------------------------------------ loading
    @classmethod
    def load(cls, key, root=PROJECTS, canon=None):
        canon = canon or Canon.load()
        d = os.path.join(root, key)
        if not os.path.isdir(d):
            raise ModelError(f"project '{key}' not found under {root}")
        meta = _yaml(os.path.join(d, "project.yaml"))
        dt = meta.get("development_type")
        if not dt:
            raise ModelError(f"project '{key}': project.yaml needs development_type (one of {sorted(canon.types)}); the type sets what the screen must cover")
        if dt not in canon.types:
            raise ModelError(f"project '{key}': unknown development_type '{dt}' (one of {sorted(canon.types)})")
        for u in meta.get("uses", []) or []:
            if canon.uses and u not in canon.uses:
                raise ModelError(f"project '{key}': unknown use '{u}' (one of {canon.uses})")
        facts = {}
        for f in _yaml(os.path.join(d, "facts.yaml")).get("facts", []):
            for req in ("id", "statement", "source", "established", "confidence"):
                if not f.get(req):
                    raise ModelError(f"fact {f.get('id', '?')}: missing '{req}' — a fact without a source is an assumption; file it as one")
            if f["confidence"] not in CONFIDENCE:
                raise ModelError(f"fact {f['id']}: unknown confidence '{f['confidence']}'")
            facts[f["id"]] = Fact(**{k: v for k, v in f.items() if k in Fact.__dataclass_fields__})
        for fid, f in facts.items():
            for old in f.supersedes:
                if old in facts:
                    facts[old].superseded_by = fid
        assumptions = {}
        for a in _yaml(os.path.join(d, "assumptions.yaml")).get("assumptions", []):
            for req in ("id", "statement", "owner", "reason"):
                if not a.get(req):
                    raise ModelError(f"assumption {a.get('id', '?')}: missing '{req}'")
            if a.get("cost_impact") and not a.get("resolved_by"):
                raise ModelError(f"assumption {a['id']}: drives money but names nothing that resolves it")
            assumptions[a["id"]] = Assumption(**{k: v for k, v in a.items() if k in Assumption.__dataclass_fields__})
        deliverables = []
        for x in _yaml(os.path.join(d, "deliverables.yaml")).get("deliverables", []):
            hours = {}
            for role, h in (x.get("hours") or {}).items():
                if role not in canon.roles:
                    raise ModelError(f"deliverable {x.get('code')}: unknown role '{role}' — Operations Manual 11.2 admits no variation; use one of {sorted(canon.roles)}")
                hours[role] = float(h)
            pts = [Passthrough(p["label"], float(p["cost"])) for p in (x.get("passthroughs") or [])]
            status = x.get("status", "proposed")
            if status not in SCOPE_STATUS:
                raise ModelError(f"deliverable {x.get('code')}: unknown status '{status}' (R11: status is an enum)")
            deliverables.append(Deliverable(
                id=x["id"], code=str(x["code"]), name=x["name"], phase=x["phase"], hours=hours,
                sequence_step=x.get("sequence_step"), window=x.get("window"), field_work=bool(x.get("field_work", False)),
                gates=x.get("gates") or [], resolves=x.get("resolves") or [], passthroughs=pts, status=status,
                authority=x.get("authority"), what_it_produces=x.get("what_it_produces", "")))
        cost_lines = []
        for x in _yaml(os.path.join(d, "program.yaml")).get("lines", []):
            if x.get("confidence") not in CONFIDENCE:
                raise ModelError(f"cost line {x.get('id')}: unknown or missing confidence (R7)")
            if not x.get("basis"):
                raise ModelError(f"cost line {x.get('id')}: missing basis (R7: every dollar names its source)")
            if x.get("payer", "cox") not in PAYERS:
                raise ModelError(f"cost line {x.get('id')}: payer must be one of {sorted(PAYERS)}")
            low, high = x.get("low"), x.get("high")
            if x["confidence"] == "pending":
                low = high = 0.0
            cost_lines.append(CostLine(id=x["id"], section=x["section"], label=x["label"], low=float(low), high=float(high),
                                       confidence=x["confidence"], basis=x["basis"], payer=x.get("payer", "cox"),
                                       driven_by=x.get("driven_by") or [], lands=x.get("lands", "")))
        unq = []
        for x in _yaml(os.path.join(d, "unquantifiable.yaml")).get("lines", []):
            for forbidden in ("low", "high", "value", "estimate"):
                if forbidden in x:
                    raise ModelError(f"unquantifiable line {x.get('id')}: carries '{forbidden}' — an unquantifiable line carries drivers and reference costs, never a number (R5)")
            if not x.get("drivers"):
                raise ModelError(f"unquantifiable line {x.get('id')}: no drivers named")
            unq.append(UnquantifiableLine(**{k: v for k, v in x.items() if k in UnquantifiableLine.__dataclass_fields__}))
        benchmarks = {}
        for x in _yaml(os.path.join(d, "benchmarks.yaml")).get("benchmarks", []):
            benchmarks[x["id"]] = Benchmark(**{k: v for k, v in x.items() if k in Benchmark.__dataclass_fields__})
        conflicts = [Conflict(**{k: v for k, v in x.items() if k in Conflict.__dataclass_fields__})
                     for x in _yaml(os.path.join(d, "conflicts.yaml")).get("conflicts", [])]
        nums = [c.number for c in conflicts]
        if len(nums) != len(set(nums)):
            raise ModelError("conflict numbers must be unique and are never reused (R10)")
        return cls(key=key, meta=meta, facts=facts, assumptions=assumptions, deliverables=deliverables,
                   cost_lines=cost_lines, unquantifiable=unq, benchmarks=benchmarks, conflicts=conflicts, canon=canon)

    # ------------------------------------------------------------ helpers
    @property
    def development_type(self):
        return self.canon.types[self.meta["development_type"]]

    def deliverable(self, code):
        for dlv in self.deliverables:
            if dlv.code == str(code) or dlv.id == code:
                return dlv
        raise KeyError(code)

    @property
    def usable_facts(self):
        """Facts that may enter a total or generated text: not superseded, not stale."""
        return {k: f for k, f in self.facts.items() if not f.superseded and not f.stale()}
