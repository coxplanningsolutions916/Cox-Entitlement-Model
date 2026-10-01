"""CLI.  python -m engine fee riego-rd | program riego-rd | schedule riego-rd --ntp 2026-10-15 | check riego-rd [--draft file]"""
import argparse
import datetime
import sys

from . import fee as fee_mod, program as program_mod, rules, schedule
from .model import Project


def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("fee", "program", "schedule", "check"):
        s = sub.add_parser(c); s.add_argument("project")
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
