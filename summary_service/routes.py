"""HTTP endpoint to summarize a normalized book every 5% and store the recaps in DynamoDB (free‑tier)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.s3_utils import download_json_from_s3
from shared.ddb_utils import batch_put
from shared.logger import get_logger
from shared.config import DDB_TABLE

from summarizer_utils import generate_percentage_summaries


router = APIRouter()
logger = get_logger("upload_service")


class SummaryPayload(BaseModel):
    user_id:       str
    book_id:       str
    normalized_key:str   # S3 path to normalized.json


@router.post("/api/books/summarize")
async def summarize_book(payload: SummaryPayload):
    try:
        book_json = download_json_from_s3(payload.normalized_key)
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch normalized book: {e}")

    summaries = generate_percentage_summaries(book_json)

    ddb_items = [
        {
            "book_id":  payload.book_id,   # PK
            "progress": s["percent"],      # SK
            "summary":  s["summary"],
            "user_id": payload.user_id,
        }
        for s in summaries
    ]

    try:
        batch_put(ddb_items)
    except Exception as e:
        raise HTTPException(500, f"Failed to store summaries: {e}")

    return {
        "status": "success",
        "summary_count": len(ddb_items),
        "ddb_table": DDB_TABLE,
    }
