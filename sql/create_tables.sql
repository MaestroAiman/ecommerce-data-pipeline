-- Athena DDL for the e-commerce business metrics written by
-- data_processing.create_business_metrics() / upload_processed_data().
--
-- Replace <YOUR_BUCKET_NAME> with the value of AWS_S3_BUCKET_NAME (.env)
-- before running this in the Athena query editor.
--
-- Each metric lives under its own S3 prefix (processed/metrics/<metric>/)
-- so it can be mapped to its own external table without mixing files
-- from different metrics into the same table.

CREATE DATABASE IF NOT EXISTS ecommerce_pipeline;

-- Customer lifetime value (CLV) per customer
CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_pipeline.customer_metrics (
    customer_id      string,
    total_spent       double,
    order_count       bigint,
    ave_order_value   double,
    first_order       timestamp,
    last_order        timestamp,
    age_group         string
)
STORED AS PARQUET
LOCATION 's3://<YOUR_BUCKET_NAME>/processed/metrics/customer_metrics/';

-- Product sales performance
CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_pipeline.product_metrics (
    product_id           string,
    total_quantity_sold   bigint,
    total_revenue         double,
    number_of_orders      bigint,
    product_name          string,
    category              string,
    price                 double
)
STORED AS PARQUET
LOCATION 's3://<YOUR_BUCKET_NAME>/processed/metrics/product_metrics/';

-- Monthly revenue / order-count trend
CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_pipeline.monthly_sales (
    order_year     bigint,
    order_month    bigint,
    total_revenue  double,
    order_count    bigint
)
STORED AS PARQUET
LOCATION 's3://<YOUR_BUCKET_NAME>/processed/metrics/monthly_sales/';
