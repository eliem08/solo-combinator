"""Get application data without typing it: form exports, Stripe payment exports and git history.

- `load_applications` reads JSON (a list of objects) or CSV, such as a Typeform, Google Forms or Tally export.
  Column names are matched loosely ("Monthly revenue ($)", "MoM growth %", "# of agents"), money may carry $ and
  thousands separators, and percentages are read as fractions (18% or 18 becomes 0.18).
- `stripe_metrics` reads a Stripe payments or invoices CSV export and returns MRR (the last complete month's
  successful revenue) and month-on-month growth (the average of the last three complete months).
- `git_ships_per_week` counts commit days per week in a repository over recent weeks.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import defaultdict
from datetime import date, datetime, timedelta

ALIASES = {
    "name": ("name", "founder", "company", "startup", "applicant", "founder_company", "your_name"),
    "mrr": ("mrr", "monthly_revenue", "monthly_recurring_revenue", "revenue_per_month", "revenue"),
    "mom_growth": ("mom_growth", "month_over_month_growth", "monthly_growth", "growth", "mom"),
    "agents": ("agents", "ai_agents", "number_of_agents", "of_agents", "agent_count"),
    "automated_share": ("automated_share", "automation", "share_automated", "automated", "of_work_automated"),
    "humans": ("humans", "team_size", "people", "employees", "headcount"),
    "monthly_burn": ("monthly_burn", "burn", "burn_rate", "monthly_costs", "monthly_spend"),
    "cash": ("cash", "cash_in_bank", "runway_cash", "bank_balance"),
    "ships_per_week": ("ships_per_week", "releases_per_week", "deploys_per_week", "ships"),
    "users": ("users", "active_users", "customers", "user_count"),
}
PERCENT = {"mom_growth", "automated_share"}
INTS = {"agents", "humans", "users"}


def _key(header: str) -> str:
    h = re.sub(r"\([^)]*\)", " ", header.lower()).replace("%", " ").replace("#", " ")
    return re.sub(r"[^a-z0-9]+", "_", h).strip("_")


def _field_for(header: str) -> str | None:
    k = _key(header)
    for field, names in ALIASES.items():
        if k in names:
            return field
    for field, names in ALIASES.items():  # "monthly_revenue_usd", "how_many_ai_agents_do_you_run"
        if any(n in k for n in names if len(n) > 4):
            return field
    return None


def _number(field: str, text: str, where: str):
    raw = text.strip()
    pct = raw.endswith("%")
    t = raw.replace("$", "").replace(",", "").replace("%", "").strip()
    if t == "":
        return None
    try:
        v = float(t)
    except ValueError:
        raise ValueError(f"{where}: {field} {text!r} is not a number") from None
    if field in PERCENT and (pct or abs(v) > 1):
        v /= 100
    return round(v) if field in INTS else v


def load_applications(path: str) -> list[dict]:
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
        if not isinstance(doc, list):
            raise ValueError(f"{path}: expected a JSON list of applications")
        return doc
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if not header:
            raise ValueError(f"{path}: empty file")
        fields = [_field_for(h) for h in header]
        if "name" not in fields:
            raise ValueError(f"{path}: no name/company column among {header}")
        apps = []
        for n, row in enumerate(reader, 2):
            if not any(c.strip() for c in row):
                continue
            app = {}
            for field, cell in zip(fields, row):
                if field is None or field in app:
                    continue
                if field == "name":
                    app["name"] = cell.strip()
                else:
                    v = _number(field, cell, f"{path} line {n}")
                    if v is not None:
                        app[field] = v
            apps.append(app)
    return apps


def _month(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _parse_when(text: str) -> date | None:
    """Stripe exports use ISO dates ("2026-11-02 14:03:11"); US dashboard exports may use 11/02/2026."""
    t = text.strip()
    try:
        return date.fromisoformat(t[:10])
    except ValueError:
        pass
    try:
        return datetime.strptime(t.split()[0] if t else t, "%m/%d/%Y").date()
    except ValueError:
        return None


def stripe_metrics(path: str, today: date | None = None) -> dict:
    """MRR and growth from a Stripe payments/invoices CSV export (columns like Created, Amount, Status)."""
    today = today or date.today()
    by_month: dict[str, float] = defaultdict(float)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = {_key(c): c for c in reader.fieldnames or []}
        when = next(
            (
                cols[k]
                for k in ("created_date", "created_utc", "created_date_utc", "created", "date", "paid_at")
                if k in cols
            ),
            None,
        )
        amount = next((cols[k] for k in ("converted_amount", "amount_paid", "amount", "total") if k in cols), None)
        refunded = next((cols[k] for k in ("amount_refunded", "converted_amount_refunded") if k in cols), None)
        status = next((cols[k] for k in ("status", "paid") if k in cols), None)
        if not when or not amount:
            raise ValueError(f"{path}: need a Created/date column and an Amount column; found {reader.fieldnames}")
        for n, row in enumerate(reader, 2):
            st = (row.get(status) or "").strip().lower() if status else "paid"
            if st not in ("paid", "succeeded", "true", "complete", "completed"):
                continue
            d = _parse_when(row.get(when) or "")
            if d is None:
                raise ValueError(f"{path} line {n}: date {row.get(when)!r} not understood")
            value = _number("amount", row.get(amount) or "0", f"{path} line {n}") or 0.0
            if refunded:
                value -= _number("amount", row.get(refunded) or "0", f"{path} line {n}") or 0.0
            by_month[_month(d)] += value
    first_of_this_month = today.replace(day=1)
    months = []
    d = first_of_this_month
    for _ in range(4):  # the last four complete months, newest first
        d = (d - timedelta(days=1)).replace(day=1)
        months.append(_month(d))
    revenue = [round(by_month.get(m, 0.0), 2) for m in months]
    growth = [(revenue[i] - revenue[i + 1]) / revenue[i + 1] for i in range(3) if revenue[i + 1] > 0]
    return {
        "mrr": revenue[0],
        "mom_growth": round(sum(growth) / len(growth), 4) if growth else 0.0,
        "months": dict(zip(months, revenue)),
    }


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=60)


def git_ships_per_week(repo: str, weeks: int = 8, today: date | None = None) -> float:
    """Days with at least one commit touching this folder, per week, over the last `weeks` weeks.

    Only commits under the given folder count, so a folder that merely sits inside some other repository is
    refused instead of being credited with that repository's history.
    """
    tracked = _git(repo, "ls-files", "--", ".")
    if tracked.returncode or not tracked.stdout.strip():
        detail = tracked.stderr.strip().splitlines()[0][:160] if tracked.stderr.strip() else "no tracked files here"
        raise ValueError(f"{repo}: not a git repository ({detail})")
    since = (today or date.today()) - timedelta(weeks=weeks)
    r = _git(repo, "log", f"--since={since.isoformat()}", "--format=%cs", "--", ".")
    if r.returncode:
        raise ValueError(f"{repo}: git log failed ({r.stderr.strip()[:160]})")
    days = {line.strip() for line in r.stdout.splitlines() if line.strip()}
    return round(len(days) / weeks, 2)
