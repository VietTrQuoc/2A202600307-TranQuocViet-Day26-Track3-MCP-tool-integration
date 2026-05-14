from __future__ import annotations

import asyncio
import json

from fastmcp import Client

from init_db import create_database


async def main() -> int:
    create_database()
    import mcp_server

    async with Client(mcp_server.mcp) as client:
        await client.ping()

        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()

        tool_names = sorted(tool.name for tool in tools)
        resource_uris = sorted(str(resource.uri) for resource in resources)
        template_uris = sorted(str(template.uriTemplate) for template in templates)

        assert {"aggregate", "insert", "search"}.issubset(tool_names)
        assert "schema://database" in resource_uris
        assert "schema://table/{table_name}" in template_uris

        search_result = await client.call_tool(
            "search",
            {
                "table": "students",
                "filters": {"cohort": "A1"},
                "columns": ["name", "cohort"],
                "order_by": "name",
            },
        )
        aggregate_result = await client.call_tool(
            "aggregate",
            {"table": "enrollments", "metric": "avg", "column": "score", "group_by": "status"},
        )
        schema_result = await client.read_resource("schema://table/students")

    print(
        json.dumps(
            {
                "ping": "ok",
                "tools": tool_names,
                "resources": resource_uris,
                "resource_templates": template_uris,
                "search": search_result.structured_content,
                "aggregate": aggregate_result.structured_content,
                "schema_table_students": schema_result[0].text,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
