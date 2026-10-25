import argparse
import csv
import json
import math
import os
import sys

from .core import post_money_safe, rank


def _finite_float(s: str) -> float:
    """argparse type: a float that is not nan/inf, so limits and prices cannot be bypassed."""
    v = float(s)
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {s!r}")
    return v


def _run(argv=None):
    ap = argparse.ArgumentParser(prog="solo-combinator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rank", help="score and rank applications from a JSON list")
    r.add_argument("file")
    r.add_argument("--json", action="store_true")
    s = sub.add_parser("safe", help="post-money SAFE ownership math")
    s.add_argument("--invest", type=_finite_float, required=True)
    s.add_argument("--cap", type=_finite_float, required=True)
    s.add_argument("--round-pre", type=_finite_float)
    s.add_argument("--round-size", type=_finite_float)
    a = ap.parse_args(argv)

    if a.cmd == "safe":
        for k, v in post_money_safe(a.invest, a.cap, a.round_pre, a.round_size).items():
            print(f"{k:<26} {v:.2%}" if "ownership" in k else f"{k:<26} ${v:,.0f}")
        return 0

    with open(a.file, encoding="utf-8-sig") as fh:
        scores = rank(json.load(fh))
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
