"""The Scenarios board package: a two-page summary and a short deck built from the model's own figures (no new
numbers), printed to PDF by Chrome when it is on the machine. Client-safe: fees and ranges, never hours or rates."""
import os
from typing import Optional

from . import report as report_mod

CSS = """body{font-family:Arial,Helvetica,sans-serif;color:#1f2328;margin:0}.page{max-width:8.5in;margin:0 auto;padding:.6in .7in;page-break-after:always}
h1{color:#1B2A6B;font-size:22pt;margin:0 0 4px}h2{color:#1B2A6B;font-size:13pt;border-bottom:1px solid #d9dde3;padding-bottom:3px;margin:18px 0 6px}
.brand{color:#1B2A6B;font-weight:bold;letter-spacing:.04em;font-size:10pt}.sub{color:#5b6470;font-size:10pt}table{width:100%;border-collapse:collapse;font-size:9.5pt;margin:6px 0}
th{background:#1B2A6B;color:#fff;text-align:left;padding:5px 7px}td{padding:5px 7px;border-bottom:1px solid #d9dde3;vertical-align:top}
.stamp{margin:10px 0;padding:8px 12px;border-left:5px solid #F5A623;background:#f4f6f9;font-weight:bold;font-size:10pt}.stamp.un{border-left-color:#b3261e;background:#fdecea;color:#b3261e}
.slide{width:10in;height:5.6in;padding:.5in .7in;box-sizing:border-box;page-break-after:always;border-top:6px solid #F5A623}.slide h1{font-size:26pt}.slide p,.slide li{font-size:14pt;line-height:1.4}
.big{font-size:30pt;color:#1B2A6B;font-weight:bold}.note{font-size:9pt;color:#5b6470;font-style:italic}@media print{@page{size:letter;margin:.5in}}"""


def _money(v):
    return f"${v:,.0f}" if v else "—"


def summary_html(rep: dict, scen: dict, md: dict) -> str:
    m = rep["meta"]
    import html as _h
    e = lambda x: _h.escape(str(x if x is not None else ""))
    dec = {it["label"]: it["cell"]["text"] for it in rep["sections"][0]["blocks"][0]["items"]}
    rows = "".join(f"<tr><td>{e(x['name'])}</td><td>{(str(x['yield'][0]) + ' to ' + str(x['yield'][1]) + ' ' + x['unit']) if x['yield'] else 'not yet on file'}</td><td>{e('; '.join(x['approvals'][:4]))}</td>"
                   f"<td>{x['duration_months'][0]} to {x['duration_months'][1]} months</td><td>{(_money(x['cost']['low']) + ' to ' + _money(x['cost']['high'])) if x['cost']['low'] else 'to price'}</td><td>{e(x['assumptions'][0] if x['assumptions'] else '')}</td></tr>" for x in scen["programs"])
    paths = "".join(f"<tr><td>{e(x['id'])}. {e(x['name'])}</td><td>{e(x['status'])}{(': ' + e(x.get('why_ruled_out', ''))) if x.get('why_ruled_out') else ''}</td><td>{e('; '.join(x['confirms'][:2]))}</td></tr>" for x in md["paths"])
    plan = "".join(f"<tr><td>{s_['step']}</td><td>{e(s_['code'])} {e(s_['name'])}</td><td>{('month ' + str(s_['month'])) if s_.get('month') is not None else ''}</td><td>{_money(s_['fee'])}</td></tr>" for s_ in md["plan"][:6])
    stamp_cls = "" if m["reviewed"] else " un"
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Board summary — {e(m['name'])}</title><style>{CSS}</style></head><body>
<div class="page"><div class="brand">COX PLANNING SOLUTIONS</div><h1>Board summary: {e(m['name'])}</h1>
<div class="sub">{e(m['address'])} · APN {e(m['apns'])} · {e(m['acres'])} acres · {e(m['jurisdiction'])} · {e(m['development_type'])} · Entitlement Roadmap, Scenarios level · {e(m['date'])}</div>
<div class="stamp{stamp_cls}">{e(m['stamp'])}</div>
<h2>The decision in three lines</h2>
<p><b>What to build.</b> {e(dec.get('WHAT TO BUILD', ''))}</p><p><b>How it gets approved.</b> {e(dec.get('HOW IT GETS APPROVED', ''))}</p><p><b>What it takes.</b> {e(dec.get('WHAT IT TAKES', ''))}</p>
<h2>Scenarios estimated on the constraints map</h2>
<table><thead><tr><th>Scenario</th><th>Yield</th><th>Approvals</th><th>Duration</th><th>Cost to entitlement</th><th>Rests on</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">{e(scen['note'])} Gross {scen['gross_acres']:g} acres; exclusions: {e('; '.join(x['name'] for x in scen['exclusions']) or 'none on the record')}. Parameters are planning ranges ({e(scen['parameters_confidence'])}).</p>
<h2>Cultural records search</h2><p>{e(scen['records_search']['state'])}: {e(scen['records_search']['reason'])}. <span class="note">{e(scen['records_search']['note'])}</span></p>
</div>
<div class="page"><h2>Candidate entitlement paths</h2><table><thead><tr><th>Path</th><th>Status</th><th>What confirms it</th></tr></thead><tbody>{paths}</tbody></table>
<h2>Verification plan: the first steps</h2><table><thead><tr><th></th><th>Deliverable</th><th>When</th><th>Cox fee</th></tr></thead><tbody>{plan}</tbody></table>
<p><b>Step 1b scope and price:</b> {e(md['step1b']['name'])}{(', ' + _money(md['step1b']['fee']) + ' (' + e(md['step1b']['confidence']) + ')') if md['step1b'].get('fee') else ', not yet priced'}.</p>
<h2>What happens next</h2><ol>{''.join('<li>' + e(n) + '</li>' for n in rep['next_steps'])}</ol>
<p class="note">{e(m['standing_header'])} {e(m['terms'])}</p></div></body></html>"""


def deck_html(rep: dict, scen: dict, md: dict) -> str:
    import html as _h
    e = lambda x: _h.escape(str(x if x is not None else ""))
    m = rep["meta"]
    dec = {it["label"]: it["cell"]["text"] for it in rep["sections"][0]["blocks"][0]["items"]}
    slides = [f"<div class='slide'><div class='brand'>COX PLANNING SOLUTIONS</div><h1>{e(m['name'])}</h1><p class='sub'>Entitlement Roadmap, Scenarios level · {e(m['jurisdiction'])} · {e(m['acres'])} acres · {e(m['date'])}</p><p>{e(dec.get('WHAT TO BUILD', ''))}</p></div>",
              f"<div class='slide'><h1>How it gets approved</h1><p>{e(dec.get('HOW IT GETS APPROVED', ''))}</p><p class='big'>{e(m['scale']['effective'].title())}</p><p class='note'>scale test: {e(m['scale']['recommended'])}{(' · planner: ' + e(m['scale']['override'])) if m['scale'].get('override') else ''}</p></div>",
              f"<div class='slide'><h1>What it takes</h1><p>{e(dec.get('WHAT IT TAKES', ''))}</p></div>"]
    for x in scen["programs"]:
        y = f"{x['yield'][0]:,} to {x['yield'][1]:,} {x['unit']}" if x["yield"] else "not yet on file"
        slides.append(f"<div class='slide'><h1>{e(x['name'])}</h1><p class='big'>{e(y)}</p><p>{e('; '.join(x['approvals'][:4]))}</p><p>{x['duration_months'][0]} to {x['duration_months'][1]} months · " + ((_money(x['cost']['low']) + " to " + _money(x['cost']['high'])) if x["cost"]["low"] else "to price") + f"</p><p class='note'>{e('; '.join(x['assumptions'][:3]))}</p></div>")
    slides.append(f"<div class='slide'><h1>What confirms the map</h1><ul>{''.join('<li>' + e(s_['code']) + ' ' + e(s_['name']) + (' · ' + _money(s_['fee']) if s_['fee'] else '') + '</li>' for s_ in md['plan'][:5])}</ul><p>Step 1b: {e(md['step1b']['name'])}{(', ' + _money(md['step1b']['fee'])) if md['step1b'].get('fee') else ''}</p></div>")
    slides.append(f"<div class='slide'><h1>What happens next</h1><ol>{''.join('<li>' + e(n) + '</li>' for n in rep['next_steps'])}</ol></div>")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>Deck — {e(m['name'])}</title><style>{CSS}@media print{{@page{{size:10in 5.6in;margin:0}}}}</style></head><body>{''.join(slides)}</body></html>"


def write(p, rep: dict, scen: dict, md: dict, out_dir: str = "out", pdf: bool = False) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    s_path = os.path.join(out_dir, f"{p.key}-board-summary.html"); d_path = os.path.join(out_dir, f"{p.key}-board-deck.html")
    open(s_path, "w").write(summary_html(rep, scen, md)); open(d_path, "w").write(deck_html(rep, scen, md))
    res = {"summary": s_path, "deck": d_path, "summary_pdf": None, "deck_pdf": None}
    if pdf:
        for k, hp in (("summary_pdf", s_path), ("deck_pdf", d_path)):
            pp = hp[:-5] + ".pdf"
            res[k] = pp if report_mod.render_pdf(hp, pp) else None
    return res
