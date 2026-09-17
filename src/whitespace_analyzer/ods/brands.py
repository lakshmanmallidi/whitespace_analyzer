import sqlite3

from whitespace_analyzer.ods.database import init_schema


def save_brand(
    conn: sqlite3.Connection,
    brand_name: str,
    industry_domain: str = "",
    website_url: str = "",
) -> int:
    init_schema(conn)
    cur = conn.execute(
        "INSERT INTO brands (brand_name, industry_domain, website_url) "
        "VALUES (?, ?, ?)",
        (brand_name, industry_domain, website_url),
    )
    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else -1


def list_brands(conn: sqlite3.Connection) -> list[dict]:
    init_schema(conn)
    rows = conn.execute(
        "SELECT id, brand_name, industry_domain, website_url, created_at "
        "FROM brands ORDER BY created_at DESC, id DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def brand_exists(conn: sqlite3.Connection, brand_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM brands WHERE brand_name = ?", (brand_name,)
    ).fetchone()
    return row is not None
