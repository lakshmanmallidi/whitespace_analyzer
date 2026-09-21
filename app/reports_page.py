"""Reports tab: charts over the gold marts in the DuckDB warehouse."""

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from whitespace_analyzer.analytics.brand_performance import (
    WarehouseNotReady,
    load_brand_performance,
)
from whitespace_analyzer.analytics.duckdb_ingest import DEFAULT_DUCKDB_PATH
from whitespace_analyzer.analytics.store_map import load_store_map

PRICE_LABELS = ["Free", "Inexpensive", "Moderate", "Expensive", "Very expensive"]

PRICE_LABEL_BY_RANK = dict(enumerate(PRICE_LABELS))

PRICE_BAND_COLOR = "#1f77b4"

PRICE_MAX_COLOR = "#d62728"

BAND_PAD = 0.08

PRICE_RANKS = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}

PRICE_AXIS = alt.Axis(
    values=list(range(len(PRICE_LABELS))),
    labelExpr=f"[{', '.join(repr(label) for label in PRICE_LABELS)}][datum.value]",
    title="Price level",
)

OURS_COLOR = [31, 119, 180]

COMPETITORS_COLOR = [214, 39, 40]

ABSENCE_TOP_N = 15

ABSENCE_METRICS = (
    {
        "field": "population",
        "title": "Population",
        "color": "#4c78a8",
        "scale": alt.Scale(),
        "axis": alt.Axis(format="~s"),
    },
    {
        "field": "competitor_store_count",
        "title": "Competitor stores",
        "color": "#d62728",
        "scale": alt.Scale(),
        "axis": alt.Axis(format="d", tickMinStep=1),
    },
    {
        "field": "competitor_max_rating",
        "title": "Max competitor rating",
        "color": "#9467bd",
        "scale": alt.Scale(domain=[0, 5]),
        "axis": alt.Axis(values=[0, 1, 2, 3, 4, 5]),
    },
)

@st.cache_data(ttl=300)
def _load(warehouse_path: str) -> pd.DataFrame:
    return load_brand_performance(warehouse_path)


@st.cache_data(ttl=300)
def _load_map(warehouse_path: str, brand: str) -> pd.DataFrame:
    return load_store_map(brand, warehouse_path)


def _labelled(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    state = out["state_name"].fillna("")
    out["city_label"] = (
        out["brand_name"] + " · " + out["city"] + ", " + state
    ).str.rstrip(", ")
    return out


POPULATION_BINS = [
    0,
    100_000,
    250_000,
    500_000,
    1_000_000,
    2_000_000,
    5_000_000,
    10_000_000,
    20_000_000,
    50_000_000,
    float("inf"),
]

POPULATION_LABELS = [
    "<100k",
    "100k–250k",
    "250k–500k",
    "500k–1M",
    "1M–2M",
    "2M–5M",
    "5M–10M",
    "10M–20M",
    "20M–50M",
    "50M+",
]


def stores_by_population_bucket(df: pd.DataFrame) -> alt.Chart | None:
    """Store counts per city-size band, ours stacked against competitors'.

    Every band is kept on the axis, including empty ones, so the shape of the
    distribution is visible even where neither side has stores.
    """
    data = df.dropna(subset=["population"]).copy()
    if data.empty:
        return None
    data["bucket"] = pd.cut(
        data["population"],
        bins=POPULATION_BINS,
        labels=POPULATION_LABELS,
        right=False,
    )
    grouped = (
        data.groupby("bucket", observed=False)
        .agg(
            our=("our_store_count", "sum"),
            competitor=("competitor_store_count", "sum"),
            cities=("city", "nunique"),
        )
        .reset_index()
    )
    grouped["bucket"] = grouped["bucket"].astype(str)
    long = grouped.melt(
        id_vars=["bucket"],
        value_vars=["our", "competitor"],
        var_name="side",
        value_name="stores",
    )
    long["side"] = long["side"].map({"our": "Ours", "competitor": "Competitors"})
    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X(
                "bucket:N",
                sort=POPULATION_LABELS,
                title="City population",
            ),
            y=alt.Y("stores:Q", title="Stores"),
            color=alt.Color(
                "side:N",
                title=None,
                scale=alt.Scale(
                    domain=["Ours", "Competitors"],
                    range=["#1f77b4", "#d62728"],
                ),
            ),
            tooltip=[
                alt.Tooltip("bucket:N", title="Population"),
                alt.Tooltip("side:N", title="Who"),
                alt.Tooltip("stores:Q", title="Stores", format=","),
            ],
        )
        .properties(height=320)
    )


def missed_opportunities(df: pd.DataFrame) -> pd.DataFrame | None:
    """The cities we are absent from where a competitor already trades.

    Ranked by the size of the missed opportunity, then capped at
    `ABSENCE_TOP_N`. The ranking decides which cities appear; it is not one of
    the displayed measures, so the cap is what the heading reports.
    """
    data = df[
        (df["our_store_count"] == 0) & (df["competitor_store_count"] > 0)
    ].copy()
    if data.empty:
        return None
    data["opportunity"] = (
        data["population"].fillna(0) * data["competitor_store_count"]
    )
    return data.sort_values("opportunity", ascending=False).head(ABSENCE_TOP_N)


def absence_metric_bar(
    data: pd.DataFrame,
    metric: dict,
    order: list[str],
) -> alt.Chart | None:
    """One city-vs-measure bar, sharing the row order of its siblings."""
    field = metric["field"]
    title = metric["title"]
    if data[field].notna().sum() == 0:
        return None
    return (
        alt.Chart(data)
        .mark_bar(color=metric["color"])
        .encode(
            x=alt.X(
                f"{field}:Q",
                title=title,
                scale=metric["scale"],
                axis=metric["axis"],
            ),
            y=alt.Y("city:N", sort=order, title=None),
            tooltip=[
                alt.Tooltip("city:N", title="City"),
                alt.Tooltip(f"{field}:Q", title=title),
                alt.Tooltip("population:Q", title="Population", format=","),
                alt.Tooltip("competitor_store_count:Q", title="Competitor stores"),
            ],
        )
        .properties(height=max(180, 30 * len(data)))
    )


def render_store_map(df: pd.DataFrame, empty_message: str) -> None:
    """Every store pin for the selected brand and its competitors, on a basemap.

    Uses pydeck's default `carto` provider, which serves token-free vector
    tiles, so the map needs no Mapbox key. The view opens fitted to the stores
    that actually exist; zoom out for nationwide context.
    """
    data = df.dropna(subset=["longitude", "latitude"]).copy()
    if data.empty:
        st.caption(empty_message)
        return

    data["dot_color"] = data["side"].map(
        {"Ours": OURS_COLOR, "Competitors": COMPETITORS_COLOR}
    )
    view = pdk.data_utils.compute_view(data[["longitude", "latitude"]])
    view.pitch = 0

    st.markdown(
        "<span style='color:#1f77b4'>&#9679;</span> Ours&nbsp;&nbsp;&nbsp;"
        "<span style='color:#d62728'>&#9679;</span> Competitors",
        unsafe_allow_html=True,
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=data,
                    get_position=["longitude", "latitude"],
                    get_fill_color="dot_color",
                    get_line_color=[255, 255, 255, 200],
                    line_width_min_pixels=1,
                    get_radius=120,
                    radius_min_pixels=3,
                    radius_max_pixels=14,
                    stroked=True,
                    pickable=True,
                    opacity=0.85,
                )
            ],
            initial_view_state=view,
            map_style="light",
            tooltip={
                "html": "<b>{store_name}</b><br/>{brand_name} · {side}"
                "<br/>{city}, {state_name}<br/>{formatted_address}",
                "style": {"backgroundColor": "#1f2937", "color": "white"},
            },
        ),
        width="stretch",
    )


def rating_dumbbell(df: pd.DataFrame) -> alt.Chart | None:
    """Where we compete, are we out-rated?"""
    data = df.dropna(subset=["our_avg_rating", "competitor_avg_rating"]).copy()
    if data.empty:
        return None
    order = data.sort_values("rating_gap")["city"].tolist()
    long = data.melt(
        id_vars=["city"],
        value_vars=["our_avg_rating", "competitor_avg_rating"],
        var_name="side",
        value_name="rating",
    )
    long["side"] = long["side"].map(
        {"our_avg_rating": "Ours", "competitor_avg_rating": "Competitors"}
    )
    lines = (
        alt.Chart(long)
        .mark_line(color="#999999")
        .encode(
            y=alt.Y("city:N", sort=order, title=None),
            x=alt.X("rating:Q", scale=alt.Scale(domain=[0, 5]), title="Average rating"),
            detail="city:N",
        )
    )
    points = (
        alt.Chart(long)
        .mark_circle(size=80)
        .encode(
            y=alt.Y("city:N", sort=order, title=None),
            x=alt.X("rating:Q", scale=alt.Scale(domain=[0, 5])),
            color=alt.Color(
                "side:N",
                title=None,
                scale=alt.Scale(range=["#1f77b4", "#d62728"]),
            ),
            tooltip=["city:N", "side:N", "rating:Q"],
        )
    )
    return (lines + points).properties(
        height=max(220, 24 * data["city"].nunique()),
    )


def share_vs_review_scatter(df: pd.DataFrame) -> alt.Chart | None:
    """Bottom-right = we have stores but not the review footprint.

    Only cities where we actually trade: with no stores of our own there is no
    reputation of ours to compare, and every such row would otherwise pile up
    on the origin with both shares at zero.
    """
    data = df[
        (df["our_store_count"] > 0)
        & df["our_store_share"].notna()
        & df["review_share"].notna()
    ].copy()
    if data.empty:
        return None
    data["population"] = data["population"].fillna(0).clip(lower=1)
    return (
        alt.Chart(data)
        .mark_circle(opacity=0.75)
        .encode(
            x=alt.X(
                "our_store_share:Q",
                title="Our share of stores",
                scale=alt.Scale(domain=[0, 1]),
            ),
            y=alt.Y(
                "review_share:Q",
                title="Our share of reviews",
                scale=alt.Scale(domain=[0, 1]),
            ),
            size=alt.Size(
                "population:Q",
                title="Population",
                scale=alt.Scale(range=[40, 900], type="sqrt"),
            ),
            color=alt.Color("brand_name:N", title="Brand"),
            tooltip=[
                alt.Tooltip("city_label:N", title="Brand · city"),
                alt.Tooltip("our_store_share:Q", title="Store share", format=".1%"),
                alt.Tooltip("review_share:Q", title="Review share", format=".1%"),
                alt.Tooltip("our_total_ratings:Q", title="Our reviews", format=","),
                alt.Tooltip(
                    "competitor_total_ratings:Q",
                    title="Competitor reviews",
                    format=",",
                ),
            ],
        )
        .properties(height=380)
    )


def price_positioning(df: pd.DataFrame) -> alt.Chart | None:
    """Our top price against the competitor price band, one row per city.

    The blue bar is the range the competitors' stores span; the red dot is
    where our own top-priced store sits on the same ladder. Only cities where
    both sides trade are shown — with one side missing there is no positioning
    to read. Left is cheaper, right is pricier.
    """
    data = df[
        (df["our_store_count"] > 0) & (df["competitor_store_count"] > 0)
    ].copy()
    data["our_top"] = data["our_max_price_level"].map(PRICE_RANKS)
    data["rival_low"] = data["competitor_min_price_level"].map(PRICE_RANKS)
    data["rival_high"] = data["competitor_max_price_level"].map(PRICE_RANKS)
    data = data.dropna(subset=["our_top", "rival_low", "rival_high"])
    if data.empty:
        return None

    for column in ("our_top", "rival_low", "rival_high"):
        data[column + "_label"] = data[column].astype(int).map(PRICE_LABEL_BY_RANK)

    # Competitors sharing one price level would be a zero-length rule, which
    # Vega-Lite draws as nothing. A small symmetric pad keeps the band visible
    # whatever the spread; the tooltip still reports the exact levels.
    data["band_low"] = (data["rival_low"] - BAND_PAD).clip(lower=0)
    data["band_high"] = (data["rival_high"] + BAND_PAD).clip(upper=4)

    order = data.sort_values("our_top")["city"].tolist()
    price_scale = alt.Scale(domain=[0, 4])
    band = (
        alt.Chart(data)
        .mark_rule(strokeWidth=10, opacity=0.4, color=PRICE_BAND_COLOR)
        .encode(
            y=alt.Y("city:N", sort=order, title=None),
            x=alt.X("band_low:Q", scale=price_scale, axis=PRICE_AXIS),
            x2="band_high:Q",
            tooltip=[
                alt.Tooltip("city:N", title="City"),
                alt.Tooltip("rival_low_label:N", title="Competitors from"),
                alt.Tooltip("rival_high_label:N", title="to"),
            ],
        )
    )
    marker = (
        alt.Chart(data)
        .mark_point(size=170, filled=True, color=PRICE_MAX_COLOR)
        .encode(
            y=alt.Y("city:N", sort=order, title=None),
            x=alt.X("our_top:Q", scale=price_scale, axis=PRICE_AXIS),
            tooltip=[
                alt.Tooltip("city:N", title="City"),
                alt.Tooltip("our_top_label:N", title="Our top price"),
                alt.Tooltip("rival_low_label:N", title="Competitors from"),
                alt.Tooltip("rival_high_label:N", title="to"),
            ],
        )
    )
    return (band + marker).properties(height=max(200, 40 * len(data)))


def _render_chart(chart: alt.Chart | None, empty_message: str) -> None:
    if chart is None:
        st.caption(empty_message)
    else:
        st.altair_chart(chart, use_container_width=True)


def _section(title: str) -> None:
    """One heading style for every section, so the tab stays even.

    Charts are drawn without their own Vega-Lite titles for this reason: two
    title systems render at two different font sizes.
    """
    st.divider()
    st.subheader(title)


def _subsection(title: str) -> None:
    """Sub heading for charts that sit inside a section, one level down."""
    st.markdown(f"#### {title}")


def render_reports_tab() -> None:
    st.subheader("Reports")
    st.caption(
        "Built from the gold layer (`gold.brand_performance`) in the DuckDB "
        "warehouse. Refresh it by running the Airflow DAGs."
    )

    try:
        df = _load(str(DEFAULT_DUCKDB_PATH))
    except WarehouseNotReady as exc:
        st.warning(str(exc))
        return

    if df.empty:
        st.info("No rows in brand_performance yet.")
        return

    df = _labelled(df)

    brand_names = sorted(df["brand_name"].dropna().unique())
    if not brand_names:
        st.info("No brand names in brand_performance yet.")
        return
    brand = st.selectbox("Brand", brand_names, key="reports_brand")
    df = df[df["brand_name"] == brand]

    try:
        store_points = _load_map(str(DEFAULT_DUCKDB_PATH), brand)
        store_map_error = None
    except WarehouseNotReady as exc:
        store_points = pd.DataFrame()
        store_map_error = str(exc)

    absent = df[(df["our_store_count"] == 0) & (df["competitor_store_count"] > 0)]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cities", len(df))
    col2.metric("Our stores", int(df["our_store_count"].sum()))
    col3.metric("Competitor stores", int(df["competitor_store_count"].sum()))
    col4.metric("Cities we are absent from", len(absent))

    if df["competitor_store_count"].sum() == 0:
        st.info(
            "No city currently has both a subject brand and one of its "
            "competitors, so every competitor metric is zero. Charts that "
            "compare against competitors will stay empty until that overlap "
            "exists."
        )

    _section("Store map")
    render_store_map(
        store_points,
        store_map_error or "No store coordinates for this brand.",
    )

    _section(f"Top {ABSENCE_TOP_N} cities we are absent from")
    absence = missed_opportunities(df)
    if absence is None:
        st.caption("No city where we are absent has a competitor present.")
    else:
        order = absence.sort_values("opportunity")["city"].tolist()
        for metric in ABSENCE_METRICS:
            _subsection(metric["title"])
            _render_chart(
                absence_metric_bar(absence, metric, order),
                f"No {metric['title'].lower()} recorded for these cities.",
            )

    _section("Stores by city population bucket")
    _render_chart(
        stores_by_population_bucket(df),
        "No city population data available.",
    )

    _section("Rating: ours vs competitors")
    _render_chart(
        rating_dumbbell(df),
        "No city where both our rating and a competitor's rating exist.",
    )

    _section(
        "Presence vs reputation — below the diagonal means we own stores "
        "but not the reviews"
    )
    _render_chart(
        share_vs_review_scatter(df),
        "No city where we are present has comparable review data.",
    )

    _section("Price positioning — further right is pricier")
    _render_chart(
        price_positioning(df),
        "No city has a recorded price band yet.",
    )

    with st.expander("Underlying rows"):
        st.dataframe(df, use_container_width=True, hide_index=True)
