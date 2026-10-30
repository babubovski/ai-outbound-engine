"""Lead CSV loading (tolerant of Apollo-style headers) and output CSV writing."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

# Header aliases so raw Apollo / Sales Nav / Clay exports load without manual cleanup.
ALIASES = {
    "name": "full_name",
    "first": "first_name",
    "last": "last_name",
    "job_title": "title",
    "company_name": "company",
    "organization": "company",
    "account_name": "company",
    "website": "domain",
    "company_website": "domain",
    "company_domain": "domain",
    "email_address": "email",
    "linkedin_url": "linkedin",
    "person_linkedin_url": "linkedin",
}

REQUIRED = ("first_name", "title", "company", "domain")

OUTPUT_COLUMNS = [
    "email", "first_name", "last_name", "title", "company", "domain", "linkedin",
    "icp_score", "icp_tier", "score_breakdown", "status",
    "subject", "first_line", "email_1", "email_2", "email_3", "generator",
]


@dataclass
class Lead:
    first_name: str
    title: str
    company: str
    domain: str
    last_name: str = ""
    email: str = ""
    industry: str = ""
    linkedin: str = ""
    notes: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


def _norm_header(header: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")
    return ALIASES.get(key, key)


def normalize_domain(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    return value.split("/")[0]


def load_leads(path: str | Path) -> list[Lead]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = [{_norm_header(k): (v or "").strip() for k, v in row.items() if k} for row in reader]

    leads = []
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        if row.get("full_name") and not row.get("first_name"):
            first, _, last = row["full_name"].partition(" ")
            row["first_name"] = first
            row["last_name"] = row.get("last_name") or last
        missing = [col for col in REQUIRED if not row.get(col)]
        if missing:
            raise ValueError(f"{path}: row {i} is missing {', '.join(missing)}")
        fields = {k: row.get(k, "") for k in Lead.__dataclass_fields__}
        fields["domain"] = normalize_domain(fields["domain"])
        leads.append(Lead(**fields))
    return leads


def write_rows(rows: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
