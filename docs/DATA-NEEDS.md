# Data needs for the Phase 1A app — request to GIS (Suzanne)

Draft 1 October 2026. Pilot area: **Sacramento County and Placer County, including every city** (Sacramento, Elk Grove, Citrus Heights, Folsom, Rancho Cordova, Galt, Isleton; Roseville, Rocklin, Lincoln, Auburn, Loomis, Colfax), then statewide. Everything below should land as **ArcGIS Online hosted feature layers with REST endpoints the app can query by parcel**, one web map per county, with metadata on each layer: source, date pulled, **license class** (public domain / open with attribution / licensed report-only / request-only, see `LICENSING.md`), refresh cadence. The `cox-screening-tool` layer work already started is the base; this list is what it grows into.

## A. Parcel and jurisdiction base

1. County assessor parcels for both counties (APN, situs, acreage, owner name and mailing address, use code, improvement value) and the refresh cadence the counties allow.
2. City limits, spheres of influence, Sacramento County urban services boundary, LAFCo annexation areas.
3. Community plan, specific plan and master plan boundaries for every jurisdiction.

## B. Zoning and land use, per jurisdiction

4. Zoning districts and overlays (historic, design review, special planning areas, airport, flood, PUD) with the code citation per district.
5. General plan land-use designations.
6. Code sources: for each jurisdiction, where the current code lives (Municode, American Legal, Code Publishing, the jurisdiction's own PDF) and the official URL per title, so standards are captured by hand with a citation and never scraped from a publisher's site (see `LICENSING.md`).
7. Use tables per district (permitted, conditional, prohibited) and development standards (density or FAR, height, setbacks, coverage, parking, open space) with effective dates. Where this lives in code text rather than GIS, flag what needs a planner to capture and estimate the hours; we may license Zoneomics or Gridics code text to shorten it.
8. Housing element sites inventories, transit priority areas and AB 2097 or SB 79 distance brackets, density-bonus and SB 9 eligibility inputs.
9. Fee schedules (impact fees, plan check, HCP fees) as a table with jurisdiction, fee, basis, effective date, source URL.
10. Pending changes: general plan updates, code rewrites, specific plans in process, moratoria, as a list with links, per jurisdiction.

## C. Constraint layers (statewide sources, clipped to the pilot)

11. **Biology**: CNDDB (our license) occurrences; USFWS critical habitat; IPaC species list service; NWI wetlands; NHD streams; vernal-pool complex mapping (Holland); Swainson's hawk foraging habitat; oak woodland; elderberry if mapped.
12. **HCP and NCCP**: South Sacramento HCP, Natomas Basin HCP, Placer County Conservation Program boundaries, fee zones and land-cover types.
13. **Flood and waters**: FEMA NFHL; DWR 200-year floodplain and Urban Level of Flood Protection maps; Central Valley Flood Protection Board jurisdiction and levee easements; county floodplain overlays; CARI.
14. **Cultural**: historic districts and listed resources; a sensitivity proxy (water proximity, landform); AB 52 tribal territories as published by NAHC if available. CHRIS and Sacred Lands are request-only; we only need to flag.
15. **Agriculture**: Williamson Act contracts (DOC), FMMP important farmland, ag mitigation ordinance areas.
16. **Hazards**: Alquist-Priolo zones, CGS liquefaction and landslide zones, CAL FIRE fire hazard severity zones, airport land use compatibility plan zones for SMF, Mather, McClellan, Executive, Lincoln and Auburn, noise contours, EnviroStor and GeoTracker sites, dam inundation.
17. **Infrastructure**: sewer service areas (Regional San, SASD, Placer SMD), water purveyors, school districts, CFD and Mello-Roos districts, VMT screening maps and transit priority areas, major corridor plans.

## D. ArcGIS Business Analyst questions

18. Does our license include the GeoEnrichment REST API (so the app can pull trade-area variables per site), or the Business Analyst Web App only?
19. How many credits do we have, what does a GeoEnrichment call and a report cost us, and can we store the returned variables in our own layer?
20. Which report templates are on our license: Market Profile, Housing Profile, Retail MarketPlace Profile, Comparison, Site Suitability, Tapestry?
21. Drive-time trade areas (5, 10, 15 minutes) versus rings (1, 3, 5 miles): both available, and what the credit difference is.
22. Can Business Analyst's Retail MarketPlace supply-demand gap be pulled by NAICS group for a trade area through the API?

## E. Marketing and direct-mail questions

23. Can we build the direct-mail list from the parcel layer: owners of vacant or underutilized parcels by zone, size and owner type (individual, trust, LLC, public), with mailing addresses, exported per campaign? Any county restrictions on using assessor owner data for mail? (Check each county's terms of use; see `LICENSING.md`.)
24. Can Business Analyst or ArcGIS produce the "100 free screens" target list: parcels in zones where the housing element or recent rezones created new capacity?
25. A map graphic per county showing the pilot coverage for the landing page and the LinkedIn campaign.

## F. Delivery

26. Naming convention and a layer register (one table: layer, source, date, license, endpoint, refresh cadence, owner) so the app's provenance footnotes can read straight from it.
27. Hours estimate per jurisdiction for sections A to C, in the order: Sacramento County unincorporated, City of Sacramento, the other Sacramento cities, Placer County, the Placer cities.
