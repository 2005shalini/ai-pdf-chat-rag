import os
from utils.pdf import extract_text_from_pdf


def chunk_text_by_pages(pages_data, chunk_size=500, chunk_overlap=100):
    """
    Splits extracted PDF page text into smaller overlapping chunks while preserving page numbers.

    :param pages_data: list of dicts [{"page": int, "text": str}]
    :param chunk_size: maximum character length per chunk (default: 500)
    :param chunk_overlap: overlapping character count between chunks (default: 100)
    :return: list of dicts [{"chunk_id": int, "text": str, "page": int}]
    """
    if not pages_data:
        return []

    chunks = []
    chunk_counter = 0
    step = max(1, chunk_size - chunk_overlap)

    for page_item in pages_data:
        page_num = page_item.get("page", 1)
        page_text = page_item.get("text", "").strip()

        if not page_text:
            continue

        # If page text fits within a single chunk
        if len(page_text) <= chunk_size:
            chunks.append({
                "chunk_id": chunk_counter,
                "text": page_text,
                "page": page_num
            })
            chunk_counter += 1
        else:
            # Sliding window chunking with overlap
            start = 0
            text_len = len(page_text)

            while start < text_len:
                end = min(start + chunk_size, text_len)
                chunk_str = page_text[start:end].strip()

                if chunk_str:
                    chunks.append({
                        "chunk_id": chunk_counter,
                        "text": chunk_str,
                        "page": page_num
                    })
                    chunk_counter += 1

                if end == text_len:
                    break

                start += step

    return chunks


def process_pdf_into_chunks(filepath, chunk_size=500, chunk_overlap=100):
    """
    Reuses PDF text extraction from pdf.py and splits the document into chunks with page metadata.

    :param filepath: path to PDF file
    :param chunk_size: chunk size in characters
    :param chunk_overlap: overlap size in characters
    :return: dict with success status, filename, total_chunks, chunks array, and message
    """
    extraction = extract_text_from_pdf(filepath)

    if not extraction["success"]:
        return {
            "success": False,
            "filename": extraction.get("filename"),
            "total_chunks": 0,
            "chunks": [],
            "message": extraction.get("message")
        }

    chunks = chunk_text_by_pages(extraction["pages"], chunk_size, chunk_overlap)

    return {
        "success": True,
        "filename": extraction["filename"],
        "total_chunks": len(chunks),
        "chunks": chunks,
        "message": f"Successfully processed PDF into {len(chunks)} chunk(s)."
    }
