from aws_cdk import (
    Stack, aws_lambda as _lambda,
    aws_sqs as sqs, aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigw,
    Tags
)
from constructs import Construct

class ReadRecallStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Add project tag to all resources
        Tags.of(self).add("Project", "ReadRecall")
        
        # ▼ SQS Queues
        book_queue = sqs.Queue.from_queue_name(
            self, "BookQueue", "book-processing-queue"
        )
        
        # ▼ S3 Buckets
        output_bucket = s3.Bucket.from_bucket_name(
            self, "OutputBucket", "normalized-book-bucket"
        )
        
        upload_bucket = s3.Bucket.from_bucket_name(
            self, "UploadBucket", "book-processing-uploads"
        )
        
        # ▼ Lambda Functions
        normalize_lambda = _lambda.Function.from_function_name(
            self, "NormalizeFunction", "normalize-books"
        )
        
        book_summary_lambda = _lambda.Function.from_function_name(
            self, "BookSummaryFunction", "bookSummaryLambda"
        )
        
        character_summary_lambda = _lambda.Function.from_function_name(
            self, "CharacterSummaryFunction", "characterSummaryLambda"
        )
        
        presigned_url_lambda = _lambda.Function.from_function_name(
            self, "PresignedUrlFunction", "generate_presigned_upload_url"
        )
