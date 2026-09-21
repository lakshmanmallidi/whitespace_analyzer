import duckdb
import pytest

from whitespace_analyzer.analytics import brand_performance as bp


def _warehouse_with_mart(tmp_path):
    path = tmp_path / "warehouse.duckdb"
    conn = duckdb.connect(str(path))
    conn.execute("CREATE SCHEMA gold")
    conn.execute(
        "CREATE TABLE gold.brand_performance "
        "(brand_id BIGINT, city VARCHAR, our_store_count BIGINT)"
    )
    conn.execute(
        "INSERT INTO gold.brand_performance VALUES (1, 'dallas', 2)"
    )
    conn.close()
    return path


def test_loads_brand_performance(tmp_path):
    df = bp.load_brand_performance(_warehouse_with_mart(tmp_path))
    assert list(df["city"]) == ["dallas"]
    assert int(df["our_store_count"].iloc[0]) == 2


def test_missing_warehouse_raises(tmp_path):
    with pytest.raises(bp.WarehouseNotReady):
        bp.load_brand_performance(tmp_path / "absent.duckdb")


def test_missing_mart_raises(tmp_path):
    path = tmp_path / "warehouse.duckdb"
    duckdb.connect(str(path)).close()
    with pytest.raises(bp.WarehouseNotReady):
        bp.load_brand_performance(path)
