# The data lake bucket is created by src/data_ingestion/s3_uploader.py, not
# by Terraform - it is only referenced here, never managed/recreated.
data "aws_s3_bucket" "data_lake" {
  bucket = var.bucket_name
}
