"""Application scoring and SAFE math for a solo-founder accelerator."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = ["WEIGHTS", "Application", "Score", "score_application", "rank", "post_money_safe"]

WEIGHTS = {"traction": 0.25, "growth": 0.25, "leverage": 0.25, "efficiency": 0.15, "velocity": 0.10}


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


@dataclass
class Application:
    name: str
    mrr: float = 0
    mom_growth: float = 0
    agents: int = 0
    automated_share: float = 0
    humans: int = 1
    monthly_burn: float = 0
    cash: float = 0
    ships_per_week: float = 0
    users: int | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Application:
        if not isinstance(d, dict):
            raise ValueError(f"each application must be an object, got {d!r}")
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        app = cls(**known)
        app.validate()
        return app

    def validate(self) -> None:
        """Reject values that would crash scoring or game it (negative burn reads as perfect efficiency)."""
        if not (isinstance(self.name, str) and self.name.strip()):
            raise ValueError(f"application name must be a non-empty string, got {self.name!r}")
        for k in ("mrr", "agents", "humans", "monthly_burn", "cash", "ships_per_week"):
            v = getattr(self, k)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise ValueError(f"{self.name}: {k} must be a finite number >= 0, got {v!r}")
        if not (isinstance(self.mom_growth, (int, float)) and math.isfinite(self.mom_growth)):
            raise ValueError(f"{self.name}: mom_growth must be a finite number")
        if not (isinstance(self.automated_share, (int, float)) and 0 <= self.automated_share <= 1):
            raise ValueError(f"{self.name}: automated_share must be between 0 and 1")
        if self.users is not None and (
            not isinstance(self.users, (int, float)) or not math.isfinite(self.users) or self.users < 0
        ):
            raise ValueError(f"{self.name}: users must be a finite number >= 0, got {self.users!r}")


@dataclass
class Score:
    name: str
    total: float
    parts: dict
    flags: list = field(default_factory=list)
    decision: str = ""


def _normalize_weights(weights: dict | None) -> dict:
    """Validate custom weights and normalize them to sum to 1.

    Missing dimensions fall back to the default weight for that
    dimension; unknown dimensions and non-finite or negative weights
    are rejected, so a custom rubric cannot silently drop a dimension
    or game the total.
    """
    if weights is None:
        return dict(WEIGHTS)
    if not isinstance(weights, dict):
        raise ValueError("weights must be an object mapping dimension to weight")
    unknown = set(weights) - set(WEIGHTS)
    if unknown:
        raise ValueError(f"unknown scoring dimensions: {sorted(unknown)}")
    merged = dict(WEIGHTS)
    merged.update(weights)
    for k, v in merged.items():
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
            raise ValueError(f"weight for {k} must be a finite number >= 0, got {v!r}")
    total = sum(merged.values())
    if total <= 0:
        raise ValueError("weights must sum to more than 0")
    return {k: v / total for k, v in merged.items()}


def score_application(app: Application, weights: dict | None = None) -> Score:
    traction = _clamp(100 * math.log10(1 + app.mrr) / math.log10(1 + 50_000))
    growth = _clamp(app.mom_growth / 0.20 * 100)
    rev_per_human = app.mrr * 12 / max(app.humans, 1)
    leverage = _clamp(
        0.35 * min(app.agents / 10, 1) * 100
        + 0.35 * app.automated_share * 100
        + 0.30 * min(rev_per_human / 1_000_000, 1) * 100
    )
    runway = app.cash / app.monthly_burn if app.monthly_burn else float("inf")
    net_new_arr = app.mrr * app.mom_growth * 12
    burn_multiple = (app.monthly_burn * 12 / net_new_arr) if net_new_arr > 0 else float("inf")
    efficiency = _clamp(0.5 * (100 if burn_multiple <= 1 else 100 / burn_multiple) + 0.5 * min(runway / 12, 1) * 100)
    velocity = _clamp(app.ships_per_week / 5 * 100)
    parts = {
        "traction": traction,
        "growth": growth,
        "leverage": leverage,
        "efficiency": efficiency,
        "velocity": velocity,
    }
    total = sum(parts[k] * w for k, w in _normalize_weights(weights).items())

    flags = []
    if runway < 3:
        flags.append(f"runway {runway:.1f} months")
    if app.mrr == 0 and not app.users:
        flags.append("no revenue and no users")
    if app.humans > 1:
        flags.append(f"{app.humans} humans - not a solo company")
    decision = "accept" if total >= 65 and not flags else "interview" if total >= 45 else "pass"
    return Score(app.name, round(total, 1), {k: round(v, 1) for k, v in parts.items()}, flags, decision)


def rank(apps: list[dict], weights: dict | None = None) -> list[Score]:
    if not isinstance(apps, list):
        raise ValueError("applications must be a JSON list")
    if not apps:
        raise ValueError("applications must be a non-empty list")
    _normalize_weights(weights)  # validate before scoring anything
    return sorted(
        (score_application(Application.from_dict(a), weights) for a in apps),
        key=lambda s: -s.total,
    )


def post_money_safe(invest: float, cap: float, round_pre: float | None = None, round_size: float | None = None) -> dict:
    """Ownership from a post-money SAFE, optionally through a subsequent priced round."""
    if cap <= 0 or invest <= 0 or invest >= cap:
        raise ValueError("need 0 < invest < cap")
    own = invest / cap
    out = {"ownership_at_conversion": own}
    if (round_pre is not None and round_pre <= 0) or (round_size is not None and round_size <= 0):
        raise ValueError("round_pre and round_size must be > 0")
    if round_pre and round_size:
        dilution = round_pre / (round_pre + round_size)
        out["ownership_after_round"] = own * dilution
        out["stake_value_after_round"] = own * dilution * (round_pre + round_size)
    return out
