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

    render_danger_zone(conn)


def render_danger_zone(conn: sqlite3.Connection) -> None:
    import streamlit as st

    from whitespace_analyzer.analytics.duckdb_ingest import DEFAULT_DUCKDB_PATH
    from whitespace_analyzer.ods.reset import (
        clear_ods,
        clear_warehouse,
        ods_data_counts,
    )

    st.divider()
    st.subheader("Danger zone")
    st.caption(
        "Deletes every brand, place and competitor in the ODS, and the whole "
        "DuckDB warehouse (raw, bronze, silver and gold, including history and "
        "sync watermarks). The API key above and the worldcities reference "
        "table are kept. This cannot be undone."
    )

    counts = ods_data_counts(conn)
    warehouse = DEFAULT_DUCKDB_PATH
    warehouse_size = (
        f"{warehouse.stat().st_size / 1_000_000:.1f} MB"
        if warehouse.exists()
        else "not built"
    )
    st.write(
        f"**Current data:** {counts['brands']} brands · {counts['places']} places "
        f"· {counts['competitors']} competitor links · warehouse {warehouse_size}"
    )

    removed = st.session_state.pop("reset_result", None)
    if removed is not None:
        counts_removed, warehouse_existed = removed
        st.success(
            f"Deleted {counts_removed['brands']} brands, "
            f"{counts_removed['places']} places and "
            f"{counts_removed['competitors']} competitor links. Warehouse file "
            f"{'deleted' if warehouse_existed else 'was already absent'}."
        )

    confirmed = st.checkbox(
        "I understand this permanently deletes all data",
        key="confirm_delete_all",
    )
    if st.button(
        "Delete all data",
        type="primary",
        disabled=not confirmed,
        key="delete_all_data",
    ):
        st.session_state["reset_result"] = (clear_ods(conn), clear_warehouse())
        st.cache_data.clear()
        st.rerun()
