from whitespace_analyzer.ods.database import get_connection
from whitespace_analyzer.ods.geo import (
    ALL_CITIES,
    ALL_COUNTRIES,
    build_places_query,
    list_cities,
    list_countries,
)


def test_countries_sorted_and_nonempty(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    conn.execute(
        "INSERT INTO worldcities (id, city, country) VALUES "
        "('2', 'Mumbai', 'India'), ('1', 'Berlin', 'Germany')"
    )
    conn.commit()
    assert list_countries(conn) == ["Germany", "India"]


def test_cities_filtered_by_country(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    conn.execute(
        "INSERT INTO worldcities (id, city, country) VALUES "
        "('1', 'Mumbai', 'India'), ('2', 'Berlin', 'Germany')"
    )
    conn.commit()
    assert list_cities(conn, "India") == ["Mumbai"]
    assert list_cities(conn, ALL_COUNTRIES) == []
    assert list_cities(conn, None) == []


def test_build_places_query():
    assert (
        build_places_query("Dominos", "India", "Mumbai")
        == "all Dominos in Mumbai city in India"
    )
    assert build_places_query("Dominos", None, "Mumbai") == (
        "all Dominos in Mumbai city"
    )
    assert (
        build_places_query("Dominos", "India", ALL_CITIES)
        == "all Dominos in India in all cities"
    )
    assert (
        build_places_query("Dominos", "India", None)
        == "all Dominos in India in all cities"
    )
    assert (
        build_places_query("Dominos", ALL_COUNTRIES, None)
        == "all Dominos stores worldwide"
    )
