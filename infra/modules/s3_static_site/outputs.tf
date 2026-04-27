output "bucket_id" {
  description = "Static web bucket ID"
  value       = aws_s3_bucket.this.id
}

output "bucket_name" {
  description = "Static web bucket name"
  value       = aws_s3_bucket.this.bucket
}

output "bucket_arn" {
  description = "Static web bucket ARN"
  value       = aws_s3_bucket.this.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.this.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.this.id
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = aws_cloudfront_distribution.this.arn
}
