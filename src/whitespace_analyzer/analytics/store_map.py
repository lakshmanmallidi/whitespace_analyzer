"""Store-grain points for the Reports map.

`brand_performance` is city grain, so it can say how many stores exist in a
city but not where each one is. This reader resolves the individual pins for
one subject brand: its own stores, plus the stores of every brand linked to it
as a competitor in the directed `brand_competitors` edge.
"""

from pathlib import Path

import duckdb
import pandas as pd

from whitespace_analyzer.analytics.brand_performance import WarehouseNotReady
from whitespace_analyzer.analytics.duckdb_ingest import DEFAULT_DUCKDB_PATH

OURS = "Ours"
COMPETITORS = "Competitors"

STORE_MAP_QUERY = """
with subject as (

    select distinct brand_id
    from gold.store_points
    where brand_name = ?

),

rivals as (

    select competitor_id as brand_id
    from gold.brand_competitors
    where brand_id in (select brand_id from subject)

)

select
    p.place_id,
    p.brand_name,
    p.store_name,
    p.formatted_address,
    p.city,
    p.state_name,
    p.country,
    p.longitude,
    p.latitude,
    p.rating,
    p.user_rating_count,
    p.price_level,
    case
        when p.brand_id in (select brand_id from subject) then 'Ours'
        else 'Competitors'
    end as side
from gold.store_points p
where p.brand_id in (select brand_id from subject)
   or p.brand_id in (select brand_id from rivals)
order by side, p.brand_name, p.place_id
"""


def load_store_map(
    subject_brand: str,
    warehouse_path: Path | str = DEFAULT_DUCKDB_PATH,
) -> pd.DataFrame:
    """Our stores and our competitors' stores for one subject brand.

    `side` is 'Ours' for the subject's own pins and 'Competitors' for the rest.
    """
    path = Path(warehouse_path)
    if not path.exists():
        raise WarehouseNotReady(
            "Warehouse not found. Run the ods_to_duckdb DAG, then the "
            "dbt_run DAG."
        )
    conn = duckdb.connect(str(path), read_only=True)
    try:
        return conn.execute(STORE_MAP_QUERY, [subject_brand]).fetch_df()
    except duckdb.CatalogException as exc:
        raise WarehouseNotReady(
            "gold.store_points not found. Run the dbt_run DAG to build the "
            "store map marts."
        ) from exc
    finally:
        conn.close()
