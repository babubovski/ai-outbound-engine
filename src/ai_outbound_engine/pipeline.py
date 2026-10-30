"""Glue: enrich -> score -> generate, one lead at a time, returning output CSV rows."""

from __future__ import annotations

from typing import Callable, Iterable

from .config import Config
from .generate import Generator
from .leads import Lead
from .scoring import score_lead

Fetcher = Callable[[str], str]


def process_lead(lead: Lead, config: Config, generator: Generator, fetch: Fetcher | None,
                 min_score: int) -> dict:
    page_text = fetch(lead.domain) if fetch else ""
    result = score_lead(lead, config.icp, page_text)
    row = {
        "email": lead.email, "first_name": lead.first_name, "last_name": lead.last_name,
        "title": lead.title, "company": lead.company, "domain": lead.domain, "linkedin": lead.linkedin,
        "icp_score": result.score, "icp_tier": result.tier, "score_breakdown": result.explain(),
    }
    if result.score < min_score:
        # Do not spend tokens (or sender reputation) on poor-fit leads.
        row["status"] = "skipped_low_fit"
        return row
    row.update(generator.generate(lead, config, result, page_text).as_dict())
    row["status"] = "ready"
    return row


def run_pipeline(leads: Iterable[Lead], config: Config, generator: Generator,
                 fetch: Fetcher | None = None, min_score: int | None = None,
                 on_row: Callable[[dict], None] | None = None) -> list[dict]:
    threshold = config.icp.min_score if min_score is None else min_score
    rows = []
    for lead in leads:
        row = process_lead(lead, config, generator, fetch, threshold)
        if on_row:
            on_row(row)
        rows.append(row)
    # Highest fit first, so the top of the file is the first batch you load into the sequencer.
    return sorted(rows, key=lambda r: r["icp_score"], reverse=True)
