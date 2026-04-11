"""
SQLite-backed leaderboard store for CodeReviewEnv.

Replaces the flat JSON file leaderboard.json with a proper SQLite database
using WAL (Write-Ahead Logging) mode for safe concurrent writes.

Benefits over leaderboard.json:
  - WAL mode allows concurrent readers + one writer without corruption
  - Schema enforced at the DB layer
  - Survives Hugging Face Spaces redeployment when mounted as a volume
  - Delta calculation uses a proper query instead of iterating a list

Usage:
    from server.leaderboard_db import leaderboard_db

    entry = leaderboard_db.append_run("gpt-4o", scores, category_scores)
    runs  = leaderboard_db.get_all_runs()
"""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

DB_PATH = Path(os.environ.get("LEADERBOARD_DB", "")) or (
    Path(__file__).parent.parent / "leaderboard.db"
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model           TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL,
    scores_json     TEXT    NOT NULL DEFAULT '{}',
    mean            REAL    NOT NULL DEFAULT 0.0,
    category_json   TEXT    NOT NULL DEFAULT '{}',
    delta_json      TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model);
CREATE INDEX IF NOT EXISTS idx_runs_mean  ON runs(mean DESC);
"""


class LeaderboardDB:
    """
    Thread-safe SQLite leaderboard backend.

    A single connection is shared per process with a module-level lock
    because sqlite3 connections are not thread-safe by default.
    WAL mode allows reads during writes, eliminating most contention.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        self._init_db()

    # ── Init ─────────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create tables and set WAL mode if database doesn't exist."""
        try:
            # Ensure parent directory exists for the SQLite file
            if str(self._path) != ":memory:":
                self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.executescript(_SCHEMA)
        except Exception as e:
            # Non-fatal: fall back to in-memory operations silently
            print(f"LeaderboardDB: init failed ({e}), using in-memory fallback")
            self._path = Path(":memory:")
            with self._connect() as conn:
                conn.executescript(_SCHEMA)

    @contextlib.contextmanager
    def _connect(self):
        """Open a WAL-mode connection, yield it, then commit + close."""
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append_run(
        self,
        model: str,
        scores: dict[str, float],
        category_scores: dict[str, Any] | None = None,
    ) -> dict:
        """
        Append a new run for *model* and return the full entry dict.

        Also computes delta vs. the last run of the same model.
        Thread-safe via module-level lock + WAL mode.
        """
        category_scores = category_scores or {}
        values = [v for v in scores.values() if isinstance(v, (int, float))]
        mean = sum(values) / len(values) if values else 0.0

        # Compute per-category delta vs previous run of same model
        last = self._get_last_run(model)
        delta: dict[str, float] = {}
        if last and last.get("category_scores"):
            for cat, score in category_scores.items():
                if score is not None:
                    prev = last["category_scores"].get(cat, score)
                    if prev is not None:
                        delta[cat] = round(float(score) - float(prev), 4)

        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        with self._lock:
            try:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO runs (model, timestamp, scores_json, mean, category_json, delta_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            model,
                            timestamp,
                            json.dumps(scores),
                            round(mean, 4),
                            json.dumps(category_scores),
                            json.dumps(delta),
                        ),
                    )
            except Exception as e:
                print(f"LeaderboardDB.append_run failed: {e}")

        return {
            "model": model,
            "timestamp": timestamp,
            "scores": scores,
            "mean": round(mean, 4),
            "category_scores": category_scores,
            "delta_from_last_run": delta,
        }

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_all_runs(self) -> list[dict]:
        """Return all runs sorted by mean score descending."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM runs ORDER BY mean DESC"
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            print(f"LeaderboardDB.get_all_runs failed: {e}")
            return []

    def _get_last_run(self, model: str) -> dict | None:
        """Return the most recent run for *model*, or None."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM runs WHERE model=? ORDER BY id DESC LIMIT 1",
                    (model,),
                ).fetchone()
            return self._row_to_dict(row) if row else None
        except Exception:
            return None

    # ── Migration ─────────────────────────────────────────────────────────────

    def import_from_json(self, json_path: Path) -> int:
        """
        One-time migration: import an existing leaderboard.json into the DB.

        Returns the number of rows imported.
        """
        if not json_path.exists():
            return 0
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                runs = json.load(f)
        except Exception:
            return 0

        count = 0
        for run in runs:
            model = run.get("model", "unknown")
            scores = run.get("scores", {})
            cat = run.get("category_scores", {})
            mean = run.get("mean", 0.0)
            timestamp = run.get("timestamp", datetime.datetime.utcnow().isoformat() + "Z")
            delta = run.get("delta_from_last_run", {})
            try:
                with self._lock:
                    with self._connect() as conn:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO runs
                            (model, timestamp, scores_json, mean, category_json, delta_json)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (model, timestamp, json.dumps(scores), mean,
                             json.dumps(cat), json.dumps(delta)),
                        )
                count += 1
            except Exception:
                pass
        return count

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "model": row["model"],
            "timestamp": row["timestamp"],
            "scores": json.loads(row["scores_json"] or "{}"),
            "mean": row["mean"],
            "category_scores": json.loads(row["category_json"] or "{}"),
            "delta_from_last_run": json.loads(row["delta_json"] or "{}"),
        }


# Module-level singleton
leaderboard_db = LeaderboardDB()

# One-time migration from JSON if it exists
_json_path = Path(__file__).parent.parent / "leaderboard.json"
if _json_path.exists():
    _imported = leaderboard_db.import_from_json(_json_path)
    if _imported:
        print(f"LeaderboardDB: imported {_imported} runs from leaderboard.json")
