import boto3
import json
from shared.config import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY, BOOK_PROCESSING_QUEUE_URL, NORMALIZED_BOOK_QUEUE_URL
from shared.logger import get_logger

logger = get_logger("queue_utils")

sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)


def send_to_normalized_queue(message: dict):
    try:
        sqs.send_message(
            QueueUrl=NORMALIZED_BOOK_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        logger.info("Normalized book data sent to queue successfully")
    except Exception as e:
        logger.exception("Error sending to normalized queue: %s", str(e))
        raise


def send_to_processing_queue(message: dict):
    try:
        sqs.send_message(
            QueueUrl=BOOK_PROCESSING_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        logger.info("SQS message sent successfully.")
    except Exception as e:
        logger.exception("SQS message failed: %s", str(e))
        raise
