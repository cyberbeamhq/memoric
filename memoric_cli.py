from __future__ import annotations

import json
from typing import Optional

import click

from .core.memory_manager import Memoric
from .db.postgres_connector import PostgresConnector
from .core.policy_executor import PolicyExecutor
from rich.console import Console
from rich.table import Table


@click.group()
def cli() -> None:
    """Memoric CLI"""


@cli.command("run-policies")
@click.option("--config", "config_path", type=click.Path(exists=True), required=False)
def run_policies_cmd(config_path: Optional[str]) -> None:
    m = Memoric(config_path=config_path)
    result = m.run_policies()
    click.echo(json.dumps(result, indent=2))


@cli.command("init-db")
@click.option("--config", "config_path", type=click.Path(exists=True), required=False)
def init_db_cmd(config_path: Optional[str]) -> None:
    m = Memoric(config_path=config_path)
    m._ensure_initialized()  # type: ignore[attr-defined]
    click.echo("DB initialized.")


@cli.command("inspect")
@click.option("--user", "user_id", type=str, required=False)
@click.option("--thread", "thread_id", type=str, required=False)
@click.option("--config", "config_path", type=click.Path(exists=True), required=False)
def inspect_cmd(user_id: Optional[str], thread_id: Optional[str], config_path: Optional[str]) -> None:
    m = Memoric(config_path=config_path)
    info = m.inspect()
    if user_id or thread_id:
        data = m.retrieve(user_id=user_id, thread_id=thread_id, top_k=5)
        info["sample"] = [{k: d.get(k) for k in ("id", "thread_id", "tier", "_score")} for d in data]
    click.echo(json.dumps(info, indent=2))

@cli.command("stats")
@click.option("--config", "config_path", type=click.Path(exists=True), required=False)
def stats_cmd(config_path: Optional[str]) -> None:
    m = Memoric(config_path=config_path)
    db: PostgresConnector = m.db
    console = Console()

    counts = db.count_by_tier()
    table = Table(title="Memoric Stats")
    table.add_column("Tier")
    table.add_column("Count")
    for tier, count in counts.items():
        table.add_row(str(tier or "(none)"), str(count))

    console.print(table)

    clusters = db.get_clusters(limit=20)
    if clusters:
        ctable = Table(title="Top Clusters")
        ctable.add_column("ID")
        ctable.add_column("Topic")
        ctable.add_column("Category")
        ctable.add_column("Size")
        for c in clusters:
            ctable.add_row(str(c.get("cluster_id")), str(c.get("topic")), str(c.get("category")), str(len(c.get("memory_ids") or [])))
        console.print(ctable)

def main() -> None:
    cli()


if __name__ == "__main__":
    main()


