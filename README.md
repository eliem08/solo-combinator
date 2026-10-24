# solo-combinator

> **Y Combinator for one-person companies** — back solo founders running a team of agents.

The next wave of companies has one human and twenty agents. Traditional
accelerators screen for co-founder teams and headcount plans; this one
screens for **leverage**: revenue per human, hours automated, and how much
of the business actually runs on agents.

This repo is the fund's operating system: application scoring, batch
ranking and SAFE math.

## What the MVP does

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
