"""ESG Scoring Engine — normalises raw metrics into 0-100 pillar scores and
a weighted final score, driven entirely by config/scoring_rules.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path(__file__).parents[2] / "config" / "scoring_rules.yaml"


@dataclass
class MetricScore:
    name: str
    raw_value: float
    normalised: float  # 0-100
    weight: float
    weighted: float


@dataclass
class PillarScore:
    name: str
    score: float  # 0-100
    metrics: list[MetricScore] = field(default_factory=list)


@dataclass
class ESGScore:
    ticker: str
    company_name: str
    environmental: PillarScore
    social: PillarScore
    governance: PillarScore
    total: float
    rating: str   # Excellent / Good / Fair / Poor
    alert: str | None  # CRITICAL / WATCH / None


def _load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _normalise(value: float, benchmarks: dict, direction: str) -> float:
    """Map a raw metric value to a 0-100 score using benchmark interpolation."""
    levels = ["excellent", "good", "fair", "poor"]
    if direction == "higher_is_better":
        score_map = {
            "excellent": 100,
            "good": 70,
            "fair": 40,
            "poor": 10,
        }
        # clamp
        if value >= benchmarks["excellent"]:
            return 100.0
        if value <= benchmarks["poor"]:
            return 0.0
        for i in range(len(levels) - 1):
            lo_label, hi_label = levels[i + 1], levels[i]
            lo_val, hi_val = benchmarks[lo_label], benchmarks[hi_label]
            if lo_val <= value <= hi_val:
                lo_score = score_map[lo_label]
                hi_score = score_map[hi_label]
                ratio = (value - lo_val) / (hi_val - lo_val)
                return lo_score + ratio * (hi_score - lo_score)
    else:  # lower_is_better
        score_map = {
            "excellent": 100,
            "good": 70,
            "fair": 40,
            "poor": 10,
        }
        if value <= benchmarks["excellent"]:
            return 100.0
        if value >= benchmarks["poor"]:
            return 0.0
        for i in range(len(levels) - 1):
            lo_label, hi_label = levels[i], levels[i + 1]
            lo_val, hi_val = benchmarks[lo_label], benchmarks[hi_label]
            if lo_val <= value <= hi_val:
                lo_score = score_map[lo_label]
                hi_score = score_map[hi_label]
                ratio = (value - lo_val) / (hi_val - lo_val)
                return lo_score + ratio * (hi_score - lo_score)
    return 50.0


def _score_pillar(pillar_name: str, pillar_cfg: dict, data: dict[str, float]) -> PillarScore:
    metric_scores: list[MetricScore] = []
    total_weight = 0.0
    weighted_sum = 0.0

    for metric_name, metric_cfg in pillar_cfg["metrics"].items():
        raw = data.get(metric_name)
        if raw is None:
            continue
        normalised = _normalise(
            value=float(raw),
            benchmarks=metric_cfg["benchmarks"],
            direction=metric_cfg["direction"],
        )
        weight = metric_cfg["weight"]
        weighted = normalised * weight
        metric_scores.append(MetricScore(
            name=metric_name,
            raw_value=float(raw),
            normalised=round(normalised, 2),
            weight=weight,
            weighted=round(weighted, 2),
        ))
        weighted_sum += weighted
        total_weight += weight

    pillar_score = (weighted_sum / total_weight * 100 / 100) if total_weight else 0.0
    return PillarScore(
        name=pillar_name,
        score=round(pillar_score, 2),
        metrics=metric_scores,
    )


def _rating(score: float, thresholds: dict) -> str:
    if score >= thresholds["excellent"]:
        return "Excellent"
    if score >= thresholds["good"]:
        return "Good"
    if score >= thresholds["fair"]:
        return "Fair"
    return "Poor"


def _alert(score: float, alerts: dict) -> str | None:
    if score < alerts["critical_breach"]:
        return "CRITICAL"
    if score < alerts["watch_list"]:
        return "WATCH"
    return None


def score_company(
    ticker: str,
    company_name: str,
    environmental_data: dict[str, float],
    social_data: dict[str, float],
    governance_data: dict[str, float],
    config: dict | None = None,
) -> ESGScore:
    """Compute a full ESGScore for one company from raw metric dicts."""
    cfg = config or _load_config()
    weights = cfg["weights"]

    e_pillar = _score_pillar("environmental", cfg["pillars"]["environmental"], environmental_data)
    s_pillar = _score_pillar("social", cfg["pillars"]["social"], social_data)
    g_pillar = _score_pillar("governance", cfg["pillars"]["governance"], governance_data)

    total = (
        e_pillar.score * weights["environmental"]
        + s_pillar.score * weights["social"]
        + g_pillar.score * weights["governance"]
    )

    return ESGScore(
        ticker=ticker,
        company_name=company_name,
        environmental=e_pillar,
        social=s_pillar,
        governance=g_pillar,
        total=round(total, 2),
        rating=_rating(total, cfg["thresholds"]),
        alert=_alert(total, cfg["alerts"]),
    )


def score_from_dict(company: dict[str, Any], config: dict | None = None) -> ESGScore:
    """Convenience wrapper — accepts the JSON structure used in data/mock/companies.json."""
    return score_company(
        ticker=company["ticker"],
        company_name=company["name"],
        environmental_data=company["environmental"],
        social_data=company["social"],
        governance_data=company["governance"],
        config=config,
    )
