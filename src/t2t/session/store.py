"""SQLite persistence store with forward-only migrations and WAL mode.

Per BUILD_GUIDE Phase 6:
Stores sessions, command log, check results, and AI calls.
Implements the AICallSink protocol.
Uses parameterized queries only, foreign keys ON, and WAL mode.
"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from t2t.ai.sink import AICallRecord, AICallSink

DEFAULT_DB_PATH = Path(".t2t/t2t.db")

ALLOWED_SESSION_COLUMNS = {
    "fault_id",
    "level",
    "started_at",
    "finished_at",
    "status",
    "hints_used",
    "failed_submits",
    "explanation",
    "tech_score",
    "ai_score",
    "final_score",
    "seconds",
}


class SQLiteStore(AICallSink):
    """SQLite persistence store with forward-only schema migrations."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._active_session_id: int | None = None
        self._init_db()

    def set_active_session_id(self, session_id: int | None) -> None:
        """Set active session id for correlating incoming AICallRecords."""
        self._active_session_id = session_id

    def _get_connection(self) -> sqlite3.Connection:
        """Open a SQLite connection with foreign keys and WAL mode configured."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a managed database connection that commits and closes cleanly."""
        conn = self._get_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Apply schema migrations to ensure the database is up to date."""
        with self._connection() as conn:
            # Check if schema_version exists
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            table_exists = cur.fetchone() is not None

            if not table_exists:
                self._apply_v1(conn)
                self._apply_v2(conn)
            else:
                cur = conn.execute("SELECT version FROM schema_version")
                row = cur.fetchone()
                current_v = row[0] if row else 0
                if current_v < 1:
                    self._apply_v1(conn)
                if current_v < 2:
                    self._apply_v2(conn)

    def _apply_v1(self, conn: sqlite3.Connection) -> None:
        """Apply initial schema version 1."""
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fault_id TEXT NOT NULL,
                level INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                hints_used INTEGER DEFAULT 0,
                failed_submits INTEGER DEFAULT 0,
                explanation TEXT,
                tech_score INTEGER,
                ai_score INTEGER,
                final_score INTEGER,
                seconds INTEGER
            );
            CREATE TABLE IF NOT EXISTS command_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                router TEXT NOT NULL,
                kind TEXT NOT NULL,
                command TEXT NOT NULL,
                ts TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS check_results(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                attempt INTEGER NOT NULL,
                check_id TEXT NOT NULL,
                passed INTEGER NOT NULL,
                observed TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ai_calls(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                purpose TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                ok INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
            );
            """
        )
        cur = conn.execute("SELECT COUNT(*) FROM schema_version")
        if cur.fetchone()[0] == 0:
            conn.execute("INSERT INTO schema_version(version) VALUES (1)")
        else:
            conn.execute("UPDATE schema_version SET version = 1")
        conn.commit()

    def _apply_v2(self, conn: sqlite3.Connection) -> None:
        """Apply forward migration to version 2 (indices for reporting and queries)."""
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_fault ON sessions(fault_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
            CREATE INDEX IF NOT EXISTS idx_command_log_session ON command_log(session_id);
            CREATE INDEX IF NOT EXISTS idx_check_results_session ON check_results(session_id);
            CREATE INDEX IF NOT EXISTS idx_ai_calls_session ON ai_calls(session_id);
            UPDATE schema_version SET version = 2;
            """
        )
        conn.commit()

    def create_session(self, fault_id: str, level: int, started_at: str) -> int:
        """Record the start of a new troubleshooting session."""
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO sessions (
                    fault_id, level, started_at, status, hints_used, failed_submits
                )
                VALUES (?, ?, ?, 'ACTIVE', 0, 0)
                """,
                (fault_id, level, started_at),
            )
            conn.commit()
            if cur.lastrowid is None:
                raise RuntimeError("Failed to obtain lastrowid for new session")
            return int(cur.lastrowid)

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        """Retrieve a session by its database ID."""
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_session(self, session_id: int, **fields: Any) -> None:
        """Update fields on a session record using parameterised query."""
        if not fields:
            return

        columns = []
        values = []
        for key, val in fields.items():
            if key not in ALLOWED_SESSION_COLUMNS:
                raise ValueError(f"Disallowed session column name: '{key}'")
            columns.append(f"{key} = ?")
            values.append(val)
        values.append(session_id)

        sql = f"UPDATE sessions SET {', '.join(columns)} WHERE id = ?"  # noqa: S608
        with self._connection() as conn:
            conn.execute(sql, tuple(values))
            conn.commit()

    def record_command(
        self,
        session_id: int,
        router: str,
        kind: str,
        command: str,
        ts: str,
    ) -> None:
        """Log a command issued during a troubleshooting session."""
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO command_log (session_id, router, kind, command, ts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, router, kind, command, ts),
            )
            conn.commit()

    def record_check_result(
        self,
        session_id: int,
        attempt: int,
        check_id: str,
        passed: bool,
        observed: str,
    ) -> None:
        """Log verification check outcome for a submission attempt."""
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO check_results (session_id, attempt, check_id, passed, observed)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, attempt, check_id, 1 if passed else 0, observed),
            )
            conn.commit()

    def log_call(self, record: AICallRecord) -> None:
        """Log an AI invocation per the AICallSink protocol."""
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ai_calls
                (session_id, purpose, provider, model, prompt_version, latency_ms, ok)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._active_session_id,
                    record.purpose,
                    record.provider,
                    record.model,
                    record.prompt_version,
                    record.latency_ms,
                    1 if record.ok else 0,
                ),
            )
            conn.commit()

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve completed troubleshooting sessions in reverse chronological order."""
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_history_stats(self) -> dict[str, Any]:
        """Compute aggregate troubleshooting metrics across all sessions."""
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN status = 'SOLVED' THEN 1 ELSE 0 END) as solved_count,
                    AVG(final_score) as avg_score,
                    AVG(seconds) as avg_seconds
                FROM sessions
                """
            )
            row = cur.fetchone()
            if not row or row["total_sessions"] == 0:
                return {
                    "total_sessions": 0,
                    "solved_count": 0,
                    "average_score": 0.0,
                    "average_seconds": 0.0,
                }
            return {
                "total_sessions": row["total_sessions"],
                "solved_count": row["solved_count"] or 0,
                "average_score": round(float(row["avg_score"] or 0.0), 1),
                "average_seconds": round(float(row["avg_seconds"] or 0.0), 1),
            }
