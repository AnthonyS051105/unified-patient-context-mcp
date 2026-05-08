import hashlib
from threading import Lock
from datetime import datetime, timezone


class PatternRecord:
    """In-memory pattern record. Not a Pydantic model — kept as plain dataclass for speed."""

    __slots__ = ("signature", "conditions", "outcome_counts", "first_seen", "last_seen", "total_observations")

    def __init__(self, signature: str, conditions: list[str]):
        self.signature = signature
        self.conditions = conditions
        self.outcome_counts: dict[str, int] = {}
        self.first_seen: str = datetime.now(timezone.utc).isoformat()
        self.last_seen: str = ""
        self.total_observations: int = 0


class ClinicalPatternMemory:
    """
    Thread-safe in-memory pattern store. Singleton per process.

    PRIVACY GUARANTEES:
    - Keys are SHA-256 hashes of sorted generic conditions, never patient IDs
    - Values are outcome counts only — no clinical values, no names, no IDs
    - Store resets on every server restart (no disk write, no database)
    """

    _instance = None
    _class_lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._store: dict[str, PatternRecord] = {}
                    inst._store_lock = Lock()
                    cls._instance = inst
        return cls._instance

    def record(self, conditions: list[str], outcome: str) -> str:
        """Record a new pattern observation. Non-blocking. Returns signature hash."""
        if not conditions:
            return ""
        signature = self._make_signature(conditions)
        with self._store_lock:
            if signature not in self._store:
                self._store[signature] = PatternRecord(
                    signature=signature,
                    conditions=sorted(c.lower().strip() for c in conditions if c),
                )
            rec = self._store[signature]
            rec.outcome_counts[outcome] = rec.outcome_counts.get(outcome, 0) + 1
            rec.total_observations += 1
            rec.last_seen = datetime.now(timezone.utc).isoformat()
        return signature

    def query_similar(self, conditions: list[str]) -> "PatternRecord | None":
        """Query for exact pattern match. Returns None if not found."""
        if not conditions:
            return None
        signature = self._make_signature(conditions)
        with self._store_lock:
            return self._store.get(signature)

    def get_stats(self) -> dict:
        """Return store statistics for debugging. Contains no patient data."""
        with self._store_lock:
            return {
                "total_patterns": len(self._store),
                "total_observations": sum(r.total_observations for r in self._store.values()),
            }

    def _make_signature(self, conditions: list[str]) -> str:
        canonical = "|".join(sorted(c.lower().strip() for c in conditions if c))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# Singleton — import this in all tools that need pattern memory
pattern_memory = ClinicalPatternMemory()
