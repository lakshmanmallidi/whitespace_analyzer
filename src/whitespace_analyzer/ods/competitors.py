import sqlite3

from whitespace_analyzer.ods.database import init_schema


def _validate(conn: sqlite3.Connection, brand_id: int, competitor_id: int) -> None:
    if brand_id == competitor_id:
        raise ValueError("A brand cannot compete with itself.")
    row = conn.execute(
        "SELECT 1 FROM brands WHERE id = ?", (competitor_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Brand {competitor_id} does not exist.")


def add_competitor(
    conn: sqlite3.Connection, brand_id: int, competitor_id: int
) -> bool:
    """Link competitor to brand. Returns False if the link already exists."""
    init_schema(conn)
    _validate(conn, brand_id, competitor_id)
    try:
        conn.execute(
            "INSERT INTO competitors (brand_id, competitor_id) VALUES (?, ?)",
            (brand_id, competitor_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def add_competitors(
    conn: sqlite3.Connection, brand_id: int, competitor_ids: list[int]
) -> int:
    """Add multiple competitors. Returns the number of new links."""
    added = 0
    for competitor_id in competitor_ids:
        if add_competitor(conn, brand_id, competitor_id):
            added += 1
    return added


def remove_competitor(
    conn: sqlite3.Connection, brand_id: int, competitor_id: int
) -> None:
    init_schema(conn)
    conn.execute(
        "DELETE FROM competitors WHERE brand_id = ? AND competitor_id = ?",
        (brand_id, competitor_id),
    )
    conn.commit()


def list_competitors(conn: sqlite3.Connection, brand_id: int) -> list[dict]:
    """Competitor brand records linked to the given brand."""
    init_schema(conn)
    rows = conn.execute(
        "SELECT b.id, b.brand_name, b.industry_domain, c.created_at "
        "FROM competitors c JOIN brands b ON b.id = c.competitor_id "
        "WHERE c.brand_id = ? ORDER BY c.created_at DESC",
        (brand_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def is_competitor(
    conn: sqlite3.Connection, brand_id: int, competitor_id: int
) -> bool:
    init_schema(conn)
    row = conn.execute(
        "SELECT 1 FROM competitors WHERE brand_id = ? AND competitor_id = ?",
        (brand_id, competitor_id),
    ).fetchone()
    return row is not None
