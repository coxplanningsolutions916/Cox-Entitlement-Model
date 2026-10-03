# The model in the funnel: how the Entitlement Roadmap is produced, sold and delivered

3 October 2026. Written so the landing page can be finished against a fixed picture of what the model does at each
moment. It follows the 2 October decisions (`Cox_Front-End_Landing_Page_Strategy_2026-10-02_v2.md`, "For the model
build"): one product, the Entitlement Roadmap, in three levels: **Screen** ($500, first 100 free, 48 hours), **Map**
($2,500, one week), **Scenarios** ($5,000, two weeks), each credited toward the next. "Screening" and "Roadmap Plus"
are retired. Step 1b (surveys) and Step 2 (conceptual design, engineering front and center) follow.

## One picture

Page → hero form → intake and payment page → Automator (Roadmap Requested) → **model drafts the Screen in 24 hours**
→ **planner reviews and signs within 48 hours** → Roadmap Delivered → delivery email with the dashboard link and the
upgrade → Map in a week (planner judgment on the record) → Scenarios in two weeks (estimates on the map) → Step 1b
proposal → Productive project, the same model as its backbone.

## Moment by moment: what the model does, what the client holds

| Moment | What happens | What the model does | What the client holds | Systems | Owner | Clock |
|---|---|---|---|---|---|---|
| Ad, mailer, post | Promise: an address in, the first level of your Entitlement Roadmap out, planner-reviewed | Nothing yet | The promise | Troo, LinkedIn, mail | Michelle, Megan | |
| Hero form | Address or APN, what you want to build, email; pilot-boundary check | **Pilot check** (Sacramento and Placer and their cities) answered from the parcel layer; outside the pilot gets the email-me-when-live path | A confirmation and the next page | Automator contact with source and UTM | Michelle (build) | seconds |
| Intake and payment page | Name, company, role, phone, how-you-heard; property documents; the three scale-test questions; order at $500 or $0; upgrade offer; QBO pay link | **Scaffolds the project from the form**: creates the project folder with the development type inferred from the parcel (confirmed by the planner), the use, the register seeded from the type, the fee families, every primary issue as a fact needed; **answers the scale-test questions it can** from the layers; stores the uploads as sources | Order confirmation with the delivery date | Automator opportunity at Roadmap Requested (level, value, source, UTM, free-screen tag); QBO invoice or $0 record; Drive proposals folder | Michelle (wiring), model | minutes |
| Within 24 hours | The draft Screen | **Builds the ten-section report** from the GIS layers, the fee schedules, CNDDB, the aerial record and the market pull; every figure sourced and confidence-labeled; the register priced from the estimating basis; publishes the dashboard page with the red unreviewed stamp; posts the review task to the planner | Nothing yet (the draft never leaves the building) | Model; dashboard /r/token (unreviewed); Productive review task | Model | 24 h |
| Within 48 hours | Planner review | **Review command** records the ten checks, notes and the signature; **corrections are logged to the correction register**; the stamp clears; the scale test prints its result and the planner's call; the PDF and page regenerate | The Screen: web page, PDF, dashboard link, the go or no-go, the three questions, the register | Automator to Roadmap Delivered; delivery email; Productive after payment per the SOP | Planner (rota) | 48 h |
| Delivery email | Offer the next level | **Credit and rung from the model**: Map with the $500 credited, or Scenarios where the scale test fired; session booking | The offer with the reason | Automator sequence | Automator | |
| Map, one week | Planner judgment on the record | **Drafts for the planner**: the desktop constraints-map layers (zoning and overlays, waters and wetlands, flood, species habitat, cultural flags, easements, access), each tagged mapped or field-verified; the **candidate-path table** (approvals each path would trigger, in order, with what confirms or rules each out); the HBU ranking from the market pull; the verification plan priced from the estimating basis; the Step 1b scope and price from the register | The Map: corrected report, constraints map, candidate paths, verification plan, session, priced Step 1b | Model; ArcGIS template (Suzanne); Productive | Senior planner | 1 week |
| Scenarios, two weeks | Estimates on the map | **Scenario calculator**: two or three programs from the net developable area after roads, drainage, parks and open space at industry-standard shares; yield, approval set, ranges and assumptions per scenario; the records-search flag from the cultural row; board summary and deck from the model's own figures; Roadmap v2 when the records search returns | Scenarios: specialist read, records search where flagged, the estimates, board package, second session | Model; specialist; Information Center | Principal | 2 weeks |
| Day 7, 14, 30 | Follow-up | Register and dashboard unchanged; the page is the reminder | The same link | Automator | | |
| Roadmap closes | Step 1b proposal signed | **onboard_from_deal**: the won deal becomes the Productive project; the model becomes its backbone; the dashboard page merges with the client statement | A project, one page for the plan and the money | Productive, QBO, dashboard | Chris | |

## What exists today, what is to build

| Model function | Status 3 Oct | Where |
|---|---|---|
| Ten-section report, web and PDF, sources and confidence, register priced from the fee build | Built; two fixtures | `engine/report.py` |
| Dashboard client page with the charts (KPI strip, Gantt, burn-up, mitigation cone, stepper, register) | Built and live | cox-dashboard `/r/<token>` |
| Review command, stamp rule, scale test with planner override | Built | `engine/review.py` |
| Development types and the coverage rule | Built | `canon/development_types.yaml`, R19 |
| Fee schedules by district, jurisdiction and agency | Built; Sutter and state seeded; Sacramento and Placer pending the fee tables | `engine/fees.py` |
| Level names, prices, turnaround and credits per 2 Oct | Updated today | `engine/report.py`, `docs/PRICING-LADDER.md` |
| **Scaffold from the form** (address, intent, uploads, scale answers → project folder) | To build, Oct 23 with the intake page | new `engine/intake.py` |
| **Pilot-boundary check and type inference from the parcel** | Needs Suzanne's parcel and city-limits layers (Oct 16) | data layer |
| **Automated layer pulls** (zoning, overlays, constraints, CNDDB, fees, Business Analyst) into the screen rows | Needs the layers; the screen format is fixed | data layer |
| **Automator and QBO hooks** (opportunity at Roadmap Requested with level, value, source, UTM, tag; Delivered on sign-off; $0 record) | To build, Oct 23 | `engine/hooks.py`, ghl_client |
| **Correction register** (planner corrections logged per draft; error rate per Screen on the dashboard) | To build, Oct 16 | `engine/review.py`, dashboard |
| **Free-screen counter**, paced (25 a month or a daily cap, delivery date shown) | To build, Oct 23 | dashboard, Automator |
| **Publish on push** (every project republished to the dashboard by a GitHub Action) | To build; needs the push token on the model repo | `.github/workflows` |
| **Map drafts**: constraints-map layers and the candidate-path table | After the layers, Oct 30 | `engine/map.py` |
| **Scenario calculator** with land-use share tables by product type | Nov 13 | `engine/scenarios.py`, `canon/land_use_shares.yaml` |
| Casebook (project history into rules, benchmarks, playbooks) | Designed; starts after the funnel items | `docs/CASEBOOK.md` |

## Contracts the page can rely on

- **The hero form** needs only address or APN, intent and email. The model does not need more to start; the intake
  page's documents become sources with provenance, not inputs the model cannot run without.
- **The three scale-test questions** on the intake page are answered by the model where the layers can (parcels and
  jurisdictions from the parcel layer; mapped resources from the constraint layers; discretionary from the use table)
  and shown to the client pre-filled to confirm, not asked cold.
- **Turnaround** is measured from order confirmation: the model's 24-hour draft leaves the planner a working day.
- **Nothing unreviewed leaves.** The stamp is in the generator, not a habit; the links page shows review state.
- **Credits** are applied by the model from the order record (Screen toward Map, Map toward Scenarios; the
  Screen-to-Scenarios jump is open).
- **The dashboard link is the deliverable's home.** The PDF is a snapshot; the page is the living model, and at
  Step 1b it carries the client statement.

## Operating rules the model enforces

The red stamp until all ten review items are answered; the scale test printed with the planner's call and reason
(R20); every planner correction logged; the free-screen pace visible on the dashboard; $0 orders create the same
project and records as paid ones; Information Center results read into the Roadmap, never forwarded; the
unreviewed dashboard page reachable only by its token and never listed as sendable.
