import json
import math
import os
import time
import boto3
import requests
from typing import List, Dict
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
PERCENT_STEP = 5
# Environment variable for the summaries table name (matches SAM template)
DDB_SUMMARIES_TABLE_NAME = os.getenv("DDB_SUMMARIES_TABLE", "summaries") # Ensure this matches your table name
# Environment variable for the Gemini API Key directly
GEMINI_API_KEY_ENV = os.getenv("GEMINI_API_KEY") # Renamed to avoid conflict with global var
REGION = os.getenv("AWS_REGION", "us-east-1")

# AWS Clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb", region_name=REGION)
# Get the DynamoDB table resource using the environment variable name
table = dynamodb.Table(DDB_SUMMARIES_TABLE_NAME)
# Removed ssm client

# Global variable to store API key (fetched once from env var)
GEMINI_API_KEY = None

# Helpers
def get_gemini_api_key():
    """Gets the Gemini API key directly from the environment variable."""
    global GEMINI_API_KEY
    if GEMINI_API_KEY is None:
        if not GEMINI_API_KEY_ENV:
            logger.error("API_KEY environment variable not set.")
            raise RuntimeError("API_KEY environment variable not set")
        GEMINI_API_KEY = GEMINI_API_KEY_ENV
        logger.info("Successfully retrieved API key from environment variable.")
    return GEMINI_API_KEY

def _flatten_paragraphs(book_json: dict) -> List[str]:
    """Return a list of pure paragraph strings in reading order."""
    paragraphs: List[str] = []
    for chap in book_json.get("chapters", []):
        for block in chap.get("content", []):
            if block.get("type") == "paragraph":
                paragraphs.append(block["text"].strip())
    logger.info(f"Flattened book into {len(paragraphs)} paragraphs.")
    return paragraphs

def _call_gemini(prompt: str, text: str) -> str:
    """Calls the Gemini API with the given prompt and text, with retry for 429 errors."""
    api_key = get_gemini_api_key() # Get key from the global variable (fetched from env var)
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    if not api_key:
        raise RuntimeError("Gemini API key not available")

    payload = {
        "contents": [{"parts": [{"text": f"{prompt}{text}"}]}]
    }

    # Retry logic for 429 errors
    max_retries = 5
    base_wait_time = 2 # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"Calling Gemini API for summarization (Attempt {attempt + 1}/{max_retries})...")
            resp = requests.post(
                GEMINI_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=60, # Increased timeout for API call
            )
            resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = resp.json()
            logger.info("Gemini API call successful.")

            # Extract text from the response structure
            generated_text = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
            )
            logger.debug(f"Generated summary text snippet: {generated_text[:200]}...") # Log snippet
            return generated_text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = base_wait_time * (2 ** attempt) # Exponential backoff
                logger.warning(f"Received 429 Too Many Requests. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"HTTP error calling Gemini API: {e}")
                raise # Re-raise other HTTP errors
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error calling Gemini API: {e}")
            raise # Re-raise other request errors

    # If all retries fail
    logger.error(f"Failed to call Gemini API after {max_retries} retries due to 429 errors.")
    raise RuntimeError(f"Gemini API rate limit exceeded after {max_retries} retries.")


def _summarize_text_slice(text: str) -> str:
    """Generates a summary for a slice of text using the Gemini API."""
    prompt = (
        "Provide a concise recap under 250-300 words of the following book content. "
        "Focus on key events and characters."
    )
    try:
        return _call_gemini(prompt, text)
    except Exception as e:
        logger.error(f"Failed to get summary from Gemini: {e}")
        # fallback: truncate raw text
        return text[:400] + " …[truncated]" if len(text) > 400 else text


def generate_percentage_summaries(book_json: dict, user_id: str, book_id: str):
    """Generates summaries at percentage intervals and saves to DynamoDB."""
    logger.info("Generating percentage summaries.")
    full_text = "".join(_flatten_paragraphs(book_json))
    total_len = len(full_text)
    if total_len == 0:
        logger.warning("Book has no text content for summarization.")
        return

    last_end = -1 # To avoid processing the same slice if total_len is small

    summaries_to_save: List[Dict] = [] # Collect items for batch write

    # Process at each PERCENT_STEP interval
    for pct in range(PERCENT_STEP, 101, PERCENT_STEP):
        end_idx = math.ceil(total_len * pct / 100)
        # Ensure we process a new slice of text
        if end_idx == last_end:
            continue

        slice_text = full_text[:end_idx]
        logger.info(f"Processing up to {pct}% ({len(slice_text)} characters) for summary.")

        # Generate summary for this slice
        summary_text = _summarize_text_slice(slice_text)

        # Prepare item for DynamoDB
        # --- ITEM KEYS MATCHING YOUR PROVIDED SUMMARIES TABLE SCHEMA ---
        summaries_to_save.append({
            "book_id": book_id, # Partition Key (String)
            "progress": pct,    # Sort Key (Number)
            "user_id": user_id, # Attribute (String)
            "summary": summary_text, # Attribute (String)
            "createdAt": int(time.time()) # Add a timestamp (Number)
        })
        # --- END ITEM KEYS ---
        last_end = end_idx

        # Optional: Add a small delay between API calls if needed to manage rate limits
        # The retry logic in _call_gemini handles rate limits more directly,
        # but a small delay here could still help space out initial calls.
        # time.sleep(1) # Adjust as necessary

    if summaries_to_save:
        logger.info(f"Saving {len(summaries_to_save)} summary entries to DynamoDB.")
        # Use batch_put_summaries to save the collected items
        batch_put_summaries(summaries_to_save)
    else:
        logger.warning("No summary entries generated to save.")


def download_json_from_s3(s3_bucket: str, s3_key: str) -> dict:
    """Downloads and parses a JSON file from S3."""
    logger.info(f"Downloading JSON from s3://{s3_bucket}/{s3_key}")
    try:
        obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        book_json = json.loads(obj["Body"].read().decode('utf-8')) # Decode bytes to string
        logger.info("Successfully downloaded and parsed JSON.")
        return book_json
    except Exception as e:
        logger.error(f"Failed to download or parse JSON from s3://{s3_bucket}/{s3_key}: {e}")
        raise # Re-raise the exception

def batch_put_summaries(items: List[dict]):
    """Writes a batch of items to the DynamoDB table."""
    logger.info(f"Starting batch write to DynamoDB table: {DDB_SUMMARIES_TABLE_NAME}")
    try:
        with table.batch_writer() as batch:
            for item in items:
                # Ensure item keys match DynamoDB attribute names (book_id, progress)
                batch.put_item(Item=item)
        logger.info("Batch write to DynamoDB completed.")
    except Exception as e:
        logger.error(f"Failed during batch write to DynamoDB: {e}")
        raise # Re-raise the exception


def lambda_handler(event, context):
    """
    Trigger source: SQS message containing payload from normalize-books lambda.
    Downloads normalized JSON, generates summaries at intervals,
    and saves to DynamoDB.
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} records.")

    processed_records_count = 0

    # SQS events contain a list of records
    for sqs_record in event.get("Records", []):
        logger.info(f"Processing SQS record: {sqs_record.get('messageId')}")
        try:
            # Parse the JSON payload from the SQS message body
            message_body = sqs_record.get("body")
            if not message_body:
                logger.warning("SQS record body is empty, skipping.")
                continue

            try:
                # The body is the JSON payload sent by the previous lambda
                payload = json.loads(message_body)
                logger.info(f"Successfully parsed SQS message body as payload: {payload}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SQS message body as JSON: {e}, skipping record.")
                continue # Skip this record if body is not valid JSON

            # Extract details from the parsed payload
            user_id = payload.get('user_id')
            book_id = payload.get('book_id')
            s3_bucket = payload.get('bucket_name') # This should be the normalized data bucket
            s3_key = payload.get('json_s3_key')

            # Validate extracted data
            if not all([user_id, book_id, s3_bucket, s3_key]):
                logger.error(f"Missing required data in payload: {payload}, skipping record.")
                continue # Skip if essential data is missing

            # Download normalized JSON file from S3
            book_json = download_json_from_s3(s3_bucket, s3_key)

            # Generate summaries at percentage intervals and save to DB
            generate_percentage_summaries(book_json, user_id, book_id)

            logger.info(f"✓ Successfully processed SQS record {sqs_record.get('messageId')}")
            processed_records_count += 1

        except Exception as exc:
            # Log the exception for the specific SQS record that failed
            logger.exception(f"❌ Failed processing SQS record {sqs_record.get('messageId')}: {exc}")
            # Depending on your retry strategy and batch size, you might re-raise
            # or handle errors differently. Logging and continuing is safer for batches > 1.

    # Return a success response
    return {
        'statusCode': 200,
        'body': json.dumps({
            "status": "summary_summarization_batch_complete",
            "processed_count": processed_records_count,
            "message": f"Successfully processed {processed_records_count} SQS records for summary summarization."
        })
    }
