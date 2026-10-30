"""`outbound` command line interface."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Optional

import anthropic
import typer
from rich.console import Console
from rich.table import Table

from .config import load_config
from .enrich import HomepageFetcher
from .generate import DEFAULT_MODEL, ClaudeGenerator, TemplateGenerator
from .leads import load_leads, write_rows
from .pipeline import run_pipeline
from .scoring import score_lead

app = typer.Typer(add_completion=False, help="Score leads against your ICP and write personalized outbound sequences.")
console = Console(stderr=True)

LeadsArg = typer.Argument(..., exists=True, dir_okay=False, help="Leads CSV (Apollo exports work as-is).")
IcpOpt = typer.Option(..., "--icp", "-c", exists=True, dir_okay=False, help="ICP + offer YAML.")


def _summary(rows: list[dict]) -> Table:
    table = Table(title="Outbound batch", show_lines=False)
    for col in ("Lead", "Company", "Score", "Tier", "Status", "First line"):
        table.add_column(col, overflow="fold", max_width=60 if col == "First line" else None)
    for r in rows:
        table.add_row(f"{r['first_name']} {r['last_name']}", r["company"], str(r["icp_score"]),
                      r["icp_tier"], r["status"], r.get("first_line", ""))
    return table


@app.command()
def run(
    leads: Path = LeadsArg,
    icp: Path = IcpOpt,
    out: Path = typer.Option(Path("outbound.csv"), "--out", "-o", help="Output CSV path."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Offline: template copy, no API key, no web fetch."),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", envvar="OUTBOUND_MODEL", help="Anthropic model ID."),
    fetch: bool = typer.Option(True, "--fetch/--no-fetch", help="Fetch each company homepage for context."),
    min_score: Optional[int] = typer.Option(None, "--min-score", help="Override icp.min_score."),
    max_words: Optional[int] = typer.Option(None, "--max-words", help="Override generation.max_words."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Only process the first N leads."),
) -> None:
    """Enrich, score and write a 3-step sequence for every lead."""
    config = load_config(icp)
    if max_words:
        config = replace(config, max_words=max_words)
    lead_list = load_leads(leads)[:limit]

    generator = TemplateGenerator() if dry_run else ClaudeGenerator(model=model)
    fetcher = HomepageFetcher() if fetch and not dry_run else None
    mode = "dry run (template, offline)" if dry_run else f"model {model}"
    console.print(f"[bold]{len(lead_list)} leads[/bold] | {mode} | fetch={'on' if fetcher else 'off'}")

    def progress(row: dict) -> None:
        console.print(f"  {row['icp_tier']} {row['icp_score']:>3}  {row['first_name']} {row['last_name']} "
                      f"@ {row['company']}  [dim]{row['status']}[/dim]")

    try:
        rows = run_pipeline(lead_list, config, generator, fetcher, min_score, on_row=progress)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError, TypeError) as exc:
        # The SDK raises TypeError when no credentials can be resolved at all.
        if isinstance(exc, TypeError) and "authentication" not in str(exc):
            raise
        console.print("[red]Anthropic auth failed.[/red] Set ANTHROPIC_API_KEY or use --dry-run.")
        raise typer.Exit(1)
    write_rows(rows, out)
    console.print(_summary(rows))
    ready = sum(r["status"] == "ready" for r in rows)
    console.print(f"[green]Wrote {out}[/green]: {ready} ready, {len(rows) - ready} skipped.")


@app.command()
def score(leads: Path = LeadsArg, icp: Path = IcpOpt) -> None:
    """Score leads only (no generation) and print the breakdown."""
    config = load_config(icp)
    table = Table(title="ICP scores")
    for col in ("Lead", "Title", "Company", "Score", "Tier", "Why"):
        table.add_column(col, overflow="fold")
    results = [(lead, score_lead(lead, config.icp)) for lead in load_leads(leads)]
    for lead, res in sorted(results, key=lambda x: x[1].score, reverse=True):
        table.add_row(lead.full_name, lead.title, lead.company, str(res.score), res.tier, res.explain())
    Console().print(table)


if __name__ == "__main__":
    app()
