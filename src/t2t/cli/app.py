"""CLI entrypoint for Ticket-to-Topology (t2t)."""

import re
import socket
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.errors import T2TError

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


def check_tcp_port(host: str, port: int = 22, timeout: float = 3.0) -> bool:
    """Check if TCP port is open within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (TimeoutError, OSError):
        return False


def _parse_ios_version(show_version_output: str) -> str:
    """Extract IOS-XE version string from show version output."""
    match = re.search(
        r"Cisco IOS XE Software,\s+Version\s+([^\s,\r\n]+)", show_version_output, re.IGNORECASE
    )
    if match:
        return match.group(1)
    match_fallback = re.search(r"Version\s+([0-9]+\.[0-9]+[^\s,\r\n]*)", show_version_output)
    if match_fallback:
        return match_fallback.group(1)
    return "Unknown"


@app.command()
def doctor(
    replay: Annotated[
        bool,
        typer.Option(
            "--replay",
            help="Run doctor checks offline using frozen test fixtures.",
        ),
    ] = False,
) -> None:
    """Check connectivity and environment health across all lab routers."""
    console = Console()
    try:
        settings = load_settings()
        inventory = load_inventory(settings.t2t_inventory)
    except Exception as err:
        console.print(f"[bold red]Configuration error:[/bold red] {err}")
        raise typer.Exit(code=1) from err

    table = Table(title="Lab Environment Doctor Check", show_lines=True)
    table.add_column("Router", style="bold cyan")
    table.add_column("TCP 22")
    table.add_column("Login")
    table.add_column("IOS-XE Release")
    table.add_column("Golden File")
    table.add_column("Archive")
    table.add_column("VRF MGMT")
    table.add_column("Overall", style="bold")

    all_passed = True
    golden_path_default = inventory.defaults.get("golden_path", "flash:golden.cfg")

    with DeviceSession(
        inventory=inventory, settings=settings, read_only=True, replay=replay
    ) as session:
        for router in inventory.routers:
            r_name = router.name
            golden_path = router.golden_path or golden_path_default

            # Check 1: TCP 22
            tcp_ok = True if replay else check_tcp_port(router.host, port=22, timeout=3.0)
            tcp_str = "[green]OPEN[/green]" if tcp_ok else "[red]CLOSED[/red]"

            if not tcp_ok:
                table.add_row(
                    r_name,
                    tcp_str,
                    "[dim]SKIPPED[/dim]",
                    "[dim]SKIPPED[/dim]",
                    "[dim]SKIPPED[/dim]",
                    "[dim]SKIPPED[/dim]",
                    "[dim]SKIPPED[/dim]",
                    "[bold red]FAIL[/bold red]",
                )
                all_passed = False
                continue

            # Check 2: Login and show version
            login_ok = False
            ios_ver = "Unknown"
            try:
                ver_out = session.show(r_name, "show version")
                login_ok = True
                ios_ver = _parse_ios_version(ver_out)
            except T2TError:
                login_ok = False

            login_str = "[green]OK[/green]" if login_ok else "[red]FAIL[/red]"

            if not login_ok:
                table.add_row(
                    r_name,
                    tcp_str,
                    login_str,
                    "[red]FAIL[/red]",
                    "[dim]SKIPPED[/dim]",
                    "[dim]SKIPPED[/dim]",
                    "[dim]SKIPPED[/dim]",
                    "[bold red]FAIL[/bold red]",
                )
                all_passed = False
                continue

            # Check 3: Golden file present
            golden_ok = False
            try:
                dir_out = session.show(r_name, f"dir {golden_path}")
                golden_ok = "golden.cfg" in dir_out and "Error" not in dir_out
            except T2TError:
                golden_ok = False
            golden_str = "[green]OK[/green]" if golden_ok else "[yellow]MISSING[/yellow]"

            # Check 4: Archive configured
            archive_ok = False
            try:
                arch_out = session.show(r_name, "show running-config | section archive")
                archive_ok = "archive" in arch_out
            except T2TError:
                archive_ok = False
            archive_str = "[green]OK[/green]" if archive_ok else "[red]MISSING[/red]"

            # Check 5: VRF MGMT
            vrf_ok = False
            try:
                vrf_out = session.show(r_name, "show vrf")
                vrf_ok = "MGMT" in vrf_out
            except T2TError:
                vrf_ok = False
            vrf_str = "[green]OK[/green]" if vrf_ok else "[red]MISSING[/red]"

            router_passed = login_ok and archive_ok and vrf_ok
            if not router_passed:
                all_passed = False

            overall_str = (
                "[bold green]PASS[/bold green]" if router_passed else "[bold red]FAIL[/bold red]"
            )
            table.add_row(
                r_name,
                tcp_str,
                login_str,
                ios_ver,
                golden_str,
                archive_str,
                vrf_str,
                overall_str,
            )

    console.print(table)
    if not all_passed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
