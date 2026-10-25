<!-- sell-kit:start -->
# Solo Combinator

[![CI](https://github.com/eliem08/solo-combinator/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/solo-combinator/actions/workflows/ci.yml)

> **Score and rank one-person companies by the leverage that actually predicts returns.**

**Who it's for:** Accelerators, angel syndicates and micro-VCs backing solo founders.

**The problem:** Solo founders running agent teams don't fit classic headcount-based screening, so good deals get missed and bad ones get through.

**What you get:** Leverage-weighted scoring of traction, growth, automation and efficiency, with ranked cohorts, red flags and post-money SAFE math.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install solo_combinator-0.1.0-py3-none-any.whl
solo-combinator rank examples/applications.json
solo-combinator safe --invest 125000 --cap 2000000 --round-pre 8000000 --round-size 2000000
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
solo-combinator-web --port 8000          # then open http://127.0.0.1:8000
solo-combinator-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t solo-combinator . && docker run -p 8000:8000 -e API_KEYS=sk_... -v solo-combinator-data:/data solo-combinator
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `solo-combinator-web usage` prints calls per key for billing.

Endpoints: `POST /api/rank`, `POST /api/safe`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Angel** | $49 per month | Up to 100 applications a month; Scoring and ranking; SAFE calculator |
| **Fund** | $299 per month | Unlimited applications; Custom scoring weights; Cohort exports |
| **Program** | $1,500 per cohort | White-label application review; Partner-ready ranking memo; Onboarding call |

To start a trial or buy a plan, email **sales@YOUR-DOMAIN.com**.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

- **Application scoring** across 5 weighted dimensions (traction, growth,
  agent leverage, capital efficiency, founder velocity), each 0–100, with
  red-flag detection (e.g. runway < 3 months, zero revenue + no users)
- **Batch ranking** from a JSON file of applications → accept / interview / pass
- **Standard deal**: post-money SAFE calculator — ownership at conversion,
  dilution through a priced round

## Quickstart

```bash
pip install -e .
solo-combinator rank examples/applications.json
solo-combinator safe --invest 125000 --cap 2000000 --round-pre 8000000 --round-size 2000000
```

## Scoring

| dimension | weight | signal |
|---|---|---|
| traction | 25% | MRR (log-scaled, $50k MRR = 100) |
| growth | 25% | MoM growth (20% MoM = 100) |
| agent leverage | 25% | agents in production, % of ops automated, revenue per human |
| capital efficiency | 15% | burn multiple, runway |
| velocity | 10% | ships per week |

## Roadmap

- Live verification via Stripe / GitHub / agent-tracer integrations
- Cohort dashboard and demo-day investor portal
- Shared agent infra credits (model, compute, tooling perks)

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
solo_combinator/core.py       domain logic (pure, importable, fully tested)
solo_combinator/__main__.py   CLI (`solo-combinator ...` / `python -m solo_combinator ...`)
tests/                unit tests + generated CLI smoke tests
examples/             sample inputs used by the docs and smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #3).
