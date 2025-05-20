import json, os, re, tempfile, logging
from uuid import uuid4

import boto3
from ebooklib import epub, ITEM_DOCUMENT
import fitz  # PyMuPDF

# ---------- config ----------
DEST_BUCKET        = os.getenv("DEST_BUCKET", "normalized-books")              # where the JSON will be written
OUTPUT_QUEUE_URL   = os.getenv("OUTPUT_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/577125335862/summarize-character-queue")         # next‑stage SQS queue
REGION             = os.getenv("AWS_REGION", "us-east-1")

s3  = boto3.client("s3")
sqs = boto3.client("sqs", region_name=REGION)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---------- helpers ----------
def download_from_s3(bucket, key, local_path):
    s3.download_file(bucket, key, local_path)

def upload_to_s3(local_path, bucket, key):
    s3.upload_file(local_path, bucket, key)

def send_next_event(user_id, book_id, json_s3_key, bucket_name):
    payload = {"user_id": user_id,
               "book_id": book_id,
               "bucket_name": bucket_name,
               "json_s3_key": json_s3_key}
    
    sqs.send_message(QueueUrl=OUTPUT_QUEUE_URL,
                     MessageBody=json.dumps(payload))

def extract_user_and_book_id_from_key(key):
    # Match keys like: books/{user_id}/{book_id}/{filename}.{ext}
    m = re.match(r"books/([^/]+)/([^/]+)/[^/]+\.[^.]+$", key)
    return (m.group(1), m.group(2)) if m else (None, None)

# ---------- normalization ----------
# --- EPUB (same logic you supplied, trimmed for brevity) ---
def normalize_epub(path, book_id, user_id):
    book       = epub.read_epub(path)
    title      = (book.get_metadata("DC", "title") or [["Unknown Title"]])[0][0]
    author     = (book.get_metadata("DC", "creator") or [["Unknown Author"]])[0][0]
    chapters   = []
    chap_idx   = 1

    for item in book.get_items():
        if item.get_type() != ITEM_DOCUMENT:
            continue
        html     = item.get_content().decode("utf‑8")
        chap_ttl = re.search(r"<title>(.*?)</title>", html)
        chap_ttl = chap_ttl.group(1) if chap_ttl else f"Chapter {chap_idx}"

        clean    = re.sub(r"<[^>]+>", " ", html)
        clean    = re.sub(r"\s+", " ", clean).strip()
        paras    = [p.strip() for p in clean.split("\n\n") if p.strip()]

        content  = [{"type": "paragraph", "text": p} for p in paras]

        for img in re.finditer(r'<img[^>]+src="([^"]+)"', html):
            content.append({"type": "image",
                            "src": f"placeholder_{uuid4()}.jpg"})

        chapters.append({"id": chap_idx,
                         "title": chap_ttl,
                         "content": content})
        chap_idx += 1

    return {"book_id": book_id, "title": title,
            "author": author, "chapters": chapters}

# --- PDF ---
def normalize_pdf(path, book_id, user_id):
    pdf   = fitz.open(path)
    meta  = pdf.metadata or {}
    title = meta.get("title",  "Unknown Title")
    auth  = meta.get("author", "Unknown Author")

    chapters, chap_id = [], 1
    current           = {"id": chap_id, "title": f"Chapter {chap_id}", "content": []}

    for i in range(len(pdf)):
        page = pdf[i]
        text = page.get_text()
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]

        # naïve chapter detection
        if i == 0 or (paras and re.match(r"^chapter\s+\d+", paras[0], re.I)):
            if current["content"]:
                chapters.append(current)
                chap_id += 1
            chapter_title = paras[0] if paras else f"Chapter {chap_id}"
            current = {"id": chap_id, "title": chapter_title, "content": []}
            paras = paras[1:] if paras else paras

        current["content"].extend({"type": "paragraph", "text": p} for p in paras)

        for _, xref, *_ in page.get_images(full=True):
            _ = pdf.extract_image(xref)   # bytes ignored – upload happens later offline
            current["content"].append({"type": "image",
                                       "src": f"placeholder_{uuid4()}.jpg"})

    if current["content"]:
        chapters.append(current)

    return {"book_id": book_id, "title": title,
            "author": auth, "chapters": chapters}

def normalize_book(path, book_id, user_id, ext):
    ext = ext.lower()
    if ext == "epub":
        return normalize_epub(path, book_id, user_id)
    if ext == "pdf":
        return normalize_pdf(path,  book_id, user_id)
    # ➜ For MOBI you usually convert to EPUB first (KindleUnpack / Calibre).  Raise for now.
    raise ValueError(f"Unsupported file type: {ext}")

# ---------- Lambda entry ----------
def lambda_handler(event, _ctx):
    """
    Trigger source: SQS message whose body **either** is:
      1. Raw S3 event (book just uploaded)  **or**
      2. Our own JSON: {"s3_key": "...", "bucket": "...", "user_id": "...", "book_id": "..."}
    """
    print("Events", event)
    for rec in event.get("Records", []):
        print(rec)
        logger.info(f"Processing record: {rec}")
        try:
            # S3 event forwarded by SQS
            if rec.get("eventSource") == "aws:s3":
                s3rec = rec.get("s3", None)
                if s3rec:
                    bucket = s3rec["bucket"]["name"]
                    key = s3rec["object"]["key"]
                user_id, book_id = extract_user_and_book_id_from_key(key)

                ext = key.rsplit(".", 1)[-1].lower()
                if ext not in ("epub", "pdf"):
                    logger.warning(f"Skip unsupported file: {key}")
                    continue

                # --- download original file
                with tempfile.NamedTemporaryFile(suffix="." + ext) as tmpin:
                    download_from_s3(bucket, key, tmpin.name)
                    print("Downloaded book name", tmpin.name)
                    book_json = normalize_book(tmpin.name, book_id, user_id, ext)
                    print("Epub book normalized", len(book_json))
                # --- write JSON to /tmp and upload
                with tempfile.NamedTemporaryFile(suffix=".json", mode="w", encoding="utf-8") as tmpout:
                    json.dump(book_json, tmpout, ensure_ascii=False)
                    tmpout.flush()
                    json_key = f"normalized/{user_id}/{book_id}/normalized.json"
                    print(tmpout.name, DEST_BUCKET, json_key)
                    upload_to_s3(tmpout.name, DEST_BUCKET, json_key)
                    print("Upload to S3 completed")

                # --- Push event for next stage
                send_next_event(user_id, book_id, json_key, bucket)
                logger.info(f"✓ normalized {key} ➜ {json_key}")
            
            else:
                continue

        except Exception as exc:
            logger.exception(f"❌ Failed record: {exc}")

    return {"status": "ok", "uploaded_book": json_key}
