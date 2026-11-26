# Glue Data Catalog database that Athena queries against. Matches the
# database created in sql/create_tables.sql.
resource "aws_glue_catalog_database" "ecommerce_pipeline" {
  name = "ecommerce_pipeline"
}

# Athena workgroup: dedicated query-results location (under the same bucket)
# and a per-query data-scanned cap to keep costs predictable.
resource "aws_athena_workgroup" "ecommerce_pipeline" {
  name = "ecommerce-pipeline-workgroup"

  configuration {
    enforce_workgroup_configuration = true
    bytes_scanned_cutoff_per_query  = var.athena_bytes_scanned_cutoff

    result_configuration {
      output_location = "s3://${data.aws_s3_bucket.data_lake.id}/athena-results/"
    }
  }
}
