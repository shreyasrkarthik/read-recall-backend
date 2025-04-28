import json
import math
import os
import time
import boto3
import requests
from typing import List, Dict

# Constants
PERCENT_STEP = 5
DDB_TABLE = os.getenv("DDB_CHARACTER_SUMMARIES_TABLE", "characters")
API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# AWS Clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DDB_TABLE)

# Helpers
def _flatten_paragraphs(book_json: dict) -> List[str]:
    """Return a list of pure paragraph strings in reading order."""
    paragraphs: List[str] = []
    for chap in book_json.get("chapters", []):
        for block in chap.get("content", []):
            if block.get("type") == "paragraph":
                paragraphs.append(block["text"].strip())
    return paragraphs

def _call_gemini(prompt: str, text: str) -> str:
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY env var not set")
    
    payload = {
        "contents": [{"parts": [{"text": f"{prompt}{text}"}]}]
    }

    resp = requests.post(
        GEMINI_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30,
    )
    time.sleep(6)  # avoid rate limits
    resp.raise_for_status()
    data = resp.json()
    
    return (
        data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
    )

def _get_characters(text: str) -> str:
    prompt = (
        "Provide a concise list of all the characters appeared in the book similar to x-ray feature of prime video. "
        "This character list should also have a one liner about the character. "
        "Just give me the list and not anything else."
    )
    try:
        return _call_gemini(prompt, text)
    except Exception:
        # fallback: truncate raw text
        return text[:400] + " …[truncated]" if len(text) > 400 else text

def generate_percentage_characters(book_json: dict, user_id: str, book_id: str) -> List[Dict]:
    full_text = "".join(_flatten_paragraphs(book_json))
    total_len = len(full_text)
    if total_len == 0:
        return []

    characters: List[Dict] = []
    last_end = -1

    for pct in range(PERCENT_STEP, 101, PERCENT_STEP):
        end_idx = math.ceil(total_len * pct / 100)
        if end_idx == last_end:
            continue
        slice_text = full_text[:end_idx]
        text_characters = _get_characters(slice_text)
        characters.append({
            "user_id": user_id,
            "book_id": book_id,
            "progress": pct,
            "characters": text_characters,
        })
        last_end = end_idx
        break
    
    print("calling db")
    batch_put_characters(characters)
    return characters

def download_json_from_s3(s3_bucket: str, s3_key: str) -> dict:
    obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
    return json.loads(obj["Body"].read())

def batch_put_characters(items: List[dict]):
    print("saving in db")
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    # Extract from event
    user_id = event['user_id']
    book_id = event['book_id']
    s3_bucket = event['bucket_name']
    s3_key = event['json_s3_key']

    # Download JSON file from S3
    book_json = download_json_from_s3(s3_bucket, s3_key)
    
    # Summarize
    summary = generate_percentage_characters(book_json, user_id, book_id)

    print("Summary generated:", summary)

    return {
        'statusCode': 200,
        'body': json.dumps('Character Summarization completed successfully')
    }
