"""FastAPI read-only web dashboard and API for Ticket-to-Topology (Phase 10)."""

import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from t2t.audit.service import AuditService
from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.errors import T2TError
from t2t.parsers.route import parse_route_detail
from t2t.session.service import SessionService
from t2t.session.store import SQLiteStore

KEY_PREFIXES = [
    ("10.10.1.0/24", "10.10.1.0 255.255.255.0"),
    ("10.10.2.0/24", "10.10.2.0 255.255.255.0"),
    ("10.10.99.0/24", "10.10.99.0 255.255.255.0"),
    ("172.16.10.0/24", "172.16.10.0 255.255.255.0"),
    ("172.16.20.16/28", "172.16.20.16 255.255.255.240"),
]


def validate_bind_address(host: str, allow_remote: bool = False, token: str | None = None) -> str:
    """Validate binding host address according to security policies.

    Refuses 0.0.0.0 or :: unless allow_remote is True AND a non-empty token is set.
    """
    clean_host = host.strip()
    if clean_host in ("0.0.0.0", "::"):  # noqa: S104
        if not allow_remote:
            raise ValueError(
                "Refusing to bind to 0.0.0.0 without --allow-remote. "
                "Use 127.0.0.1 for local access."
            )
        if not token or not token.strip():
            raise ValueError(
                "Refusing to bind to 0.0.0.0 without a token. "
                "Set a secure bearer token when allowing remote access."
            )
    return clean_host


def create_app(replay: bool = False, token: str | None = None) -> FastAPI:
    """Factory creating the read-only FastAPI dashboard application.

    Strictly exposes GET endpoints only. No mutation endpoints exist.
    """
    app = FastAPI(
        title="Ticket-to-Topology Read-Only Web Dashboard",
        description="Topology visualization, status monitoring, and session metrics.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url=None,
    )

    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)

    db_path_str = os.environ.get("T2T_DB_PATH")
    db_file = Path(db_path_str) if db_path_str else Path(".t2t/t2t.db")
    store = SQLiteStore(db_file)

    def verify_auth(request: Request) -> None:
        """Verify optional bearer token if configured."""
        if not token:
            return
        auth_header = request.headers.get("Authorization", "")
        bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        query_token = request.query_params.get("token", "")
        if bearer_token != token and query_token != token:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: invalid or missing bearer token.",
            )

    @app.get("/api/status", dependencies=[Depends(verify_auth)])
    def get_status() -> dict[str, Any]:
        """Return redistribution prefix matrix and link health states."""
        service = SessionService(
            settings=settings,
            inventory=inventory,
            replay=replay,
            store=store,
        )
        active_state = service.get_active_state()

        prefix_results: list[dict[str, Any]] = []
        node_routes: dict[str, dict[str, Any]] = {r.name: {} for r in inventory.routers}

        scenario = f"faulted/{active_state.fault_id}" if active_state else "baseline"
        with DeviceSession(
            inventory=inventory,
            settings=settings,
            read_only=True,
            replay=replay,
            scenario=scenario,
        ) as dev_session:
            for prefix_label, prefix_cmd in KEY_PREFIXES:
                row_data: dict[str, Any] = {"prefix": prefix_label, "routers": {}}
                for r in inventory.routers:
                    try:
                        out = dev_session.show(r.name, f"show ip route {prefix_cmd}")
                        route = parse_route_detail(out)
                        if route is None:
                            row_data["routers"][r.name] = {"status": "MISSING"}
                            node_routes[r.name][prefix_label] = None
                        else:
                            r_info = {
                                "status": "PRESENT",
                                "protocol": route.protocol,
                                "distance": route.distance,
                                "tag": route.tag,
                                "next_hops": [h.ip for h in route.next_hops],
                            }
                            row_data["routers"][r.name] = r_info
                            node_routes[r.name][prefix_label] = r_info
                    except T2TError:
                        row_data["routers"][r.name] = {"status": "ERROR"}
                        node_routes[r.name][prefix_label] = None
                prefix_results.append(row_data)

        # Derive link colors: green (optimal), amber (suboptimal/degraded), red (outage/missing)
        # Links: R1-R2, R1-R3, R2-R4, R3-R4
        links: dict[str, str] = {
            "R1-R2": "green",
            "R1-R3": "green",
            "R2-R4": "green",
            "R3-R4": "green",
        }

        # Check for T3 symptom (vendor prefix 10.10.99.0 on R3 has OSPF 110 instead of EIGRP 170)
        r3_vendor = node_routes.get("R3", {}).get("10.10.99.0/24")
        if r3_vendor:
            if r3_vendor.get("protocol") == "ospf":
                links["R1-R3"] = "amber"
                links["R3-R4"] = "amber"
        elif active_state:
            links["R1-R2"] = "amber"

        # Check if prefixes are completely missing -> red
        for r_name in ("R2", "R3"):
            if node_routes.get(r_name, {}).get("10.10.99.0/24") is None:
                links[f"R1-{r_name}"] = "red"
                links[f"{r_name}-R4"] = "red"

        return {
            "prefixes": prefix_results,
            "links": links,
            "topology": {
                "routers": [
                    {"name": r.name, "host": r.host, "role": r.role} for r in inventory.routers
                ]
            },
        }

    @app.get("/api/session", dependencies=[Depends(verify_auth)])
    def get_session() -> dict[str, Any]:
        """Return current troubleshooting session state or idle summary."""
        service = SessionService(
            settings=settings,
            inventory=inventory,
            replay=replay,
            store=store,
        )
        active = service.get_active_state()
        if not active:
            return {"active": False, "session": None}

        fault_model = service._load_fault(active.fault_id)
        return {
            "active": True,
            "session": {
                "session_id": active.session_id,
                "fault_id": active.fault_id,
                "title": fault_model.title,
                "level": active.level,
                "symptom_class": fault_model.symptom_class,
                "hint_level": active.hint_level,
                "failed_submits": active.failed_submits,
                "started_at": active.started_at,
                "business_context": fault_model.business_context,
            },
        }

    @app.get("/api/history", dependencies=[Depends(verify_auth)])
    def get_history() -> dict[str, Any]:
        """Return past troubleshooting history and summary metrics."""
        records = store.get_history(limit=50)
        stats = store.get_history_stats()
        return {"history": records, "stats": stats}

    @app.get("/api/audit/latest", dependencies=[Depends(verify_auth)])
    def get_audit_latest() -> dict[str, Any]:
        """Return latest static configuration audit results."""
        # Check synthetic baseline audit or live audit
        from_dir = Path("tests/synthetic/audit/baseline")
        audit_service = AuditService(
            inventory=inventory,
            settings=settings,
            replay=replay,
        )
        report = audit_service.execute_audit(from_dir=from_dir if from_dir.is_dir() else None)
        return {
            "passed": report.passed,
            "findings_count": len(report.findings),
            "findings": [
                {
                    "rule": f.rule_id,
                    "severity": f.severity,
                    "device": f.device,
                    "message": f.message,
                    "remediation": f.remediation,
                    "exam_topic": f.exam_topic,
                }
                for f in report.findings
            ],
            "devices": report.device_list,
            "timestamp": report.timestamp,
        }

    @app.get("/", response_class=HTMLResponse)
    def get_dashboard() -> str:
        """Render the single-page HTML/SVG topology dashboard."""
        return _render_dashboard_html()

    return app


def _render_dashboard_html() -> str:
    """Produce the standalone HTML/JS dashboard page with interactive SVG."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ticket-to-Topology (t2t) — Live Topology Dashboard</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --green: #22c55e;
      --amber: #eab308;
      --red: #ef4444;
      --cyan: #06b6d4;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 { font-size: 1.5rem; color: var(--cyan); }
    .badge {
      background: var(--card-bg);
      border: 1px solid var(--border);
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 0.85rem;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
    }
    .card h2 { font-size: 1.15rem; margin-bottom: 16px; color: var(--cyan); }
    svg {
      width: 100%;
      height: 380px;
      background: #090d16;
      border-radius: 8px;
    }
    .node-circle { fill: #1e293b; stroke: #38bdf8; stroke-width: 3; }
    .node-text { fill: #f8fafc; font-weight: bold; font-size: 14px; text-anchor: middle; }
    .node-subtext { fill: #94a3b8; font-size: 11px; text-anchor: middle; }
    .link-line { stroke-width: 5; transition: stroke 0.3s; stroke-linecap: round; }
    .link-green { stroke: var(--green); }
    .link-amber { stroke: var(--amber); }
    .link-red { stroke: var(--red); }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }
    th { color: var(--text-muted); font-weight: 600; }
    .status-pill {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: bold;
    }
    .pill-green { background: rgba(34, 197, 94, 0.2); color: var(--green); }
    .pill-amber { background: rgba(234, 179, 8, 0.2); color: var(--amber); }
    .pill-red { background: rgba(239, 68, 68, 0.2); color: var(--red); }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Ticket-to-Topology (t2t)</h1>
      <p style="color: var(--text-muted); font-size: 0.9rem;">
        EIGRP &harr; OSPF Mutual Redistribution Dashboard
      </p>
    </div>
    <div class="badge" id="live-indicator">&bull; Live (Polling 3s)</div>
  </header>

  <div class="grid">
    <!-- Topology SVG Card -->
    <div class="card">
      <h2>Network Redistribution Topology</h2>
      <svg id="topo-svg" viewBox="0 0 700 420">
        <!-- Links -->
        <line id="link-R1-R2" class="link-line link-green" x1="120" y1="210" x2="350" y2="90" />
        <line id="link-R1-R3" class="link-line link-green" x1="120" y1="210" x2="350" y2="330" />
        <line id="link-R2-R4" class="link-line link-green" x1="350" y1="90" x2="580" y2="210" />
        <line id="link-R3-R4" class="link-line link-green" x1="350" y1="330" x2="580" y2="210" />

        <!-- Router R1 (Branch) -->
        <g transform="translate(120, 210)">
          <circle class="node-circle" r="32" />
          <text class="node-text" dy="5">R1</text>
          <text class="node-subtext" dy="48">Branch (EIGRP)</text>
        </g>

        <!-- Router R2 (ASBR 1) -->
        <g transform="translate(350, 90)">
          <circle class="node-circle" r="32" />
          <text class="node-text" dy="5">R2</text>
          <text class="node-subtext" dy="48">ASBR 1 (Dual)</text>
        </g>

        <!-- Router R3 (ASBR 2) -->
        <g transform="translate(350, 330)">
          <circle class="node-circle" r="32" />
          <text class="node-text" dy="5">R3</text>
          <text class="node-subtext" dy="48">ASBR 2 (Dual)</text>
        </g>

        <!-- Router R4 (HQ Core) -->
        <g transform="translate(580, 210)">
          <circle class="node-circle" r="32" />
          <text class="node-text" dy="5">R4</text>
          <text class="node-subtext" dy="48">HQ Core (OSPF)</text>
        </g>
      </svg>
    </div>

    <!-- Active Ticket Card -->
    <div class="card">
      <h2>Active Incident Ticket</h2>
      <div id="ticket-panel">
        <p style="color: var(--text-muted);">Loading active session...</p>
      </div>
    </div>
  </div>

  <div class="grid" style="margin-top: 24px;">
    <!-- Key Prefix Routing Status -->
    <div class="card">
      <h2>Key Prefix Routing Status</h2>
      <table id="prefix-table">
        <thead>
          <tr>
            <th>Prefix</th>
            <th>R1</th>
            <th>R2</th>
            <th>R3</th>
            <th>R4</th>
          </tr>
        </thead>
        <tbody>
          <tr><td colspan="5" style="color: var(--text-muted);">Polling status...</td></tr>
        </tbody>
      </table>
    </div>

    <!-- History & Metrics -->
    <div class="card">
      <h2>Troubleshooting History</h2>
      <div id="stats-summary"
           style="margin-bottom: 12px; font-size: 0.9rem; color: var(--text-muted);"></div>
      <table id="history-table">
        <thead>
          <tr>
            <th>Session</th>
            <th>Fault</th>
            <th>Status</th>
            <th>Score</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          <tr><td colspan="5" style="color: var(--text-muted);">Loading history...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <script>
    async function updateDashboard() {
      try {
        // 1. Status & Links
        const resStatus = await fetch('/api/status');
        if (resStatus.ok) {
          const statusData = await resStatus.json();
          // Update links
          for (const [linkId, color] of Object.entries(statusData.links || {})) {
            const el = document.getElementById('link-' + linkId);
            if (el) {
              el.className = 'link-line link-' + color;
            }
          }
          // Update Prefix Table
          const tbody = document.querySelector('#prefix-table tbody');
          if (tbody && statusData.prefixes) {
            tbody.innerHTML = statusData.prefixes.map(p => {
              return `<tr>
                <td><strong>${p.prefix}</strong></td>
                ${['R1', 'R2', 'R3', 'R4'].map(r => {
                  const info = p.routers[r];
                  if (!info || info.status === 'MISSING') {
                    return `<td><span class="status-pill pill-red">MISSING</span></td>`;
                  }
                  const tag = info.tag ? ` tag ${info.tag}` : '';
                  const proto = info.protocol.toUpperCase();
                  return `<td><span class="status-pill pill-green">${proto}</span> ` +
                         `(${info.distance})${tag}</td>`;
                }).join('')}
              </tr>`;
            }).join('');
          }
        }

        // 2. Active Session
        const resSession = await fetch('/api/session');
        if (resSession.ok) {
          const sessionData = await resSession.json();
          const panel = document.getElementById('ticket-panel');
          if (panel) {
            if (!sessionData.active) {
              panel.innerHTML =
                '<p style="color: var(--green); font-weight: 500;">' +
                '✓ Network Baseline Healthy. No active fault session.</p>' +
                '<p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 8px;">' +
                'Run <code>t2t new-ticket</code> to inject a troubleshooting scenario.</p>';
            } else {
              const s = sessionData.session;
              panel.innerHTML = `
                <div style="margin-bottom: 12px;">
                  <span class="status-pill pill-amber">${s.fault_id}</span>
                  <span class="status-pill pill-green">Level ${s.level}</span>
                  <span style="font-size: 0.85rem; color: var(--text-muted); margin-left: 8px;">
                    Hints: ${s.hint_level}/3
                  </span>
                </div>
                <h3 style="font-size: 1rem; margin-bottom: 8px;">${s.title}</h3>
                <p style="font-size: 0.9rem; margin-bottom: 12px; color: #cbd5e1;">
                  ${s.business_context}
                </p>
                <p style="font-size: 0.8rem; color: var(--text-muted);">Started: ${s.started_at}</p>
              `;
            }
          }
        }

        // 3. History
        const resHistory = await fetch('/api/history');
        if (resHistory.ok) {
          const histData = await resHistory.json();
          const statsDiv = document.getElementById('stats-summary');
          if (statsDiv && histData.stats) {
            const st = histData.stats;
            statsDiv.innerHTML =
              `Total: ${st.total_sessions} | Solved: ${st.solved_count} | ` +
              `Avg Score: ${st.average_score} pts | Avg Time: ${st.average_seconds}s`;
          }
          const histTbody = document.querySelector('#history-table tbody');
          if (histTbody && histData.history) {
            histTbody.innerHTML = histData.history.slice(0, 5).map(h => {
              const pillClass = h.status === 'SOLVED' ? 'pill-green' : 'pill-red';
              const scoreVal = h.final_score !== null ? h.final_score : '-';
              const durVal = h.seconds ? h.seconds + 's' : '-';
              return `
              <tr>
                <td>#${h.id}</td>
                <td>${h.fault_id}</td>
                <td><span class="status-pill ${pillClass}">${h.status}</span></td>
                <td><strong>${scoreVal}</strong></td>
                <td>${durVal}</td>
              </tr>
            `;
            }).join('');
          }
        }
      } catch (err) {
        console.error('Error polling dashboard:', err);
      }
    }

    updateDashboard();
    setInterval(updateDashboard, 3000);
  </script>
</body>
</html>
"""
