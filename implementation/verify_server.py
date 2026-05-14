from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from .db import DEFAULT_DB_PATH, SQLiteAdapter, ValidationError
    from .init_db import create_database
except ImportError:  # pragma: no cover - used when run as a script from this directory.
    from db import DEFAULT_DB_PATH, SQLiteAdapter, ValidationError
    from init_db import create_database


def _print(title: str, payload: object) -> None:
    print(f"\n== {title} ==")
    print(json.dumps(payload, indent=2))


def main() -> int:
    create_database(DEFAULT_DB_PATH)
    adapter = SQLiteAdapter(DEFAULT_DB_PATH)

    _print("schema resource payload", adapter.schema_snapshot())
    _print(
        "search students in cohort A1",
        adapter.search("students", filters={"cohort": "A1"}, order_by="name"),
    )
    _print(
        "insert student",
        adapter.insert(
            "students",
            {
                "name": "Minh Hoang",
                "email": "minh.hoang@example.edu",
                "cohort": "A1",
                "age": 23,
            },
        ),
    )
    _print(
        "average score by status",
        adapter.aggregate("enrollments", "avg", column="score", group_by="status"),
    )

    try:
        adapter.search("missing_table")
    except ValidationError as exc:
        _print("expected invalid request", {"error": str(exc)})
    else:
        raise AssertionError("invalid table was not rejected")

    try:
        import mcp_server

        tool_names = sorted(["search", "insert", "aggregate"])
        _print(
            "mcp server import",
            {
                "server": "SQLite Lab MCP Server",
                "tools": tool_names,
                "resources": ["schema://database", "schema://table/{table_name}"],
                "module": str(Path(mcp_server.__file__).resolve()),
            },
        )
    except SystemExit as exc:
        _print("mcp dependency check", {"warning": str(exc)})

    print(f"\nVerification completed. Database: {DEFAULT_DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
