import duckdb
import pytest

from whitespace_analyzer.analytics import store_map as sm


def _warehouse(tmp_path, with_edges=True):
    path = tmp_path / "warehouse.duckdb"
    conn = duckdb.connect(str(path))
    conn.execute("CREATE SCHEMA gold")
    conn.execute(
        "CREATE TABLE gold.store_points ("
        "place_id VARCHAR, brand_id BIGINT, brand_name VARCHAR, "
        "store_name VARCHAR, formatted_address VARCHAR, city VARCHAR, "
        "state_name VARCHAR, country VARCHAR, longitude DOUBLE, "
        "latitude DOUBLE, rating DOUBLE, user_rating_count BIGINT, "
        "price_level VARCHAR)"
    )
    conn.execute(
        "INSERT INTO gold.store_points VALUES "
        "('p1', 1, 'dominos', 'D1', 'a', 'new york', 'New York', 'US', "
        "-73.9, 40.7, 4.1, 100, 'PRICE_LEVEL_INEXPENSIVE'), "
        "('p2', 2, 'pizza hut', 'P1', 'b', 'new york', 'New York', 'US', "
        "-73.8, 40.8, 3.9, 50, 'PRICE_LEVEL_INEXPENSIVE'), "
        "('p3', 3, 'little caesars', 'L1', 'c', 'bronx', 'New York', 'US', "
        "-73.7, 40.9, 4.4, 20, 'PRICE_LEVEL_MODERATE')"
    )
    if with_edges:
        conn.execute(
            "CREATE TABLE gold.brand_competitors ("
            "brand_id BIGINT, brand_name VARCHAR, competitor_id BIGINT, "
            "competitor_name VARCHAR)"
        )
        conn.execute(
            "INSERT INTO gold.brand_competitors VALUES "
            "(1, 'dominos', 2, 'pizza hut')"
        )
    conn.close()
    return path


def test_subject_with_a_competitor_edge(tmp_path):
    df = sm.load_store_map("dominos", _warehouse(tmp_path))
    sides = dict(zip(df["place_id"], df["side"], strict=True))
    assert sides == {"p1": "Ours", "p2": "Competitors"}
    assert "p3" not in sides, "an unlinked brand must not appear"


def test_subject_without_edges_returns_only_its_own_stores(tmp_path):
    df = sm.load_store_map("little caesars", _warehouse(tmp_path))
    assert set(df["place_id"]) == {"p3"}
    assert set(df["side"]) == {"Ours"}


def test_unknown_brand_returns_nothing(tmp_path):
    df = sm.load_store_map("nobody", _warehouse(tmp_path))
    assert df.empty


def test_missing_warehouse_raises(tmp_path):
    with pytest.raises(sm.WarehouseNotReady):
        sm.load_store_map("dominos", tmp_path / "absent.duckdb")


def test_missing_mart_raises(tmp_path):
    path = tmp_path / "warehouse.duckdb"
    duckdb.connect(str(path)).close()
    with pytest.raises(sm.WarehouseNotReady):
        sm.load_store_map("dominos", path)
