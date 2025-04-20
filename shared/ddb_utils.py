import boto3
from typing import List

from shared.config import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY, DDB_SUMMARIES_TABLE, DDB_CHARACTERS_TABLE
from shared.logger import get_logger

logger = get_logger("s3_utils")

ddb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)
logger.info("Summary %s, Characters %s", DDB_SUMMARIES_TABLE, DDB_CHARACTERS_TABLE)

ddb_summaries = ddb.Table(DDB_SUMMARIES_TABLE)
ddb_characters = ddb.Table(DDB_CHARACTERS_TABLE)


def batch_put_summaries(items: List[dict]):
    with ddb_summaries.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


def batch_put_characters(items: List[dict]):
    with ddb_characters.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
