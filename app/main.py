import streamlit as st

from whitespace_analyzer.ods.brands import brand_exists, list_brands, save_brand
from whitespace_analyzer.ods.database import get_connection
from whitespace_analyzer.ods.geo import (
    ALL_CITIES,
    ALL_COUNTRIES,
    build_places_query,
    list_cities,
    list_countries,
)
from whitespace_analyzer.ods.settings import get_setting

try:
    from app.places_page import render_places_tab
    from app.reports_page import render_reports_tab
    from app.settings_page import render_settings_tab
except ModuleNotFoundError:  # `streamlit run app/main.py` puts app/ on sys.path
    from places_page import render_places_tab
    from reports_page import render_reports_tab
    from settings_page import render_settings_tab

st.set_page_config(page_title="Whitespace Analyzer", page_icon="🗺️", layout="wide")

INDUSTRY_DOMAINS = ["pizza", "urgent_care", "coffee", "fitness", "other"]


def render_brand_form(conn) -> None:
    brands = list_brands(conn)
    with st.form("brand_form", clear_on_submit=True):
        brand_name = st.text_input("Brand name", placeholder="e.g. Domino's Pizza")
        col1, col2 = st.columns(2)
        industry_domain = col1.selectbox("Industry domain", INDUSTRY_DOMAINS)
        website_url = col2.text_input("Website URL", placeholder="https://...")
        competitor_names = st.multiselect(
            "Competitors (optional, from existing brands)",
            [b["brand_name"] for b in brands],
            default=None,
            help="Multi-select existing brands that compete with this one.",
        )
        submitted = st.form_submit_button("Save brand", type="primary")

    if submitted:
        name = brand_name.strip()
        if not name:
            st.error("Brand name is required.")
        elif brand_exists(conn, name):
            st.error(f"Brand `{name}` already exists.")
        else:
            from whitespace_analyzer.ods.competitors import add_competitors

            brand_id = save_brand(conn, name, industry_domain, website_url.strip())
            id_by_name = {b["brand_name"]: b["id"] for b in brands}
            selected_ids = [
                id_by_name[n] for n in competitor_names if n in id_by_name
            ]
            n_added = add_competitors(conn, brand_id, selected_ids)
            st.success(f"Saved `{name}` with {n_added} competitor(s).")


def render_google_section(conn, brand_id: int, brand_name: str) -> None:
    from whitespace_analyzer.ingestion.google_places import (
        PlacesApiError,
        fetch_places,
        persist_places,
    )

    st.write("**Google Places locations**")
    api_key = get_setting(conn, "google_places_api_key")
    has_key = bool(api_key.strip())

    countries = [ALL_COUNTRIES, *list_countries(conn)]
    country = st.selectbox(
        "Country",
        countries,
        key=f"country_{brand_id}",
    )
    cities = (
        [ALL_CITIES, *list_cities(conn, country)] if country != ALL_COUNTRIES else []
    )
    city = None
    if cities:
        city = st.selectbox("City (optional)", cities, key=f"city_{brand_id}")
    else:
        st.caption("Select a country to filter by city, or leave worldwide.")

    col1, col2 = st.columns([3, 1])
    preview = build_places_query(brand_name, country, city)
    col1.caption(f"Query preview: `{preview}`")
    max_results = col2.number_input(
        "Max results",
        min_value=1,
        max_value=60,
        value=20,
        key=f"maxresults_{brand_id}",
        help="Places API returns 20 per page, up to 60.",
    )

    google_clicked = st.button(
        "Get locations from Google",
        key=f"google_{brand_id}",
        disabled=not has_key,
        help="Fetch store locations via Google Places API"
        if has_key
        else "Add your Google Places API key in Settings to enable",
    )
    if not has_key:
        st.info("Add your Google Places API key in Settings to enable.")
    elif google_clicked:
        try:
            with st.spinner("Querying Google Places…"):
                places = fetch_places(
                    api_key.strip(), preview, max_results=int(max_results)
                )
        except (PlacesApiError, RuntimeError, OSError, ValueError) as e:
            st.error(f"Google fetch failed: {e}")
            return
        n_total, n_new = persist_places(conn, brand_id, places)
        st.success(
            f"Fetched {n_total} place(s) → {n_new} new, "
            f"{n_total - n_new} updated in the Places collection. "
            "See the Places tab."
        )


def render_competitors_section(conn, brand_id: int, brands: list[dict]) -> None:
    from whitespace_analyzer.ods.competitors import (
        add_competitors,
        list_competitors,
        remove_competitor,
    )

    st.write("**Competitors**")
    competitors = list_competitors(conn, brand_id)
    st.metric("Competitors", len(competitors))
    for comp in competitors:
        col1, col2 = st.columns([4, 1])
        col1.caption(
            f"{comp['brand_name']} ({comp['industry_domain']}) · "
            f"added {comp['created_at']}"
        )
        if col2.button(
            "Remove", key=f"rm_comp_{brand_id}_{comp['id']}"
        ):
            remove_competitor(conn, brand_id, comp["id"])
            st.rerun()

    existing_ids = {c["id"] for c in competitors}
    selectable = [b for b in brands if b["id"] != brand_id and b["id"] not in existing_ids]
    if not selectable:
        st.caption("All existing brands are already linked as competitors.")
        return
    selected = st.multiselect(
        "Add competitors",
        [b["brand_name"] for b in selectable],
        key=f"add_competitors_{brand_id}",
    )
    if st.button("Add competitors", key=f"btn_add_competitors_{brand_id}"):
        id_by_name = {b["brand_name"]: b["id"] for b in selectable}
        n_added = add_competitors(
            conn, brand_id, [id_by_name[n] for n in selected if n in id_by_name]
        )
        if n_added:
            st.success(f"Added {n_added} competitor(s).")
            st.rerun()
        else:
            st.info("Nothing to add.")


def render_brands_tab(conn) -> None:
    render_brand_form(conn)
    brands = list_brands(conn)
    st.subheader("Brands")
    st.metric("Total brands", len(brands))
    if not brands:
        st.info("No brands yet — add one above.")
        return
    for brand in brands:
        with st.expander(f"{brand['brand_name']} ({brand['industry_domain']})"):
            st.caption(brand["website_url"])
            render_competitors_section(conn, brand["id"], brands)
            st.divider()
            render_google_section(conn, brand["id"], brand["brand_name"])


def main() -> None:
    st.title("Whitespace Analyzer")
    st.caption("Competitive whitespace platform backed by the SQLite ODS.")

    conn = get_connection()
    brands_tab, places_tab, reports_tab, settings_tab = st.tabs(
        ["Brands", "Places", "Reports", "Settings"]
    )
    with brands_tab:
        render_brands_tab(conn)
    with places_tab:
        render_places_tab(conn)
    with reports_tab:
        render_reports_tab()
    with settings_tab:
        render_settings_tab(conn)


if __name__ == "__main__":
    main()
