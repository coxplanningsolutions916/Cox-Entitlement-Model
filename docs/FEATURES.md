# Recommended features — Cox Phase 1A / Roadmap app

Drawn from `COMPETITION.md` and the product decisions of 1 October 2026 (developer first, ten sections, web report plus PDF, Sacramento and Placer counties with their cities as the pilot, one staff hour in the $500 product, four in the $2,500 Roadmap, 100 free screens at launch). The organizing idea: the apps are wide and shallow; this app is two counties deep, and every number carries its source and its confidence.

Priority key: **L** = needed for the 100-screen launch · **P** = pilot v2, before paid expansion · **R** = Roadmap-only (planner's four hours) · **X** = later or never.

## 1. Intake and the report itself

| # | Feature | Why (competitor or decision) | Pri |
|---|---|---|---|
| 1.1 | Address, APN, or KML in; parcel resolved from the county assessor layer; multi-parcel assemblage allowed | Transect's free KML mini-report is the right shape; assemblages are what developers actually screen | L |
| 1.2 | Stated use and program from the client (use type, units or square feet, stories), or "find the fit" (HBU mode) | Q7 decision: one process, zoning rules versus the client's use or the market fit | L |
| 1.3 | Ten-section report, web plus PDF, with page one = the decision in three lines, the approval set, and the top five assumptions | PermitPortal's go/no-go is the format developers already read | L |
| 1.4 | Provenance on every figure (source, date pulled, link), rendered as a hover or footnote | Deepblocks' "every figure has a source"; the engine already refuses facts without one | L |
| 1.5 | Confidence label on every line (strong, moderate, weak) with "what firms it up" and the Step 1b task and cost that does so | The upsell is visible in the product itself; this is the assumption register made commercial | L |
| 1.6 | Assumption register as a live table: assumption, basis, risk if wrong, verify-by task, owner | The board-grade requirement; no competitor ships one | L |
| 1.7 | Persona cuts of the same report: developer (full), investor (one-page risk and timeline), owner (what it is worth pursuing), broker (listing-ready facts) | Personas decision; same model, shorter reads | P |
| 1.8 | Reviewer mode: the staff-hour checklist (section 6) inline, with sign-off, reviewer name and date printed on the PDF | The staff hour is the differentiator; make it visible on the output | L |
| 1.9 | Upgrade path on the last page: Roadmap at $2,500 with the $500 credited, and the three scale-test questions pre-answered by the model | Scale test from the pricing decision; Transect's mini-report ends the same way | L |
| 1.10 | Project continuity: the 1A record becomes the Roadmap record becomes the Productive project; facts replace assumptions in place | The living-model decision; the thing an app cannot copy | P |
| 1.11 | Client dashboard tie: from Step 1a the client's link on the Cox dashboard shows the current roadmap, budget with confidence, assumption register, change log and next step; at Step 2 it merges with the client statement (hours, invoiced, paid, percent complete) | Chris's direction 1 Oct; one page for the plan and the money | L |

## 2. Zoning and land-use fit

| # | Feature | Why | Pri |
|---|---|---|---|
| 2.1 | Zoning district, general plan designation, community or specific plan, overlays, per parcel, from each pilot jurisdiction's GIS (county plus every city) | Table stakes; every competitor has it | L |
| 2.2 | Digitized use tables per district for the pilot jurisdictions: permitted, conditional, prohibited, with the code citation | The real cost of the pilot and the depth that ArchiWise and Build.inc lack locally; Zoneomics or Gridics code text as a possible supplier | L |
| 2.3 | Development standards per district: density or FAR, height, setbacks, lot coverage, parking, open space, with effective dates | Needed for the capacity read and for the standards-versus-program test | L |
| 2.4 | By-right versus discretionary determination for the stated use, then the approvals list (use permit, design review, rezone, GPA, specific plan amendment, subdivision map, variance, annexation) | ArchiWise's entitlement viability, done with the local code rather than a national proxy | L |
| 2.5 | State overlays and streamlining tests: SB 9, SB 35 / SB 423, AB 2011, AB 2097 parking, density bonus, housing element sites inventory, ADU eligibility, Class 32 infill exemption candidates | California-specific; none of the national tools apply them correctly | L |
| 2.6 | Simple yield: units or square feet achievable from standards versus the client's program, flagged where the program exceeds the envelope | Enough of Deepblocks and TestFit to be useful; no 3D massing | P |
| 2.7 | Pending changes: general plan updates, zoning code rewrites, moratoria, specific plans in process, tracked per jurisdiction | PermitPortal's nightly monitoring and Build.inc's pending-changes flag | P |
| 2.8 | Urban services boundary, sphere of influence, LAFCo annexation need, growth boundary (Sacramento County USB, Placer city SOIs) | Decisive in the pilot region and invisible to national tools | L |

## 3. Constraints: the depth

| # | Feature | Why | Pri |
|---|---|---|---|
| 3.1 | Biology screen: CNDDB occurrences (licensed) within 1 and 5 miles, USFWS critical habitat, IPaC species list, NWI wetlands, NHD streams, vernal-pool complexes, Swainson's hawk foraging habitat, elderberry, oak woodland | The CNDDB license is the hard-to-copy asset; this is what PermitPortal will not do | L |
| 3.2 | HCP and NCCP coverage with fee schedules: South Sacramento HCP, Natomas Basin HCP, Placer County Conservation Program, with in-area versus out-of-area consequences | Turns a biology flag into a dollar and a path; the strongest regional differentiator | L |
| 3.3 | Waters and flood: NWI, NHD, FEMA NFHL zones, 200-year floodplain and Urban Level of Flood Protection (SB 5) status, levee and Central Valley Flood Protection Board jurisdiction, county floodplain ordinances | ULOP alone can stop a Sacramento-region project; no competitor carries it | L |
| 3.4 | Federal nexus and the resource-permit stack: waters present → 404 → 401 → ESA Section 7 → NHPA 106; state 1602 and 2081; season windows | Rule R2 in the engine; the approval set nobody else maps | L |
| 3.5 | Cultural: AB 52 consultation flag, NAHC and CHRIS records-search status (request required, not public), sensitivity by landform and water proximity, historic resources listings | Sacred Lands File and CHRIS cannot be automated; the app says what to request and flags sensitivity | L |
| 3.6 | Agriculture: Williamson Act contracts, FMMP important farmland, ag mitigation ordinances and ratios, right-to-farm buffers | Pilot-region specific | L |
| 3.7 | Hazards: Alquist-Priolo, liquefaction, CAL FIRE fire hazard severity zones, airport land use compatibility (SMF, Mather, McClellan, Executive, Lincoln, Auburn), noise contours, EnviroStor and GeoTracker sites, dam inundation | Constraint layers the apps have in part; the app ties each to the approval it triggers | L |
| 3.8 | Trees: heritage and native oak ordinances by jurisdiction, oak woodland mitigation (SB 1334) | Local ordinances with real cost | P |
| 3.9 | Infrastructure: sewer agency and capacity (Regional San, SASD, Placer SMD), water purveyor and will-serve likelihood, school district and developer fees, CFD and Mello-Roos overlays, utility providers | PermitPortal and The Handover list utilities; this version names the agency and the fee | P |
| 3.10 | Transportation: SB 743 VMT screening maps by jurisdiction, transit priority areas, major corridor plans | Decides the traffic analysis scope under CEQA; local maps exist for both counties | P |
| 3.11 | CEQA pathway: exemption candidates, ND/MND versus EIR likelihood, prior EIRs to tier from (community and specific plan EIRs, CEQAnet search on the parcel and vicinity) | The pathway decision drives schedule and cost more than any other line | L |

## 4. Program, cost, schedule

| # | Feature | Why | Pri |
|---|---|---|---|
| 4.1 | Approval schedule with predecessor chain, season windows, placement after NTP, slack | PermitPortal's predecessor chain; the engine's schedule module already does it | L |
| 4.2 | Order-of-magnitude cost ranges: consulting (OM 14.3 build), agency fees from jurisdiction fee schedules, HCP fees, mitigation ratios and credit prices, impact fees; each with confidence | The engine's program module; competitors stop at the pro forma | L |
| 4.2a | Fee districts as GIS layers: drainage and flood control zones, Quimby and park districts, specific plan and finance plan fee areas, transportation fee districts, sewer and water connection fee areas, school fee areas, habitat and ag mitigation fee zones, inclusionary and in-lieu zones, CFDs; the parcel's location prices the program's agency fees automatically | Chris's direction 1 Oct; no competitor prices local fees by parcel | L |
| 4.3 | Unquantifiable lines carried as named exclusions, never zero | Program rule; board-grade honesty | L |
| 4.4 | Historical approval timelines from Cox's own project history (Productive, the Barnett archive) and agency agendas, by jurisdiction and approval type | PermitPortal sells this; Cox has fourteen years of local history to mine | P |
| 4.5 | Watch: nightly re-check of the layers and the jurisdiction's pending changes for every active site, with a change notice | PermitPortal's monitoring; the model's Phase 6 | P |
| 4.6 | Political read: commission and council composition, recent approvals and denials, opposition signals | PermitPortal does it; useful but a planner's judgment, so Roadmap-only | R |

## 5. Market analysis: recommendation

Frame the market section as the third gate of the appraiser's highest-and-best-use test, which is exactly the Q7 process Chris described: **legally permissible** (sections 2 and 3) × **physically possible** (section 3) × **financially feasible** (market) → **maximally productive** (the ranked fit). The app runs the first two gates from the layers, feeds the third from ArcGIS Business Analyst and public data, and the planner's hour calls the fourth.

**Phase 1A, automated (one GeoEnrichment call per site, reviewed in the staff hour; included in the free launch screens).** Business Analyst's GeoEnrichment REST service returns the variables for a drive-time or ring trade area in one request, at a few credits per site, which is well under a dollar at published credit rates. Pull, for 5/10/15-minute drive times (or 1/3/5 miles rural):

- Population, households, five-year growth, median and average household income, daytime population, median age, Tapestry top three segments.
- Housing: units, tenure, vacancy, median home value, average rent, units built since 2010.
- Employment: businesses and employees by NAICS group, daytime workers.
- For retail or commercial uses, the Retail MarketPlace supply-demand gap for the relevant NAICS lines (leakage means demand the site could capture).
- For industrial or logistics uses, truck-route proximity and employment base; for residential, the jobs-housing ratio and the housing element RHNA progress.

Print the trade-area map, the ten most decision-relevant figures, and one sentence each on what they say for the stated use. Label the section "market context, not a feasibility study or appraisal", and carry absorption, rent and pricing as **moderate or weak confidence** assumptions in the register with "verify by: broker opinion of value or feasibility study" as the Step 1b lever.

**Roadmap, planner-run in Business Analyst Web App (part of the four hours).** The planner runs a Comparison report against two or three alternative sites or the jurisdiction, a Site Suitability or Smart Map Search where the use is location-sensitive, and the Housing Profile or Retail MarketPlace Profile PDF as an appendix, then writes the HBU read: which of the legally permissible uses the market supports, ranked. That read is the planner's product, not the software's.

**Public data to add beside Business Analyst (free, cited):** SACOG MTP/SCS growth forecasts by community (the regional planning authority's own numbers carry weight with agencies); county and city permit data (units and square feet permitted by year); Census Building Permits Survey; HUD Fair Market Rents; Zillow ZHVI and ZORI for value and rent trend; the jurisdiction's housing element sites inventory and annual progress report (RHNA shortfall is a market and an entitlement signal at once); California Department of Finance E-5 population estimates.

**What not to build.** No pro forma and no appraisal: the developer's own analyst produces those, and producing one creates an expectation Cox cannot stand behind. No CoStar-grade comps unless a license is bought later; say so in the register. The market section exists to rank the permissible uses and to flag where the client's program is out of step with demand, which is where the planner's advice and the upsell live.

## 6. The staff-hour checklist (1A reviewer)

Ten items, one per section, on the reviewer screen; each ticks or raises a note that prints on the PDF.

1. Parcel and jurisdiction resolved correctly, including city versus county and any annexation question.
2. Zoning, general plan and overlays match the jurisdiction's current map, not a stale layer.
3. The stated use is classified correctly in the use table; borderline uses named and the interpretation route stated.
4. Standards-versus-program test reads right; any variance or exception need is called out.
5. Biology flags are plausible on the aerial (vernal pools, drainages, oaks, elderberry); CNDDB hits within range are the right species for the habitat.
6. Flood and ULOP status checked against the jurisdiction's own map; levee or CVFPB jurisdiction confirmed.
7. The approval set is complete and the CEQA pathway call is defensible; a tiering document, if named, is the right one.
8. Cost and schedule ranges pass the smell test against comparable Cox projects; confidence labels are honest.
9. Market section figures are current and the trade area is the right shape for the use.
10. Assumption register lists the five assumptions that matter most, each with a verify-by task and cost; the upgrade recommendation is right for the scale test.

## 7. Not now

3D massing and site-plan generation (TestFit, Deepblocks); national or statewide coverage before the pilot proves depth; a political read in the automated product; a subscription seat model; a pro forma. Zoneomics or Gridics code text may be worth licensing to shorten section 2 capture, and Regrid parcels when expansion beyond the two counties begins.
