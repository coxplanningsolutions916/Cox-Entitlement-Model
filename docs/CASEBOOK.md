# The casebook: learning the firm's judgment from its projects

Chris, 3 October 2026: analyze more of our projects, including the challenges each faced and what resolved them, so the
model thinks and acts like an expert principal planner: how to strategize, navigate, when to question a theory or an
approach, and how to direct a project team to approvals and compliance efficiently. The same record answers client and
prospect questions, feeds marketing, and keeps the human side.

## What a case is

One record per project (and per task order where the story changed), structured so the engine can use it and a person
can read it. Facts with sources, like everything else in the model; the judgment parts are attributed to the person who
made the call.

| Field | What it holds | Example (Riego Rd) |
|---|---|---|
| identity | key, client, jurisdiction, development type, uses, acres, program, years | greenfield, Sutter County, 160 acres, 58 to 62 lots, 2026 to open |
| path | the approval set as planned, and as it actually ran | GPA, rezone with PD, map, EIR; 404, 401, 1602, 2081 |
| timeline | dated events: NTP, filings, agency responses, hearings, permits, closeout; planned versus actual per step | fall recon window closes 30 Nov 2026 |
| money | fee by task order as proposed, as changed, as billed; agency fees; mitigation; the client's consultants | TO1 $273,000 firm; EIR $350K to $550K benchmarked |
| challenges | what went wrong or threatened to: each with the signal that revealed it, when, who noticed | third-party delineation's contested classifications; two delivered membership claims that were wrong |
| decisions | the call, the alternatives considered, who made it, why, what it cost or saved | ARI verification rides with the 404 application, not a PJD (conflict 8, 18 Aug 2026) |
| resolutions | what fixed the challenge, how long it took, what it cost, whether it would be done the same way again | supersede the ISR language; cite the plan boundary layer |
| people | the agency staff, consultants and client roles that mattered, what they asked for, how the relationship was managed (names where consented, roles otherwise) | Corps project manager's intake practice; the contract biologist's call of 24 Aug |
| lessons | the reusable rule, in one sentence, tagged to the engine rule it became or should become | "a membership claim needs a map citation" became R1 |
| quotables | lines a client or prospect would understand, cleared for marketing (anonymized) | "the number nobody can put on the table yet is the mitigation" |
| outcome | approved, conditions, time to entitlement, final cost against the first estimate, what the client did next | open |

## Where the record comes from

- **Productive**: projects, task lists, tasks with dates and comments, time by role and deliverable, budgets, invoices, change orders. The quantitative spine and most of the timeline.
- **Asana phase boards** (2017 to mid-2026) and the **Barnett Dropbox archive** (about 120 jobs, 2014 to 2022): the earlier history, including the projects the Cox team ran under Barnett. These hold the challenges and the agency correspondence.
- **Drive project folders**: proposals, task orders, agency letters, permits, conditions of approval, the deliverables themselves.
- **Gmail and Granola**: the human side. Agency calls, client decisions, the sentence that changed the approach.
- **Chris and Kristin**: a structured interview per project, forty minutes, against the case skeleton the model drafts first, so the interview fills gaps and corrects rather than starts from blank.

## How it is built

1. **Draft from the record.** For each project the model drafts the case from Productive, Drive and the archive: identity, path, timeline, money, and a first list of challenges found in the documents (change orders, schedule slips, agency comment letters, re-submittals). Every line sourced.
2. **Interview.** Chris or Kristin reads the draft and answers the questions the draft could not: why the call was made, what the alternative was, who mattered, what they would do differently. Recorded by Granola, transcribed into the decisions, people and lessons fields.
3. **Extract the rules.** Each lesson is tested against the engine: does a rule already enforce it (R1 to R20), should one, or is it a benchmark (a duration, a fee, a review cycle count) that goes into canon. Lessons that are judgment rather than rule become **playbook entries** by development type and approval, which the Roadmap generator cites when the same pattern appears.
4. **Release the stories.** Quotables and anonymized challenge-and-resolution pairs go to the marketing queue (the newsletter and the Roadmap page's "what we have seen before") under the case-study rules Megan set: no owner names without consent, no unpermitted-work claims.

## What the engine gets

- **Benchmarks with provenance**: real durations per approval and jurisdiction (how long the County took on the last three rezones), real agency review cycles, real fee outcomes, real mitigation prices paid. These replace "typical duration" text with figures the dashboard can chart.
- **Playbooks by type and approval**: for an infill rezone in Sacramento, for a 404 individual permit in the Sacramento District, for a Williamson Act cancellation: the sequence Cox runs, the early calls to make, the documents that pre-empt the usual comment letter, the trap to avoid.
- **Risk signals**: the patterns that preceded trouble (a third-party delineation older than the farming operations; a specific plan membership asserted without a map; a wastewater answer still open at design) so the screen flags them before they cost anything.
- **Answers for clients and prospects**: "how long did your last three rezones take in this county", "what happened when the Corps asked for a PJD", "what did mitigation actually cost on a 160-acre vernal pool site", each answered from the cases with the sources behind them.
- **The human side**: who to call, what each agency's staff ask for first, how a hearing went and why, kept as part of the record rather than in one person's head.

## Schema and storage

`casebook/<project-key>.yaml`, loaded and validated like the rest of the model: facts need sources, decisions need a decider and a date, lessons need a rule or benchmark tag or a reason they are judgment only. The engine's existing conflicts and supersession machinery applies, so a case can record that an early theory was wrong and what replaced it. Cases publish to a team-only page on the dashboard (never to a client page) and to the marketing queue only through the release step.

## First pass

Twelve cases to prove the schema, chosen for range: Riego Rd and Lemon Hill (already in the model), Grant Line Rd (the sold CUP roadmap), 474 Joaquin and Kausen Drive (long multi-permit federal programs), Las Colinas (compliance and mitigation monitoring), Napa 55 (a Barnett-era program carried into Cox), Rancho Oso and Ponderosa (storm-damage emergency permitting), 21st Street (the restroom redesign and the change order), Monte Vista Memorial Gardens and Panattoni (the two largest accounts). About two hours per case including the interview, so a month at the current pace, and the model learns something from every one.


## As built (3 October 2026)

`engine/casebook.py` loads and validates `casebook/<key>.yaml`: required identity fields; every timeline entry,
challenge and decision carries a source; decisions carry who and when; resolutions point at a challenge id; people
carry a role and a name only with recorded consent; lessons are typed (rule with an R-number or a proposed one,
benchmark, playbook, process, or judgment with the reason it cannot be a rule); quotables are uncleared until someone
clears them; benchmarks carry metric, value and source. `python -m engine case <key>` prints a case; `publish-all`
writes `casebook/index.json` (cases with consent-filtered names, the benchmark table, the playbook by type) into the
dashboard, where `/casebook` and `/casebook/<key>` are team-only pages. First case: Grant Line Rd (The Swing Lab),
drafted from Productive, Automator, Drive, Gmail and Granola, with eight interview questions open for Chris.
