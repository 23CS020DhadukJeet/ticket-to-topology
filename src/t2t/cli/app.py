"""CLI entrypoint for Ticket-to-Topology (t2t)."""

from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import typer

app = typer.Typer(
    name="t2t",
    help=(
        "Dual-mode troubleshooting and audit platform for EIGRP/OSPF redistribution"
        " on Cisco IOS-XE."
    ),
    no_args_is_help=True,
)


def _get_version() -> str:
    """Retrieve package version."""
    try:
        return version("ticket-to-topology")
    except PackageNotFoundError:
        return "0.1.0"


def version_callback(value: bool) -> None:
    """Callback to print version and exit."""
    if value:
        typer.echo(f"t2t {_get_version()}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show the application version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Ticket-to-Topology CLI root."""


@app.command()
def doctor() -> None:
    """Check connectivity and environment health (stub)."""
    typer.echo("not implemented yet")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
