"""Destructive reset of all captured data, across the ODS and the warehouse.

Scope:
- ODS: `brands`, `places` and `competitors` are dropped and recreated empty,
  so a reset really is a clean slate (ids restart at 1).
- Warehouse: the DuckDB file itself is removed. That takes out raw, bronze,
  silver, gold, the `places_history` snapshot and `_sync_watermarks` together,
  which is what forces the next ingest to reload everything from scratch.

Deliberately preserved:
- `app_settings`, so the Google Places API key survives a reset.
- `worldcities`, the reference table behind the city/country selectors.

Deletes in the ODS never propagate on their own (raw sync is watermark-based
and only sees rows that exist), so the warehouse must be cleared alongside it.
"""

import sqlite3
from pathlib import Path

from whitespace_analyzer.analytics.duckdb_ingest import DEFAULT_DUCKDB_PATH
from whitespace_analyzer.ods.database import init_schema

# Children before parents, so both DELETE and DROP satisfy the foreign keys.
DATA_TABLES: tuple[str, ...] = ("places", "competitors", "brands")


def ods_data_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Row counts per captured table, for before/after reporting."""
    init_schema(conn)
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in DATA_TABLES
    }


def clear_ods(conn: sqlite3.Connection) -> dict[str, int]:
    """Drop and recreate the captured tables. Returns rows removed per table."""
    removed = ods_data_counts(conn)
    for table in DATA_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    init_schema(conn)
    conn.commit()
    return removed


def clear_warehouse(warehouse_path: Path | str = DEFAULT_DUCKDB_PATH) -> bool:
    """Delete the DuckDB warehouse file. Returns True when one existed."""
    path = Path(warehouse_path)
    existed = path.exists()
    for candidate in (path, Path(f"{path}.wal")):
        candidate.unlink(missing_ok=True)
    return existed
