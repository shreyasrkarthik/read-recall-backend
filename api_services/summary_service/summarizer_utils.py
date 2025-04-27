"""Utility that slices a normalized book into 5% chunks and asks
Google Gemini2‑flash to generate concise recaps."""

import json
import math
import os
import time
from typing import List, Dict
import requests

from shared.logger import get_logger

PERCENT_STEP = 5  # generate summary every 5%
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key={api_key}"
)
logger = get_logger("summarizer")


def _flatten_paragraphs(book_json: dict) -> List[str]:
    """Return a list of pure paragraph strings in reading order."""
    paragraphs: List[str] = []
    for chap in book_json.get("chapters", []):
        for block in chap.get("content", []):
            if block.get("type") == "paragraph":
                paragraphs.append(block["text"].strip())
    return paragraphs


def _call_gemini(prompt: str, text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var not set")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{prompt}{text}"
                    }
                ]
            }
        ]
    }

    resp = requests.post(
        GEMINI_URL.format(api_key=api_key),
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30,
    )
    time.sleep(6)
    resp.raise_for_status()
    data = resp.json()
    return (
        data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
    )


def _summarize_text(text: str) -> str:
    prompt = (
        "Provide a concise recap under 250-300 words of the following book content."
        "Focus on key events and characters"
    )
    try:
        return _call_gemini(prompt, text)
    except Exception:
        # fallback: truncate raw text
        return text[:400] + " …[truncated]" if len(text) > 400 else text


def generate_percentage_summaries(book_json: dict) -> List[Dict]:
    full_text = "".join(_flatten_paragraphs(book_json))
    total_len = len(full_text)
    if total_len == 0:
        return []

    summaries: List[Dict] = []
    last_end = -1

    for pct in range(PERCENT_STEP, 101, PERCENT_STEP):
        logger.info("Total %s, PCT %s", total_len, pct)
        end_idx = math.ceil(total_len * pct / 100)
        if end_idx == last_end:
            continue
        slice_text = full_text[:end_idx]
        logger.info("Slice Text %s", len(slice_text))
        summary = _summarize_text(slice_text)

        summaries.append({
            "percent": pct,
            "summary": summary,
        })
        last_end = end_idx

    return summaries
