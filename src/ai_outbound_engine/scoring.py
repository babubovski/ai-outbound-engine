"""Transparent, rule-based ICP scoring. Every point is traceable to a matched keyword."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import ICP
from .leads import Lead

TIER_A_THRESHOLD = 70


@dataclass
class ScoreResult:
    score: int
    tier: str
    breakdown: list[tuple[str, int, str]] = field(default_factory=list)

    def explain(self) -> str:
        if not self.breakdown:
            return "no ICP signals matched"
        return "; ".join(f"{name} {points:+d} ({hit})" for name, points, hit in self.breakdown)


def _has(keyword: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE) is not None


def _best(weights: dict[str, int], text: str) -> tuple[int, str]:
    hits = [(points, kw) for kw, points in weights.items() if _has(kw, text)]
    return max(hits) if hits else (0, "")


def score_lead(lead: Lead, icp: ICP, page_text: str = "") -> ScoreResult:
    breakdown: list[tuple[str, int, str]] = []

    points, kw = _best(icp.title_keywords, lead.title)
    if points:
        breakdown.append(("title", points, kw))

    points, kw = _best(icp.seniority, lead.title)
    if points:
        breakdown.append(("seniority", points, kw))

    context = " ".join([lead.industry, lead.company, lead.notes, page_text])
    industry_hits = [kw for kw in icp.industry_keywords if _has(kw, context)]
    if industry_hits:
        points = min(len(industry_hits) * icp.industry_points, icp.industry_max)
        breakdown.append(("industry", points, ", ".join(industry_hits)))

    negatives = [kw for kw in icp.negative_keywords if _has(kw, lead.title)]
    if negatives:
        breakdown.append(("negative", -icp.negative_penalty, ", ".join(negatives)))

    score = max(0, min(100, sum(p for _, p, _ in breakdown)))
    if score >= TIER_A_THRESHOLD:
        tier = "A"
    elif score >= icp.min_score:
        tier = "B"
    else:
        tier = "C"
    return ScoreResult(score=score, tier=tier, breakdown=breakdown)
