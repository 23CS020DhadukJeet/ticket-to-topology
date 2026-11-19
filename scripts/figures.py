"""
Script to generate high-resolution, sequentially numbered figures for the
compressed (~30-page) Ticket-to-Topology (t2t) project report.

Sequential figure mapping (matches exact order of appearance):
  1. Fig 2.1: Gantt Chart (14-Week Development Schedule)
  2. Fig 3.1: System Use Case Diagram
  3. Fig 4.1: Multi-Tier System Architecture
  4. Fig 4.2: End-to-End Troubleshooting Activity Process Flow
  5. Fig 4.3: High-Level Unified Class Diagram (OOP Design)
  6. Fig 4.4: Sequence Diagram: Verification & Socratic Guidance Lifecycle
  7. Fig 5.1: CCNP Enterprise Dual-Point Mutual Route Redistribution Topology
  8. Fig 5.2: FastAPI Lightweight Web Interface Mockup with Interactive SVG Canvas
  9. Fig 5.3: Finite State Machine (FSM) Lifecycle Diagram
 10. Fig 5.4: SQLite WAL Session Store Entity-Relationship (ER) Schema
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

FIG_DIR = Path(__file__).resolve().parent.parent / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]


def generate_gantt_chart():
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=300)
    tasks = [
        "Phase 1: Project Setup & Baseline Topology",
        "Phase 2: IOS-XE Show Run Parsers & AST",
        "Phase 3: Static Redistribution Audit Engine",
        "Phase 4: Device Session & Netmiko Abstraction",
        "Phase 5: Fault Injection Catalog (T1-T7)",
        "Phase 6: Verification Oracle (No-AI)",
        "Phase 7: Scoring Engine & Anti-Drift Penalty",
        "Phase 8: Socratic AI Mentor & Redactor",
        "Phase 9: CLI Interface & Offline Replay",
        "Phase 10: Read-Only FastAPI & SVG Web UI",
        "Testing, Qualification & Lab Benchmarking",
        "Final Report & Documentation Assembly",
    ]
    starts = [1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13]
    durations = [2, 2, 2, 3, 2, 2, 2, 2, 2, 2, 2, 2]
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(tasks)))

    y_pos = np.arange(len(tasks))
    ax.barh(y_pos, durations, left=starts, align="center", color=colors, edgecolor="#1b365d", height=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(tasks, fontsize=8.5, fontweight="bold", color="#1b365d")
    ax.invert_yaxis()
    ax.set_xlabel("Project Timeline (Weeks 1 to 14)", fontsize=9.5, fontweight="bold", color="#1b365d")
    ax.set_xlim(1, 15)
    ax.set_xticks(range(1, 15))
    ax.set_xticklabels([f"W{i}" for i in range(1, 15)], fontsize=8.5)
    ax.grid(axis="x", linestyle="--", alpha=0.6)
    ax.set_title("Fig 2.1: 14-Week Development Schedule (Gantt Chart)", fontsize=11.5, fontweight="bold", color="#1b365d", pad=12)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_2_1_gantt_chart.png", dpi=300)
    plt.close()


def generate_use_case_diagram():
    fig, ax = plt.subplots(figsize=(10, 5.0), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    box = patches.FancyBboxPatch((2.2, 0.4), 5.6, 9.2, boxstyle="round,pad=0.18",
                                 ec="#1b365d", fc="#f8fafc", lw=2)
    ax.add_patch(box)
    ax.text(5.0, 9.25, "Ticket-to-Topology (t2t) System Boundary", ha="center", va="center",
            fontsize=10.5, fontweight="bold", color="#1b365d")

    def draw_actor(x, y, label):
        ax.plot([x, x], [y - 0.2, y - 0.6], color="#0f172a", lw=2)
        head = patches.Circle((x, y), 0.2, ec="#0f172a", fc="#cbd5e1", lw=2)
        ax.add_patch(head)
        ax.plot([x - 0.25, x + 0.25], [y - 0.35, y - 0.35], color="#0f172a", lw=2)
        ax.plot([x, x - 0.2], [y - 0.6, y - 0.9], color="#0f172a", lw=2)
        ax.plot([x, x + 0.2], [y - 0.6, y - 0.9], color="#0f172a", lw=2)
        ax.text(x, y - 1.05, label, ha="center", va="top", fontsize=8.5, fontweight="bold", color="#0f172a")

    draw_actor(0.8, 6.8, "Network Engineer /\nCandidate")
    draw_actor(0.8, 2.7, "Compliance Auditor")
    draw_actor(9.2, 7.6, "Verification Oracle\n(Deterministic)")
    draw_actor(9.2, 4.7, "Socratic AI Mentor\n(Ollama / LLM)")
    draw_actor(9.2, 1.9, "Cisco IOS-XE\nRouters")

    use_cases = [
        (5.0, 8.4, "UC1: Initialize Scenario / Inject Fault"),
        (5.0, 7.15, "UC2: Run Static Redistribution Audit"),
        (5.0, 5.9, "UC3: Inspect Route Detail & Diagnostics"),
        (5.0, 4.65, "UC4: Push Candidate Remediation Config"),
        (5.0, 3.4, "UC5: Verify Invariants & Anti-Feedback"),
        (5.0, 2.15, "UC6: Query Socratic Pedagogical Hint"),
        (5.0, 0.95, "UC7: Monitor Topology Telemetry (Web SVG)"),
    ]

    for ux, uy, ulabel in use_cases:
        ellipse = patches.Ellipse((ux, uy), 4.3, 0.72, ec="#2563eb", fc="#eff6ff", lw=1.5)
        ax.add_patch(ellipse)
        ax.text(ux, uy, ulabel, ha="center", va="center", fontsize=8.2, fontweight="bold", color="#1e3a8a")

    conns = [
        ((1.1, 6.3), (2.85, 8.4)),
        ((1.1, 6.3), (2.85, 5.9)),
        ((1.1, 6.3), (2.85, 4.65)),
        ((1.1, 6.3), (2.85, 3.4)),
        ((1.1, 6.3), (2.85, 2.15)),
        ((1.1, 6.3), (2.85, 0.95)),
        ((1.1, 2.4), (2.85, 7.15)),
        ((7.15, 3.4), (8.9, 7.2)),
        ((7.15, 2.15), (8.9, 4.4)),
        ((7.15, 8.4), (8.9, 1.8)),
        ((7.15, 4.65), (8.9, 1.8)),
    ]
    for (x1, y1), (x2, y2) in conns:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-", color="#64748b", lw=1.15))

    ax.set_title("Fig 3.1: System Use Case Diagram", fontsize=11.5, fontweight="bold", color="#1b365d", pad=8)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_3_1_use_case.png", dpi=300)
    plt.close()


def generate_architecture_diagram():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    layers = [
        (0.5, 7.7, 9.0, 1.9, "#dbeafe", "#1e40af", "Presentation Layer (CLI & Web UI)",
         "Typer CLI (Rich Tables, Live Spinners, Colored Status)  |  FastAPI Read-Only Server (SVG Dynamic Topology Canvas)"),
        (0.5, 4.1, 9.0, 3.1, "#e0e7ff", "#3730a3", "Core Application & Domain Engine",
         "Fault Catalog & Loader (YAML T1-T7)  |  Redistribution AST Parser (Hierarchical IOS-XE Grammar)\n"
         "Static Audit Engine (Rules A1-A7: Tagging, Metrics, Loops)  |  Verification Oracle (Decoupled Routing Invariants)\n"
         "Session FSM & Scoring Engine (Time Decay, Anti-Drift AST Diff)  |  Socratic AI Mentor (Regex Redaction & Safety Guard)"),
        (0.5, 0.6, 9.0, 3.0, "#f1f5f9", "#0f172a", "Infrastructure & Integration Layer",
         "Device Abstraction (DeviceSession with Abstract DeviceProtocol)\n"
         "Netmiko Live SSH Driver (Bounded Timeout)  <--->  Mock Replay Engine (Offline Deterministic Fixtures)\n"
         "SQLite Session Store (WAL Mode, Foreign Keys)  <--->  Local / Cloud LLM APIs (Ollama / Anthropic / OpenAI)"),
    ]

    for x, y, w, h, bg, border, title, desc in layers:
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.18",
                                     ec=border, fc=bg, lw=2)
        ax.add_patch(box)
        ax.text(x + 0.3, y + h - 0.38, title, fontsize=10, fontweight="bold", color=border)
        ax.text(x + 0.3, y + h * 0.38, desc, fontsize=8.3, color="#1e293b", va="center")

    ax.annotate("", xy=(5.0, 7.55), xytext=(5.0, 7.25),
                arrowprops=dict(arrowstyle="<->", color="#1e40af", lw=2))
    ax.annotate("", xy=(5.0, 3.95), xytext=(5.0, 3.65),
                arrowprops=dict(arrowstyle="<->", color="#3730a3", lw=2))

    ax.set_title("Fig 4.1: Ticket-to-Topology (t2t) Multi-Tier System Architecture",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_4_1_architecture.png", dpi=300)
    plt.close()


def generate_activity_diagram():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    start = patches.Circle((5.0, 9.5), 0.18, ec="#0f172a", fc="#0f172a")
    ax.add_patch(start)
    ax.text(5.0, 9.75, "Start", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    nodes = [
        (5.0, 8.65, "Generate Troubleshooting Ticket (Select Fault Scenario T1-T7)"),
        (5.0, 7.55, "Inject Misconfiguration via Netmiko / Replay Harness"),
        (5.0, 6.45, "Candidate Discovery & Static Audit Scan (Rules A1-A7)"),
        (5.0, 5.35, "Candidate Applies Remediation Config (DeviceSession.push_config)"),
        (5.0, 4.25, "Verification Oracle Evaluates Topology Invariants"),
    ]

    for x, y, text in nodes:
        box = patches.FancyBboxPatch((x - 2.6, y - 0.32), 5.2, 0.64, boxstyle="round,pad=0.12",
                                     ec="#2563eb", fc="#eff6ff", lw=1.5)
        ax.add_patch(box)
        ax.text(x, y, text, ha="center", va="center", fontsize=8, fontweight="bold", color="#1e3a8a")

    diamond = patches.Polygon([[5.0, 3.35], [6.2, 2.7], [5.0, 2.05], [3.8, 2.7]],
                              ec="#d97706", fc="#fef3c7", lw=1.8)
    ax.add_patch(diamond)
    ax.text(5.0, 2.7, "All Invariants\nPassed?", ha="center", va="center", fontsize=8, fontweight="bold", color="#92400e")

    pass_box = patches.FancyBboxPatch((0.8, 0.7), 3.3, 0.78, boxstyle="round,pad=0.14",
                                      ec="#16a34a", fc="#f0fdf4", lw=1.5)
    ax.add_patch(pass_box)
    ax.text(2.45, 1.09, "Record Score & Award Ticket\n(Time Decay + AST Anti-Drift)", ha="center", va="center",
            fontsize=8, fontweight="bold", color="#166534")

    fail_box = patches.FancyBboxPatch((5.9, 0.7), 3.3, 0.78, boxstyle="round,pad=0.14",
                                      ec="#dc2626", fc="#fef2f2", lw=1.5)
    ax.add_patch(fail_box)
    ax.text(7.55, 1.09, "Penalize & Provide Socratic Hint\n(Redacted Banned Terms)", ha="center", va="center",
            fontsize=8, fontweight="bold", color="#991b1b")

    ax.annotate("", xy=(5.0, 9.0), xytext=(5.0, 9.3), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.4))
    ax.annotate("", xy=(5.0, 7.9), xytext=(5.0, 8.3), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.4))
    ax.annotate("", xy=(5.0, 6.8), xytext=(5.0, 7.2), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.4))
    ax.annotate("", xy=(5.0, 5.7), xytext=(5.0, 6.1), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.4))
    ax.annotate("", xy=(5.0, 4.6), xytext=(5.0, 5.0), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.4))
    ax.annotate("", xy=(5.0, 3.38), xytext=(5.0, 3.9), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.4))

    ax.annotate("YES", xy=(2.45, 1.52), xytext=(4.0, 2.7),
                arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.5),
                fontsize=8.5, fontweight="bold", color="#16a34a")
    ax.annotate("NO", xy=(7.55, 1.52), xytext=(6.0, 2.7),
                arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.5),
                fontsize=8.5, fontweight="bold", color="#dc2626")

    ax.annotate("", xy=(7.65, 5.35), xytext=(8.6, 1.52),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.25", color="#dc2626", lw=1.5, ls="--"))
    ax.text(8.85, 3.5, "Retry\nRemediation", fontsize=7.8, fontweight="bold", color="#dc2626", ha="center")

    ax.set_title("Fig 4.2: End-to-End Troubleshooting Activity Process Flow",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_4_2_activity_flow.png", dpi=300)
    plt.close()


def generate_class_diagram():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    classes = [
        (2.3, 8.2, 3.6, 2.2, "DeviceSession",
         "- host: str\n- read_only: bool\n- _protocol: DeviceProtocol\n+ send_command(cmd): str\n+ push_config(lines): str"),
        (7.7, 8.2, 3.6, 2.2, "RedistributionAST",
         "- eigrp_instances: Dict\n- ospf_processes: Dict\n- route_maps: Dict\n+ get_redistributed_sources()\n+ find_metric_issues()"),
        (2.3, 4.7, 3.6, 2.2, "VerificationOracle",
         "- baseline_checks: List[Check]\n- fault_checks: List[Check]\n+ evaluate(devices): Result\n+ check_route_invariants()"),
        (7.7, 4.7, 3.6, 2.2, "AuditEngine",
         "- rules: List[Rule]\n- ast: RedistributionAST\n+ evaluate_rules(): AuditReport\n+ check_ad_inversion()"),
        (5.0, 1.4, 3.8, 2.1, "SessionFSM",
         "- state: State\n- clock: Clock\n- db: SQLiteManager\n+ transition_to(new_state)\n+ score_attempt(diff, elapsed)"),
    ]

    for x, y, w, h, name, attrs in classes:
        box = patches.FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="square,pad=0",
                                     ec="#1e3a8a", fc="#ffffff", lw=1.5, zorder=2)
        ax.add_patch(box)
        header = patches.Rectangle((x - w / 2, y + h / 2 - 0.5), w, 0.5, fc="#dbeafe", ec="#1e3a8a", lw=1.5, zorder=3)
        ax.add_patch(header)
        ax.text(x, y + h / 2 - 0.25, name, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1e3a8a", zorder=4)
        ax.text(x - w / 2 + 0.14, y - 0.22, attrs, ha="left", va="center", fontsize=7.0, color="#0f172a", family="monospace", zorder=4)

    # Clean non-overlapping connectors
    ax.plot([4.1, 5.9], [8.2, 8.2], color="#64748b", lw=1.5, zorder=1)
    ax.plot([2.3, 2.3], [7.1, 5.8], color="#64748b", lw=1.5, zorder=1)
    ax.plot([7.7, 7.7], [7.1, 5.8], color="#64748b", lw=1.5, zorder=1)
    ax.plot([2.3, 3.1], [3.6, 2.45], color="#64748b", lw=1.5, zorder=1)
    ax.plot([7.7, 6.9], [3.6, 2.45], color="#64748b", lw=1.5, zorder=1)

    ax.set_title("Fig 4.3: High-Level Unified Class Diagram (OOP Design)",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_4_3_class_diagram.png", dpi=300)
    plt.close()


def generate_sequence_diagram():
    fig, ax = plt.subplots(figsize=(10, 5.0), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    lifelines = [
        (1.0, "Candidate\n(CLI/Web)"),
        (3.0, "Session FSM\n& Controller"),
        (5.0, "DeviceSession\n(Netmiko/Mock)"),
        (7.0, "Verification\nOracle"),
        (9.0, "Socratic\nAI Mentor"),
    ]

    for x, label in lifelines:
        box = patches.FancyBboxPatch((x - 0.8, 8.75), 1.6, 0.85, boxstyle="round,pad=0.08",
                                     ec="#1e3a8a", fc="#dbeafe", lw=1.5)
        ax.add_patch(box)
        ax.text(x, 9.18, label, ha="center", va="center", fontsize=8, fontweight="bold", color="#1e3a8a")
        ax.plot([x, x], [0.6, 8.7], color="#94a3b8", lw=1.2, ls="--")

    seqs = [
        (1.0, 3.0, 8.0, "1. t2t new-ticket (Scenario T3)"),
        (3.0, 5.0, 7.2, "2. inject_fault(device, catalog)"),
        (5.0, 3.0, 6.4, "3. Fault Injected (ACK)"),
        (1.0, 5.0, 5.6, "4. t2t submit (Remediation Config)"),
        (3.0, 7.0, 4.8, "5. run_verification(checks)"),
        (7.0, 3.0, 4.0, "6. Invariant Status (PASS / FAIL)"),
        (3.0, 9.0, 3.2, "7. Request Diagnostic Hint (Fail)"),
        (9.0, 3.0, 2.4, "8. Filter & Return Socratic Hint"),
        (3.0, 1.0, 1.5, "9. Render Score & Guided Question"),
    ]

    for x1, x2, y, msg in seqs:
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color="#2563eb", lw=1.5))
        ax.text((x1 + x2) / 2, y + 0.14, msg, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#0f172a")

    ax.set_title("Fig 4.4: Sequence Diagram: Verification & Socratic Guidance Lifecycle",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_4_4_sequence_diagram.png", dpi=300)
    plt.close()


def generate_topology_diagram():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    eigrp_bubble = patches.Ellipse((2.1, 5.0), 3.7, 6.4, ec="#f59e0b", fc="#fffbeb", lw=1.5, ls="--", zorder=0)
    ax.add_patch(eigrp_bubble)
    ax.text(1.4, 7.7, "EIGRP Domain\n(AS 100)", fontsize=9.5, fontweight="bold", color="#b45309", ha="center")

    ospf_bubble = patches.Ellipse((7.9, 5.0), 3.7, 6.4, ec="#3b82f6", fc="#eff6ff", lw=1.5, ls="--", zorder=0)
    ax.add_patch(ospf_bubble)
    ax.text(8.6, 7.7, "OSPF Domain\n(Area 0)", fontsize=9.5, fontweight="bold", color="#1d4ed8", ha="center")

    routers = [
        (1.6, 4.8, "R1\n(Branch Core)", "#10b981"),
        (4.8, 7.3, "R2\n(ASBR-1)", "#6366f1"),
        (4.8, 2.3, "R3\n(ASBR-2)", "#6366f1"),
        (8.4, 4.8, "R4\n(HQ Core)", "#0ea5e9"),
    ]

    def draw_link(r1, r2, label, sub=""):
        ax.plot([r1[0], r2[0]], [r1[1], r2[1]], color="#475569", lw=2, zorder=1)
        mx, my = (r1[0] + r2[0]) / 2, (r1[1] + r2[1]) / 2
        ax.text(mx, my + 0.28, label, fontsize=7.5, fontweight="bold", color="#1e293b", ha="center",
                bbox=dict(boxstyle="round,pad=0.12", fc="#ffffff", ec="none", alpha=0.8), zorder=2)
        if sub:
            ax.text(mx, my - 0.25, sub, fontsize=6.7, color="#475569", ha="center", zorder=2)

    draw_link((1.6, 4.8), (4.8, 7.3), "Gig0/1 - Gig0/1", "10.1.12.0/24")
    draw_link((1.6, 4.8), (4.8, 2.3), "Gig0/2 - Gig0/1", "10.1.13.0/24")
    draw_link((4.8, 7.3), (8.4, 4.8), "Gig0/2 - Gig0/1", "10.1.24.0/24")
    draw_link((4.8, 2.3), (8.4, 4.8), "Gig0/2 - Gig0/2", "10.1.34.0/24")
    draw_link((4.8, 7.3), (4.8, 2.3), "Gig0/3 - Gig0/3", "10.1.23.0/24 (Inter-ASBR)")

    for x, y, label, col in routers:
        circle = patches.Circle((x, y), 0.72, ec=col, fc="#ffffff", lw=2.5, zorder=3)
        ax.add_patch(circle)
        ax.text(x, y, label, ha="center", va="center", fontsize=8.0, fontweight="bold", color="#0f172a", zorder=4)

    ax.text(4.8, 9.0, "Dual Mutual Redistribution: EIGRP AS 100 <---> OSPF Area 0\n"
                      "Route-Tagging: Tag 110 / 120  |  AD Tuning: distance ospf external 171",
            ha="center", va="center", fontsize=7.6, fontweight="bold", color="#4338ca",
            bbox=dict(boxstyle="round,pad=0.3", fc="#e0e7ff", ec="#6366f1", lw=1.2), zorder=5)

    ax.set_title("Fig 5.1: CCNP Enterprise Dual-Point Mutual Route Redistribution Topology",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_5_1_redistribution_topology.png", dpi=300)
    plt.close()


def generate_web_dashboard():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    frame = patches.FancyBboxPatch((0.4, 0.4), 9.2, 9.2, boxstyle="square,pad=0",
                                   ec="#cbd5e1", fc="#ffffff", lw=2)
    ax.add_patch(frame)

    navbar = patches.Rectangle((0.4, 8.85), 9.2, 0.75, fc="#1e293b", ec="#cbd5e1", lw=1)
    ax.add_patch(navbar)
    ax.text(0.7, 9.22, "Ticket-to-Topology (t2t) Live Dashboard  |  Read-Only Audit & Status Monitor (127.0.0.1)",
            fontsize=8.5, fontweight="bold", color="#ffffff", va="center")

    topo_panel = patches.Rectangle((0.7, 0.9), 5.3, 7.6, fc="#f8fafc", ec="#e2e8f0", lw=1.5)
    ax.add_patch(topo_panel)
    ax.text(3.35, 8.1, "Dynamic SVG Topology Map (Real-Time Health)", ha="center", fontsize=8.2, fontweight="bold", color="#1e3a8a")

    ax.plot([1.8, 3.35], [4.9, 6.6], color="#16a34a", lw=3, zorder=2)
    ax.plot([1.8, 3.35], [4.9, 3.2], color="#eab308", lw=3, zorder=2)
    ax.plot([3.35, 4.9], [6.6, 4.9], color="#16a34a", lw=3, zorder=2)
    ax.plot([3.35, 4.9], [3.2, 4.9], color="#dc2626", lw=3, zorder=2)
    ax.plot([3.35, 3.35], [6.6, 3.2], color="#16a34a", lw=3, zorder=2)

    nodes = [(1.8, 4.9, "R1"), (3.35, 6.6, "R2"), (3.35, 3.2, "R3"), (4.9, 4.9, "R4")]
    for nx, ny, nl in nodes:
        circ = patches.Circle((nx, ny), 0.42, fc="#ffffff", ec="#1e40af", lw=2, zorder=3)
        ax.add_patch(circ)
        ax.text(nx, ny, nl, ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a", zorder=4)

    ax.text(3.35, 1.45, "Link Legend: [Green = Verified]  [Amber = Warning]  [Red = Invariant Fail]",
            ha="center", fontsize=7.2, color="#475569")

    t_panel = patches.Rectangle((6.25, 4.95), 3.1, 3.55, fc="#eff6ff", ec="#bfdbfe", lw=1.5)
    ax.add_patch(t_panel)
    ax.text(6.45, 8.1, "Active Scenario Telemetry", fontsize=8.2, fontweight="bold", color="#1e40af")
    ax.text(6.45, 6.45, "Ticket ID: T3-SUBOPTIMAL-01\nDomain: EIGRP AS 100 <-> OSPF 1\nIssue: OSPF External AD (110)\nDefeats EIGRP External (170)\nStatus: EVALUATING\nPenalty Count: 1 attempt",
            fontsize=7.2, color="#1e293b", va="center")

    h_panel = patches.Rectangle((6.25, 0.9), 3.1, 3.75, fc="#f1f5f9", ec="#e2e8f0", lw=1.5)
    ax.add_patch(h_panel)
    ax.text(6.45, 4.25, "Audit & Invariant History", fontsize=8.2, fontweight="bold", color="#0f172a")
    ax.text(6.45, 2.55, "14:22:01 - Audit Engine: Rule A4 FAIL\n14:22:05 - Verification: c_t3_r3 FAIL\n14:23:10 - Remediation Pushed (R3)\n14:23:12 - Verification: PASS (100%)\nFinal Score: 94.2 / 100",
            fontsize=6.9, color="#334155", va="center", family="monospace")

    ax.set_title("Fig 5.2: FastAPI Lightweight Web Interface Mockup with Interactive SVG Canvas",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_5_2_web_dashboard.png", dpi=300)
    plt.close()


def generate_state_machine():
    fig, ax = plt.subplots(figsize=(10, 4.3), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    states = [
        (1.1, 5.0, "IDLE"),
        (3.4, 5.0, "ACTIVE\n(Fault Injected)"),
        (6.0, 7.6, "EVALUATING\n(Verification)"),
        (8.8, 7.6, "RESOLVED\n(Scored)"),
        (6.0, 2.4, "ACTIVE\n(Feedback & Retry)"),
        (8.8, 2.4, "EXPIRED\n(Timeout)"),
    ]

    for x, y, label in states:
        box = patches.FancyBboxPatch((x - 0.95, y - 0.72), 1.9, 1.44, boxstyle="round,pad=0.16",
                                     ec="#1e3a8a", fc="#f8fafc", lw=1.6, zorder=2)
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center", fontsize=8, fontweight="bold", color="#1e3a8a", zorder=3)

    def draw_trans(x1, y1, x2, y2, text, dx=0.0, dy=0.35):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#2563eb", lw=1.6), zorder=4)
        ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, text,
                ha="center", va="center", fontsize=7.3, fontweight="bold", color="#0f172a", zorder=5)

    draw_trans(2.15, 5.0, 2.38, 5.0, "t2t new-ticket", dy=0.55)
    draw_trans(4.45, 5.5, 4.95, 7.2, "t2t submit", dx=-0.35, dy=0.3)
    draw_trans(7.05, 7.6, 7.75, 7.6, "All Pass", dy=0.45)
    draw_trans(6.0, 6.75, 6.0, 3.25, "Check Fails", dx=0.68, dy=0.0)
    draw_trans(4.95, 2.6, 4.15, 4.2, "Retry Config", dx=-0.45, dy=-0.2)
    draw_trans(7.05, 2.4, 7.75, 2.4, "Timeout", dy=-0.45)

    ax.set_title("Fig 5.3: Finite State Machine (FSM) Lifecycle Diagram",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_5_3_state_machine.png", dpi=300)
    plt.close()


def generate_er_diagram():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    entities = [
        (2.2, 7.6, 3.5, 2.3, "SESSION",
         "session_id (PK): TEXT\nfault_id: TEXT\nstatus: TEXT\nstarted_at: TIMESTAMP\ncompleted_at: TIMESTAMP"),
        (7.8, 7.6, 3.5, 2.3, "ATTEMPT",
         "attempt_id (PK): INTEGER\nsession_id (FK): TEXT\nsubmitted_config: TEXT\nast_diff_penalty: REAL\ntimestamp: TIMESTAMP"),
        (2.2, 2.4, 3.5, 2.3, "VERIFICATION_LOG",
         "log_id (PK): INTEGER\nsession_id (FK): TEXT\ncheck_id: TEXT\nstatus: TEXT (PASS/FAIL)\nobserved_value: TEXT"),
        (7.8, 2.4, 3.5, 2.3, "SCORE_RECORD",
         "score_id (PK): INTEGER\nsession_id (FK): TEXT\nfinal_score: REAL\ntime_decay: REAL\nawarded_at: TIMESTAMP"),
    ]

    for x, y, w, h, name, attrs in entities:
        box = patches.FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="square,pad=0",
                                     ec="#047857", fc="#ffffff", lw=1.6, zorder=2)
        ax.add_patch(box)
        hdr = patches.Rectangle((x - w / 2, y + h / 2 - 0.52), w, 0.52, fc="#d1fae5", ec="#047857", lw=1.6, zorder=3)
        ax.add_patch(hdr)
        ax.text(x, y + h / 2 - 0.26, name, ha="center", va="center", fontsize=8.8, fontweight="bold", color="#065f46", zorder=4)
        ax.text(x - w / 2 + 0.14, y - 0.22, attrs, ha="left", va="center", fontsize=7.4, color="#0f172a", family="monospace", zorder=4)

    ax.plot([3.95, 6.05], [7.6, 7.6], color="#047857", lw=1.6, zorder=1)
    ax.text(5.0, 7.85, "1 : N (Submissions)", ha="center", va="bottom", fontsize=7.6, fontweight="bold", color="#047857")

    ax.plot([2.2, 2.2], [6.45, 3.55], color="#047857", lw=1.6, zorder=1)
    ax.text(2.35, 5.0, "1 : N (Checks)", ha="left", va="center", fontsize=7.6, fontweight="bold", color="#047857")

    ax.plot([3.95, 6.05], [6.45, 3.55], color="#047857", lw=1.6, ls="--", zorder=1)
    ax.text(5.4, 5.1, "1 : 1 (Outcome)", ha="left", va="center", fontsize=7.6, fontweight="bold", color="#047857")

    ax.set_title("Fig 5.4: SQLite WAL Session Store Entity-Relationship (ER) Schema",
                 fontsize=11.5, fontweight="bold", color="#1b365d", pad=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig_5_4_er_diagram.png", dpi=300)
    plt.close()


if __name__ == "__main__":
    generate_gantt_chart()
    generate_use_case_diagram()
    generate_architecture_diagram()
    generate_activity_diagram()
    generate_class_diagram()
    generate_sequence_diagram()
    generate_topology_diagram()
    generate_web_dashboard()
    generate_state_machine()
    generate_er_diagram()
    print(f"All 10 figures generated cleanly in {FIG_DIR}")
