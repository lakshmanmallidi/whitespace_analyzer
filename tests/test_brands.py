from whitespace_analyzer.ods.brands import brand_exists, list_brands, save_brand
from whitespace_analyzer.ods.database import get_connection


def test_save_and_list_brands(tmp_path):
    conn = get_connection(tmp_path / "ods.sqlite")
    save_brand(conn, "Domino's Pizza", "pizza", "https://dominos.com")
    save_brand(conn, "Pizza Hut", "pizza")

    brands = list_brands(conn)
    assert len(brands) == 2
    assert brands[0]["brand_name"] == "Pizza Hut"
    assert brands[1]["brand_name"] == "Domino's Pizza"
    assert brand_exists(conn, "Domino's Pizza")
    assert not brand_exists(conn, "Papa John's")
