"""
Optional helper: runs one query from sql/queries.sql against real Athena and
prints the result.

NOT executed by the pipeline, by any test, or automatically by Claude - this
talks to real AWS and incurs real query-scan cost. Run manually once the
tables from sql/create_tables.sql and the Terraform-managed workgroup exist:

    python scripts/run_athena_query.py --query-index 0

Requires AWS credentials in .env and the Glue database / Athena workgroup
created by infrastructure/terraform.
"""
import argparse
import os
import time
from pathlib import Path

import boto3
from dotenv import load_dotenv

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
DEFAULT_DATABASE = "ecommerce_pipeline"
DEFAULT_WORKGROUP = "ecommerce-pipeline-workgroup"


def load_queries():
    text = (SQL_DIR / "queries.sql").read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
    return [q.strip() for q in text.split(";") if q.strip()]


def run_query(athena, query, database, workgroup, output_location):
    start = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        WorkGroup=workgroup,
        ResultConfiguration={"OutputLocation": output_location},
    )
    execution_id = start["QueryExecutionId"]

    status = "RUNNING"
    while status in ("RUNNING", "QUEUED"):
        time.sleep(1)
        status = athena.get_query_execution(QueryExecutionId=execution_id)["QueryExecution"]["Status"]["State"]

    if status != "SUCCEEDED":
        raise RuntimeError(f"Athena query {execution_id} ended with status {status}")

    rows = athena.get_query_results(QueryExecutionId=execution_id)["ResultSet"]["Rows"]
    header = [c.get("VarCharValue", "") for c in rows[0]["Data"]]
    data_rows = [[c.get("VarCharValue", "") for c in r["Data"]] for r in rows[1:]]
    return header, data_rows


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run one query from sql/queries.sql against Athena")
    parser.add_argument("--query-index", type=int, default=0, help="0-based index into sql/queries.sql")
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--workgroup", default=DEFAULT_WORKGROUP)
    args = parser.parse_args()

    bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    if not bucket_name:
        raise SystemExit("AWS_S3_BUCKET_NAME not set in .env")

    queries = load_queries()
    query = queries[args.query_index]
    output_location = f"s3://{bucket_name}/athena-results/"

    athena = boto3.client("athena", region_name=region)
    header, data_rows = run_query(athena, query, args.database, args.workgroup, output_location)

    print(" | ".join(header))
    for row in data_rows:
        print(" | ".join(row))


if __name__ == "__main__":
    main()
