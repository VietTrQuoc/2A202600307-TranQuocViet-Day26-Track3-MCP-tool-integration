from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .db import DEFAULT_DB_PATH, SQLiteAdapter, ValidationError
    from .init_db import create_database
except ImportError:  # pragma: no cover - used when run as a script from this directory.
    from db import DEFAULT_DB_PATH, SQLiteAdapter, ValidationError
    from init_db import create_database

try:
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without dependency installed.
    raise SystemExit(
        "FastMCP is not installed. Run: python -m pip install -r requirements.txt"
    ) from exc


if not Path(DEFAULT_DB_PATH).exists():
    create_database(DEFAULT_DB_PATH)

adapter = SQLiteAdapter(DEFAULT_DB_PATH)
mcp = FastMCP("SQLite Lab MCP Server")


def _tool_error(exc: ValidationError) -> ValueError:
    return ValueError(str(exc))


@mcp.tool(name="search")
def search(
    table: str,
    filters: Any | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows with validated filters, ordering, and pagination."""
    try:
        return adapter.search(table, columns, filters, limit, offset, order_by, descending)
    except ValidationError as exc:
        raise _tool_error(exc) from exc


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert a row after validating the table and every column name."""
    try:
        return adapter.insert(table, values)
    except ValidationError as exc:
        raise _tool_error(exc) from exc


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: Any | None = None,
    group_by: str | list[str] | None = None,
) -> dict[str, Any]:
    """Run count, avg, sum, min, or max with optional filters and grouping."""
    try:
        return adapter.aggregate(table, metric, column, filters, group_by)
    except ValidationError as exc:
        raise _tool_error(exc) from exc


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full database schema as formatted JSON."""
    return json.dumps(adapter.schema_snapshot(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as formatted JSON."""
    try:
        payload = {"table": table_name, "columns": adapter.get_table_schema(table_name)}
        return json.dumps(payload, indent=2)
    except ValidationError as exc:
        raise _tool_error(exc) from exc


if __name__ == "__main__":
    mcp.run()
