"""Google Places API (New) — Text Search ingestion into the ODS.

Endpoint: POST https://places.googleapis.com/v1/places:searchText
Auth: X-Goog-Api-Key header. Fields are constrained via X-Goog-FieldMask.
Text Search returns up to 20 results per page; up to 3 pages (60 places)
via nextPageToken.
"""

import requests

from whitespace_analyzer.ods.places import upsert_place

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PAGE_SIZE = 20
MAX_PAGES = 3

FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.addressComponents,"
    "places.location,"
    "places.websiteUri,"
    "places.nationalPhoneNumber,"
    "places.internationalPhoneNumber,"
    "places.rating,"
    "places.userRatingCount,"
    "places.googleMapsUri,"
    "places.businessStatus,"
    "places.priceLevel,"
    "places.types,"
    "places.primaryType,"
    "places.utcOffsetMinutes,"
    "places.regularOpeningHours.openNow,"
    "places.regularOpeningHours.weekdayDescriptions,"
    "places.currentOpeningHours.openNow"
)


class PlacesApiError(RuntimeError):
    """Raised when the Places API returns an error response."""


def search_places(
    api_key: str, query: str, page_token: str | None = None
) -> dict:
    """One Text Search page. Returns the raw JSON response dict."""
    payload: dict = {"textQuery": query, "pageSize": PAGE_SIZE}
    if page_token:
        payload["pageToken"] = page_token
    response = requests.post(
        PLACES_TEXT_SEARCH_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        json=payload,
        timeout=30,
    )
    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text[:300]
        raise PlacesApiError(
            f"Places API {response.status_code}: {detail}"
        )
    return response.json()


def fetch_places(api_key: str, query: str, max_results: int = 20) -> list[dict]:
    """Fetch up to `max_results` places, following nextPageToken pages."""
    places: list[dict] = []
    page_token: str | None = None
    for _ in range(MAX_PAGES):
        payload = search_places(api_key, query, page_token)
        places.extend(payload.get("places", []))
        page_token = payload.get("nextPageToken")
        if not page_token or len(places) >= max_results:
            break
    return places[:max_results]


def _postal_code(place: dict) -> str | None:
    """Extract the postal code from addressComponents, preferring longText."""
    for component in place.get("addressComponents") or []:
        if "postal_code" in (component.get("types") or []):
            return component.get("longText") or component.get("shortText")
    return None


def place_to_row(brand_id: int, place: dict) -> dict:
    """Map a Places API place object to a places-collection row."""
    loc = place.get("location") or {}
    regular_hours = place.get("regularOpeningHours") or {}
    return {
        "brand_id": brand_id,
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "formatted_address": place.get("formattedAddress"),
        "postal_code": _postal_code(place),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude"),
        "national_phone": place.get("nationalPhoneNumber"),
        "international_phone": place.get("internationalPhoneNumber"),
        "website_uri": place.get("websiteUri"),
        "rating": place.get("rating"),
        "user_rating_count": place.get("userRatingCount"),
        "price_level": place.get("priceLevel"),
        "business_status": place.get("businessStatus"),
        "primary_type": place.get("primaryType"),
        "types": place.get("types") or [],
        "utc_offset_minutes": place.get("utcOffsetMinutes"),
        "open_now": 1
        if (place.get("currentOpeningHours") or {}).get("openNow")
        else 0,
        "weekday_hours": regular_hours.get("weekdayDescriptions") or [],
        "google_maps_uri": place.get("googleMapsUri"),
        "raw_json": place,
    }


def persist_places(conn, brand_id: int, places: list[dict]) -> tuple[int, int]:
    """Save fetched places into the places collection (upsert by place_id).

    Returns (n_total, n_new).
    """
    n_total = 0
    n_new = 0
    for place in places:
        if not place.get("id"):
            continue
        _, is_new = upsert_place(conn, place_to_row(brand_id, place))
        n_total += 1
        if is_new:
            n_new += 1
    return n_total, n_new
