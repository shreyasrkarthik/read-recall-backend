import os
from dotenv import load_dotenv

load_dotenv()
AWS_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

# SQS Queues
BOOK_PROCESSING_QUEUE_URL = os.getenv("BOOK_PROCESSING_QUEUE_URL")
NORMALIZED_BOOK_QUEUE_URL = os.getenv("NORMALIZED_BOOK_QUEUE_URL")
