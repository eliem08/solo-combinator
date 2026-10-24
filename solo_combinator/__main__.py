import argparse
import json
import sys

from .core import post_money_safe, rank


def main(argv=None):
    ap = argparse.ArgumentParser(prog="solo-combinator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rank", help="score and rank applications from a JSON list")
    r.add_argument("file")
    r.add_argument("--json", action="store_true")
    s = sub.add_parser("safe", help="post-money SAFE ownership math")
    s.add_argument("--invest", type=float, required=True)
    s.add_argument("--cap", type=float, required=True)
    s.add_argument("--round-pre", type=float)
    s.add_argument("--round-size", type=float)
    a = ap.parse_args(argv)

    if a.cmd == "safe":
        for k, v in post_money_safe(a.invest, a.cap, a.round_pre, a.round_size).items():
            print(f"{k:<26} {v:.2%}" if "ownership" in k else f"{k:<26} ${v:,.0f}")
        return 0

    with open(a.file, encoding="utf-8") as fh:
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


if __name__ == "__main__":
    sys.exit(main())
