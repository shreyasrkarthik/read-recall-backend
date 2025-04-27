from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from uuid import uuid4
import aiofiles
import os

from shared.s3_utils import upload_to_s3, presigned_put_url
from shared.queue_utils import send_to_processing_queue
from shared.logger import get_logger
from shared.config import SIGNED_URL_TTL_SEC

router = APIRouter()
logger = get_logger("upload_service")


@router.post("/api/books/upload-url")
async def get_book_upload_url(
    user_id: str = Form(...),
    file_ext: str = Form(...),          # client sends ".epub", ".pdf", …
):
    try:
        book_id = str(uuid4())
        s3_key = f"books/{user_id}/{book_id}/original.{file_ext.lstrip('.')}"
        upload_url = presigned_put_url(s3_key)
        logger.info("Pre signed URL is %s", upload_url)

        # 🛈  If you **must** keep the old queue‑first flow,
        #     leave this line; otherwise delete it and use an S3 event
        # send_to_processing_queue({"user_id": user_id, "book_id": book_id, "s3_key": s3_key})

        return {
            "book_id":    book_id,
            "s3_key":     s3_key,
            "upload_url": upload_url,
            "expires_in": SIGNED_URL_TTL_SEC,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not create upload URL: {e}")


@router.post("/api/books/upload")
async def upload_book(file: UploadFile = File(...), user_id: str = Form(...)):
    try:
        # Generate IDs and paths
        logger.info("Starting upload for user: %s for file %s", user_id, file)
        book_id = str(uuid4())
        file_ext = file.filename.split('.')[-1].lower()
        s3_key = f"books/{user_id}/{book_id}/original.{file_ext}"
        local_path = f"/tmp/{book_id}.{file_ext}"

        # Save file temporarily to /tmp
        async with aiofiles.open(local_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # Upload to S3
        file_upload_status = upload_to_s3(local_path, s3_key)
        logger.info("Status of S3 upload %s", file_upload_status)

        # Send SQS message
        send_to_processing_queue({
            "user_id": user_id,
            "book_id": book_id,
            "s3_key": s3_key,
            "file_type": file_ext
        })

        # Cleanup
        os.remove(local_path)

        return {
            "message": "Book uploaded and processing started.",
            "book_id": book_id,
            "s3_key": s3_key
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/api/covers/upload")
async def upload_cover(file: UploadFile = File(...), user_id: str = Form(...), book_id: str = Form(...)):
    try:
        # Generate paths
        logger.info("Starting cover upload for user: %s, book: %s, file: %s", user_id, book_id, file)
        file_ext = file.filename.split('.')[-1]
        s3_key = f"books/{user_id}/{book_id}/cover.{file_ext}"
        local_path = f"/tmp/cover_{book_id}.{file_ext}"

        # Save file temporarily to /tmp
        async with aiofiles.open(local_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # Upload to S3
        file_upload_status = upload_to_s3(local_path, s3_key)
        logger.info("Status of S3 upload %s", file_upload_status)

        # Cleanup
        os.remove(local_path)

        return {
            "message": "Cover uploaded successfully.",
            "book_id": book_id,
            "s3_key": s3_key
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover upload failed: {str(e)}")
