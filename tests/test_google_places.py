import json

import pytest

from whitespace_analyzer.ingestion.google_places import (
    PlacesApiError,
    fetch_places,
    persist_places,
    place_to_row,
    search_places,
)
from whitespace_analyzer.ods.brands import save_brand
from whitespace_analyzer.ods.database import get_connection
from whitespace_analyzer.ods.places import list_places

FAKE_PLACE = {
    "id": "place-1",
    "displayName": {"text": "Domino's Pizza Koramangala"},
    "formattedAddress": "80, 4th Block, Koramangala, Bengaluru, Karnataka 560034, India",
    "addressComponents": [
        {"longText": "80", "shortText": "80", "types": ["premise"]},
        {
            "longText": "Bengaluru",
            "shortText": "Bengaluru",
            "types": ["locality", "political"],
        },
        {
            "longText": "560034",
            "shortText": "560034",
            "types": ["postal_code"],
        },
    ],
    "location": {"latitude": 12.9352, "longitude": 77.6245},
    "websiteUri": "https://www.dominos.co.in",
    "nationalPhoneNumber": "+91 80 4123 4567",
    "internationalPhoneNumber": "+91 80 4123 4568",
    "rating": 4.2,
    "userRatingCount": 1200,
    "googleMapsUri": "https://maps.google.com/?cid=123",
    "businessStatus": "OPERATIONAL",
    "priceLevel": "PRICE_LEVEL_MODERATE",
    "types": ["restaurant", "meal_takeaway"],
    "primaryType": "restaurant",
    "utcOffsetMinutes": 330,
    "regularOpeningHours": {
        "openNow": True,
        "weekdayDescriptions": [
            "Monday: 11:00 AM – 11:00 PM",
            "Tuesday: 11:00 AM – 11:00 PM",
        ],
    },
    "currentOpeningHours": {"openNow": True},
}


def test_place_to_row_maps_all_fields():
    row = place_to_row(42, FAKE_PLACE)
    assert row["brand_id"] == 42
    assert row["place_id"] == "place-1"
    assert row["name"] == "Domino's Pizza Koramangala"
    assert row["latitude"] == 12.9352
    assert row["national_phone"] == "+91 80 4123 4567"
    assert row["international_phone"] == "+91 80 4123 4568"
    assert row["rating"] == 4.2
    assert row["business_status"] == "OPERATIONAL"
    assert row["open_now"] == 1
    assert len(row["weekday_hours"]) == 2
    assert row["postal_code"] == "560034"
    assert row["raw_json"] == FAKE_PLACE


def test_search_places_sends_field_mask_and_token(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"places": [FAKE_PLACE]}

        return FakeResponse()

    monkeypatch.setattr(
        "whitespace_analyzer.ingestion.google_places.requests.post", fake_post
    )
    payload = search_places("key", "all Dominos in India in all cities")
    assert payload["places"] == [FAKE_PLACE]
    assert "places:searchText" in captured["url"]
    assert captured["headers"]["X-Goog-Api-Key"] == "key"
    assert "places.regularOpeningHours.weekdayDescriptions" in captured[
        "headers"
    ]["X-Goog-FieldMask"]


def test_search_places_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        class FakeResponse:
            status_code = 400
            text = "bad"

            def json(self):
                return {"error": {"message": "API key not valid"}}

        return FakeResponse()

    monkeypatch.setattr(
        "whitespace_analyzer.ingestion.google_places.requests.post", fake_post
    )
    with pytest.raises(PlacesApiError, match="API key not valid"):
        search_places("bad-key", "query")


def test_fetch_places_stops_without_token(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"places": [FAKE_PLACE]}

        return FakeResponse()

    monkeypatch.setattr(
        "whitespace_analyzer.ingestion.google_places.requests.post", fake_post
    )
    places = fetch_places("key", "query", max_results=40)
    assert len(places) == 1
    assert len(calls) == 1


def test_persist_places_upserts_and_sets_timestamps(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    brand_id = save_brand(conn, "Domino's", "pizza")

    n_total, n_new = persist_places(conn, brand_id, [FAKE_PLACE])
    assert (n_total, n_new) == (1, 1)
    places = list_places(conn, brand_id=brand_id)
    assert len(places) == 1
    row = places[0]
    assert row["created_at"]
    assert row["updated_at"]
    assert row["place_id"] == "place-1"
    assert row["name"] == "Domino's Pizza Koramangala"
    assert row["rating"] == 4.2
    assert json.loads(row["types"]) == ["restaurant", "meal_takeaway"]
    assert row["postal_code"] == "560034"
    assert len(json.loads(row["weekday_hours"])) == 2

    # Same place fetched again → updated, not duplicated.
    FAKE_PLACE["rating"] = 4.5
    n_total, n_new = persist_places(conn, brand_id, [FAKE_PLACE])
    assert (n_total, n_new) == (1, 0)
    assert len(list_places(conn, brand_id=brand_id)) == 1
    assert list_places(conn, brand_id=brand_id)[0]["rating"] == 4.5


def test_persist_places_skips_missing_id(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    brand_id = save_brand(conn, "Domino's", "pizza")
    n_total, n_new = persist_places(conn, brand_id, [{"displayName": {"text": "x"}}])
    assert (n_total, n_new) == (0, 0)
