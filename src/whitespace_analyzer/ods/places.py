import json
import sqlite3

from whitespace_analyzer.ods.database import init_schema


def _encode(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _row_values(row: dict) -> dict:
    return {
        "brand_id": row["brand_id"],
        "place_id": row["place_id"],
        "name": row["name"],
        "formatted_address": row["formatted_address"],
        "postal_code": row["postal_code"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "national_phone": row["national_phone"],
        "international_phone": row["international_phone"],
        "website_uri": row["website_uri"],
        "rating": row["rating"],
        "user_rating_count": row["user_rating_count"],
        "price_level": row["price_level"],
        "business_status": row["business_status"],
        "primary_type": row["primary_type"],
        "types": _encode(row["types"]),
        "utc_offset_minutes": row["utc_offset_minutes"],
        "open_now": row["open_now"],
        "weekday_hours": _encode(row["weekday_hours"]),
        "google_maps_uri": row["google_maps_uri"],
        "raw_json": _encode(row["raw_json"]),
    }


def upsert_place(conn: sqlite3.Connection, row: dict) -> tuple[int, bool]:
    """Insert or refresh a place by place_id. Returns (id, is_new)."""
    init_schema(conn)
    values = _row_values(row)
    cols = list(values.keys())
    existing = conn.execute(
        "SELECT id FROM places WHERE place_id = ?", (row["place_id"],)
    ).fetchone()
    if existing:
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        conn.execute(
            f"UPDATE places SET {set_clause}, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [*values.values(), existing["id"]],
        )
        conn.commit()
        return existing["id"], False
    placeholders = ", ".join(["?"] * len(cols))
    cur = conn.execute(
        f"INSERT INTO places ({', '.join(cols)}) VALUES ({placeholders})",
        list(values.values()),
    )
    conn.commit()
    return (cur.lastrowid if cur.lastrowid is not None else -1), True


def list_places(
    conn: sqlite3.Connection, brand_id: int | None = None
) -> list[dict]:
    init_schema(conn)
    query = (
        "SELECT id, brand_id, place_id, name, formatted_address, "
        "postal_code, latitude, longitude, national_phone, "
        "international_phone, website_uri, rating, user_rating_count, "
        "price_level, business_status, primary_type, types, "
        "utc_offset_minutes, open_now, weekday_hours, google_maps_uri, "
        "created_at, updated_at FROM places"
    )
    params: list = []
    if brand_id is not None:
        query += " WHERE brand_id = ?"
        params.append(brand_id)
    query += " ORDER BY rating DESC NULLS LAST, id DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_place(conn: sqlite3.Connection, place_row_id: int) -> dict | None:
    init_schema(conn)
    row = conn.execute(
        "SELECT * FROM places WHERE id = ?", (place_row_id,)
    ).fetchone()
    return dict(row) if row else None


def place_counts(conn: sqlite3.Connection) -> list[dict]:
    init_schema(conn)
    rows = conn.execute(
        "SELECT brand_id, COUNT(*) AS n FROM places GROUP BY brand_id"
    ).fetchall()
    return [dict(row) for row in rows]
