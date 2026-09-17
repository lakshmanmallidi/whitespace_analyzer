from whitespace_analyzer.ods.database import (
    get_connection,
    seed_worldcities,
    worldcities_count,
)

HEADER = "city,city_ascii,lat,lng,country,iso2,iso3,admin_name,capital,population,id\n"


def _write_csv(path):
    path.write_text(
        HEADER
        + "Tokyo,Tokyo,35.6850,139.7514,Japan,JP,JPN,Tōkyō,primary,39105000,1392685764\n"
        + "Nīlī,Nili,33.7218,66.1302,Afghanistan,AF,AFG,Dāykundī,admin,,1004642532\n",
        encoding="utf-8",
    )


def test_seed_loads_csv_with_types(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    assert worldcities_count(conn) == 0

    csv_path = tmp_path / "cities.csv"
    _write_csv(csv_path)
    inserted = seed_worldcities(conn, csv_path)

    assert inserted == 2
    assert worldcities_count(conn) == 2
    row = conn.execute(
        "SELECT * FROM worldcities WHERE id = '1392685764'"
    ).fetchone()
    assert row["city"] == "Tokyo"
    assert row["lat"] == 35.685
    assert row["lng"] == 139.7514
    assert row["population"] == 39105000
    empty_pop = conn.execute(
        "SELECT population FROM worldcities WHERE id = '1004642532'"
    ).fetchone()
    assert empty_pop["population"] is None


def test_seed_is_idempotent_and_tmp_conn_does_not_autoseed(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    assert worldcities_count(conn) == 0  # tmp DBs never auto-seed

    csv_path = tmp_path / "cities.csv"
    _write_csv(csv_path)
    assert seed_worldcities(conn, csv_path) == 2
    assert seed_worldcities(conn, csv_path) == 0
    assert worldcities_count(conn) == 2


def test_seed_missing_csv_is_noop(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    assert seed_worldcities(conn, tmp_path / "nope.csv") == 0
    assert worldcities_count(conn) == 0
