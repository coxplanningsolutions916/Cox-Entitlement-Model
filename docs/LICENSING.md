# What we can put in a deliverable: regulations, data and licensing

Draft 1 October 2026. Practical guidance, not legal advice; the two items marked **confirm** should go to counsel or the vendor before launch. The rule that covers most of it: **the law and the facts are free to state and cite; a publisher's formatted compilation, a vendor's raw dataset, and bulk copies are not ours to redistribute.** The app stores facts with citations, quotes sparingly, and links to the official source.

## Municipal and county codes (Municode, American Legal, Code Publishing, Quality Code)

- The ordinance text itself is an edict of government. Under the government-edicts doctrine (Supreme Court, *Georgia v. Public.Resource.Org*, 2020, which reached even the state's official annotations) the law cannot be owned by anyone, so quoting a zoning section, restating a use table, or tabulating development standards in a client report is fine, with the section cited.
- What is restricted is the publisher's platform: Municode (CivicPlus), American Legal Publishing and Code Publishing terms prohibit scraping, bulk downloading and republishing their compilation. So: no automated harvesting of a publisher's site into our database, and no reproducing their page formatting or their editorial notes.
- Practice for the app: capture standards into our own tables (district, standard, value, section, effective date, official URL) by hand or from the jurisdiction's own PDF; quote at most a short passage per point, in quotation marks, with the citation; link to the official code page; never ship a code chapter as an appendix. Where a jurisdiction publishes its code as a PDF or on its own site (many do), that copy is the one to work from. Public Records Act requests get any ordinance the website lacks.
- Zoneomics or Gridics code text, if licensed, comes with its own redistribution terms; those would govern what the app may display versus what it may only use internally. **Confirm** before signing.

## Public GIS and government data

- **Federal** (FEMA NFHL, USFWS critical habitat and IPaC, NWI, NHD, EPA, Census, HUD): public domain. Use, store, redistribute, with the source and date on the figure.
- **State** (DWR flood maps, CGS hazard zones, CAL FIRE FHSZ, Department of Conservation Williamson Act and FMMP, EnviroStor, GeoTracker, CEQAnet, Department of Finance): open data, generally free to use with attribution; a few layers carry a disclaimer the deliverable should carry forward ("mapped, not field-verified").
- **County and city GIS** (parcels, zoning, general plan, overlays, service areas): published through open-data portals with a terms-of-use page. Sacramento County and Placer County both allow use with attribution and a disclaimer; the app's layer register records the terms per layer. Assessor **owner names and mailing addresses** are public record, but some counties restrict commercial reuse of the full roll, and the direct-mail use case should be checked against each county's terms before the first campaign. **Confirm** per county.
- **HCP, specific plan, housing element and fee schedule documents**: public agency documents; cite and summarize freely.

## Licensed data

- **CNDDB** (our subscription): the subscriber agreement allows the data to be used in reports and maps delivered to clients with the CDFW citation and the date of the data release, and prohibits redistributing the dataset itself or giving third parties access to it. So: occurrence summaries, buffered presence maps and species lists in the deliverable are fine; the raw records, the full export, and any API that hands records to a client are not. The app queries CNDDB server-side and shows derived results only.
- **ArcGIS Business Analyst and Esri demographics**: Esri's terms allow reports, infographics and derived figures to be delivered to clients, and prohibit redistributing the underlying data or building a product that substitutes for Esri's. So: the market section's figures and the trade-area map are fine with the Esri attribution; storing the enriched variables for our own analysis is fine; exposing them as a data feed is not.
- **Google Earth and Google Maps imagery**: Google's geo guidelines allow imagery in reports and presentations, including commercial ones, with the Google attribution left in place and no alteration beyond annotation; a Maps Platform key is needed for anything served live in the app. Esri World Imagery is available through our ArcGIS license as an alternative with simpler terms.
- **CHRIS records and the Sacred Lands File**: request-only, confidential; results go to the client under the information center's conditions, never into the app's database.

## How the app enforces it

1. Every source in the layer register carries a license class: public domain, open with attribution, licensed (report-only), request-only. The report generator prints the attribution the class requires and refuses to export raw records from a report-only source.
2. Quotations are limited by the generator to a short passage per citation; standards appear as our tables with section numbers.
3. The PDF carries a standard page: sources and dates, the mapped-not-verified disclaimer, and the CDFW and Esri attributions.
4. Nothing is harvested from a code publisher's site by script; jurisdiction code capture is a planner's task with the official URL recorded.
