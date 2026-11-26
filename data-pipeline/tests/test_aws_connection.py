import os
import boto3
import pytest
from dotenv import load_dotenv


@pytest.mark.integration
def test_aws_connection():
    """Integration test: needs real AWS credentials and network access.
    Excluded by default (see pytest.ini); run explicitly with `pytest -m integration`.
    """
    load_dotenv()

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION")
    bucket_name = os.getenv("AWS_S3_BUCKET_NAME")

    print("Testing AWS Connection")
    print(f"Region: {region}")
    print(f"Bucket: {bucket_name}")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    buckets = s3.list_buckets()
    print(f"Connected! You have {len(buckets['Buckets'])} S3 buckets")


if __name__ == "__main__":
    test_aws_connection()
