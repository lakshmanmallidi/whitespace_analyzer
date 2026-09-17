import sqlite3

from whitespace_analyzer.ods.database import init_schema

ALL_COUNTRIES = "All countries"
ALL_CITIES = "All cities"


def list_countries(conn: sqlite3.Connection) -> list[str]:
    init_schema(conn)
    rows = conn.execute(
        "SELECT DISTINCT country FROM worldcities "
        "WHERE country IS NOT NULL AND country != '' ORDER BY country"
    ).fetchall()
    return [row["country"] for row in rows]


def list_cities(conn: sqlite3.Connection, country: str | None = None) -> list[str]:
    init_schema(conn)
    if not country or country == ALL_COUNTRIES:
        return []
    rows = conn.execute(
        "SELECT DISTINCT city FROM worldcities WHERE country = ? "
        "AND city IS NOT NULL AND city != '' ORDER BY city",
        (country,),
    ).fetchall()
    return [row["city"] for row in rows]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value in (ALL_COUNTRIES, ALL_CITIES):
        return None
    return value


def build_places_query(
    brand_name: str,
    country: str | None = None,
    city: str | None = None,
) -> str:
    brand = brand_name.strip()
    country_clean = _clean(country)
    city_clean = _clean(city)
    if city_clean and country_clean:
        return f"all {brand} in {city_clean} city in {country_clean}"
    if country_clean:
        return f"all {brand} in {country_clean} in all cities"
    if city_clean:
        return f"all {brand} in {city_clean} city"
    return f"all {brand} stores worldwide"
