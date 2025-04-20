"""HTTP endpoint to summarize a normalized book every 5% and store the recaps in DynamoDB (free‑tier)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.s3_utils import download_json_from_s3
from shared.ddb_utils import batch_put_characters
from shared.logger import get_logger
from shared.config import DDB_CHARACTERS_TABLE

from characters_utils import generate_percentage_characters


router = APIRouter()
logger = get_logger("characters")


class SummaryPayload(BaseModel):
    user_id:        str
    book_id:        str
    normalized_key: str   # S3 path to normalized.json


@router.post("/api/books/characters")
async def summarize_book(payload: SummaryPayload):
    try:
        book_json = download_json_from_s3(payload.normalized_key)
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch normalized book: {e}")

    characters = generate_percentage_characters(book_json)

    ddb_items = [
        {
            "book_id":  payload.book_id,   # PK
            "progress": c["percent"],      # SK
            "characters":  c["characters"],
            "user_id": payload.user_id,
        }
        for c in characters
    ]

    try:
        batch_put_characters(ddb_items)
    except Exception as e:
        raise HTTPException(500, f"Failed to store summaries: {e}")

    return {
        "status": "success",
        "summary_count": len(ddb_items),
        "ddb_table": DDB_CHARACTERS_TABLE,
    }
