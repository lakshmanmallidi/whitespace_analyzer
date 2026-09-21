"""Read the gold marts from the DuckDB warehouse for reporting.

The Streamlit control plane reads the SQLite ODS; the Reports tab reads the
warehouse instead, because the analysis lives in the gold layer.
"""

from pathlib import Path

import duckdb
import pandas as pd

from whitespace_analyzer.analytics.duckdb_ingest import DEFAULT_DUCKDB_PATH

BRAND_PERFORMANCE = "gold.brand_performance"


class WarehouseNotReady(RuntimeError):
    """Raised when the warehouse or a required mart has not been built yet."""


def load_brand_performance(
    warehouse_path: Path | str = DEFAULT_DUCKDB_PATH,
) -> pd.DataFrame:
    """brand_performance as a DataFrame: brand × city × state × country."""
    path = Path(warehouse_path)
    if not path.exists():
        raise WarehouseNotReady(
            "Warehouse not found. Run the ods_to_duckdb DAG, then the "
            "dbt_run DAG."
        )
    conn = duckdb.connect(str(path), read_only=True)
    try:
        return conn.execute(f"SELECT * FROM {BRAND_PERFORMANCE}").fetch_df()
    except duckdb.CatalogException as exc:
        raise WarehouseNotReady(
            f"{BRAND_PERFORMANCE} not found. Run the dbt_run DAG to build it."
        ) from exc
    finally:
        conn.close()
