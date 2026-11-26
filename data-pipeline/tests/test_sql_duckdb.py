"""
Validates the query LOGIC in sql/queries.sql by running the exact same SQL
text through DuckDB against small local Parquet files, with no AWS/Athena
access at all.

DuckDB is not Athena: both use an ANSI-SQL/Trino-like dialect, but the engines
differ (DuckDB is embedded, Athena is Trino/Presto over Hive tables), so a
query that works here is not guaranteed to run unmodified on Athena - this
only pins the logic, not full Athena-dialect compatibility.
"""
from pathlib import Path

import duckdb
import pandas as pd
import pytest

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"

QUALIFIED_TABLE_NAMES = {
    "ecommerce_pipeline.customer_metrics": "customer_metrics",
    "ecommerce_pipeline.product_metrics": "product_metrics",
    "ecommerce_pipeline.monthly_sales": "monthly_sales",
}


def load_queries():
    text = (SQL_DIR / "queries.sql").read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
    return [q.strip() for q in text.split(";") if q.strip()]


def for_duckdb(query, tmp_path):
    """Swap the Athena-qualified table names for DuckDB read_parquet() calls."""
    for qualified, name in QUALIFIED_TABLE_NAMES.items():
        parquet_path = (tmp_path / f"{name}.parquet").as_posix()
        query = query.replace(qualified, f"read_parquet('{parquet_path}')")
    return query


@pytest.fixture
def metrics_parquet(tmp_path):
    customer_metrics = pd.DataFrame([
        {"customer_id": "c1", "age_group": "26-35", "total_spent": 500.0,
         "order_count": 3, "ave_order_value": 166.67},
        {"customer_id": "c2", "age_group": "36-50", "total_spent": 900.0,
         "order_count": 2, "ave_order_value": 450.0},
    ])
    product_metrics = pd.DataFrame([
        {"product_id": "p1", "product_name": "Widget", "category": "Tools",
         "total_revenue": 300.0, "total_quantity_sold": 10, "number_of_orders": 5},
        {"product_id": "p2", "product_name": "Gadget", "category": "Tools",
         "total_revenue": 700.0, "total_quantity_sold": 20, "number_of_orders": 8},
    ])
    monthly_sales = pd.DataFrame([
        {"order_year": 2025, "order_month": 1, "total_revenue": 1000.0, "order_count": 10},
        {"order_year": 2025, "order_month": 2, "total_revenue": 1500.0, "order_count": 12},
    ])

    customer_metrics.to_parquet(tmp_path / "customer_metrics.parquet", index=False)
    product_metrics.to_parquet(tmp_path / "product_metrics.parquet", index=False)
    monthly_sales.to_parquet(tmp_path / "monthly_sales.parquet", index=False)

    return tmp_path


def test_top_customers_by_clv_query(metrics_parquet):
    query = load_queries()[0]
    result = duckdb.sql(for_duckdb(query, metrics_parquet)).df()

    assert list(result["customer_id"]) == ["c2", "c1"]  # ordered by total_spent desc
    assert result.iloc[0]["total_spent"] == 900.0


def test_monthly_revenue_trend_query(metrics_parquet):
    query = load_queries()[1]
    result = duckdb.sql(for_duckdb(query, metrics_parquet)).df()

    assert list(result["order_month"]) == [1, 2]
    assert list(result["total_revenue"]) == [1000.0, 1500.0]


def test_product_ranking_query(metrics_parquet):
    query = load_queries()[2]
    result = duckdb.sql(for_duckdb(query, metrics_parquet)).df()

    assert list(result["product_id"]) == ["p2", "p1"]  # ordered by total_revenue desc
