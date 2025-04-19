import boto3
from shared.config import AWS_BUCKET, AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY
from shared.logger import get_logger

logger = get_logger("s3_utils")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)


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