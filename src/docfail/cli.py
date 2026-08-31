"""Command-line entry point.

This is the only place that reads a dotenv file or creates directories, so
importing any library module stays free of side effects.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from docfail.settings import load_settings

app = typer.Typer(add_completion=False, help="Document extraction failure-mode analysis.")
console = Console()


def _bootstrap():
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv()
    return load_settings()


@app.command()
def config() -> None:
    """Show resolved settings. Safe to paste: it holds no credentials."""
    settings = _bootstrap()
    table = Table("setting", "value")
    for key, value in settings.model_dump().items():
        table.add_row(key, str(value))
    console.print(table)


@app.command()
def conditions() -> None:
    """List registered degradation conditions."""
    from docfail.degrade.transforms import CONDITIONS

    for name in sorted(CONDITIONS):
        console.print(f"- {name}")


if __name__ == "__main__":
    app()
