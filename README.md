# cox-entitlement-model

Cox Planning Solutions' entitlement program model, built to the brief of 25 September 2026 ("Build Brief: Cox Entitlement Program Model"). The deterministic layer: facts with provenance, a fee build that follows Operations Manual 14.3 step for step, confidence composition on every total, the strategy rules as testable predicates, season-window scheduling, and the program budget with unquantifiable lines carried as named exclusions. No model calls anywhere in `engine/`; Claude's judgment lands in the YAML files as reviewable proposals, never in a total.

**Regression fixture:** Riego Rd Task Order 1 reproduces exactly — labor 246,580; pass-through 1,725; coordination 24,658; total 273,000; 1,463 hours (`tests/test_fee_riego.py`).

## Status (build order from the brief, §12)

| Phase | Scope | State |
|---|---|---|
| 1. Core, offline | Fact / assumption / deliverable / cost line / unquantifiable line / benchmark / conflict types with validation; fee build; confidence taxonomy and composition; Riego TO1 reproduced | **done, 30 Sept 2026** |
| 2. Graph and schedule | Season windows, placement after NTP, slack to window close, mobilization grouping (R3, R4) | **done (minimal)**; authorization dependency graph with structural edges (R2) not yet built |
| 3. Generation | Roadmap docx, internal and client workbooks, scope docx, with the client whitelist enforced by the generator | not started; `program.render_text` and `fee.internal_table` are text previews only |
| 4. Scenario | Levers, propagation, diffing | not started (levers are referenced by id in the seed data) |
| 5. Acquisition | Chrome, GIS, intake, source registry with TTLs | not started (facts carry `ttl_days`; `Fact.stale()` exists) |
| 6. Watch | Scheduled digest of expired facts, closing windows, fired change-order triggers | not started |

## Use

```
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q                       # 13 tests, Riego fixture included
.venv/bin/python -m engine fee riego-rd             # INTERNAL fee backup + payment schedule (hours and rates: never client-facing)
.venv/bin/python -m engine program riego-rd         # program budget by section with confidence composition and exclusions
.venv/bin/python -m engine schedule riego-rd --ntp 2026-10-15
.venv/bin/python -m engine check riego-rd [--draft file.md]   # strategy rules; exit 1 on a hard violation
```

## Layout

```
engine/   model.py (types + loaders)  fee.py  confidence.py  rules.py  schedule.py  program.py  __main__.py (CLI)
canon/    roles.yaml (OM 11.2 canonical roles + rates + fee rules)  windows.yaml  confidence.yaml
projects/riego-rd/   project.yaml  deliverables.yaml  program.yaml  unquantifiable.yaml  benchmarks.yaml  facts.yaml  assumptions.yaml  conflicts.yaml
tests/
```

## Rules implemented (`engine/rules.py`)

R1 membership needs a map citation (hard) · R5 unquantifiable lines carry no number (hard) · R6 benchmark applicability by jurisdiction/region and project size (hard) · R7 every dollar has a confidence class and basis · R11 discussed is not authorized (hard) · R12 round once at the total · R13 quarantined language is rejected in drafts (hard) · R18 local-rule facts past their TTL block (hard). R2, R3 (validation), R4 (reporting), R8–R10, R14–R17 are next.

## Guardrails that are structural here

- A fact without `source`, `established` and `confidence` does not load. A superseded fact stays in the file, marked, and is unusable (`Project.usable_facts`); its `quarantined_terms` fail any draft that contains them.
- An unquantifiable line that carries `low`, `high`, `value` or `estimate` does not load.
- A role key that is not one of the Operations Manual 11.2 strings does not load.
- Money is held to the cent; the only rounding is once, at the task-order total (`fee_rules.round_total_to`).
- Margin is computed from `cost_rate` and printed only by `fee.internal_table`; it has no client-facing path.
- Nothing here writes to Productive. Export on approval is Phase 3+.


## Development types

Every project names a `development_type` (greenfield, infill, redevelopment, rural_resource, public_infrastructure) from `canon/development_types.yaml`; the type sets what the screen must cover (rule R19), the default levers, the fee families and what the report leads with. See `docs/DEVELOPMENT-TYPES.md`. Fixtures: `riego-rd` (greenfield) and `lemon-hill` (infill).


## The funnel commands (part 1)

```
python -m engine intake --from order.json            # or --address ... --jurisdiction ... --level screen --free ...
python -m engine hooks <key> all [--live]            # Automator order, Productive review task, QBO request, delivery email (dry run by default)
python -m engine review <key> --reviewer "..." --ok 1,2,... --fix "section|field|from|to|reason"
python -m engine hooks <key> delivered --live        # Roadmap Delivered + note with the dashboard link
python -m engine publish-all [--dash ~/code/cox-dashboard]   # every project + roadmaps/_metrics.json (free counter, error rate)
```

`python -m engine map <key>` prints and exports the Map drafts; `python -m engine scenarios <key>` prints the Scenarios estimates; `report --rung plus --pdf` also writes the board summary and deck.
