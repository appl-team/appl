import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from litellm import ModelResponse
from loguru import logger

from ..core.config import configs
from ..core.globals import global_vars
from .utils import dict_to_pydantic, encode_to_uuid_v5, pydantic_to_dict


class DBCache:
    """SQLite-based caching implementation."""

    def __init__(
        self,
        db_path: str = "cache.db",
        max_size: Optional[int] = None,
        time_to_live: Optional[int] = None,
        cleanup_interval: Optional[int] = None,
    ):
        """Initialize the database cache.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.max_size = max_size or configs.getattrs(
            "settings.caching.max_size", 100000
        )
        self.time_to_live = time_to_live or configs.getattrs(
            "settings.caching.time_to_live", 43200
        )
        self.cleanup_interval = cleanup_interval or configs.getattrs(
            "settings.caching.cleanup_interval", 1440
        )
        self._init_db()
        self._init_cleanup_tracker()
        self._maybe_cleanup()

    def _init_db(self) -> None:
        """Initialize the database and create the cache table if it doesn't exist."""
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    uuid TEXT PRIMARY KEY,
                    key TEXT,
                    value TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _init_cleanup_tracker(self) -> None:
        """Initialize the cleanup tracker table."""
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cleanup_tracker (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_cleanup DATETIME
                )
            """)
            # Insert initial cleanup time if not exists
            conn.execute("""
                INSERT OR IGNORE INTO cleanup_tracker (id, last_cleanup)
                VALUES (1, CURRENT_TIMESTAMP)
            """)

    def _should_cleanup(self, now: Optional[datetime] = None) -> bool:
        """Check if cleanup should be performed based on the last cleanup time."""
        with self.connect() as conn:
            now = now or datetime.now()
            cursor = conn.execute(
                "SELECT last_cleanup FROM cleanup_tracker WHERE id = 1"
            )
            last_cleanup = datetime.fromisoformat(cursor.fetchone()[0])
            return now - last_cleanup > timedelta(minutes=self.cleanup_interval)

    def _update_cleanup_time(self, now: Optional[datetime] = None) -> None:
        """Update the last cleanup timestamp."""
        with self.connect() as conn:
            now = now or datetime.now()
            conn.execute(
                """
                UPDATE cleanup_tracker 
                SET last_cleanup = ? 
                WHERE id = 1
                """,
                (now.isoformat(),),
            )

    def _maybe_cleanup(self, now: Optional[datetime] = None) -> None:
        """Perform cleanup if enough time has passed since last cleanup."""
        if self._should_cleanup(now=now):
            self._cleanup(now=now)
            self._update_cleanup_time(now=now)

    def _cleanup(self, now: Optional[datetime] = None) -> None:
        """Remove expired entries and enforce size limit."""
        with self.connect() as conn:
            # Remove expired entries
            now = now or datetime.now()
            expiry_time = now - timedelta(minutes=self.time_to_live)
            print("exp", expiry_time)
            conn.execute(
                "DELETE FROM cache WHERE timestamp < ?", (expiry_time.isoformat(),)
            )

            # Enforce size limit by removing oldest entries
            conn.execute(
                """
                DELETE FROM cache 
                WHERE uuid IN (
                    SELECT uuid FROM cache 
                    ORDER BY timestamp ASC 
                    LIMIT max(0, (SELECT COUNT(*) FROM cache) - ?)
                )
            """,
                (self.max_size,),
            )

    def connect(self) -> sqlite3.Connection:
        """Create and return a database connection.

        Returns:
            sqlite3.Connection: Database connection object
        """
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        return sqlite3.connect(self.db_path)

    def find(self, key: str) -> Optional[Any]:
        """Find a value in the cache by key.

        Args:
            key: Cache key to look up

        Returns:
            The cached value if found, None otherwise
        """
        self._maybe_cleanup()  # Only clean if needed

        uuid = encode_to_uuid_v5(key)

        with self.connect() as conn:
            cursor = conn.execute(
                "SELECT key, value FROM cache WHERE uuid = ?", (uuid,)
            )
            result = cursor.fetchone()

            if result is None:
                return None

            stored_key, value = result
            assert stored_key == key
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

    def write(self, key: str, value: Any, timestamp: Optional[datetime] = None) -> None:
        """Write a value to the cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
        """
        self._maybe_cleanup()  # Only clean if needed

        uuid = encode_to_uuid_v5(key)

        serialized_value = json.dumps(value)
        if timestamp is None:
            timestamp = datetime.now()

        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache (uuid, key, value, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (uuid, key, serialized_value, timestamp.isoformat()),
            )


def find_in_cache(
    args: Dict, cache: Optional[DBCache] = None
) -> Optional[ModelResponse]:
    """Find a value in the LLM cache by key.

    Args:
        args: The arguments of the completion.
        cache: The cache to search in. Defaults to the global LLM cache.

    Returns:
        The completion result if found, otherwise None.
    """
    cache = cache or getattr(global_vars, "llm_cache", None)
    if cache is None:
        return None
    if args.get("temperature", 1.0) > 0.0 and not configs.getattrs(
        "settings.caching.allow_temp_greater_than_0", False
    ):
        return None
    # only cache the completions with temperature == 0
    value = cache.find(json.dumps(args))
    if value is None:
        return None
    return dict_to_pydantic(value, ModelResponse)


def add_to_cache(
    args: Dict, value: ModelResponse, cache: Optional[DBCache] = None
) -> None:
    """Add a value to the LLM cache."""
    cache = cache or getattr(global_vars, "llm_cache", None)
    if cache is None:
        logger.warning("No cache to add to")
        return
    if args.get("temperature", 1.0) > 0.0 and not configs.getattrs(
        "settings.caching.allow_temp_greater_than_0", False
    ):
        return
    args_str = json.dumps(args)
    value_dict = pydantic_to_dict(value)
    logger.info(f"Adding to cache, args: {args_str}, value: {value_dict}")
    cache.write(args_str, value_dict)
