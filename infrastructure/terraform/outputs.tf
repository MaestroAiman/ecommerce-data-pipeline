output "glue_database_name" {
  description = "Glue Data Catalog database used by Athena (see sql/create_tables.sql)."
  value       = aws_glue_catalog_database.ecommerce_pipeline.name
}

output "athena_workgroup_name" {
  description = "Athena workgroup name (see scripts/run_athena_query.py)."
  value       = aws_athena_workgroup.ecommerce_pipeline.name
}

output "athena_results_location" {
  description = "S3 prefix where Athena writes query results."
  value       = "s3://${data.aws_s3_bucket.data_lake.id}/athena-results/"
}
