import json
import uuid
import boto3
import os

s3_client = boto3.client('s3')
BUCKET_NAME = os.environ.get("BUCKET_NAME", "book-processing-uploads") # Set this in Lambda environment variables

ALLOWED_EXTENSIONS = {".pdf", ".epub"}

def lambda_handler(event, context):
    print(event)
    try:
        # Ensure the body is a string before attempting to load it
        try:
            body = json.loads(event.get("body", {}))
        except Exception as e:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": str(e)})
            }

        # Extract the necessary fields
        user_id = body.get("user_id")
        file_name = body.get("file_name", "")
        file_ext = os.path.splitext(file_name)[-1].lower()
        print("Fields", user_id, file_name, file_ext)
        # Validate input
        if not user_id or file_ext not in ALLOWED_EXTENSIONS:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid user_id or file extension"})
            }

        # Generate a unique book_id and S3 key
        book_id = str(uuid.uuid4())
        s3_key = f"books/{user_id}/{book_id}/{file_name}"

        # Generate a pre-signed URL
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key,
                'ContentType': 'application/pdf'  # You can refine content type based on the file type
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )

        # Return the response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "upload_url": presigned_url,
                "s3_key": s3_key,
                "book_id": book_id
            })
        }

    except Exception as e:
        # Handle any errors and return a descriptive error message
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
