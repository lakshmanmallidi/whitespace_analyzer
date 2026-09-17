import json
import sqlite3


def render_places_tab(conn: sqlite3.Connection) -> None:
    import streamlit as st

    from whitespace_analyzer.ods.brands import list_brands
    from whitespace_analyzer.ods.places import list_places

    st.subheader("Places")

    brands = list_brands(conn)
    brand_labels = ["All brands", *[b["brand_name"] for b in brands]]
    brand_choice = st.selectbox("Brand", brand_labels, key="places_brand_filter")
    brand_id = None
    if brand_choice != "All brands":
        brand_id = next(b["id"] for b in brands if b["brand_name"] == brand_choice)

    places = list_places(conn, brand_id=brand_id)
    st.metric("Places", len(places))
    if not places:
        st.info("No places yet — fetch from Google in the Brands tab.")
        return

    st.dataframe(
        [
            {
                "place_id": p["place_id"],
                "name": p["name"],
                "address": p["formatted_address"],
                "pincode": p["postal_code"],
                "rating": p["rating"],
                "reviews": p["user_rating_count"],
                "open_now": "Yes" if p["open_now"] else "No",
                "status": p["business_status"],
                "phone": p["national_phone"],
                "website": p["website_uri"],
                "lat": p["latitude"],
                "lng": p["longitude"],
                "created_at": p["created_at"],
            }
            for p in places
        ],
        use_container_width=True,
        hide_index=True,
    )

    by_id = {p["id"]: p for p in places}
    selected_id = st.selectbox(
        "Inspect place",
        list(by_id.keys()),
        format_func=lambda i: f"#{i} — {by_id[i]['name'] or '(unnamed)'} "
        f"({by_id[i]['formatted_address'] or '?'})",
        key="place_inspect_select",
    )
    place = by_id[selected_id]
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"created: {place['created_at']} · updated: {place['updated_at']}")
        st.caption(f"place_id: `{place['place_id']}`")
        if place["google_maps_uri"]:
            st.link_button("Open in Google Maps", place["google_maps_uri"])
        st.write("**Opening hours**")
        weekday_hours = json.loads(place["weekday_hours"] or "[]")
        if weekday_hours:
            for line in weekday_hours:
                st.text(line)
        else:
            st.caption("No hours available.")
    with col2:
        st.write("**Raw API payload**")
        full = conn.execute(
            "SELECT raw_json FROM places WHERE id = ?", (selected_id,)
        ).fetchone()
        st.json(json.loads(full["raw_json"] or "{}"), expanded=False)
