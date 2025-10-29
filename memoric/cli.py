from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

# Use proper package imports now that we have memoric/ structure
from memoric.core.memory_manager import Memoric
from memoric.db.postgres_connector import PostgresConnector


@click.group()
def cli() -> None:
    """Memoric - Memory Management for AI Agents"""


@cli.command("version")
def version_cmd() -> None:
    """Show Memoric version information."""
    import memoric

    console = Console()
    version = getattr(memoric, "__version__", "unknown")

    console.print(f"[bold cyan]Memoric[/bold cyan] version [green]{version}[/green]")
    console.print("\nFor help: [cyan]memoric --help[/cyan]")
    console.print("Documentation: [cyan]https://github.com/cyberbeamhq/memoric[/cyan]")


@cli.command("init-config")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="memoric_config.yaml",
    help="Output path for config file (default: memoric_config.yaml)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing file if it exists",
)
def init_config_cmd(output: str, force: bool) -> None:
    """Initialize a new config file from the default template.

    This command copies the default configuration file to your specified location,
    which you can then customize for your needs.

    Examples:
        memoric init-config
        memoric init-config -o my_config.yaml
        memoric init-config -o config.yaml --force
    """
    console = Console()
    output_path = Path(output)

    # Check if file exists
    if output_path.exists() and not force:
        console.print(
            f"[red]Error:[/red] File '{output}' already exists. "
            f"Use --force to overwrite.",
            style="bold",
        )
        raise click.Abort()

    # Find the default config file in the package
    try:
        import memoric

        package_dir = Path(memoric.__file__).parent
        default_config = package_dir / "config" / "default_config.yaml"

        if not default_config.exists():
            console.print(
                "[red]Error:[/red] Default config file not found in package.",
                style="bold",
            )
            console.print(
                "Please ensure Memoric is properly installed: pip install -e .",
                style="dim",
            )
            raise click.Abort()

        # Copy the default config
        shutil.copy(default_config, output_path)

        console.print(f"[green]✓[/green] Config file created: [cyan]{output}[/cyan]")
        console.print("\nNext steps:", style="bold")
        console.print(f"  1. Edit {output} to customize your configuration")
        console.print(f"  2. Use it: [cyan]m = MemoryManager(config_path='{output}')[/cyan]")
        console.print("\nKey sections to review:", style="bold")
        console.print("  • text_processing - Prevent data loss (set to 'noop')")
        console.print("  • database.dsn - Set your database connection")
        console.print("  • storage.tiers - Configure memory tiers")
        console.print("\nSee TEXT_PROCESSING_GUIDE.md for detailed configuration help.")

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to create config file: {e}", style="bold")
        raise click.Abort()


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
    m.initialize()  # Use public method instead of private _ensure_initialized
    click.echo("DB initialized.")


@cli.command("inspect")
@click.option("--user", "user_id", type=str, required=False)
@click.option("--thread", "thread_id", type=str, required=False)
@click.option("--config", "config_path", type=click.Path(exists=True), required=False)
def inspect_cmd(
    user_id: Optional[str], thread_id: Optional[str], config_path: Optional[str]
) -> None:
    m = Memoric(config_path=config_path)
    info = m.inspect()
    if user_id or thread_id:
        data = m.retrieve(user_id=user_id, thread_id=thread_id, top_k=5)
        info["sample"] = [
            {k: d.get(k) for k in ("id", "thread_id", "tier", "_score")} for d in data
        ]
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
            ctable.add_row(
                str(c.get("cluster_id")),
                str(c.get("topic")),
                str(c.get("category")),
                str(len(c.get("memory_ids") or [])),
            )
        console.print(ctable)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
