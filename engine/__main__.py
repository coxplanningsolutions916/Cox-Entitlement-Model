"""CLI.  python -m engine fee riego-rd | fees riego-rd | program riego-rd | schedule riego-rd --ntp 2026-10-15 | check riego-rd [--draft file]
        python -m engine report riego-rd [--rung screening|roadmap|plus] [--out out] [--pdf] [--internal] [--ntp DATE]
        python -m engine publish riego-rd [--rung ...] [--dash ~/code/cox-dashboard]   -> roadmaps/<key>.json for the client dashboard
        python -m engine scale riego-rd | review riego-rd --reviewer "Chris Cox" --ok 1,2,3,4,6,7,8,9,10 --note 5="..." [--rung roadmap --reason "..."]"""
import argparse
import datetime
import sys

from . import casebook as casebook_mod, fee as fee_mod, fees as fees_mod, hooks as hooks_mod, intake as intake_mod, mapdraft, program as program_mod, scenarios as scenarios_mod, publish as publish_mod, report as report_mod, review as review_mod, rules, schedule
from .model import Project


def _run_hook(key, what, live):
    if what == "order":
        return hooks_mod.automator_order(key, live)
    if what == "review-task":
        return hooks_mod.productive_review_task(key, live)
    if what == "qbo":
        return hooks_mod.qbo_request(key)
    if what == "delivered":
        return hooks_mod.automator_delivered(key, live)
    if what == "email":
        return hooks_mod.delivery_email(key)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("fee", "fees", "program", "schedule", "check", "report", "publish", "scale", "review"):
        s = sub.add_parser(c); s.add_argument("project")
        if c == "review":
            s.add_argument("--reviewer", required=True); s.add_argument("--date", default="")
            s.add_argument("--ok", default="", help="checklist items passed, e.g. 1,2,3,4,6,7,8,9,10")
            s.add_argument("--note", action="append", default=[], help='item note, e.g. --note 5="CNDDB hits are plausible; confirm elderberry"')
            s.add_argument("--summary", default=""); s.add_argument("--rung", default="", choices=["", "screening", "roadmap", "plus"]); s.add_argument("--reason", default="")
            s.add_argument("--fix", action="append", default=[], help='a correction to the draft: "section|field|from|to|reason" (goes to the correction register)')
        if c == "publish":
            s.add_argument("--rung", default="screening", choices=sorted(report_mod.RUNGS)); s.add_argument("--dash", default=""); s.add_argument("--ntp", default="")
        if c == "report":
            s.add_argument("--rung", default="screening", choices=sorted(report_mod.RUNGS)); s.add_argument("--out", default="out")
            s.add_argument("--pdf", action="store_true"); s.add_argument("--internal", action="store_true"); s.add_argument("--ntp", default="")
        if c == "schedule":
            s.add_argument("--ntp", default=datetime.date.today().isoformat()); s.add_argument("--horizon", type=int, default=60)
        if c == "check":
            s.add_argument("--draft", default="")
    s = sub.add_parser("intake", help="scaffold a project from an order (flags or --from order.json)")
    s.add_argument("--from", dest="from_json", default=""); s.add_argument("--address", default=""); s.add_argument("--apn", action="append", default=[])
    s.add_argument("--jurisdiction", default=""); s.add_argument("--intent", default=""); s.add_argument("--use", default="residential"); s.add_argument("--acres", type=float, default=None)
    s.add_argument("--name", default=""); s.add_argument("--email", default=""); s.add_argument("--company", default=""); s.add_argument("--role", default=""); s.add_argument("--phone", default="")
    s.add_argument("--source", default=""); s.add_argument("--utm", default=""); s.add_argument("--doc", action="append", default=[], help="label=url")
    s.add_argument("--level", default="screen", choices=["screen", "map", "scenarios"]); s.add_argument("--free", action="store_true"); s.add_argument("--type", default="")
    s.add_argument("--scale", default="", help="parcels=1,resources=unknown,discretionary=no,board=no")
    s.add_argument("--hooks", action="store_true", help="also run the order hooks (dry run unless --live)"); s.add_argument("--live", action="store_true")
    s = sub.add_parser("map", help="the Map-level drafts: constraints manifest (exported), candidate paths, HBU, verification plan"); s.add_argument("project"); s.add_argument("--out", default="out"); s.add_argument("--ntp", default="")
    s = sub.add_parser("scenarios", help="the Scenarios-level estimates on the constraints map"); s.add_argument("project"); s.add_argument("--ntp", default="")
    s = sub.add_parser("hooks", help="run an order's hooks: order | review-task | qbo | delivered | email"); s.add_argument("project"); s.add_argument("what", choices=["order", "review-task", "qbo", "delivered", "email", "all"]); s.add_argument("--live", action="store_true")
    s = sub.add_parser("case", help="validate and print a casebook record"); s.add_argument("case_key")
    s = sub.add_parser("publish-all", help="republish every project and the metrics to the dashboard"); s.add_argument("--dash", default="")
    a = ap.parse_args(argv)
    if a.cmd == "intake":
        import json as _json
        if a.from_json:
            order = _json.load(open(a.from_json))
        else:
            scale = dict(kv.split("=", 1) for kv in a.scale.split(",") if "=" in kv)
            order = {"address": a.address, "apns": a.apn, "jurisdiction": a.jurisdiction, "intent": a.intent, "use": a.use, "acres": a.acres,
                     "name": a.name, "email": a.email, "company": a.company, "role": a.role, "phone": a.phone, "source": a.source, "utm": a.utm,
                     "documents": [{"label": d.split("=", 1)[0], "url": d.split("=", 1)[1] if "=" in d else ""} for d in a.doc],
                     "level": a.level, "free": a.free, "development_type": a.type or None, "scale": scale}
        r = intake_mod.scaffold(order)
        print(f"project {r['key']} scaffolded: {r['level']} ({'free' if r['free'] else '$' + format(r['price'], ',')}), type {r['development_type']}{' (inferred)' if r['type_inferred'] else ''}, pilot {'yes' if r['pilot'] else 'NO'}, delivery due {r['delivery_due']}")
        if r.get("free_slot") and r["free_slot"].get("paced"):
            print(f"  free Screen paced into {r['free_slot']['month']} ({r['free_slot']['used_month']} of {r['free_slot']['pace']} that month)")
        print(f"  next: python -m engine report {r['key']} --rung {r['level']} --pdf · python -m engine hooks {r['key']} all{' --live' if a.live else ''}")
        if a.hooks:
            for what in ("order", "review-task", "qbo"):
                print(f"  hook {what}: {_run_hook(r['key'], what, a.live)}")
        return 0
    if a.cmd == "case":
        print(casebook_mod.render_text(casebook_mod.load(a.case_key)))
        return 0
    if a.cmd == "publish-all":
        for x in publish_mod.publish_all(a.dash or None): print(x)
        return 0
    p = Project.load(a.project)
    if a.cmd == "scenarios":
        from .report import load_screen
        ntp = datetime.date.fromisoformat(a.ntp) if a.ntp else datetime.date.today()
        print(scenarios_mod.render_text(p, scenarios_mod.build(p, load_screen(p), fee_mod.build(p), program_mod.build(p), ntp)))
        return 0
    if a.cmd == "map":
        from .report import load_screen
        ntp = datetime.date.fromisoformat(a.ntp) if a.ntp else datetime.date.today()
        m = mapdraft.build(p, load_screen(p), fee_mod.build(p), ntp)
        print(mapdraft.render_text(p, m))
        files = mapdraft.export_manifest(p, m["layers"], a.out)
        print(f"\nmanifest: {files['csv']}  {files['json']}")
        return 0
    if a.cmd == "hooks":
        for what in (["order", "review-task", "qbo", "email"] if a.what == "all" else [a.what]):
            print(f"{what}: {_run_hook(a.project, what, a.live)}")
        return 0
    if a.cmd == "fee":
        fb = fee_mod.build(p)
        print(fee_mod.internal_table(fb, p))
        for n in fb.notes: print(n)
        ms = p.meta.get("task_order_1", {}).get("payment_milestones")
        if ms:
            print("\nPayment schedule (on the rounded total):")
            for m in fee_mod.payment_schedule(fb.total, ms): print(f"  {m['milestone']:38} {m['share']:>5.0%}  {m['amount']:>10,.0f}  {m['trigger']}")
    elif a.cmd == "fees":
        print(fees_mod.render_text(p, fees_mod.build(p)))
    elif a.cmd == "program":
        print(program_mod.render_text(p, program_mod.build(p)))
    elif a.cmd == "schedule":
        ntp = datetime.date.fromisoformat(a.ntp)
        pl = schedule.place(p, ntp, a.horizon)
        print(f"Notice to proceed {ntp.isoformat()}; windows (R3):")
        for x in schedule.critical_window_sequence(pl):
            print(f"  {x.code:5} {x.name[:48]:48} {x.opens} → {x.closes}  slack {x.slack_days:>4}d  {x.flag}")
        for x in pl:
            if not x.window: print(f"  {x.code:5} {x.name[:48]:48} (not window-constrained)")
        print("Shared mobilizations (R4):")
        for g in schedule.mobilizations(p, pl): print(f"  {', '.join(g['codes'])}  window {g['shared_window'][0]} → {g['shared_window'][1]}  trips saved {g['trips_saved']}")
    elif a.cmd == "report":
        ntp = datetime.date.fromisoformat(a.ntp) if a.ntp else None
        res = report_mod.write(p, a.rung, a.out, a.pdf, a.internal, ntp)
        print(f"{res['html']}  ({res['sources']} sources cited, {res['facts_needed']} facts needed)")
        if res.get("board"): print(f"board package: {res['board']['summary']}  {res['board']['deck']}" + (f"  (PDFs: {res['board']['summary_pdf']}, {res['board']['deck_pdf']})" if res['board'].get('summary_pdf') else ""))
        if a.pdf: print(res["pdf"] or "PDF not produced: Chrome not found (set CHROME=/path/to/chrome)")
    elif a.cmd == "publish":
        ntp = datetime.date.fromisoformat(a.ntp) if a.ntp else None
        print(publish_mod.write(p, a.rung, a.dash or None, ntp=ntp))
    elif a.cmd == "scale":
        st = review_mod.scale_test(p)
        print(f"Scale test for {p.meta.get('name')}: {st['recommended'].upper()}" + (f" (planner override: {st['override']} — {st['override_reason']})" if st["override"] else ""))
        for t in st["triggers"]: print(f"  trigger: {t}")
        print(f"  {st['note']}")
    elif a.cmd == "review":
        items = {}
        for n in [x for x in a.ok.split(",") if x.strip()]:
            items[int(n)] = "ok"
        for note in a.note:
            k, _, v = note.partition("=")
            items[int(k)] = v.strip().strip('"')
        missing = [n for n in range(1, 11) if n not in items]
        if missing:
            print(f"review incomplete: items {missing} have no result (ok or a note); the stamp stays red until all ten are answered")
        block = review_mod.record_review(p, a.reviewer, items, a.date or None, a.rung or None, a.reason or None, a.summary)
        if a.fix:
            path = review_mod.record_corrections(p, [review_mod.parse_fix(x) for x in a.fix], a.reviewer, a.date or None)
            print(f"{len(a.fix)} correction(s) logged in {path}")
        it = intake_mod.load_intake(p.key)
        if it:
            it["reviewer"] = a.reviewer; intake_mod.save_intake(p.key, it)
        print(f"review recorded in projects/{p.key}/screen.yaml: {block['reviewer']} {block['date']}, {sum(1 for v in block['items'].values() if v == 'ok')} ok, {len(block['items']) - sum(1 for v in block['items'].values() if v == 'ok')} with notes" + (f", rung override {block['rung_override']}" if block.get("rung_override") else ""))
    elif a.cmd == "check":
        draft = open(a.draft).read() if a.draft else ""
        v = rules.check(p, fee_mod.build(p), draft)
        if not v:
            print("all rules hold"); return 0
        for x in v: print(x)
        return 1 if any(x.hard for x in v) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
