from whitespace_analyzer.ods.database import get_connection
from whitespace_analyzer.ods.settings import get_setting, get_settings, set_setting


def test_settings_defaults(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    assert get_setting(conn, "google_places_api_key") == ""
    assert get_settings(conn) == {"google_places_api_key": ""}


def test_settings_roundtrip(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    set_setting(conn, "google_places_api_key", "secret-key")
    set_setting(conn, "google_places_api_key", "rotated-key")

    assert get_setting(conn, "google_places_api_key") == "rotated-key"
    assert get_settings(conn)["google_places_api_key"] == "rotated-key"
