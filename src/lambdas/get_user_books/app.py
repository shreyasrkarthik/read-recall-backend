import json
import os
import boto3
import logging
from boto3.dynamodb.conditions import Key
from decimal import Decimal # Import Decimal for serialization

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get the User Books table name from environment variables
USER_BOOKS_TABLE_NAME = os.getenv("USER_BOOKS_TABLE_NAME", "user_books") # Default to 'user_books'

# --- Add check for environment variable ---
if not USER_BOOKS_TABLE_NAME:
    logger.error("USER_BOOKS_TABLE_NAME environment variable is not set.")
    # Raising an error here will cause the Lambda initialization to fail.
    raise ValueError("USER_BOOKS_TABLE_NAME environment variable is not set.")
# --- End check ---

# Initialize the DynamoDB resource
dynamodb = boto3.resource("dynamodb")
# Get the User Books DynamoDB table object
user_books_table = dynamodb.Table(USER_BOOKS_TABLE_NAME)

# Custom JSON Encoder to handle Decimal types (same as other Lambdas)
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        # If the object is an instance of Decimal
        if isinstance(obj, Decimal):
            # Convert Decimal to float. Adjust if you need integer representation.
            return float(obj)
        # Otherwise, use the default encoder behavior
        return json.JSONEncoder.default(self, obj)


def lambda_handler(event, context):
    """
    Retrieves a list of books for a given user from the User Books table.
    Triggered by API Gateway GET /users/{userId}/books.
    Expects user_id in request headers (e.g., 'user-id', 'User-Id', or 'user_id').
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract user_id from request headers
        # API Gateway headers are case-insensitive, but the keys in the event dictionary
        # might vary depending on the client and API Gateway configuration.
        # Check for common variations including the one seen in logs ('user_id').
        headers = event.get('headers', {})
        # --- MODIFIED: Added check for 'user_id' with underscore ---
        user_id = headers.get('user-id') or headers.get('User-Id') or headers.get('user_id')
        # --- End MODIFIED ---

        # In a real application, you would typically authenticate the user
        # and verify that the requested userId matches the authenticated user's ID
        # to prevent users from listing books for other users.

        # --- Explicitly return 400 if user_id is missing BEFORE querying DB ---
        if not user_id:
            logger.warning("Missing user_id in request headers.")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Missing user_id in headers'})
            }
        # --- End explicit return ---

        logger.info(f"Querying books for user: {user_id}")

        # Query DynamoDB for all items with the given userId (Partition Key)
        # This will return all books owned by this user.
        response = user_books_table.query(
            KeyConditionExpression=Key('user_id').eq(user_id) # Use 'user_id' as the Partition Key name
        )

        # Get the list of items from the query response
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} books for user {user_id}.")

        # The items are returned sorted by the Sort Key (bookId) by default.

        # Return the retrieved book items in the response body
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            # Use the custom DecimalEncoder to serialize the items
            'body': json.dumps(items, cls=DecimalEncoder)
        }

    except Exception as e:
        # Log any unexpected exceptions
        logger.error(f"An unexpected error occurred: {e}")
        # Return a 500 Internal Server Error response
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'An unexpected error occurred'})
        }
