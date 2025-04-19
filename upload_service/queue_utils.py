import boto3
import json
from config import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY, SQS_QUEUE_URL
from logger import get_logger

logger = get_logger("queue_utils")

sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)


def send_to_processing_queue(message: dict):
    try:
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        logger.info("SQS message sent successfully.")
    except Exception as e:
        logger.exception("SQS message failed: %s", str(e))
        raise
