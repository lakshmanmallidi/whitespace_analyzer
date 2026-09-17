import pytest

from whitespace_analyzer.ods.brands import save_brand
from whitespace_analyzer.ods.competitors import (
    add_competitor,
    add_competitors,
    is_competitor,
    list_competitors,
    remove_competitor,
)
from whitespace_analyzer.ods.database import get_connection


@pytest.fixture
def conn(tmp_path):
    c = get_connection(tmp_path / "ods.sqlite")
    return c, save_brand(c, "Domino's", "pizza"), save_brand(c, "Pizza Hut", "pizza"), save_brand(c, "Papa John's", "pizza")


def test_add_and_list_competitors(conn):
    c, dominos, hut, papa = conn
    assert add_competitor(c, dominos, hut) is True
    assert add_competitor(c, dominos, papa) is True

    competitors = list_competitors(c, dominos)
    assert len(competitors) == 2
    assert {b["brand_name"] for b in competitors} == {"Pizza Hut", "Papa John's"}
    assert all(b["created_at"] for b in competitors)


def test_add_duplicate_competitor_is_noop(conn):
    c, dominos, hut, _ = conn
    assert add_competitor(c, dominos, hut) is True
    assert add_competitor(c, dominos, hut) is False
    assert len(list_competitors(c, dominos)) == 1


def test_brand_cannot_compete_with_itself(conn):
    c, dominos, _, _ = conn
    with pytest.raises(ValueError, match="itself"):
        add_competitor(c, dominos, dominos)


def test_add_competitors_bulk_and_remove(conn):
    c, dominos, hut, papa = conn
    assert add_competitors(c, dominos, [hut, papa, hut]) == 2
    assert is_competitor(c, dominos, hut)

    remove_competitor(c, dominos, hut)
    assert not is_competitor(c, dominos, hut)
    assert is_competitor(c, dominos, papa)


def test_nonexistent_competitor_brand_rejected(conn):
    c, dominos, _, _ = conn
    with pytest.raises(ValueError, match="does not exist"):
        add_competitor(c, dominos, 9999)
