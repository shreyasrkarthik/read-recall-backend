import re
from uuid import uuid4

import fitz
from ebooklib import epub, ITEM_DOCUMENT
from shared.logger import get_logger

logger = get_logger("book_utils")


def normalize_epub(filepath: str, book_id: str, user_id: str):
    """
    Convert EPUB to normalized JSON format
    """
    try:
        # Open the EPUB file
        book = epub.read_epub(filepath)
        
        # Extract title and author
        title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Unknown Title"
        authors = book.get_metadata('DC', 'creator')
        author = authors[0][0] if authors else "Unknown Author"
        
        # Initialize chapters list
        chapters = []
        chapter_id = 1
        
        # Process documents in the book
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8')
                
                # Basic HTML parsing (a proper implementation would use BeautifulSoup)
                # Extract title from html
                chapter_title = f"Chapter {chapter_id}"
                title_match = re.search(r'<title>(.*?)</title>', content)
                if title_match:
                    chapter_title = title_match.group(1)
                
                # Extract text content
                text_content = []
                
                # Remove HTML tags for a simple text extraction
                # In a production app, use a proper HTML parser
                clean_text = re.sub(r'<[^>]+>', ' ', content)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                # Split into paragraphs
                paragraphs = clean_text.split('\n\n')
                for paragraph in paragraphs:
                    if paragraph.strip():
                        text_content.append({
                            "type": "paragraph",
                            "text": paragraph.strip()
                        })
                
                # Check for images
                image_matches = re.finditer(r'<img[^>]+src="([^"]+)"[^>]*>', content)
                for img_match in image_matches:
                    img_src = img_match.group(1)
                    # In a real implementation, extract and upload the image to S3
                    # Here, we'll just add a placeholder
                    text_content.append({
                        "type": "image",
                        "src": f"placeholder_for_image_{uuid4()}.jpg"
                    })
                
                # Add chapter to the list
                if text_content:  # Only add if there's content
                    chapters.append({
                        "id": chapter_id,
                        "title": chapter_title,
                        "content": text_content
                    })
                    chapter_id += 1
        
        # Construct normalized book data
        normalized_book = {
            "book_id": book_id,
            "title": title,
            "author": author,
            "chapters": chapters
        }
        
        logger.info(f"EPUB normalization completed for book: {book_id}")
        return normalized_book
        
    except Exception as e:
        logger.exception(f"EPUB normalization failed: {str(e)}")
        raise


def normalize_pdf(filepath: str, book_id: str, user_id: str):
    """
    Convert PDF to normalized JSON format
    """
    try:
        # Open PDF file
        pdf_document = fitz.open(filepath)
        
        # Initialize book data
        title = "Unknown Title"
        author = "Unknown Author"
        
        # Try to extract metadata
        metadata = pdf_document.metadata
        if metadata:
            if metadata.get('title'):
                title = metadata['title']
            if metadata.get('author'):
                author = metadata['author']
        
        # Initialize chapters list
        chapters = []
        chapter_id = 1
        current_chapter = {
            "id": chapter_id,
            "title": f"Chapter {chapter_id}",
            "content": []
        }
        
        # Process each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Extract text
            text = page.get_text()
            
            # Split into paragraphs
            paragraphs = text.split('\n\n')
            
            # Check if this is a new chapter based on simple heuristics
            # This is a simplified approach - real implementation would be more robust
            if page_num == 0 or len(paragraphs) > 0 and re.match(r'^chapter\s+\d+', paragraphs[0].lower()):
                # If we already have content in the current chapter, add it to chapters
                if current_chapter["content"]:
                    chapters.append(current_chapter)
                    chapter_id += 1
                
                # Start a new chapter
                chapter_title = f"Chapter {chapter_id}"
                if len(paragraphs) > 0:
                    chapter_title = paragraphs[0].strip()
                    paragraphs = paragraphs[1:]  # Remove the title from paragraphs
                
                current_chapter = {
                    "id": chapter_id,
                    "title": chapter_title,
                    "content": []
                }
            
            # Add paragraphs to current chapter
            for paragraph in paragraphs:
                if paragraph.strip():
                    current_chapter["content"].append({
                        "type": "paragraph",
                        "text": paragraph.strip()
                    })
            
            # Extract images
            image_list = page.get_images(full=True)
            for img_index, img_info in enumerate(image_list):
                img_index, xref, _ = img_info
                
                # Extract image
                base_image = pdf_document.extract_image(xref)
                if base_image:
                    image_bytes = base_image["image"]
                    
                    # In a production environment, upload the image to S3
                    # Here we'll just add a placeholder
                    current_chapter["content"].append({
                        "type": "image",
                        "src": f"placeholder_for_image_{uuid4()}.jpg"
                    })
        
        # Add the last chapter if it has content
        if current_chapter["content"]:
            chapters.append(current_chapter)
        
        # Construct normalized book data
        normalized_book = {
            "book_id": book_id,
            "title": title,
            "author": author,
            "chapters": chapters
        }
        
        logger.info(f"PDF normalization completed for book: {book_id}")
        return normalized_book
        
    except Exception as e:
        logger.exception(f"PDF normalization failed: {str(e)}")
        raise


def normalize_book(filepath: str, book_id: str, user_id: str, file_ext: str):
    """
    Normalize book based on file extension
    """
    if file_ext.lower() == 'epub':
        return normalize_epub(filepath, book_id, user_id)
    elif file_ext.lower() == 'pdf':
        return normalize_pdf(filepath, book_id, user_id)
    else:
        logger.error(f"Unsupported file format: {file_ext}")
        raise ValueError(f"Unsupported file format: {file_ext}") 