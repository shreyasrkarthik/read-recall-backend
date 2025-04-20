import boto3
from typing import List

from shared.config import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY, DDB_TABLE
from shared.logger import get_logger

logger = get_logger("s3_utils")

ddb = boto3.resource(
        "dynamodb",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
     ).Table(DDB_TABLE)


def batch_put(items: List[dict]):
    with ddb.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
