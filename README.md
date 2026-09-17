# Whitespace Analyzer

Competitive whitespace data platform for physical-store brands: a Streamlit control plane over a SQLite ODS, store locations ingested from the Google Places API (New), landed incrementally in DuckDB and modelled with dbt, orchestrated by Airflow.

See [`architecture.md`](architecture.md) for the design.

## Setup

```bash
# Application, ingestion and dbt
uv sync

# Airflow runs in its own environment (Python 3.12)
cd airflow && uv sync
```

---

## Getting started

Do these in order. Steps 1–4 are for collecting data; steps 5–7 turn that data into models.

### 1. Start the app

```bash
uv run streamlit run app/main.py
```

Open **http://localhost:8501**. Leave this terminal running — it is where you add data.

### 2. Get and add your Google Places API key

**What it is.** An API key is what identifies your Google Cloud project to Google and bills it for every request. The app uses it to call the **Places API (New)** Text Search endpoint, which is where store locations, ratings, opening hours and coordinates come from. Until a key is saved, the **Get locations from Google** button stays disabled.

**How to get one.** Google's official walkthrough is **Set up the Places API (New)** — <https://developers.google.com/maps/documentation/places/web-service/get-api-key>. In short:

1. In the [Google Cloud Console](https://console.cloud.google.com), create a project (or pick one) and **enable billing** on it — the Places API will not respond without a billing account.
2. In **APIs & Services → Library**, search for and **enable "Places API (New)"**.
3. In **APIs & Services → Credentials**, click **Create credentials → API key** and copy the key.
4. Recommended: restrict the key to **Places API (New)** so it can't be used against anything else.

**Add it to the app.** Go to the **Settings** tab, paste the key, and click **Save settings**. That is the last step — the app can fetch locations from here on.

One cost note: opening hours and business status are billed at Google's Enterprise SKU, so a fetch costs more than a bare text search.

### 3. Add brands and their competitors

In the **Brands** tab, fill in a brand name, an industry domain, its website, and optionally multi-select any existing brands that compete with it, then click **Save brand**.

Add a couple of brands this way, and link them to each other as competitors. Competitors are picked from brands that already exist, so add the brands first and link them afterwards from each brand's panel.

### 4. Pull locations from Google Places

Expand a brand and use the **Google Places locations** section:

1. Pick a **Country** (and optionally a **City**) — these come from the bundled reference data. Leave the city as "All cities" to search the whole country.
2. Set **Max results** (up to 60).
3. Check the query preview, then click **Get locations from Google**.

Repeat for each brand and each geography you care about. The **Places** tab shows everything you have collected, and you can inspect any place there.

### 5. Start Airflow

In a **new terminal**:

```bash
./airflow/start_airflow.zsh
```

Open **http://localhost:8080** and sign in with **`admin` / `admin`** (development credentials).

### 6. Ingest into DuckDB

In the Airflow UI, find the **`ods_to_duckdb`** DAG and trigger it with the **▶ (Trigger DAG)** button. Wait for the run to finish — this copies everything new from the ODS into the DuckDB warehouse.

### 7. Run all dbt models

Find the **`dbt_run`** DAG and trigger it with **▶**. It runs the models, the snapshot and the tests in order (`seed → run → snapshot → test`), so this single trigger builds everything and fails visibly if a data-quality check breaks.
