import argparse
import csv
import json
import math
import os
import sys

from .core import post_money_safe, rank
from .intake import git_ships_per_week, load_applications, stripe_metrics


def _finite_float(s: str) -> float:
    """argparse type: a float that is not nan/inf, so limits and prices cannot be bypassed."""
    v = float(s)
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {s!r}")
    return v


def build_parser():
    ap = argparse.ArgumentParser(prog="solo-combinator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rank", help="score and rank applications from JSON or a form export (CSV)")
    r.add_argument("file", help="a JSON list, or a CSV export from Typeform, Google Forms, Tally and the like")
    r.add_argument("--json", action="store_true")
    r.add_argument(
        "--weights",
        default=None,
        help='custom scoring weights as JSON, e.g. \'{"traction": 0.4, "growth": 0.1}\' '
        "(missing dimensions keep their defaults; weights are normalized to sum to 1)",
    )
    m = sub.add_parser("metrics", help="measure an applicant instead of asking: Stripe revenue or git shipping")
    m.add_argument("source", choices=("stripe", "git"))
    m.add_argument("path", help="a Stripe payments/invoices CSV export, or a git repository")
    m.add_argument("--weeks", type=int, default=8, help="git: weeks of history to count")
    s = sub.add_parser("safe", help="post-money SAFE ownership math")
    s.add_argument("--invest", type=_finite_float, required=True)
    s.add_argument("--cap", type=_finite_float, required=True)
    s.add_argument("--round-pre", type=_finite_float)
    s.add_argument("--round-size", type=_finite_float)
    return ap


def _run(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)

    if a.cmd == "safe":
        for k, v in post_money_safe(a.invest, a.cap, a.round_pre, a.round_size).items():
            print(f"{k:<26} {v:.2%}" if "ownership" in k else f"{k:<26} ${v:,.0f}")
        return 0

    if a.cmd == "metrics":
        if a.source == "stripe":
            m = stripe_metrics(a.path)
            for month, revenue in m["months"].items():
                print(f"  {month}  ${revenue:>12,.2f}")
            print(f"mrr {m['mrr']:.2f}  mom_growth {m['mom_growth']:.4f}   (paste into the application)")
        else:
            if not 1 <= a.weeks <= 104:
                raise ValueError("--weeks must be between 1 and 104")
            print(f"ships_per_week {git_ships_per_week(a.path, a.weeks)}   (days with commits, last {a.weeks} weeks)")
        return 0

    weights = None
    if getattr(a, "weights", None):
        try:
            weights = json.loads(a.weights)
        except json.JSONDecodeError as e:
            raise ValueError(f"--weights must be valid JSON: {e}") from e
    scores = rank(load_applications(a.file), weights)
    if a.json:
        print(json.dumps([s.__dict__ for s in scores], indent=2))
        return 0
    for s in scores:
        print(f"{s.total:5.1f}  {s.decision.upper():<9} {s.name}")
        print("       " + "  ".join(f"{k}={v:.0f}" for k, v in s.parts.items()))
        for f in s.flags:
            print(f"       ! {f}")
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
