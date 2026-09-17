import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ODS_PATH = PROJECT_ROOT / "data" / "ods.sqlite"
DEFAULT_WORLDCITIES_CSV = PROJECT_ROOT / "dbt" / "seeds" / "worldcities.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL UNIQUE,
    industry_domain TEXT,
    website_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS worldcities (
    id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    city_ascii TEXT,
    lat REAL,
    lng REAL,
    country TEXT,
    iso2 TEXT,
    iso3 TEXT,
    admin_name TEXT,
    capital TEXT,
    population INTEGER
);
CREATE INDEX IF NOT EXISTS idx_worldcities_country ON worldcities(country);
CREATE INDEX IF NOT EXISTS idx_worldcities_city_ascii ON worldcities(city_ascii);
CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    place_id TEXT NOT NULL UNIQUE,
    name TEXT,
    formatted_address TEXT,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    national_phone TEXT,
    international_phone TEXT,
    website_uri TEXT,
    rating REAL,
    user_rating_count INTEGER,
    price_level TEXT,
    business_status TEXT,
    primary_type TEXT,
    types TEXT NOT NULL DEFAULT '[]',
    utc_offset_minutes INTEGER,
    open_now INTEGER,
    weekday_hours TEXT NOT NULL DEFAULT '[]',
    google_maps_uri TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_places_brand_id ON places(brand_id);
CREATE TABLE IF NOT EXISTS competitors (
    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    competitor_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (brand_id, competitor_id)
);
"""


def get_connection(ods_path: Path | str = DEFAULT_ODS_PATH) -> sqlite3.Connection:
    path = Path(ods_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    try:
        if path.resolve() == DEFAULT_ODS_PATH.resolve():
            seed_worldcities(conn)
    except OSError:
        pass
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate_drop_legacy_collections(conn)
    conn.commit()


def _migrate_drop_legacy_collections(conn: sqlite3.Connection) -> None:
    """One-time cleanup after the Google-Places-only pivot.

    Drops the retired locations/contacts/scrape_urls collections; the
    `places` collection replaces them and starts fresh.
    """
    for table in ("locations", "contacts", "scrape_urls"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    _migrate_places_columns(conn)


def _migrate_places_columns(conn: sqlite3.Connection) -> None:
    """Ensure columns added after first release exist on older DBs.

    Replaces the address_components JSON column with a scalar postal_code
    extracted from raw_json (which retains the full address components).
    """
    import json as _json

    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(places)").fetchall()
    }
    if not cols:
        return  # fresh DB: SCHEMA creates the table complete
    if "postal_code" not in cols:
        conn.execute("ALTER TABLE places ADD COLUMN postal_code TEXT")
    if "address_components" in cols:
        rows = conn.execute(
            "SELECT id, raw_json FROM places"
        ).fetchall()
        for r in rows:
            try:
                payload = _json.loads(r["raw_json"] or "{}")
            except _json.JSONDecodeError:
                continue
            postal = next(
                (
                    c.get("longText") or c.get("shortText")
                    for c in payload.get("addressComponents", [])
                    if "postal_code" in (c.get("types") or [])
                ),
                None,
            )
            if postal:
                conn.execute(
                    "UPDATE places SET postal_code = ? WHERE id = ?",
                    (postal, r["id"]),
                )
        conn.execute("ALTER TABLE places DROP COLUMN address_components")


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def worldcities_count(conn: sqlite3.Connection) -> int:
    init_schema(conn)
    row = conn.execute("SELECT COUNT(*) AS n FROM worldcities").fetchone()
    return int(row["n"]) if row else 0


def seed_worldcities(
    conn: sqlite3.Connection,
    csv_path: Path | str = DEFAULT_WORLDCITIES_CSV,
) -> int:
    """Load worldcities.csv into the ODS on first initialization.

    No-op when the table already has rows. Returns rows inserted.
    """
    init_schema(conn)
    if worldcities_count(conn) > 0:
        return 0
    csv_file = Path(csv_path)
    if not csv_file.exists():
        return 0
    with csv_file.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                (row.get("id") or "").strip(),
                (row.get("city") or "").strip(),
                (row.get("city_ascii") or "").strip() or None,
                _to_float(row.get("lat")),
                _to_float(row.get("lng")),
                (row.get("country") or "").strip() or None,
                (row.get("iso2") or "").strip() or None,
                (row.get("iso3") or "").strip() or None,
                (row.get("admin_name") or "").strip() or None,
                (row.get("capital") or "").strip() or None,
                _to_int(row.get("population")),
            )
            for row in reader
            if (row.get("id") or "").strip() and (row.get("city") or "").strip()
        ]
    if not rows:
        return 0
    conn.executemany(
        "INSERT OR IGNORE INTO worldcities "
        "(id, city, city_ascii, lat, lng, country, iso2, iso3, "
        "admin_name, capital, population) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return worldcities_count(conn)
