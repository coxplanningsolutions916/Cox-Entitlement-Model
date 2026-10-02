# Fee schedule registry

One YAML per jurisdiction or agency. The engine prices a project's agency fees from these schedules and the
project's quantities (`projects/<key>/fees.yaml`). Nothing in here is typed from memory: every schedule names
its adopted source and effective date, and a line without an adopted amount carries `amount: null` and a
`verify:` note, which prices as **pending** until the fee table arrives (the GIS fee layers in DATA-NEEDS item 9).

```yaml
schedules:
  - id: fee.<owner>.<name>            # stable id; generated cost lines are fee.<schedule>.<line>
    name: "..."
    owner: "Sutter County"            # who collects it
    kind: processing | drainage | park | specific_plan | transportation | sewer | water | school | habitat | ag_mitigation | inclusionary | cfd | facility | agency
    scope:                            # exactly one of
      jurisdiction: "Sutter County"   #   applies to every project in that jurisdiction (project.yaml jurisdiction)
      district: {layer: "sac_drainage_fee_zones", feature: "Zone 11A", polygon: [[lon, lat], ...]}   # membership by map (R1): declared in fees.yaml with a map citation, or point-in-polygon when the polygon is on file
      agency: "Section 401"           #   applies when the approval set (screen.yaml) names it
    source: {document: "...", revised: "YYYY-MM-DD"}
    effective: "YYYY-MM-DD"
    review_by: "YYYY-MM-DD"           # after this date the schedule is treated as benchmarked, not published, until re-confirmed
    lines:
      - {id: gpa, label: "General Plan amendment", basis: flat, amount: 9911, lands: "At application"}
      - {id: project_fee, label: "Project fee", basis: per_impact_acre, amount: 37544, less: 4212, cap: 365465}
      - {id: park, label: "Park impact fee", basis: per_unit, amount: null, verify: "Adopted fee schedule, parks chapter", applies_to: [residential]}
```

Bases: `flat`, `per_unit`, `per_acre`, `per_sqft`, `per_impact_acre`, `per_year` (quantity `years`), `per_edu`,
`range` (`low`/`high` instead of `amount`). Confidence of a priced line: **published** when the schedule is
current and every quantity it uses is a fact; **benchmarked** when a quantity is an assumption or the schedule
is past its review date; **pending** when the amount or the quantity is not on file.
