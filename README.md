# SQLite FastMCP Database Server Lab

This repository contains a complete MCP lab submission: a FastMCP server backed by SQLite with safe `search`, `insert`, and `aggregate` tools plus schema resources.

## What Is Included

- FastMCP server: `implementation/mcp_server.py`
- SQLite adapter with input validation: `implementation/db.py`
- Reproducible schema and seed data: `implementation/init_db.py`
- Direct verification script: `implementation/verify_server.py`
- FastMCP client smoke test: `implementation/verify_mcp_client.py`
- Automated tests: `implementation/tests/`
- Inspector helper: `implementation/start_inspector.ps1`

The sample database has three tables: `students`, `courses`, and `enrollments`.

## Setup

Run these commands from the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r implementation\requirements.txt
.\.venv\Scripts\python.exe implementation\init_db.py
```

The server also creates the database automatically if `implementation/sqlite_lab.db` is missing.

## Run The MCP Server

```powershell
.\.venv\Scripts\python.exe implementation\mcp_server.py
```

The server uses stdio transport by default, which is the easiest mode for local MCP clients.

## Tools

### `search`

Search rows with filters, selected columns, ordering, limit, and offset.

Example arguments:

```json
{
  "table": "students",
  "filters": { "cohort": "A1" },
  "columns": ["name", "email", "cohort"],
  "limit": 10,
  "offset": 0,
  "order_by": "name"
}
```

Supported filter operators include `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `in`, `is_null`, and `not_null`.

### `insert`

Insert a row after validating the table and column names.

Example arguments:

```json
{
  "table": "students",
  "values": {
    "name": "Minh Hoang",
    "email": "minh.hoang@example.edu",
    "cohort": "A1",
    "age": 23
  }
}
```

### `aggregate`

Run `count`, `avg`, `sum`, `min`, or `max`, with optional filters and grouping.

Example arguments:

```json
{
  "table": "enrollments",
  "metric": "avg",
  "column": "score",
  "group_by": "status"
}
```

## Resources

- `schema://database` returns the full database schema as JSON.
- `schema://table/{table_name}` returns one table schema, for example `schema://table/students`.

## Validation And Safety

The implementation rejects:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate metrics
- empty inserts
- non-numeric `avg` and `sum` targets

SQL values are passed through bound parameters. Table and column identifiers are accepted only after checking them against SQLite schema metadata.

## Verification

Run all automated tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest_tmp
```

Run direct functional verification:

```powershell
.\.venv\Scripts\python.exe implementation\verify_server.py
```

This demonstrates schema output, valid `search`, valid `insert`, valid `aggregate`, and a rejected invalid table request.

Run FastMCP client verification:

```powershell
.\.venv\Scripts\python.exe implementation\verify_mcp_client.py
```

This verifies a real FastMCP client can ping the server, discover tools, discover resources, call tools, and read a schema resource.

Current local verification result:

```text
11 passed
```

## MCP Inspector

Start Inspector from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File implementation\start_inspector.ps1
```

In Inspector, check:

- tools list contains `search`, `insert`, and `aggregate`
- resources list contains `schema://database`
- resource templates contain `schema://table/{table_name}`
- valid calls return rows
- invalid calls return clear errors

## Client Configuration Examples

Replace the paths with absolute paths on your machine if needed.

### Claude Code `.mcp.json`

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "C:\\ABSOLUTE\\PATH\\TO\\.venv\\Scripts\\python.exe",
      "args": ["C:\\ABSOLUTE\\PATH\\TO\\implementation\\mcp_server.py"],
      "env": {}
    }
  }
}
```

### Codex `~/.codex/config.toml`

```toml
[mcp_servers.sqlite_lab]
command = "C:\\ABSOLUTE\\PATH\\TO\\.venv\\Scripts\\python.exe"
args = ["C:\\ABSOLUTE\\PATH\\TO\\implementation\\mcp_server.py"]
```

### Gemini CLI

```powershell
gemini mcp add sqlite-lab C:\ABSOLUTE\PATH\TO\.venv\Scripts\python.exe C:\ABSOLUTE\PATH\TO\implementation\mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

Then try:

```powershell
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server to show the top 2 students in cohort A1."
```

## Demo Script

For a short demo video, show these steps:

1. Run `.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest_tmp`.
2. Run `.\.venv\Scripts\python.exe implementation\verify_mcp_client.py`.
3. Open Inspector and show the three tools.
4. Read `schema://database` and `schema://table/students`.
5. Call `search` for cohort `A1`.
6. Call `insert` with a new student.
7. Call `aggregate` average score by status.
8. Call `search` with a missing table to show a clear validation error.
