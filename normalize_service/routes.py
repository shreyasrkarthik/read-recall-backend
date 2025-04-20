import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import tempfile
from shared.logger import get_logger
from shared.s3_utils import download_from_s3, upload_to_s3
from book_utils import normalize_book
from shared.queue_utils import send_to_normalized_queue

router = APIRouter()
logger = get_logger("normalize_service")


class BookNormalizeRequest(BaseModel):
    user_id: str
    book_id: str
    s3_key: str
    file_type: str


class BookNormalizeResponse(BaseModel):
    success: bool
    book_id: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


@router.post("/api/books/normalize", 
             response_model=BookNormalizeResponse,
             responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def normalize_book_api(book_data: BookNormalizeRequest):
    """
    Normalize a book from S3 and send it to the normalized book queue
    """
    try:
        # Extract parameters
        user_id = book_data.user_id
        book_id = book_data.book_id
        s3_key = book_data.s3_key
        file_type = book_data.file_type.lower()
        
        # Validate file type
        if file_type not in ['epub', 'pdf']:
            logger.warning(f"Unsupported file type: {file_type}")
            raise HTTPException(
                status_code=400, 
                detail={"success": False, "error": f"Unsupported file type: {file_type}"}
            )
        
        # Download the book from S3
        local_path = f"/tmp/{book_id}.{file_type}"
        download_from_s3(s3_key, local_path)
        
        # Normalize the book
        normalized_data = normalize_book(local_path, book_id, user_id, file_type)

        # Send this to S3 bucket
        fd, tmp_path = tempfile.mkstemp()
        os.close(fd)
        with open(tmp_path, "w", encoding="utf-8") as fp:
            json.dump(normalized_data, fp, ensure_ascii=False)

        json_key = f"normalized/{user_id}/{book_id}/normalized.json"
        upload_to_s3(tmp_path, json_key)
        os.remove(tmp_path)

        # Send normalized data to the queue
        send_to_normalized_queue({"json_key": json_key})
        
        # Cleanup
        if os.path.exists(local_path):
            os.remove(local_path)
        
        logger.info(f"Book {book_id} successfully normalized and sent to queue")
        
        return {
            "success": True,
            "book_id": book_id,
            "message": "Book successfully normalized and sent to queue"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing book: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={"success": False, "error": f"Internal server error: {str(e)}"}
        )
