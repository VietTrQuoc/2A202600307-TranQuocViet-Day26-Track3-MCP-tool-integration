from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).with_name("sqlite_lab.db")


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    """Small SQLite data access layer with strict identifier validation."""

    FILTER_OPERATORS = {
        "=": "=",
        "==": "=",
        "eq": "=",
        "!=": "!=",
        "<>": "!=",
        "ne": "!=",
        ">": ">",
        "gt": ">",
        ">=": ">=",
        "gte": ">=",
        "<": "<",
        "lt": "<",
        "<=": "<=",
        "lte": "<=",
        "like": "LIKE",
        "in": "IN",
        "is_null": "IS NULL",
        "not_null": "IS NOT NULL",
    }
    AGGREGATES = {"count", "avg", "sum", "min", "max"}
    NUMERIC_TYPES = {"INTEGER", "INT", "REAL", "NUMERIC", "DECIMAL", "FLOAT", "DOUBLE"}

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        self._validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({self._quote(table)})").fetchall()
        return [
            {
                "name": row["name"],
                "type": row["type"],
                "nullable": not bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            }
            for row in rows
        ]

    def schema_snapshot(self) -> dict[str, Any]:
        return {
            "database": str(self.db_path),
            "tables": {table: self.get_table_schema(table) for table in self.list_tables()},
        }

    def search(
        self,
        table: str,
        columns: Sequence[str] | None = None,
        filters: Any | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        schema = self._schema_map(table)
        selected_columns = self._validate_selected_columns(columns, schema)
        select_sql = ", ".join(self._quote(column) for column in selected_columns)
        where_sql, params = self._build_where(filters, schema)
        safe_limit = self._validate_limit(limit)
        safe_offset = self._validate_offset(offset)

        sql = f"SELECT {select_sql} FROM {self._quote(table)}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if order_by is not None:
            self._validate_column(order_by, schema)
            direction = "DESC" if descending else "ASC"
            sql += f" ORDER BY {self._quote(order_by)} {direction}"
        sql += " LIMIT ? OFFSET ?"

        with self.connect() as conn:
            rows = conn.execute(sql, [*params, safe_limit, safe_offset]).fetchall()

        return {
            "table": table,
            "columns": selected_columns,
            "rows": [dict(row) for row in rows],
            "count": len(rows),
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def insert(self, table: str, values: Mapping[str, Any]) -> dict[str, Any]:
        schema = self._schema_map(table)
        if not isinstance(values, Mapping) or not values:
            raise ValidationError("insert values must be a non-empty object")

        columns = list(values.keys())
        for column in columns:
            self._validate_column(column, schema)

        quoted_columns = ", ".join(self._quote(column) for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {self._quote(table)} ({quoted_columns}) VALUES ({placeholders})"

        try:
            with self.connect() as conn:
                cursor = conn.execute(sql, [values[column] for column in columns])
                row_id = cursor.lastrowid
                conn.commit()
                inserted = self._fetch_inserted_row(conn, table, schema, row_id, values)
        except sqlite3.IntegrityError as exc:
            raise ValidationError(f"insert failed: {exc}") from exc

        return {"table": table, "inserted": inserted, "rowid": row_id}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any | None = None,
        group_by: str | Sequence[str] | None = None,
    ) -> dict[str, Any]:
        schema = self._schema_map(table)
        safe_metric = self._validate_metric(metric)
        group_columns = self._normalize_group_by(group_by, schema)
        aggregate_column = self._aggregate_column(safe_metric, column, schema)
        where_sql, params = self._build_where(filters, schema)

        select_parts = [self._quote(column_name) for column_name in group_columns]
        select_parts.append(f"{safe_metric.upper()}({aggregate_column}) AS value")
        sql = f"SELECT {', '.join(select_parts)} FROM {self._quote(table)}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if group_columns:
            sql += " GROUP BY " + ", ".join(self._quote(column_name) for column_name in group_columns)
        sql += " ORDER BY " + (", ".join(self._quote(column_name) for column_name in group_columns) if group_columns else "value")

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "metric": safe_metric,
            "column": column,
            "group_by": group_columns,
            "rows": [dict(row) for row in rows],
        }

    def _fetch_inserted_row(
        self,
        conn: sqlite3.Connection,
        table: str,
        schema: Mapping[str, Mapping[str, Any]],
        row_id: int,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        primary_keys = [name for name, column in schema.items() if column["primary_key"]]
        if len(primary_keys) == 1:
            pk = primary_keys[0]
            pk_value = values.get(pk, row_id)
            row = conn.execute(
                f"SELECT * FROM {self._quote(table)} WHERE {self._quote(pk)} = ?",
                [pk_value],
            ).fetchone()
            if row is not None:
                return dict(row)
        return dict(values)

    def _validate_table(self, table: str) -> None:
        if not isinstance(table, str) or not table:
            raise ValidationError("table name must be a non-empty string")
        if table not in self.list_tables():
            raise ValidationError(f"unknown table: {table}")

    def _schema_map(self, table: str) -> dict[str, dict[str, Any]]:
        return {column["name"]: column for column in self.get_table_schema(table)}

    def _validate_column(self, column: str, schema: Mapping[str, Any]) -> None:
        if not isinstance(column, str) or not column:
            raise ValidationError("column name must be a non-empty string")
        if column not in schema:
            raise ValidationError(f"unknown column: {column}")

    def _validate_selected_columns(
        self, columns: Sequence[str] | None, schema: Mapping[str, Any]
    ) -> list[str]:
        if columns is None:
            return list(schema.keys())
        if isinstance(columns, str) or not isinstance(columns, Sequence) or not columns:
            raise ValidationError("columns must be a non-empty list of column names")
        selected = list(columns)
        for column in selected:
            self._validate_column(column, schema)
        return selected

    def _build_where(self, filters: Any | None, schema: Mapping[str, Any]) -> tuple[str, list[Any]]:
        if filters is None or filters == {} or filters == []:
            return "", []
        conditions = self._normalize_filters(filters)
        clauses: list[str] = []
        params: list[Any] = []

        for condition in conditions:
            column = condition["column"]
            operator = self._validate_filter_operator(condition["operator"])
            value = condition.get("value")
            self._validate_column(column, schema)

            if operator in {"IS NULL", "IS NOT NULL"}:
                clauses.append(f"{self._quote(column)} {operator}")
            elif operator == "IN":
                if isinstance(value, str) or not isinstance(value, Sequence) or not value:
                    raise ValidationError("IN filter value must be a non-empty list")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{self._quote(column)} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{self._quote(column)} {operator} ?")
                params.append(value)

        return " AND ".join(clauses), params

    def _normalize_filters(self, filters: Any) -> list[dict[str, Any]]:
        if isinstance(filters, Mapping):
            if "column" in filters:
                return [
                    {
                        "column": filters["column"],
                        "operator": filters.get("operator", filters.get("op", "=")),
                        "value": filters.get("value"),
                    }
                ]

            conditions = []
            for column, raw_condition in filters.items():
                if isinstance(raw_condition, Mapping):
                    conditions.append(
                        {
                            "column": column,
                            "operator": raw_condition.get("operator", raw_condition.get("op", "=")),
                            "value": raw_condition.get("value"),
                        }
                    )
                else:
                    conditions.append({"column": column, "operator": "=", "value": raw_condition})
            return conditions

        if isinstance(filters, Sequence) and not isinstance(filters, str):
            conditions = []
            for raw_condition in filters:
                if not isinstance(raw_condition, Mapping) or "column" not in raw_condition:
                    raise ValidationError("each filter must include a column")
                conditions.append(
                    {
                        "column": raw_condition["column"],
                        "operator": raw_condition.get("operator", raw_condition.get("op", "=")),
                        "value": raw_condition.get("value"),
                    }
                )
            return conditions

        raise ValidationError("filters must be an object or a list of filter objects")

    def _validate_filter_operator(self, operator: str) -> str:
        if not isinstance(operator, str):
            raise ValidationError("filter operator must be a string")
        normalized = operator.lower()
        if normalized not in self.FILTER_OPERATORS:
            raise ValidationError(f"unsupported filter operator: {operator}")
        return self.FILTER_OPERATORS[normalized]

    def _validate_metric(self, metric: str) -> str:
        if not isinstance(metric, str):
            raise ValidationError("metric must be a string")
        normalized = metric.lower()
        if normalized not in self.AGGREGATES:
            raise ValidationError(f"unsupported aggregate metric: {metric}")
        return normalized

    def _aggregate_column(self, metric: str, column: str | None, schema: Mapping[str, Mapping[str, Any]]) -> str:
        if metric == "count" and column is None:
            return "*"
        if column is None:
            raise ValidationError(f"{metric} aggregate requires a column")
        self._validate_column(column, schema)
        if metric in {"avg", "sum"} and not self._is_numeric(schema[column]["type"]):
            raise ValidationError(f"{metric} aggregate requires a numeric column")
        return self._quote(column)

    def _normalize_group_by(
        self, group_by: str | Sequence[str] | None, schema: Mapping[str, Any]
    ) -> list[str]:
        if group_by is None:
            return []
        group_columns = [group_by] if isinstance(group_by, str) else list(group_by)
        if not group_columns:
            raise ValidationError("group_by must include at least one column")
        for column in group_columns:
            self._validate_column(column, schema)
        return group_columns

    def _validate_limit(self, limit: int) -> int:
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValidationError("limit must be an integer between 1 and 100")
        return limit

    def _validate_offset(self, offset: int) -> int:
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative integer")
        return offset

    def _is_numeric(self, declared_type: str) -> bool:
        return any(token in declared_type.upper() for token in self.NUMERIC_TYPES)

    def _quote(self, identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'
