import sqlite3


def render_settings_tab(conn: sqlite3.Connection) -> None:
    import streamlit as st

    from whitespace_analyzer.ods.settings import get_settings, set_setting

    st.subheader("Settings")
    st.caption(
        "Google Places API key is used to fetch store locations via the "
        "Places API (New) Text Search endpoint."
    )
    settings = get_settings(conn)

    with st.form("settings_form"):
        google_key = st.text_input(
            "Google Places API key",
            value=settings.get("google_places_api_key", ""),
            type="password",
        )
        submitted = st.form_submit_button("Save settings", type="primary")

    if submitted:
        set_setting(conn, "google_places_api_key", google_key.strip())
        st.success("Settings saved.")
