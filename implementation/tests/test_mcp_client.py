from __future__ import annotations

import asyncio

import pytest

fastmcp = pytest.importorskip("fastmcp")


def test_fastmcp_client_discovers_and_calls_tools():
    asyncio.run(_run_client_smoke_test())


async def _run_client_smoke_test():
    from fastmcp import Client

    from implementation.init_db import create_database

    create_database()
    from implementation import mcp_server

    async with Client(mcp_server.mcp) as client:
        await client.ping()
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()

        assert {"aggregate", "insert", "search"}.issubset({tool.name for tool in tools})
        assert "schema://database" in {str(resource.uri) for resource in resources}
        assert "schema://table/{table_name}" in {str(template.uriTemplate) for template in templates}

        result = await client.call_tool(
            "search",
            {"table": "students", "filters": {"cohort": "A1"}, "columns": ["name", "cohort"]},
        )
        assert result.structured_content["count"] == 2

        schema = await client.read_resource("schema://table/students")
        assert "cohort" in schema[0].text
