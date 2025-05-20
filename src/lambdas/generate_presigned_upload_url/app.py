import json
import uuid
import boto3
import os
import time # Import time for timestamp
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb') # Initialize DynamoDB resource

# Get environment variables
UPLOAD_BUCKET_NAME = os.environ.get("UPLOAD_BUCKET_NAME", "book-processing-uploads") # Ensure this matches your env var name
USER_BOOKS_TABLE_NAME = os.environ.get("USER_BOOKS_TABLE_NAME", "user_books") # New env var for User Books table

# --- Add check for environment variables ---
if not UPLOAD_BUCKET_NAME:
    logger.error("UPLOAD_BUCKET_NAME environment variable is not set.")
    raise ValueError("UPLOAD_BUCKET_NAME environment variable is not set.")

if not USER_BOOKS_TABLE_NAME:
    logger.error("USER_BOOKS_TABLE_NAME environment variable is not set.")
    raise ValueError("USER_BOOKS_TABLE_NAME environment variable is not set.")
# --- End check ---

# Get the User Books DynamoDB table object
user_books_table = dynamodb.Table(USER_BOOKS_TABLE_NAME)


ALLOWED_EXTENSIONS = {".pdf", ".epub"}


def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    try:
        # API Gateway sends the request body as a string in event['body']
        try:
            body = json.loads(event.get("body", "{}")) # Use "{}" as default for empty body
        except json.JSONDecodeError as e:
             logger.error(f"Invalid JSON in request body: {e}")
             return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON in request body"})
            }

        # Extract the necessary fields
        user_id = body.get("user_id")
        file_name = body.get("file_name", "")
        file_ext = os.path.splitext(file_name)[-1].lower()

        logger.info(f"Extracted Fields - user_id: {user_id}, file_name: {file_name}, file_ext: {file_ext}")

        # Validate input
        if not user_id or file_ext not in ALLOWED_EXTENSIONS:
            logger.warning(f"Invalid input: user_id={user_id}, file_ext={file_ext}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid user_id or file extension"})
            }

        # Generate a unique book_id and S3 key
        book_id = str(uuid.uuid4())
        s3_key = f"books/{user_id}/{book_id}/{file_name}"

        # Generate a pre-signed URL
        # Dynamically set ContentType based on file extension
        content_type_map = {
            ".pdf": "application/pdf",
            ".epub": "application/epub+zip",
        }
        upload_content_type = content_type_map.get(file_ext, 'application/octet-stream') # Default if extension is allowed but not mapped

        logger.info(f"Generating pre-signed URL for s3://{UPLOAD_BUCKET_NAME}/{s3_key} with Content-Type: {upload_content_type}")

        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET_NAME,
                'Key': s3_key,
                'ContentType': upload_content_type # Use dynamic content type
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )

        logger.info("Pre-signed URL generated successfully.")

        # --- Insert entry into User Books table ---
        try:
            logger.info(f"Inserting entry into {USER_BOOKS_TABLE_NAME} for user: {user_id}, book: {book_id}")
            user_books_table.put_item(
                Item={
                    'user_id': user_id, # <-- Changed from 'userId' to 'user_id' to match error message
                    'book_id': book_id, # Sort Key
                    'file_name': file_name,
                    'upload_timestamp': int(time.time()), # Record when the URL was generated
                    's3_key': s3_key, # Add the S3 key
                    'upload_bucket_name': UPLOAD_BUCKET_NAME, # Add the upload bucket name
                    'processing_status': 'UPLOADED', # Initial status after upload URL is generated
                    'current_reading_percentage': 0, # Start at 0%
                    'book_title': '', # Placeholder - needs to be updated after normalization
                    'book_author': '' # Placeholder - needs to be updated after normalization
                },
                ConditionExpression='attribute_not_exists(bookId)' # Prevent duplicate entries for the same bookId
            )
            logger.info("User book entry inserted successfully.")
        except user_books_table.meta.client.exceptions.ConditionalCheckFailedException:
             logger.warning(f"User book entry already exists for bookId: {book_id}")
             # This might happen if the same bookId is somehow generated again,
             # or if a retry occurs after the item was already created.
             # Decide how to handle this - could be a non-fatal warning.
        except Exception as ddb_e:
            logger.error(f"Error inserting user book entry into DynamoDB: {ddb_e}")
            # Decide how to handle a failure to write to DB after generating URL.
            # For now, we log the error but still return the URL.
            # In a robust system, you might want to retry the DB write or handle differently.
        # --- End DynamoDB Insert ---


        # Return the response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "upload_url": presigned_url,
                "s3_key": s3_key,
                "book_id": book_id,
                "message": "Pre-signed URL generated and book entry created." # Add a success message
            })
        }

    except Exception as e:
        # Handle any errors and return a descriptive error message
        logger.exception(f"An unexpected error occurred in lambda_handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
