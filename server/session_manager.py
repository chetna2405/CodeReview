"""
SessionManager — Thread-safe, LRU-evicting session store for CodeReviewEnv.

Solves the critical architectural flaw of the global singleton environment.
Each episode gets its own isolated CodeReviewEnvironment instance, keyed by
episode_id. This enables:
  - Concurrent RL rollout workers without state collision
  - Multiple simultaneous browser sessions
  - Stateless horizontal scaling (promote to Redis-backed store in production)

Usage:
    from server.session_manager import session_manager

    env = session_manager.get_or_create(episode_id)
    env.reset(task_id=...)
    env.step(action)
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.code_review_environment import CodeReviewEnvironment

# Maximum number of concurrent sessions kept in memory.
# At ~5 KB per env instance, 500 sessions ≈ 2.5 MB overhead.
MAX_SESSIONS = 500

# Sessions idle for longer than this (seconds) are eligible for eviction.
SESSION_TTL_SECONDS = 7200  # 2 hours


class _Session:
    """Wraps a CodeReviewEnvironment with access metadata."""

    __slots__ = ("env", "created_at", "last_access")

    def __init__(self, env: "CodeReviewEnvironment") -> None:
        self.env = env
        self.created_at = time.monotonic()
        self.last_access = time.monotonic()

    def touch(self) -> None:
        self.last_access = time.monotonic()

    @property
    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_access


class SessionManager:
    """
    LRU-evicting, thread-safe session store.

    Eviction policy (in order):
    1. Sessions idle longer than SESSION_TTL_SECONDS
    2. Oldest sessions (LRU) when MAX_SESSIONS is reached
    """

    def __init__(
        self,
        max_sessions: int = MAX_SESSIONS,
        ttl_seconds: float = SESSION_TTL_SECONDS,
    ) -> None:
        # OrderedDict preserves insertion order → O(1) LRU eviction
        self._sessions: OrderedDict[str, _Session] = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_sessions
        self._ttl = ttl_seconds

    # ── Public API ───────────────────────────────────────────────────────────

    def get_or_create(self, episode_id: str) -> "CodeReviewEnvironment":
        """
        Return the environment for *episode_id*, creating one if needed.

        Thread-safe. Evicts expired / excess sessions before creating new ones.
        Moves the accessed session to the end of the LRU queue.
        """
        # Import here to avoid circular imports at module load time
        from server.code_review_environment import CodeReviewEnvironment

        with self._lock:
            self._evict_expired()

            if episode_id in self._sessions:
                session = self._sessions[episode_id]
                session.touch()
                # Move to end (most-recently used)
                self._sessions.move_to_end(episode_id)
                return session.env

            # Evict oldest if at capacity
            while len(self._sessions) >= self._max:
                self._sessions.popitem(last=False)  # oldest (LRU) first

            env = CodeReviewEnvironment()
            self._sessions[episode_id] = _Session(env)
            return env

    def remove(self, episode_id: str) -> None:
        """Explicitly remove a session (e.g. after episode completion)."""
        with self._lock:
            self._sessions.pop(episode_id, None)

    def get(self, episode_id: str) -> "CodeReviewEnvironment | None":
        """Return the environment for *episode_id* if it exists, else None."""
        with self._lock:
            session = self._sessions.get(episode_id)
            if session is not None:
                session.touch()
                self._sessions.move_to_end(episode_id)
                return session.env
            return None

    @property
    def active_count(self) -> int:
        """Number of sessions currently tracked (including idle ones)."""
        with self._lock:
            return len(self._sessions)

    @property
    def active_ids(self) -> list[str]:
        """List of active episode IDs (thread-safe snapshot)."""
        with self._lock:
            return list(self._sessions.keys())

    # ── Internal ─────────────────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        """Remove sessions that have exceeded SESSION_TTL_SECONDS of idle time.

        Must be called with self._lock held.
        """
        expired = [
            eid
            for eid, session in self._sessions.items()
            if session.idle_seconds > self._ttl
        ]
        for eid in expired:
            del self._sessions[eid]


# Module-level singleton — one session manager per process
session_manager = SessionManager()
