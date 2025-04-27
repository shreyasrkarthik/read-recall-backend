import json
import math
import os
import time
import boto3
import requests
from typing import List, Dict

PERCENT_STEP = 5
DDB_TABLE = os.getenv("DDB_SUMMARIES_TABLE", "BookSummaries")
API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DDB_TABLE)


def _flatten_paragraphs(book_json: dict) -> List[str]:
    paragraphs: List[str] = []
    for chap in book_json.get("chapters", []):
        for block in chap.get("content", []):
            if block.get("type") == "paragraph":
                paragraphs.append(block["text"].strip())
    return paragraphs


def _call_gemini(prompt: str, text: str) -> str:
    # print(GEMINI_URL)
    # print("calling gemi",prompt,len(text))
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY env var not set")

    payload = {
        "contents": [{"parts": [{"text": f"{prompt}{text}"}]}]
    }
    # print("payload", payload)
    print("api key len", len(API_KEY))

    resp = requests.post(
        GEMINI_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30,
    )
    time.sleep(6)
    resp.raise_for_status()
    data = resp.json()
    print("data",data)
    return (
        data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
    )


def _summarize_text(text: str) -> str:
    prompt = (
        "Provide a concise recap under 250-300 words of the following book content. "
        "Focus on key events and characters."
    )
    try:
        _call_gemini(prompt, text)
    except Exception as e:
        print("exception",e)
        return text[:400] + " …[truncated]" if len(text) > 400 else text


def generate_percentage_summaries(book_json: dict) -> List[Dict]:
    full_text = "".join(_flatten_paragraphs(book_json))
    total_len = len(full_text)
    if total_len == 0:
        return []

    summaries = []
    last_end = -1

    for pct in range(PERCENT_STEP, 101, PERCENT_STEP):
        end_idx = math.ceil(total_len * pct / 100)
        if end_idx == last_end:
            continue
        slice_text = full_text[:end_idx]
        summary = _summarize_text(slice_text)
        summaries.append({
            "percent": pct,
            "summary": summary,
        })
        last_end = end_idx

    return summaries


def download_json_from_s3(s3_key: str) -> dict:
    """Assumes key is of the form 'bucket/path/to/file.json'"""
    if not s3_key.count("/"):
        raise ValueError("Invalid S3 key format")
    bucket, *key_parts = s3_key.split("/")
    key = "/".join(key_parts)
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def batch_put_summaries(book_id: str, user_id: str, summaries: List[Dict]):
    with table.batch_writer() as batch:
        for s in summaries:
            batch.put_item(Item={
                "book_id": book_id,
                "progress": s["percent"],
                "summary": s["summary"],
                "user_id": user_id,
            })

def lambda_handler(event, context):        
    # Updated keys based on your sample
    s3_bucket = event['bucket_name']
    s3_key = event['json_s3_key']
        
    # Download JSON file from S3
    s3_object = s3.get_object(Bucket=s3_bucket, Key=s3_key)
    file_content = s3_object['Body'].read().decode('utf-8')
    book_json = json.loads(file_content)
    # Flatten paragraphs
    paragraphs = _flatten_paragraphs(book_json)

    
    # Join paragraphs
    full_text = "\n\n".join(paragraphs)
    
    # Summarize
    summary = _summarize_text(full_text)

    print(summary)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Summarization completed successfully')
    }
