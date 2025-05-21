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
        
        # ▼ Lambda Functions
        userregisterlambda_lambda = _lambda.Function.from_function_name(
            self, "userRegisterLambdaFunction", "userRegisterLambda"
        )

        getbookcharacters_lambda = _lambda.Function.from_function_name(
            self, "getBookCharactersFunction", "getBookCharacters"
        )

        loginuserlambda_lambda = _lambda.Function.from_function_name(
            self, "loginUserLambdaFunction", "loginUserLambda"
        )

        getuserbooks_lambda = _lambda.Function.from_function_name(
            self, "getUserBooksFunction", "getUserBooks"
        )

        charactersummarylambda_lambda = _lambda.Function.from_function_name(
            self, "characterSummaryLambdaFunction", "characterSummaryLambda"
        )

        normalizebooks_lambda = _lambda.Function.from_function_name(
            self, "normalizebooksFunction", "normalize-books"
        )

        generatepresigneduploadurl_lambda = _lambda.Function.from_function_name(
            self, "generatePresignedUploadUrlFunction", "generatePresignedUploadUrl"
        )

        apiendpointauthorizer_lambda = _lambda.Function.from_function_name(
            self, "apiEndpointAuthorizerFunction", "apiEndpointAuthorizer"
        )

        booksummarylambda_lambda = _lambda.Function.from_function_name(
            self, "bookSummaryLambdaFunction", "bookSummaryLambda"
        )

        getbooksummary_lambda = _lambda.Function.from_function_name(
            self, "getBookSummaryFunction", "getBookSummary"
        )

        getmeuserlambda_lambda = _lambda.Function.from_function_name(
            self, "getMeUserLambdaFunction", "getMeUserLambda"
        )

        # ▼ S3 Buckets
        awssamclimanageddefaultsamclisourcebucketyc7zsffcj5te_bucket = s3.Bucket.from_bucket_name(
            self, "awssamclimanageddefaultsamclisourcebucketyc7zsffcj5teBucket", "aws-sam-cli-managed-default-samclisourcebucket-yc7zsffcj5te"
        )

        bookprocessinguploads_bucket = s3.Bucket.from_bucket_name(
            self, "bookprocessinguploadsBucket", "book-processing-uploads"
        )

        cftemplates1sam0e6e0go8zuseast1_bucket = s3.Bucket.from_bucket_name(
            self, "cftemplates1sam0e6e0go8zuseast1Bucket", "cf-templates-1sam0e6e0go8z-us-east-1"
        )

        lambdasservices_bucket = s3.Bucket.from_bucket_name(
            self, "lambdasservicesBucket", "lambdas-services"
        )

        normalizedbooks_bucket = s3.Bucket.from_bucket_name(
            self, "normalizedbooksBucket", "normalized-books"
        )

        # ▼ SQS Queues
        bookprocessingqueue_queue = sqs.Queue.from_queue_arn(
            self, "bookprocessingqueueQueue", "arn:aws:sqs:us-east-1:577125335862:book-processing-queue"
        )

        summarizecharacterqueue_queue = sqs.Queue.from_queue_arn(
            self, "summarizecharacterqueueQueue", "arn:aws:sqs:us-east-1:577125335862:summarize-character-queue"
        )

        # ▼ DynamoDB Tables
        characters_table = dynamodb.Table.from_table_name(
            self, "charactersTable", "characters"
        )

        summaries_table = dynamodb.Table.from_table_name(
            self, "summariesTable", "summaries"
        )

        userbooks_table = dynamodb.Table.from_table_name(
            self, "userbooksTable", "user_books"
        )

        users_table = dynamodb.Table.from_table_name(
            self, "usersTable", "users"
        )

        # ▼ API Gateway
        readrecallapi_api = apigw.RestApi.from_rest_api_id(
            self, "ReadRecallAPIApi", "hgtv5vd4n3"
        )
