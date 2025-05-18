import json
import os
import boto3
import logging
from boto3.dynamodb.conditions import Key
from decimal import Decimal # Import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get the characters table name from environment variables
CHARACTER_TABLE_NAME = os.getenv("CHARACTER_TABLE_NAME", "characters") # Default to 'characters'

# --- Add check for environment variable ---
if not CHARACTER_TABLE_NAME:
    logger.error("CHARACTER_TABLE_NAME environment variable is not set.")
    # Raising an error here will cause the Lambda initialization to fail,
    # providing a clear error in the logs before any requests are processed.
    raise ValueError("CHARACTER_TABLE_NAME environment variable is not set.")
# --- End check ---

# Initialize the DynamoDB resource
dynamodb = boto3.resource("dynamodb")
# Get the DynamoDB table object
table = dynamodb.Table(CHARACTER_TABLE_NAME)

# Custom JSON Encoder to handle Decimal types (same as summaries lambda)
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
    Retrieves book characters for a specific book up to a given percentage.
    Triggered by API Gateway GET /books/{bookId}/characters?percentage={percentage}.
    Expects bookId in path parameters and percentage in query string parameters.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract bookId from path parameters provided by API Gateway
        path_parameters = event.get('pathParameters', {})
        book_id = path_parameters.get('bookId')

        # Extract percentage from query string parameters provided by API Gateway
        query_string_parameters = event.get('queryStringParameters', {})
        percentage_str = query_string_parameters.get('percentage')

        # In a real application, you would typically authenticate the user
        # and obtain their user_id from the request context (e.g., from a JWT).
        # This user_id would then be used to ensure they can only access
        # characters for books they own or have permission to view.
        # For this example, we are not implementing authentication/authorization.

        # Validate required parameters
        if not book_id or not percentage_str:
            logger.warning("Missing bookId in path or percentage in query string.")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Missing bookId or percentage'})
            }

        try:
            # Convert percentage from string to integer and validate range
            percentage = int(percentage_str)
            if not (0 <= percentage <= 100):
                 logger.warning(f"Invalid percentage value: {percentage_str}. Must be between 0 and 100.")
                 return {
                    'statusCode': 400,
                    'body': json.dumps({'message': 'Percentage must be between 0 and 100'})
                 }
        except ValueError:
            logger.warning(f"Invalid percentage format: {percentage_str}. Must be an integer.")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Invalid percentage format'})
            }

        logger.info(f"Querying characters for bookId: {book_id} up to {percentage}%.")

        # Query DynamoDB for character items.
        # We use KeyConditionExpression to filter by Partition Key (book_id)
        # and Sort Key (progress) using the 'lte' (less than or equal to) condition.
        # This efficiently retrieves all items for the given book_id where the progress
        # is less than or equal to the requested percentage.
        response = table.query(
            KeyConditionExpression=Key('book_id').eq(book_id) & Key('progress').lte(percentage)
            # If you were filtering by user_id, you would add a FilterExpression here:
            # FilterExpression=Attr('user_id').eq(user_id_from_auth)
            # Note: FilterExpression is applied *after* the query, so it consumes
            # read capacity for all items matching the KeyConditionExpression,
            # even if they are filtered out. Design your keys/indexes carefully.
        )

        # Get the list of items from the query response
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} character items for bookId {book_id} up to {percentage}%.")

        # The items returned by the query are already sorted by the Sort Key (progress)
        # in ascending order by default, which is suitable for displaying characters
        # in chronological order of progress. No additional sorting is needed here.

        # Return the retrieved character items in the response body
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
