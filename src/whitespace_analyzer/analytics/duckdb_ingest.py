"""Incremental ODS (SQLite) → warehouse (DuckDB) ingestion.

Raw ingestion lands in the `raw` schema of the warehouse; dbt models then
build bronze/silver/gold layers on top.

Sync strategy per table (watermark + merge):
- Each incremental table has a watermark column and a primary-key column.
- A run loads only rows newer than the stored watermark into a temp delta,
  then deletes-and-reinserts those keys in `raw`. So updated rows (e.g. a
  place re-fetched with a higher updated_at) REPLACE the existing raw row
  keyed on place_id instead of appending a duplicate.
- worldcities is NOT synced here: it is loaded by dbt from
  dbt/seeds/worldcities.csv (`dbt seed`).

Watermarks live in DuckDB table `_sync_watermarks(table_name, last_sync)`
inside the warehouse file itself (main schema). Caveat: deletes in the ODS
never propagate (watermarks only see rows that exist).
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ODS_PATH = PROJECT_ROOT / "data" / "ods.sqlite"
DEFAULT_DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

RAW_SCHEMA = "raw"

# table → (watermark column, primary-key columns). Note app_settings has
# only updated_at; competitors/brands only created_at. competitors is
# keyed on a composite PK.
INCREMENTAL_TABLES: dict[str, tuple[str, list[str]]] = {
    "brands": ("created_at", ["id"]),
    "places": ("updated_at", ["place_id"]),
    "competitors": ("created_at", ["brand_id", "competitor_id"]),
    "app_settings": ("updated_at", ["key"]),
}

DELTA_TABLE = "_ingest_delta"


def ingest_ods_to_duckdb(
    ods_path: Path | str = DEFAULT_ODS_PATH,
    duckdb_path: Path | str = DEFAULT_DUCKDB_PATH,
) -> dict[str, int]:
    """Sync ODS collections into the raw schema. Returns {table: rows_synced}."""
    ods = Path(ods_path)
    warehouse = Path(duckdb_path)
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    summary: dict[str, int] = {}
    conn = duckdb.connect(str(warehouse))
    try:
        conn.execute("INSTALL sqlite")
        conn.execute("LOAD sqlite")
        conn.execute(
            f"ATTACH IF NOT EXISTS '{ods.as_posix()}' AS ods_db (TYPE sqlite)"
        )
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
        for table, (watermark_col, pk_cols) in INCREMENTAL_TABLES.items():
            _create_dest_if_absent(conn, table)
            last = _watermark(conn, table)
            if last:
                conn.execute(
                    f"CREATE OR REPLACE TEMP TABLE {DELTA_TABLE} AS "
                    f"SELECT * FROM ods_db.{table} WHERE {watermark_col} > ?",
                    [last],
                )
            else:
                conn.execute(
                    f"CREATE OR REPLACE TEMP TABLE {DELTA_TABLE} AS "
                    f"SELECT * FROM ods_db.{table}"
                )
            synced = conn.execute(
                f"SELECT COUNT(*) FROM {DELTA_TABLE}"
            ).fetchone()[0]
            if synced:
                keys = ", ".join(pk_cols)
                conn.execute(
                    f"DELETE FROM {RAW_SCHEMA}.{table} "
                    f"WHERE ({keys}) IN (SELECT {keys} FROM {DELTA_TABLE})"
                )
                conn.execute(
                    f"INSERT INTO {RAW_SCHEMA}.{table} SELECT * FROM {DELTA_TABLE}"
                )
                max_ts = conn.execute(
                    f"SELECT MAX({watermark_col}) FROM {DELTA_TABLE}"
                ).fetchone()[0]
                if max_ts is not None:
                    _set_watermark(conn, table, str(max_ts))
            summary[table] = synced
        return summary
    finally:
        conn.close()


def _create_dest_if_absent(
    conn: duckdb.DuckDBPyConnection, table: str
) -> None:
    try:
        conn.execute(f"DESCRIBE {RAW_SCHEMA}.{table}")
    except duckdb.CatalogException:
        conn.execute(
            f"CREATE TABLE {RAW_SCHEMA}.{table} AS "
            f"SELECT * FROM ods_db.{table} LIMIT 0"
        )


def _watermark(conn: duckdb.DuckDBPyConnection, table: str) -> str | None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _sync_watermarks "
        "(table_name VARCHAR PRIMARY KEY, last_sync TIMESTAMP)"
    )
    row = conn.execute(
        "SELECT last_sync FROM _sync_watermarks WHERE table_name = ?", [table]
    ).fetchone()
    return str(row[0]) if row else None


def _set_watermark(
    conn: duckdb.DuckDBPyConnection, table: str, value: str
) -> None:
    conn.execute(
        "INSERT INTO _sync_watermarks VALUES (?, ?) "
        "ON CONFLICT (table_name) DO UPDATE SET last_sync = excluded.last_sync",
        [table, value],
    )
