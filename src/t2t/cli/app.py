"""CLI entrypoint for Ticket-to-Topology (t2t)."""

import re
import socket
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.errors import T2TError
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import load_baseline_checks, load_catalog, load_fault
from t2t.faults.qualify import qualify_all, qualify_fault
from t2t.faults.state import clear_active_fault, get_state
from t2t.parsers.route import parse_route_detail

app = typer.Typer(
    name="t2t",
    help=(
        "Dual-mode troubleshooting and audit platform for EIGRP/OSPF redistribution"
        " on Cisco IOS-XE."
    ),
    no_args_is_help=True,
)

KEY_PREFIXES = [
    ("10.10.1.0/24", "10.10.1.0 255.255.255.0"),
    ("10.10.2.0/24", "10.10.2.0 255.255.255.0"),
    ("10.10.99.0/24", "10.10.99.0 255.255.255.0"),
    ("172.16.10.0/24", "172.16.10.0 255.255.255.0"),
    ("172.16.20.16/28", "172.16.20.16 255.255.255.240"),
]


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
        r"Cisco IOS XE Software,\s+Version\s+([^\s,\r\n]+)",
        show_version_output,
        re.IGNORECASE,
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


@app.command()
def status(
    replay: Annotated[
        bool,
        typer.Option(
            "--replay",
            help="Query routing status offline using frozen test fixtures.",
        ),
    ] = False,
) -> None:
    """Display routing table status for key prefixes across all routers."""
    console = Console()
    try:
        settings = load_settings()
        inventory = load_inventory(settings.t2t_inventory)
    except Exception as err:
        console.print(f"[bold red]Configuration error:[/bold red] {err}")
        raise typer.Exit(code=1) from err

    table = Table(title="Redistribution Status: Key Prefixes", show_lines=True)
    table.add_column("Prefix", style="bold cyan")
    for r in inventory.routers:
        table.add_column(r.name, justify="center")

    with DeviceSession(
        inventory=inventory, settings=settings, read_only=True, replay=replay
    ) as session:
        for prefix_label, prefix_cmd in KEY_PREFIXES:
            row: list[str] = [prefix_label]
            for r in inventory.routers:
                try:
                    out = session.show(r.name, f"show ip route {prefix_cmd}")
                    route = parse_route_detail(out)
                    if route is None:
                        row.append("[bold red]MISSING[/bold red]")
                    else:
                        tag_str = f" tag {route.tag}" if route.tag is not None else ""
                        hops_str = f" via {route.next_hops[0].ip}" if route.next_hops else ""
                        proto_str = f"[green]{route.protocol.upper()}[/green]"
                        row.append(f"{proto_str} ({route.distance}){tag_str}{hops_str}")
                except T2TError:
                    row.append("[bold red]MISSING[/bold red]")
            table.add_row(*row)

    console.print(table)


@app.command()
def reset(
    force: Annotated[
        bool,
        typer.Option("--force", help="Clear stale active fault state and lock files."),
    ] = False,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run reset offline using mock devices."),
    ] = False,
) -> None:
    """Restore lab routers to baseline golden configuration."""
    console = Console()
    try:
        settings = load_settings()
        inventory = load_inventory(settings.t2t_inventory)
    except Exception as err:
        console.print(f"[bold red]Configuration error:[/bold red] {err}")
        raise typer.Exit(code=1) from err

    if force:
        clear_active_fault(force=True)
        console.print("[yellow]Cleared active fault state and lock files (--force).[/yellow]")

    baseline_path = Path("src/t2t/faults/baseline.yaml")
    baseline_checks = load_baseline_checks(baseline_path) if baseline_path.exists() else []

    with DeviceSession(
        inventory=inventory, settings=settings, read_only=False, replay=replay
    ) as session:
        engine = FaultEngine(
            session=session,
            inventory=inventory,
            baseline_checks=baseline_checks,
        )
        console.print("[bold cyan]Resetting routers to golden configuration...[/bold cyan]")
        statuses = engine.reset_lab(baseline_checks=baseline_checks)

    table = Table(title="Lab Reset Results", show_lines=True)
    table.add_column("Router", style="bold cyan")
    table.add_column("Status", justify="center")
    table.add_column("Duration", justify="right")

    all_ok = True
    for r_name, stat in statuses.items():
        if not stat.success:
            all_ok = False
        stat_str = "[bold green]OK[/bold green]" if stat.success else "[bold red]FAIL[/bold red]"
        table.add_row(r_name, stat_str, f"{stat.duration_s}s")

    console.print(table)
    if not all_ok:
        console.print(
            "[bold red]Reset failed on one or more routers.[/bold red] "
            "Runbook: Verify golden_path and archive config, or reboot routers."
        )
        raise typer.Exit(code=1)
    console.print("[bold green]Lab reset to baseline completed successfully.[/bold green]")


@app.command()
def reveal(
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Reveal reference fix (revert commands) for the currently active fault."""
    console = Console()
    state = get_state()
    if state.active_fault is None:
        console.print("[yellow]No fault is currently active.[/yellow]")
        raise typer.Exit(code=0)

    if not yes:
        confirm = typer.confirm(
            f"Are you sure you want to reveal the reference fix for {state.active_fault}?",
            default=False,
        )
        if not confirm:
            console.print("[dim]Reveal cancelled.[/dim]")
            raise typer.Exit(code=0)

    try:
        settings = load_settings()
        inventory = load_inventory(settings.t2t_inventory)
        fault_path = Path(f"src/t2t/faults/catalog/{state.active_fault}.yaml")
        fault = load_fault(fault_path, inventory)
    except Exception as err:
        console.print(f"[bold red]Error loading active fault:[/bold red] {err}")
        raise typer.Exit(code=1) from err

    console.print(f"\n[bold cyan]Active Fault:[/bold cyan] {fault.id} — {fault.title}")
    console.print(f"[bold cyan]Root Cause:[/bold cyan] {fault.root_cause}\n")
    console.print("[bold green]Reference Fix Commands:[/bold green]")
    for r_name, cmds in fault.revert.items():
        console.print(f"  [bold]{r_name}:[/bold]")
        for c in cmds:
            console.print(f"    {c}")
    console.print()


@app.command()
def qualify(
    fault: Annotated[
        str | None,
        typer.Option("--fault", help="Fault ID to qualify (e.g. T3)."),
    ] = None,
    all_faults: Annotated[
        bool,
        typer.Option("--all", help="Qualify all faults in catalog."),
    ] = False,
    runs: Annotated[
        int,
        typer.Option("--runs", help="Number of qualification cycles per fault."),
    ] = 3,
    capture: Annotated[
        bool,
        typer.Option("--capture", help="Capture outputs to tests/fixtures/faulted/."),
    ] = False,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run qualification offline using frozen test fixtures."),
    ] = False,
) -> None:
    """Qualify faults against live lab or offline test fixtures."""
    console = Console()
    if not fault and not all_faults:
        console.print("[bold red]Error:[/bold red] Specify either --fault <ID> or --all.")
        raise typer.Exit(code=1)

    try:
        settings = load_settings()
        inventory = load_inventory(settings.t2t_inventory)
        catalog = load_catalog(Path("src/t2t/faults/catalog"), inventory)
        baseline_checks = load_baseline_checks(Path("src/t2t/faults/baseline.yaml"))
    except Exception as err:
        console.print(f"[bold red]Configuration error:[/bold red] {err}")
        raise typer.Exit(code=1) from err

    targets: dict[str, Any] = {}
    if all_faults:
        targets = catalog
    elif fault:
        if fault not in catalog:
            console.print(f"[bold red]Unknown fault ID:[/bold red] {fault}")
            raise typer.Exit(code=1)
        targets = {fault: catalog[fault]}

    with DeviceSession(
        inventory=inventory, settings=settings, read_only=False, replay=replay
    ) as session:
        engine = FaultEngine(
            session=session,
            inventory=inventory,
            baseline_checks=baseline_checks,
        )

        reports = []
        if all_faults:
            reports = qualify_all(
                catalog=targets,
                engine=engine,
                baseline_checks=baseline_checks,
                runs=runs,
                capture=capture,
            )
        elif fault is not None:
            single_fault = targets[fault]
            rep = qualify_fault(
                fault=single_fault,
                engine=engine,
                baseline_checks=baseline_checks,
                runs=runs,
                capture=capture,
            )
            reports = [rep]

    table = Table(title="Fault Qualification Summary", show_lines=True)
    table.add_column("Fault", style="bold cyan")
    table.add_column("Title")
    table.add_column("Runs", justify="center")
    table.add_column("Duration", justify="right")
    table.add_column("Result", style="bold", justify="center")

    all_passed = True
    for rep in reports:
        if not rep.qualified:
            all_passed = False
        res_str = (
            "[bold green]QUALIFIED[/bold green]" if rep.qualified else "[bold red]FAILED[/bold red]"
        )
        table.add_row(
            rep.fault_id, rep.title, str(len(rep.runs)), f"{rep.total_duration_s}s", res_str
        )

    console.print(table)
    if not all_passed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
