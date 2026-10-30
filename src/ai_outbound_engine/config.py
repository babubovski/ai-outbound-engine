"""ICP and offer configuration loaded from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Offer:
    sender_name: str
    sender_company: str
    value_prop: str
    proof: str = ""
    cta: str = "Open to a quick 15 minute call next week?"


@dataclass(frozen=True)
class ICP:
    title_keywords: dict[str, int] = field(default_factory=dict)
    seniority: dict[str, int] = field(default_factory=dict)
    industry_keywords: list[str] = field(default_factory=list)
    industry_points: int = 10
    industry_max: int = 30
    negative_keywords: list[str] = field(default_factory=list)
    negative_penalty: int = 30
    min_score: int = 40


@dataclass(frozen=True)
class Config:
    offer: Offer
    icp: ICP
    max_words: int = 90


def _lower_keys(mapping: dict | None) -> dict[str, int]:
    return {str(k).lower(): int(v) for k, v in (mapping or {}).items()}


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    try:
        offer = Offer(**data["offer"])
    except (KeyError, TypeError) as exc:
        raise ValueError(f"{path}: 'offer' needs sender_name, sender_company, value_prop") from exc

    raw_icp = dict(data.get("icp") or {})
    raw_icp["title_keywords"] = _lower_keys(raw_icp.get("title_keywords"))
    raw_icp["seniority"] = _lower_keys(raw_icp.get("seniority"))
    for key in ("industry_keywords", "negative_keywords"):
        raw_icp[key] = [str(k).lower() for k in raw_icp.get(key) or []]
    icp = ICP(**raw_icp)

    max_words = int((data.get("generation") or {}).get("max_words", 90))
    return Config(offer=offer, icp=icp, max_words=max_words)
