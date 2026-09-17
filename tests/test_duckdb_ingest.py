import sqlite3

import duckdb
import pytest

from whitespace_analyzer.analytics import duckdb_ingest as di

NOW = "2026-01-01 00:00:00"
LATER = "2026-02-01 00:00:00"


@pytest.fixture
def ods(tmp_path):
    p = tmp_path / "ods.sqlite"
    conn = sqlite3.connect(p)
    conn.executescript(
        """
        CREATE TABLE brands (
            id INTEGER PRIMARY KEY, brand_name TEXT, created_at TIMESTAMP
        );
        CREATE TABLE places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT NOT NULL UNIQUE,
            name TEXT, rating REAL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute("INSERT INTO brands VALUES (1, 'KFC', ?)", [NOW])
    conn.execute(
        "INSERT INTO places (place_id, name, rating, created_at, updated_at) "
        "VALUES ('p1', 'KFC A', 4.0, ?, ?)",
        [NOW, NOW],
    )
    conn.commit()
    conn.close()
    return p


@pytest.fixture
def tables(monkeypatch):
    monkeypatch.setattr(
        di,
        "INCREMENTAL_TABLES",
        {
            "brands": ("created_at", ["id"]),
            "places": ("updated_at", ["place_id"]),
        },
    )


def test_first_run_full_copy(tmp_path, ods, tables):
    warehouse = tmp_path / "warehouse.duckdb"
    summary = di.ingest_ods_to_duckdb(ods, warehouse)
    assert summary == {"brands": 1, "places": 1}
    wh = duckdb.connect(str(warehouse), read_only=True)
    assert wh.execute("SELECT rating FROM raw.places").fetchone()[0] == 4.0


def test_updated_place_merges_not_duplicates(tmp_path, ods, tables):
    warehouse = tmp_path / "warehouse.duckdb"
    di.ingest_ods_to_duckdb(ods, warehouse)

    conn = sqlite3.connect(ods)
    conn.execute(
        "UPDATE places SET rating = 4.8, updated_at = ? WHERE place_id = 'p1'",
        [LATER],
    )
    conn.commit()
    conn.close()

    summary = di.ingest_ods_to_duckdb(ods, warehouse)
    assert summary["places"] == 1

    wh = duckdb.connect(str(warehouse), read_only=True)
    rows = wh.execute(
        "SELECT rating FROM raw.places WHERE place_id = 'p1'"
    ).fetchall()
    assert len(rows) == 1, "same place_id must merge, not append"
    assert rows[0][0] == 4.8


def test_unchanged_rows_not_resynced(tmp_path, ods, tables):
    warehouse = tmp_path / "warehouse.duckdb"
    di.ingest_ods_to_duckdb(ods, warehouse)
    summary = di.ingest_ods_to_duckdb(ods, warehouse)
    assert summary == {"brands": 0, "places": 0}


def test_new_place_appends(tmp_path, ods, tables):
    warehouse = tmp_path / "warehouse.duckdb"
    di.ingest_ods_to_duckdb(ods, warehouse)

    conn = sqlite3.connect(ods)
    conn.execute(
        "INSERT INTO places (place_id, name, rating, created_at, updated_at) "
        "VALUES ('p2', 'KFC B', 4.5, ?, ?)",
        [LATER, LATER],
    )
    conn.commit()
    conn.close()

    di.ingest_ods_to_duckdb(ods, warehouse)
    wh = duckdb.connect(str(warehouse), read_only=True)
    assert wh.execute("SELECT COUNT(*) FROM raw.places").fetchone()[0] == 2
