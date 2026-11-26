import boto3
import pandas as pd
import pytest
from moto import mock_aws

from data_processing.data_processing import download_data_from_s3, upload_processed_data

BUCKET = "test-ecommerce-bucket"


@pytest.fixture
def s3_bucket():
    """A moto-mocked S3 bucket - no real AWS call is made."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        yield s3


def test_download_data_from_s3_reads_raw_csv_files(s3_bucket):
    customers_csv = "customer_id,email\nc1,a@example.com\nc2,b@example.com\n"
    s3_bucket.put_object(Bucket=BUCKET, Key="raw-data/customers.csv", Body=customers_csv.encode("utf-8"))

    datasets = download_data_from_s3(s3_bucket, BUCKET)

    assert "customers" in datasets
    assert len(datasets["customers"]) == 2
    assert list(datasets["customers"]["email"]) == ["a@example.com", "b@example.com"]
    # the other expected raw files are absent from the bucket - the function
    # logs and skips them instead of crashing
    assert "products" not in datasets


def test_upload_processed_data_writes_parquet_and_is_idempotent(s3_bucket):
    processed = {
        "customers_clean": pd.DataFrame({"customer_id": ["c1"], "age_group": pd.Categorical(["26-35"])}),
    }
    metrics = {
        "monthly_sales": pd.DataFrame({"order_year": [2025], "order_month": [1], "total_revenue": [10.0]}),
    }

    success = upload_processed_data(s3_bucket, BUCKET, processed, metrics)
    assert success is True

    keys = sorted(obj["Key"] for obj in s3_bucket.list_objects_v2(Bucket=BUCKET)["Contents"])
    assert keys == [
        "processed/customers_clean.parquet",
        "processed/metrics/monthly_sales/monthly_sales.parquet",
    ]

    # rerunning with the same fixed keys overwrites them in place, no duplicates
    upload_processed_data(s3_bucket, BUCKET, processed, metrics)
    keys_after_rerun = sorted(obj["Key"] for obj in s3_bucket.list_objects_v2(Bucket=BUCKET)["Contents"])
    assert keys_after_rerun == keys
