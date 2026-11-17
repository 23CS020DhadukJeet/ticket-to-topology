"""Unit tests for Phase 6 SQLite store and schema migrations (U6.3)."""

import sqlite3
from pathlib import Path

from t2t.ai.sink import AICallRecord
from t2t.session.store import SQLiteStore


def test_u6_3_store_initialization_and_pragmas(tmp_path: Path) -> None:
    """Verify tables are created with WAL journal mode and foreign keys enabled."""
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)

    # Check journal mode is WAL
    with sqlite3.connect(db_file) as conn:
        cursor = conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0].lower() == "wal"

    # Check store connection enforces foreign keys
    with store._get_connection() as conn:
        cursor = conn.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1

        # Check tables exist
        tables_cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in tables_cursor.fetchall()}
        expected_tables = {
            "schema_version",
            "sessions",
            "command_log",
            "check_results",
            "ai_calls",
        }
        assert expected_tables.issubset(tables)

        # Check version
        v_cursor = conn.execute("SELECT version FROM schema_version")
        version = v_cursor.fetchone()[0]
        assert version >= 2


def test_u6_3_migration_v1_to_v2(tmp_path: Path) -> None:
    """Verify forward-only migration from sample v1 database to v2."""
    db_file = tmp_path / "v1_sample.db"

    # Manually create a v1 database
    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("CREATE TABLE schema_version(version INTEGER NOT NULL);")
        conn.execute("INSERT INTO schema_version(version) VALUES (1);")
        conn.execute(
            """
            CREATE TABLE sessions(id INTEGER PRIMARY KEY, fault_id TEXT, level INTEGER,
              started_at TEXT, finished_at TEXT, status TEXT, hints_used INTEGER,
              failed_submits INTEGER, explanation TEXT, tech_score INTEGER,
              ai_score INTEGER, final_score INTEGER, seconds INTEGER);
            """
        )
        conn.execute(
            """
            CREATE TABLE command_log(id INTEGER PRIMARY KEY, session_id INTEGER, router TEXT,
              kind TEXT, command TEXT, ts TEXT);
            """
        )
        conn.execute(
            """
            CREATE TABLE check_results(id INTEGER PRIMARY KEY, session_id INTEGER, attempt INTEGER,
              check_id TEXT, passed INTEGER, observed TEXT);
            """
        )
        conn.execute(
            """
            CREATE TABLE ai_calls(id INTEGER PRIMARY KEY, session_id INTEGER, purpose TEXT,
              provider TEXT, model TEXT, prompt_version TEXT, latency_ms INTEGER, ok INTEGER);
            """
        )
        # Insert a sample v1 session
        conn.execute(
            """
            INSERT INTO sessions(fault_id, level, started_at, status, hints_used, failed_submits)
            VALUES ('T3', 2, '2026-11-17T10:00:00Z', 'ACTIVE', 1, 0);
            """
        )
        conn.commit()

    # Now open with SQLiteStore; it must migrate to v2
    store = SQLiteStore(db_file)
    assert store.get_session(1) is not None
    with sqlite3.connect(db_file) as conn:
        v_cursor = conn.execute("SELECT version FROM schema_version")
        assert v_cursor.fetchone()[0] == 2

        # Check session persisted through migration
        sess_cursor = conn.execute("SELECT fault_id, level, status FROM sessions WHERE id = 1")
        row = sess_cursor.fetchone()
        assert row[0] == "T3"
        assert row[1] == 2
        assert row[2] == "ACTIVE"


def test_u6_3_session_roundtrip_and_ai_call_sink(tmp_path: Path) -> None:
    """Verify session CRUD, check results, command logging, and AICallSink."""
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)

    # 1. Create session
    sess_id = store.create_session(fault_id="T3", level=2, started_at="2026-11-17T12:00:00Z")
    assert sess_id == 1

    # 2. Get active session
    sess = store.get_session(sess_id)
    assert sess is not None
    assert sess["fault_id"] == "T3"
    assert sess["level"] == 2
    assert sess["status"] == "ACTIVE"

    # 3. Record command
    store.record_command(
        session_id=sess_id,
        router="R3",
        kind="config",
        command="distance ospf external 171",
        ts="2026-11-17T12:05:00Z",
    )

    # 4. Record check results
    store.record_check_result(
        session_id=sess_id,
        attempt=1,
        check_id="c1",
        passed=True,
        observed="10.10.99.0/24 via 10.1.13.1",
    )

    # 5. Log AI call via AICallSink interface
    store.set_active_session_id(sess_id)
    store.log_call(
        AICallRecord(
            purpose="generate_hint",
            provider="GeminiProvider",
            model="gemini-2.0-flash",
            prompt_version="mentor_v1",
            latency_ms=350,
            ok=True,
        )
    )

    # 6. Update session on completion
    store.update_session(
        sess_id,
        finished_at="2026-11-17T12:10:00Z",
        status="SOLVED",
        hints_used=1,
        failed_submits=0,
        explanation="Restored OSPF external distance to 171.",
        tech_score=60,
        ai_score=40,
        final_score=100,
        seconds=600,
    )

    updated = store.get_session(sess_id)
    assert updated is not None
    assert updated["status"] == "SOLVED"
    assert updated["final_score"] == 100

    # 7. Query history and stats
    history = store.get_history()
    assert len(history) == 1
    assert history[0]["fault_id"] == "T3"
    assert history[0]["final_score"] == 100

    stats = store.get_history_stats()
    assert stats["total_sessions"] == 1
    assert stats["solved_count"] == 1
    assert stats["average_score"] == 100.0
