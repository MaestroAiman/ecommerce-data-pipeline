variable "bucket_name" {
  description = "Name of the existing S3 bucket (already created by src/data_ingestion/s3_uploader.py) used as the data lake. Matches AWS_S3_BUCKET_NAME in .env."
  type        = string
}

variable "aws_region" {
  description = "AWS region the bucket and Athena/Glue resources live in."
  type        = string
  default     = "us-east-1"
}

variable "athena_bytes_scanned_cutoff" {
  description = "Per-query data-scanned limit for the Athena workgroup, in bytes (cost control). AWS minimum is 10,000,000 bytes."
  type        = number
  default     = 1073741824 # 1 GiB
}
