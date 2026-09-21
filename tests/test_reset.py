from whitespace_analyzer.analytics import duckdb_ingest as di
from whitespace_analyzer.ods.brands import list_brands, save_brand
from whitespace_analyzer.ods.competitors import add_competitor
from whitespace_analyzer.ods.database import get_connection
from whitespace_analyzer.ods.reset import clear_ods, clear_warehouse, ods_data_counts
from whitespace_analyzer.ods.settings import get_setting, set_setting


def _ods_path(tmp_path):
    return tmp_path / "ods.sqlite"


def _populate(tmp_path):
    conn = get_connection(_ods_path(tmp_path))
    kfc = save_brand(conn, "KFC", "pizza")
    popeyes = save_brand(conn, "Popeyes", "pizza")
    add_competitor(conn, kfc, popeyes)
    conn.execute(
        "INSERT INTO places (brand_id, place_id, name) VALUES (?, 'p1', 'KFC A')",
        (kfc,),
    )
    conn.execute(
        "INSERT INTO worldcities (id, city, country) "
        "VALUES ('1', 'New York', 'United States')"
    )
    conn.commit()
    set_setting(conn, "google_places_api_key", "secret-key")
    return conn


def test_clear_ods_removes_captured_data(tmp_path):
    conn = _populate(tmp_path)
    assert ods_data_counts(conn) == {"places": 1, "competitors": 1, "brands": 2}

    removed = clear_ods(conn)

    assert removed == {"places": 1, "competitors": 1, "brands": 2}
    assert ods_data_counts(conn) == {"places": 0, "competitors": 0, "brands": 0}
    assert list_brands(conn) == []


def test_clear_ods_keeps_settings_and_reference_data(tmp_path):
    conn = _populate(tmp_path)
    clear_ods(conn)

    assert get_setting(conn, "google_places_api_key") == "secret-key"
    assert conn.execute("SELECT COUNT(*) FROM worldcities").fetchone()[0] == 1


def test_clear_ods_restarts_ids(tmp_path):
    conn = _populate(tmp_path)
    clear_ods(conn)

    assert save_brand(conn, "KFC", "pizza") == 1


def test_clear_ods_is_idempotent(tmp_path):
    conn = _populate(tmp_path)
    clear_ods(conn)

    assert clear_ods(conn) == {"places": 0, "competitors": 0, "brands": 0}


def test_clear_warehouse_deletes_file_and_wal(tmp_path):
    warehouse = tmp_path / "warehouse.duckdb"
    warehouse.write_bytes(b"duckdb")
    wal = tmp_path / "warehouse.duckdb.wal"
    wal.write_bytes(b"wal")

    assert clear_warehouse(warehouse) is True
    assert not warehouse.exists()
    assert not wal.exists()


def test_clear_warehouse_without_file_returns_false(tmp_path):
    assert clear_warehouse(tmp_path / "warehouse.duckdb") is False


def test_reset_then_reingest_reloads_everything(tmp_path):
    conn = _populate(tmp_path)
    ods = _ods_path(tmp_path)
    warehouse = tmp_path / "warehouse.duckdb"

    di.ingest_ods_to_duckdb(ods, warehouse)
    assert di.ingest_ods_to_duckdb(ods, warehouse)["places"] == 0

    clear_ods(conn)
    clear_warehouse(warehouse)

    brand_id = save_brand(conn, "KFC", "pizza")
    conn.execute(
        "INSERT INTO places (brand_id, place_id, name) VALUES (?, 'p1', 'KFC A')",
        (brand_id,),
    )
    conn.commit()

    assert di.ingest_ods_to_duckdb(ods, warehouse) == {
        "brands": 1,
        "places": 1,
        "competitors": 0,
        "app_settings": 1,
    }
