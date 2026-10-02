"""CLI.  python -m engine fee riego-rd | fees riego-rd | program riego-rd | schedule riego-rd --ntp 2026-10-15 | check riego-rd [--draft file]
        python -m engine report riego-rd [--rung screening|roadmap|plus] [--out out] [--pdf] [--internal] [--ntp DATE]
        python -m engine publish riego-rd [--rung ...] [--dash ~/code/cox-dashboard]   -> roadmaps/<key>.json for the client dashboard"""
import argparse
import datetime
import sys

from . import fee as fee_mod, fees as fees_mod, program as program_mod, publish as publish_mod, report as report_mod, rules, schedule
from .model import Project


def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("fee", "fees", "program", "schedule", "check", "report", "publish"):
        s = sub.add_parser(c); s.add_argument("project")
        if c == "publish":
            s.add_argument("--rung", default="screening", choices=sorted(report_mod.RUNGS)); s.add_argument("--dash", default=""); s.add_argument("--ntp", default="")
        if c == "report":
            s.add_argument("--rung", default="screening", choices=sorted(report_mod.RUNGS)); s.add_argument("--out", default="out")
            s.add_argument("--pdf", action="store_true"); s.add_argument("--internal", action="store_true"); s.add_argument("--ntp", default="")
        if c == "schedule":
            s.add_argument("--ntp", default=datetime.date.today().isoformat()); s.add_argument("--horizon", type=int, default=60)
        if c == "check":
            s.add_argument("--draft", default="")
    a = ap.parse_args(argv)
    p = Project.load(a.project)
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
        if a.pdf: print(res["pdf"] or "PDF not produced: Chrome not found (set CHROME=/path/to/chrome)")
    elif a.cmd == "publish":
        ntp = datetime.date.fromisoformat(a.ntp) if a.ntp else None
        print(publish_mod.write(p, a.rung, a.dash or None, ntp=ntp))
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
