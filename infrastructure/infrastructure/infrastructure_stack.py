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
        book_processing_queue = sqs.Queue.from_queue_arn(
            self, "BookProcessingQueue",
            f"arn:aws:sqs:{Stack.of(self).region}:{Stack.of(self).account}:book-processing-queue"
        )
        
        summarize_character_queue = sqs.Queue.from_queue_arn(
            self, "SummarizeCharacterQueue",
            f"arn:aws:sqs:{Stack.of(self).region}:{Stack.of(self).account}:summarize-character-queue"
        )
        
        # ▼ S3 Buckets
        normalized_books_bucket = s3.Bucket.from_bucket_name(
            self, "NormalizedBooksBucket",
            "normalized-books"
        )
        
        uploads_bucket = s3.Bucket.from_bucket_name(
            self, "UploadsBucket",
            "book-processing-uploads"
        )
        
        lambdas_services_bucket = s3.Bucket.from_bucket_name(
            self, "LambdasServicesBucket",
            "lambdas-services"
        )
        
        sam_cli_bucket = s3.Bucket.from_bucket_name(
            self, "SamCliBucket",
            "aws-sam-cli-managed-default-samclisourcebucket-yc7zsffcj5te"
        )
        
        cf_templates_bucket = s3.Bucket.from_bucket_name(
            self, "CfTemplatesBucket",
            "cf-templates-1sam0e6e0go8z-us-east-1"
        )
        
        # ▼ Lambda Functions
        normalize_books_lambda = _lambda.Function.from_function_name(
            self, "NormalizeBooksFunction", 
            "normalize-books"
        )
        
        book_summary_lambda = _lambda.Function.from_function_name(
            self, "BookSummaryFunction", 
            "bookSummaryLambda"
        )
        
        character_summary_lambda = _lambda.Function.from_function_name(
            self, "CharacterSummaryFunction", 
            "characterSummaryLambda"
        )
        
        generate_presigned_upload_url_lambda = _lambda.Function.from_function_name(
            self, "GeneratePresignedUploadUrlFunction", 
            "generatePresignedUploadUrl"
        )
        
        user_register_lambda = _lambda.Function.from_function_name(
            self, "UserRegisterFunction", 
            "userRegisterLambda"
        )
        
        login_user_lambda = _lambda.Function.from_function_name(
            self, "LoginUserFunction", 
            "loginUserLambda"
        )
        
        get_me_user_lambda = _lambda.Function.from_function_name(
            self, "GetMeUserFunction", 
            "getMeUserLambda"
        )
        
        get_user_books_lambda = _lambda.Function.from_function_name(
            self, "GetUserBooksFunction", 
            "getUserBooks"
        )
        
        get_book_summary_lambda = _lambda.Function.from_function_name(
            self, "GetBookSummaryFunction", 
            "getBookSummary"
        )
        
        get_book_characters_lambda = _lambda.Function.from_function_name(
            self, "GetBookCharactersFunction", 
            "getBookCharacters"
        )
        
        api_endpoint_authorizer_lambda = _lambda.Function.from_function_name(
            self, "ApiEndpointAuthorizerFunction", 
            "apiEndpointAuthorizer"
        )

        # ▼ DynamoDB Tables
        characters_table = dynamodb.Table.from_table_name(
            self, "CharactersTable", 
            "characters"
        )
        
        summaries_table = dynamodb.Table.from_table_name(
            self, "SummariesTable", 
            "summaries"
        )
        
        user_books_table = dynamodb.Table.from_table_name(
            self, "UserBooksTable", 
            "user_books"
        )
        
        users_table = dynamodb.Table.from_table_name(
            self, "UsersTable", 
            "users"
        )
        
        # ▼ API Gateway
        read_recall_api = apigw.RestApi.from_rest_api_id(
            self, "ReadRecallApi", 
            "ReadRecallAPI"  # You might need to replace this with the actual API ID
        )
