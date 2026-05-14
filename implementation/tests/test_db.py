from __future__ import annotations

import pytest

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database


@pytest.fixture()
def adapter(tmp_path):
    db_path = tmp_path / "lab.db"
    create_database(db_path)
    return SQLiteAdapter(db_path)


def test_search_filters_order_and_pagination(adapter):
    result = adapter.search(
        "students",
        filters={"cohort": "A1"},
        columns=["name", "cohort"],
        limit=1,
        offset=0,
        order_by="name",
    )

    assert result["count"] == 1
    assert result["columns"] == ["name", "cohort"]
    assert result["rows"][0] == {"name": "An Nguyen", "cohort": "A1"}


def test_insert_returns_inserted_payload(adapter):
    result = adapter.insert(
        "students",
        {
            "name": "Minh Hoang",
            "email": "minh.hoang@example.edu",
            "cohort": "A1",
            "age": 23,
        },
    )

    assert result["inserted"]["id"] > 0
    assert result["inserted"]["email"] == "minh.hoang@example.edu"


def test_aggregate_average_by_status(adapter):
    result = adapter.aggregate("enrollments", "avg", column="score", group_by="status")

    rows_by_status = {row["status"]: row["value"] for row in result["rows"]}
    assert rows_by_status["active"] == pytest.approx(80.6666667)
    assert rows_by_status["completed"] == pytest.approx(88.3)


def test_schema_snapshot_contains_tables(adapter):
    schema = adapter.schema_snapshot()

    assert set(schema["tables"]) == {"courses", "enrollments", "students"}
    assert any(column["name"] == "cohort" for column in schema["tables"]["students"])


@pytest.mark.parametrize(
    ("method_name", "args", "message"),
    [
        ("search", ("missing",), "unknown table"),
        ("search", ("students", None, {"missing": "x"}), "unknown column"),
        ("search", ("students", None, {"age": {"op": "contains", "value": 20}}), "unsupported"),
        ("insert", ("students", {}), "non-empty"),
        ("aggregate", ("students", "median", "age"), "unsupported"),
        ("aggregate", ("students", "avg", "name"), "numeric"),
    ],
)
def test_invalid_requests_are_rejected(adapter, method_name, args, message):
    method = getattr(adapter, method_name)

    with pytest.raises(ValidationError, match=message):
        method(*args)
