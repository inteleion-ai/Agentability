"""FastAPI dependency injection for shared resources.

Provides a process-wide singleton SQLiteStore injected into all route
handlers via FastAPI's ``Depends()`` mechanism.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import os
from functools import lru_cache

from agentability.storage.sqlite_store import SQLiteStore


@lru_cache(maxsize=1)
def get_store() -> SQLiteStore:
    """Return the process-wide SQLiteStore singleton.

    The database path is read from the ``AGENTABILITY_DB`` environment
    variable, defaulting to ``agentability.db`` in the current directory.
    """
    db_path = os.getenv("AGENTABILITY_DB", "agentability.db")
    return SQLiteStore(database_path=db_path)
