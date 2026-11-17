"""CLI entrypoint for Ticket-to-Topology (t2t)."""

import os
import re
import socket
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from t2t.audit.report import render_json, render_markdown, render_table
from t2t.audit.service import AuditService
from t2t.cli.ui import (
    get_console,
    render_check_results,
    render_closing_card,
    render_hint_card,
    render_history_table,
    render_ticket_card,
)
from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.errors import T2TError
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import load_baseline_checks, load_catalog, load_fault
from t2t.faults.qualify import qualify_all, qualify_fault
from t2t.faults.state import clear_active_fault, get_state
from t2t.parsers.route import parse_route_detail
from t2t.session.drift import DriftReport
from t2t.session.service import SessionService
from t2t.session.store import SQLiteStore

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
    ctx: typer.Context,
    replay: Annotated[
        bool,
        typer.Option(
            "--replay",
            help="Run in offline replay mode using recorded fixtures.",
        ),
    ] = False,
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
    ctx.ensure_object(dict)
    ctx.obj["replay"] = replay


def _get_service(
    ctx: typer.Context | None = None,
    replay: bool = False,
) -> SessionService:
    """Helper to instantiate SessionService configured with settings and replay mode."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)

    global_replay = False
    if ctx and hasattr(ctx, "obj") and isinstance(ctx.obj, dict):
        global_replay = bool(ctx.obj.get("replay", False))
    effective_replay = replay or global_replay

    state_path_str = os.environ.get("T2T_STATE_FILE")
    state_file = Path(state_path_str) if state_path_str else Path(".t2t/state.json")

    db_path_str = os.environ.get("T2T_DB_PATH")
    db_file = Path(db_path_str) if db_path_str else Path(".t2t/t2t.db")
    store = SQLiteStore(db_file)

    return SessionService(
        settings=settings,
        inventory=inventory,
        replay=effective_replay,
        store=store,
        state_file=state_file,
    )


@app.command("new-ticket")
def new_ticket(
    ctx: typer.Context,
    fault: Annotated[
        str | None,
        typer.Option("--fault", help="Fault ID to inject (e.g. T3)."),
    ] = None,
    level: Annotated[
        int | None,
        typer.Option("--level", help="Target fault difficulty level (1..5)."),
    ] = None,
    random_fault: Annotated[
        bool,
        typer.Option("--random", help="Select a random fault."),
    ] = False,
    no_ai: Annotated[
        bool,
        typer.Option("--no-ai", help="Run session with deterministic offline fallbacks."),
    ] = False,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run offline using mock fixtures."),
    ] = False,
) -> None:
    """Start a new candidate troubleshooting session and generate an incident ticket."""
    console = get_console()
    try:
        service = _get_service(ctx, replay)
        with console.status("[bold cyan]Injecting fault and preparing ticket...[/bold cyan]"):
            active_state, ticket_text = service.start_ticket(
                fault_id=fault,
                level=level,
                random_fault=random_fault,
                no_ai=no_ai,
            )

        fault_model = service._load_fault(active_state.fault_id)
        card = render_ticket_card(
            ticket_text=ticket_text,
            fault_id=active_state.fault_id,
            level=active_state.level,
            symptom_class=fault_model.symptom_class,
            flows=fault_model.flows,
        )
        console.print(card)
        console.print(
            "\n[dim]Investigate the topology using 't2t status' or router show commands. "
            "Need help? Run 't2t hint'. Ready to submit? Run 't2t submit'.[/dim]"
        )
    except T2TError as err:
        console.print(f"[bold red]Error:[/bold red] {err}")
        raise typer.Exit(code=err.exit_code) from err
    except Exception as err:
        console.print(f"[bold red]Unexpected error:[/bold red] {err}")
        raise typer.Exit(code=1) from err


@app.command("hint")
def hint(
    ctx: typer.Context,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run offline using mock fixtures."),
    ] = False,
) -> None:
    """Request the next pedagogical mentor hint (costs points)."""
    console = get_console()
    try:
        service = _get_service(ctx, replay)
        with console.status("[bold yellow]Generating mentor hint...[/bold yellow]"):
            lvl, hint_text, penalty, is_max = service.get_hint()

        card = render_hint_card(
            hint_text=hint_text,
            level=lvl,
            penalty=penalty,
            is_max=is_max,
        )
        console.print(card)
    except T2TError as err:
        console.print(f"[bold red]Error:[/bold red] {err}")
        raise typer.Exit(code=err.exit_code) from err
    except Exception as err:
        console.print(f"[bold red]Unexpected error:[/bold red] {err}")
        raise typer.Exit(code=1) from err


@app.command("submit")
def submit(
    ctx: typer.Context,
    explanation: Annotated[
        str | None,
        typer.Option("--explanation", "-e", help="1-2 sentence explanation of root cause and fix."),
    ] = None,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run offline using mock fixtures."),
    ] = False,
) -> None:
    """Submit your fix for technical verification, drift evaluation, and AI grading."""
    console = get_console()
    try:
        service = _get_service(ctx, replay)
        state = service.get_active_state()
        if state is None:
            console.print(
                "[bold red]Error:[/bold red] No active ticket session. "
                "Run 't2t new-ticket' to start one."
            )
            raise typer.Exit(code=1)

        user_exp: str = (
            explanation
            if explanation and explanation.strip()
            else str(typer.prompt("Enter your 1-2 sentence explanation of the root cause and fix"))
        )

        with console.status(
            "[bold cyan]Running verification checks and evaluating drift...[/bold cyan]"
        ):
            passed, check_results, drift_report, score, feedback = service.submit_explanation(
                user_exp
            )

        table = render_check_results(check_results)
        console.print(table)
        console.print()

        if not passed:
            console.print(
                "[bold red]Verification checks failed.[/bold red] "
                "Your score was not recorded. Inspect the failed checks above and try again."
            )
            raise typer.Exit(code=1)

        if score and drift_report:
            card = render_closing_card(
                score=score,
                drift=drift_report,
                feedback=feedback,
            )
            console.print(card)
            console.print(
                "\n[bold green]Congratulations! Your session has been recorded "
                "in the database.[/bold green]"
            )
    except typer.Exit:
        raise
    except T2TError as err:
        console.print(f"[bold red]Error:[/bold red] {err}")
        raise typer.Exit(code=err.exit_code) from err
    except Exception as err:
        console.print(f"[bold red]Unexpected error:[/bold red] {err}")
        raise typer.Exit(code=1) from err


@app.command("abandon")
def abandon(
    ctx: typer.Context,
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Skip confirmation prompt."),
    ] = False,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run offline using mock fixtures."),
    ] = False,
) -> None:
    """Abandon current active troubleshooting session and restore baseline."""
    console = get_console()
    try:
        service = _get_service(ctx, replay)
        state = service.get_active_state()
        if state is None:
            console.print("[yellow]No ticket session is currently active.[/yellow]")
            raise typer.Exit(code=0)

        if not yes:
            confirm = typer.confirm(
                f"Are you sure you want to abandon session for fault {state.fault_id}? "
                "Your score will be forfeited.",
                default=False,
            )
            if not confirm:
                console.print("[dim]Abandon cancelled.[/dim]")
                raise typer.Exit(code=0)

        with console.status(
            "[bold yellow]Abandoning session and reverting network...[/bold yellow]"
        ):
            service.abandon_session()

        console.print(
            "[yellow]Session abandoned. Router configurations reverted to baseline.[/yellow]"
        )
    except typer.Exit:
        raise
    except T2TError as err:
        console.print(f"[bold red]Error:[/bold red] {err}")
        raise typer.Exit(code=err.exit_code) from err


@app.command("history")
def history(
    stats: Annotated[
        bool,
        typer.Option("--stats", help="Display aggregate performance statistics."),
    ] = False,
) -> None:
    """View past troubleshooting sessions and performance statistics."""
    console = get_console()
    db_path_str = os.environ.get("T2T_DB_PATH")
    db_file = Path(db_path_str) if db_path_str else Path(".t2t/t2t.db")
    store = SQLiteStore(db_file)

    records = store.get_history()
    stats_dict = store.get_history_stats() if stats else None
    table = render_history_table(records, stats_dict)
    console.print(table)


@app.command("shell")
def shell(
    ctx: typer.Context,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run shell in offline replay mode."),
    ] = False,
) -> None:
    """Interactive REPL shell with prompt 'sim>'."""
    import cmd

    console = get_console()
    console.print("[bold cyan]Starting Ticket-to-Topology Interactive Shell (REPL)...[/bold cyan]")
    console.print("[dim]Type 'help' for available commands or 'exit' to quit.[/dim]\n")

    class T2TShell(cmd.Cmd):
        prompt = "sim> "

        def do_status(self, arg: str) -> None:
            """Show routing table status across key prefixes."""
            try:
                status(ctx=ctx, replay=replay)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        def do_hint(self, arg: str) -> None:
            """Request next mentor hint."""
            try:
                hint(ctx=ctx, replay=replay)
            except typer.Exit:
                pass
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        def do_submit(self, arg: str) -> None:
            """Submit explanation and verify fix: submit <explanation>"""
            try:
                exp = arg.strip() if arg.strip() else None
                submit(ctx=ctx, explanation=exp, replay=replay)
            except typer.Exit:
                pass
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        def do_reveal(self, arg: str) -> None:
            """Reveal reference fix."""
            try:
                reveal(ctx=ctx, yes=False, replay=replay)
            except typer.Exit:
                pass
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        def do_abandon(self, arg: str) -> None:
            """Abandon active session."""
            try:
                abandon(ctx=ctx, yes=False, replay=replay)
            except typer.Exit:
                pass
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        def do_history(self, arg: str) -> None:
            """View session history: history [--stats]"""
            try:
                show_stats = "--stats" in arg
                history(stats=show_stats)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        def do_reset(self, arg: str) -> None:
            """Reset lab routers to golden configuration."""
            try:
                reset(force=False, replay=replay)
            except typer.Exit:
                pass
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        def do_exit(self, arg: str) -> bool:
            """Exit interactive shell."""
            console.print("[dim]Exiting sim shell.[/dim]")
            return True

        def do_quit(self, arg: str) -> bool:
            """Exit interactive shell."""
            return self.do_exit(arg)

        def emptyline(self) -> bool:
            return False

    T2TShell().cmdloop()


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
    ctx: typer.Context | None = None,
    replay: Annotated[
        bool,
        typer.Option(
            "--replay",
            help="Query routing status offline using frozen test fixtures.",
        ),
    ] = False,
) -> None:
    """Display routing table status for key prefixes across all routers."""
    console = get_console()
    global_replay = False
    if ctx and hasattr(ctx, "obj") and isinstance(ctx.obj, dict):
        global_replay = bool(ctx.obj.get("replay", False))
    effective_replay = replay or global_replay

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
        inventory=inventory, settings=settings, read_only=True, replay=effective_replay
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
    ctx: typer.Context | None = None,
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
    console = get_console()
    global_replay = False
    if ctx and hasattr(ctx, "obj") and isinstance(ctx.obj, dict):
        global_replay = bool(ctx.obj.get("replay", False))
    effective_replay = replay or global_replay
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

    statuses: dict[str, Any] = {}
    try:
        with DeviceSession(
            inventory=inventory, settings=settings, read_only=False, replay=effective_replay
        ) as session:
            engine = FaultEngine(
                session=session,
                inventory=inventory,
                baseline_checks=baseline_checks,
            )
            console.print("[bold cyan]Resetting routers to golden configuration...[/bold cyan]")
            statuses = engine.reset_lab(baseline_checks=baseline_checks)
    except T2TError as err:
        console.print(f"[bold red]Reset failed:[/bold red] {err}")
        raise typer.Exit(code=err.exit_code) from err

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
    ctx: typer.Context | None = None,
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Skip confirmation prompt."),
    ] = False,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run offline using mock devices."),
    ] = False,
) -> None:
    """Reveal reference fix (revert commands) for the currently active fault."""
    console = get_console()
    service = _get_service(ctx, replay)
    active_session = service.get_active_state()

    if active_session is not None:
        if not yes:
            confirm = typer.confirm(
                f"Are you sure you want to reveal the reference fix for {active_session.fault_id}? "
                "This will forfeit your session score (final score = 0).",
                default=False,
            )
            if not confirm:
                console.print("[dim]Reveal cancelled.[/dim]")
                raise typer.Exit(code=0)

        with console.status("[bold yellow]Revealing fault and reverting network...[/bold yellow]"):
            root_cause, revert_cmds, score = service.reveal_fault()

        closing_card = render_closing_card(
            score=score,
            drift=DriftReport(clean_fix=False, diffs={}, summary="Fix revealed; score forfeited."),
            root_cause=root_cause,
        )
        console.print(closing_card)
        console.print("\n[bold green]Reference Fix Commands (Applied):[/bold green]")
        for r_name, cmds in revert_cmds.items():
            console.print(f"  [bold]{r_name}:[/bold]")
            for c in cmds:
                console.print(f"    {c}")
        console.print()
        return

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
    ctx: typer.Context | None = None,
) -> None:
    """Qualify faults against live lab or offline test fixtures."""
    console = Console()
    global_replay = False
    if ctx and hasattr(ctx, "obj") and isinstance(ctx.obj, dict):
        global_replay = bool(ctx.obj.get("replay", False))
    effective_replay = replay or global_replay

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

    reports: list[Any] = []
    try:
        with DeviceSession(
            inventory=inventory, settings=settings, read_only=False, replay=effective_replay
        ) as session:
            engine = FaultEngine(
                session=session,
                inventory=inventory,
                baseline_checks=baseline_checks,
            )

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
    except T2TError as err:
        console.print(f"[bold red]Qualification error:[/bold red] {err}")
        raise typer.Exit(code=err.exit_code) from err

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


@app.command()
def audit(
    ctx: typer.Context,
    from_dir: Annotated[
        Path | None,
        typer.Option("--from-dir", help="Directory of saved router configs for offline audit."),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", help="Output format: table, json, md."),
    ] = "table",
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Write report to specified file or directory."),
    ] = None,
    fail_on: Annotated[
        str,
        typer.Option("--fail-on", help="Severity threshold to fail (exit 1): high, medium."),
    ] = "medium",
    strict_host_keys: Annotated[
        bool,
        typer.Option("--strict-host-keys", help="Enforce strict SSH host key checking."),
    ] = False,
    replay: Annotated[
        bool,
        typer.Option("--replay", help="Run offline using mock fixtures."),
    ] = False,
) -> None:
    """Run read-only audit to identify redistribution risks across devices."""
    console = get_console()
    global_replay = False
    if ctx and hasattr(ctx, "obj") and isinstance(ctx.obj, dict):
        global_replay = bool(ctx.obj.get("replay", False))
    effective_replay = replay or global_replay

    try:
        settings = load_settings()
        inventory = None
        if not from_dir:
            inventory = load_inventory(settings.t2t_inventory)

        service = AuditService(
            inventory=inventory,
            settings=settings,
            replay=effective_replay,
            strict_host_keys=strict_host_keys,
        )

        with console.status(
            "[bold cyan]Collecting configurations and auditing rules...[/bold cyan]"
        ):
            report = service.execute_audit(from_dir=from_dir, fail_on=fail_on)

    except (FileNotFoundError, ValueError) as err:
        console.print(f"[bold red]Audit error:[/bold red] {err}")
        raise typer.Exit(code=2) from err
    except T2TError as err:
        console.print(f"[bold red]Audit error:[/bold red] {err}")
        raise typer.Exit(code=2) from err
    except Exception as err:
        console.print(f"[bold red]Unexpected error during audit:[/bold red] {err}")
        raise typer.Exit(code=2) from err

    # Format output
    out_format = format.lower()
    rendered_text = ""
    if out_format == "json":
        rendered_text = render_json(report)
        if not output:
            console.print(rendered_text)
    elif out_format in ("md", "markdown"):
        rendered_text = render_markdown(report)
        if not output:
            console.print(rendered_text)
    else:
        table = render_table(report)
        console.print(table)

    # Save to file if --output specified
    if output:
        try:
            target_path = output
            if target_path.is_dir() or str(target_path).endswith(("/", "\\")):
                ext = (
                    "json"
                    if out_format == "json"
                    else ("md" if out_format in ("md", "markdown") else "txt")
                )
                target_path = target_path / f"audit_report.{ext}"
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if out_format in ("json", "md", "markdown"):
                target_path.write_text(rendered_text, encoding="utf-8")
            else:
                file_console = Console(record=True, width=120)
                file_console.print(render_table(report))
                target_path.write_text(file_console.export_text(), encoding="utf-8")
            console.print(f"[dim]Report written to {target_path}[/dim]")
        except Exception as err:
            console.print(f"[bold red]Failed to write report output:[/bold red] {err}")
            raise typer.Exit(code=2) from err

    # Exit code: 0 if passed (no findings at or above fail_on threshold), 1 if failed
    if not report.passed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
