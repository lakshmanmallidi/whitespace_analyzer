import sqlite3

from whitespace_analyzer.ods.database import init_schema

DEFAULTS: dict[str, str] = {
    "google_places_api_key": "",
}


def get_setting(conn: sqlite3.Connection, key: str) -> str:
    init_schema(conn)
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?", (key,)
    ).fetchone()
    if row is not None:
        return row["value"]
    return DEFAULTS.get(key, "")


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    init_schema(conn)
    conn.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
        "updated_at = CURRENT_TIMESTAMP",
        (key, value),
    )
    conn.commit()


def get_settings(conn: sqlite3.Connection) -> dict[str, str]:
    init_schema(conn)
    rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    settings = dict(DEFAULTS)
    for row in rows:
        settings[row["key"]] = row["value"]
    return settings
