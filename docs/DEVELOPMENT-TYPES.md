# Development types

Added 2 October 2026 at Chris's direction. Riego Rd and Lemon Hill are different kinds of project, and the model
should know it before it screens anything: Riego is **greenfield** (agricultural land to an urban use, so aquatic and
biological resources and the federal nexus dominate); Lemon Hill is **infill** (inside the city, surrounded by
development, so neighbors, density, parking and design review dominate).

`canon/development_types.yaml` holds five types: greenfield, infill, redevelopment and adaptive reuse, rural and
resource land use, public and infrastructure projects. Each carries what it means, the signals that identify it,
one sentence on what drives it, the CEQA expectation, a typical schedule band, the **primary issues** the screen
must address (each with keywords and what verifies it), the default levers to test, the typical approval set, the
fee families that apply, the assumptions the register should start with, and what the report leads with. A project
also names one or more **uses** (residential, commercial, industrial, mixed use, institutional, infrastructure,
agricultural); use is a separate axis from land context.

What the type does in the engine:

- `project.yaml` must name `development_type`; the loader refuses a project without one.
- **Rule R19** (soft): the screen must address every primary issue of the type, or the issue is carried as a fact
  needed. Lemon Hill's screen covers ten of eleven infill issues and misses historic and cultural resources, so the
  report adds that row with what verifies it.
- The report's section 1 states the type and what drives it; section 5 orders the constraint rows in the type's
  issue order and appends the missing issues; section 3 falls back to the type's default levers when a project has
  none on file.
- The published JSON carries the type profile and the coverage gaps, so the dashboard can badge the page and the
  team can see what the screen has not yet covered.

What it does not do yet: choose deliverable templates by type (the estimating basis in the proposals plugin is
the place for that), or weight the scale test by type. Both are natural next steps once Suzanne's layers can tell
the type from the parcel (zoning, city limits, services at the frontage, developed neighbours).

## The genericity result

Lemon Hill ran through the same engine as Riego with no code written for it:

- The April 2026 fee backup's hours price at **$24,000** under Operations Manual 14.3 against the **$23,200** proposal
  of record, which was built with per-deliverable rounding and project management embedded. The delta is recorded
  on the project, not hidden.
- The program total reproduces the Roadmap's **$160,000** for a clean site: the firm task order plus the Roadmap's
  balance as one derived line until the Figure 2 split is captured, with agency fees pending.
- The rules found two real gaps: the Roadmap's "outside the South Sacramento HCP" claim has no map citation (R1,
  hard), and the screen does not address historic resources (R19).
- Two conflicts are open: the screening fee ($3,000 in the Roadmap, $6,000 in the fee backup) and transit proximity
  (bus only in the Roadmap, a light-rail station in the vicinity in the market screen).
- There are no season-window deliverables, so the Gantt has no window bands and the schedule block is the task
  order's milestones alone, which is right for an infill site.
