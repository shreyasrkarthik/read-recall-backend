import boto3
import botocore
import tempfile
import os
import json

from shared.config import AWS_BUCKET, AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY, SIGNED_URL_TTL_SEC
from shared.logger import get_logger

logger = get_logger("s3_utils")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)


def presigned_put_url(key: str, ttl: int = SIGNED_URL_TTL_SEC) -> str:
    """
    Return a one‑time pre‑signed URL that lets the browser upload directly to S3.
    """
    try:
        return s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": AWS_BUCKET, "Key": key},
            ExpiresIn=ttl,
            HttpMethod="PUT",
        )
    except Exception as e:
        logger.exception("Failed to presign URL for %s: %s", key, e)
        raise


def upload_to_s3(local_path: str, s3_key: str):
    try:
        with open(local_path, "rb") as f:
            s3.upload_fileobj(f, AWS_BUCKET, s3_key)
        logger.info(f"Upload to S3 succeeded: {s3_key}")
    except Exception as e:
        logger.exception("S3 upload failed: %s", str(e))
        raise


def download_from_s3(s3_key: str, local_path: str):
    try:
        s3.download_file(AWS_BUCKET, s3_key, local_path)
        logger.info(f"Download from S3 succeeded: {s3_key}")
        return True
    except Exception as e:
        logger.exception("S3 download failed: %s", str(e))
        raise


def download_json_from_s3(key: str) -> dict:
    fd, tmp = tempfile.mkstemp()
    os.close(fd)
    s3.download_file(AWS_BUCKET, key, tmp)
    with open(tmp, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    os.remove(tmp)
    return data

