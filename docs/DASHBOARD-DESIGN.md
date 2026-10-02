# Roadmap page: design review and recommendations

1 October 2026. Reviewed the live `/r/<token>` page against the patterns in development-management and
investment dashboards (Northspyre project and budget views, Dealpath pipeline and development dashboards,
Procore-style schedule views, PermitPortal's one-page risk brief) and against the Cox client statement, which
already has a Gantt the client knows. The page is correct and complete; it is not yet a dashboard. It reads as
a long report: nine tables of equal weight, no time axis, no picture of the money, and the thing the client
most wants to understand, the mitigation unknown, is a sentence.

## What the good ones do

1. **Answer the four questions on the first screen**: how much, how long, how sure, what next. A KPI strip of four
   or five tiles, then one chart per question. Tables come after, behind the charts they explain.
2. **One chart per question.** Time is always a Gantt with a today line. Money is cumulative against a budget
   envelope (a burn-up), never a bare table. Risk is a register with a status chip and an owner.
3. **Few colors, used for meaning.** One color for what is firm, one for what is estimated, grey for unknown, red
   only for what needs the reader's attention. Northspyre and Dealpath each use three.
4. **Uncertainty is drawn, not footnoted.** Ranges are bands; confidence is a share of the bar; unknowns are grey
   space with a date on which they stop being unknown.
5. **Progressive disclosure.** Summary first; detail opens below it or on a click. The print version and the screen
   version are the same page.

## Recommended page, top to bottom

| Block | What it shows | Chart | Data it needs from the model |
|---|---|---|---|
| **Header and stamp** | Site, client, rung, reviewed-by, refreshed date | as now | as now |
| **KPI strip** (5 tiles) | Program to entitlement (range); firm, quoted and published share; months to entitlement; register progress (verified / open / pending); next step with fee and date | tiles with a small bar under the share and the register | `budget.total`, months from the cost lines, register counts, `next_steps[0]` plus the task-order fee |
| **The decision** | What to build, how it gets approved, what it takes | three cards in a row | as now |
| **Schedule** | Steps and task orders as bars by month; approvals as bars under the step that files them; season windows as light bands behind the bars; a today line; milestone diamonds (notice to proceed, delineation delivered, preferred plan, filings, hearings, permits); the critical window sequence outlined; agency-controlled durations hatched | **Gantt** (reuse the statement's Gantt CSS so the two pages match) | start and end month per cost line parsed from `lands` ("Months 15 to 30"); window placements; milestones from the task order's payment schedule; approvals' typical durations |
| **Investment** | Cumulative money over the same months: the program envelope (low to high) as a band rising step by step; the firm line (Task Order 1) solid; invoiced and paid lines from the statement once the project has one; a stacked bar per step beside it split by who pays (Cox, client's consultants, agency fees) | **Burn-up** with an envelope, plus the stacked step bars | per-line low, high, payer and months; from Step 1b the statement's invoiced and paid by month (the dashboard already holds QBO invoices by date) |
| **Mitigation: from unknown to known** | The compensatory-mitigation line drawn as a cone of uncertainty: full-height grey "not yet quantifiable" today, narrowing at each resolving deliverable (delineation of record, preferred plan, 2027 surveys, mitigation plan) to a range, then a quote, then a firm figure; the reference unit costs listed under it (credit price pending, land per acre, endowment per acre); a driver checklist with a status dot per driver | **Resolution cone** (a band that narrows left to right with dated gates) | the unquantifiable line's drivers with `resolved_by` deliverables and their window dates; reference benchmarks and their status; later, the range, quote and firm figure as they land |
| **Approval path** | County track and federal/state track side by side, the nexus drawn as the link between them, CEQA across both | **Stepper** (two lanes) | approvals with body, duration and `federal_nexus` |
| **Register** | A ring for verified / open / pending, then the table grouped by status with open first and the fee to verify in the row | ring plus grouped table with filter chips | as now, plus counts |
| **Change log** | Dated dots, newest first, five shown, the rest behind "show all" | timeline | as now |

## Visual system

- **Palette with meaning**: navy for firm and for Cox's own lines; teal for published and agency figures; amber for
  derived and assumed; grey for pending and unknown; red only for a fact the reader must supply. Gold stays the
  accent (today line, milestones, the stamp rule). Nothing else.
- **Type**: one family (Arial on the statement, keep it), three sizes: 24 for the KPI number, 14 for body, 12 for
  the small print. Weight 400 and 700 only.
- **Layout**: a 12-column card grid; charts full width; tiles five across on desktop, two across on a phone; the
  Gantt scrolls sideways on a phone with the label column pinned, as the statement's does.
- **Print**: the same page prints to the PDF the client files; page breaks before Schedule, Investment and the
  register; no sideways scroll in print.
- **Stamp**: the unreviewed stamp stays red and stays at the top. Nothing else on the page is red.

## How to build it

Server-rendered SVG from a small `charts.py` in the dashboard (no JavaScript libraries, prints cleanly, consistent
with the statement's Gantt). Three additions to the published JSON: per-line start and end months (parsed from
`lands`), the task order's milestones with months, and the mitigation drivers with their resolving deliverables,
dates and reference costs. Order of work, about three days: KPI strip and the Gantt (a day, reusing the statement's
Gantt CSS); the burn-up and the stacked step bars (a day); the mitigation cone, the stepper and the register
regroup (a day). Chart data is unit-tested the same way the fee build is.

Sources consulted: Northspyre, "Best real estate project management software" and "Best real estate development
software" (northspyre.com); Dealpath, "Top 8 real estate dashboards" and the development page (dealpath.com);
Gantt templates for real estate development (instagantt.com, clickup.com, tomsplanner.com, ganttpro.com).
