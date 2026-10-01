"""Season windows govern the schedule (R3). Given a notice-to-proceed date, place every window-constrained
deliverable in its next open window; report slack to window close; flag windows closing inside a
horizon; group field tasks that could share a mobilization (R4)."""
import datetime
from dataclasses import dataclass
from typing import List, Optional

from .model import Project


@dataclass
class Placement:
    code: str
    name: str
    window: Optional[str]
    opens: Optional[datetime.date]
    closes: Optional[datetime.date]
    slack_days: Optional[int]       # days from NTP (or today) until the window closes
    flag: str = ""


def _md(year, md):
    m, d = (int(x) for x in md.split("-"))
    return datetime.date(year, m, d)


def next_window(window: dict, after: datetime.date):
    """The next (opens, closes) on or after `after`, handling windows that cross the year end."""
    for year in (after.year, after.year + 1, after.year + 2):
        opens = _md(year, window["opens"])
        closes = _md(year, window["closes"])
        if closes < opens:                       # crosses New Year
            closes = _md(year + 1, window["closes"])
        if closes >= after:
            return (max(opens, after), closes) if opens <= after else (opens, closes)
    raise ValueError("no window found")


def place(p: Project, ntp: datetime.date, horizon_days: int = 60) -> List[Placement]:
    out = []
    for d in p.deliverables:
        if not d.window:
            out.append(Placement(d.code, d.name, None, None, None, None, ""))
            continue
        w = p.canon.windows.get(d.window)
        if not w:
            out.append(Placement(d.code, d.name, d.window, None, None, None, f"unknown window {d.window} (R3)"))
            continue
        opens, closes = next_window(w, ntp)
        slack = (closes - ntp).days
        flag = ""
        if opens > ntp:
            flag = f"waits for {w['name']} opening {opens.isoformat()}"
        if slack <= horizon_days:
            flag = (flag + "; " if flag else "") + f"window closes in {slack} days"
        out.append(Placement(d.code, d.name, d.window, opens, closes, slack, flag))
    return out


def critical_window_sequence(placements: List[Placement]) -> List[Placement]:
    """The critical path is the latest window sequence, not a sum of durations."""
    dated = [x for x in placements if x.closes]
    return sorted(dated, key=lambda x: (x.closes, x.opens))


def mobilizations(p: Project, placements: List[Placement]) -> List[dict]:
    """Field tasks whose windows overlap can share a trip. Reports the groups; the field days saved is the
    number of tasks in a group minus one, per shared trip (a conservative count)."""
    field = [x for x in placements if x.opens and p.deliverable(x.code).field_work]
    groups = []
    for x in field:
        placed = False
        for g in groups:
            if x.opens <= g["closes"] and x.closes >= g["opens"]:
                g["codes"].append(x.code)
                g["opens"] = max(g["opens"], x.opens); g["closes"] = min(g["closes"], x.closes)
                placed = True; break
        if not placed:
            groups.append({"codes": [x.code], "opens": x.opens, "closes": x.closes})
    return [{"codes": g["codes"], "shared_window": (g["opens"].isoformat(), g["closes"].isoformat()),
             "trips_saved": len(g["codes"]) - 1} for g in groups if len(g["codes"]) > 1]
