-- Reference queries against the tables created in create_tables.sql.
-- Run in the Athena query editor (or via scripts/run_athena_query.py).
--
-- tests/test_sql_duckdb.py runs these same statements through DuckDB against
-- small local Parquet files to validate the query logic without AWS. DuckDB's
-- SQL dialect is close to Athena's (Trino/Presto) but not identical, so this
-- only pins the logic - always double check column/function compatibility
-- before relying on an unmodified run in Athena.

-- Top 10 customers by lifetime value (CLV)
SELECT customer_id, age_group, total_spent, order_count, ave_order_value
FROM ecommerce_pipeline.customer_metrics
ORDER BY total_spent DESC
LIMIT 10;

-- Monthly revenue trend
SELECT order_year, order_month, total_revenue, order_count
FROM ecommerce_pipeline.monthly_sales
ORDER BY order_year, order_month;

-- Product ranking by revenue
SELECT product_id, product_name, category, total_revenue, total_quantity_sold, number_of_orders
FROM ecommerce_pipeline.product_metrics
ORDER BY total_revenue DESC
LIMIT 10;
