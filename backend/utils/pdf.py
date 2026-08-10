import os
import pymupdf



def extract_text_from_pdf(filepath):
    """
    Extracts text from every page of a PDF document using PyMuPDF.
    Preserves page numbers with page text for source citations.

    Returns dict with:
      - success: bool
      - filename: str
      - total_pages: int
      - pages: list of dicts {"page": int, "text": str}
      - full_text: str
      - error: str or None
      - message: str
    """
    filename = os.path.basename(filepath)

    if not os.path.exists(filepath):
        return {
            "success": False,
            "filename": filename,
            "total_pages": 0,
            "pages": [],
            "full_text": "",
            "error": "PDF file not found",
            "message": f"File does not exist: {filepath}"
        }

    try:
        doc = pymupdf.open(filepath)
        total_pages = len(doc)


        if total_pages == 0:
            doc.close()
            return {
                "success": False,
                "filename": filename,
                "total_pages": 0,
                "pages": [],
                "full_text": "",
                "error": "PDF is empty (0 pages)",
                "message": "PDF document contains no pages."
            }

        extracted_pages = []
        full_text_list = []

        for page_index in range(total_pages):
            page = doc.load_page(page_index)
            text = page.get_text("text").strip()
            page_number = page_index + 1

            extracted_pages.append({
                "page": page_number,
                "text": text
            })

            if text:
                full_text_list.append(f"--- Page {page_number} ---\n{text}")

        doc.close()

        combined_text = "\n\n".join(full_text_list).strip()

        if not combined_text:
            return {
                "success": False,
                "filename": filename,
                "total_pages": total_pages,
                "pages": extracted_pages,
                "full_text": "",
                "error": "No extractable text found",
                "message": "PDF contains no readable text."
            }

        return {
            "success": True,
            "filename": filename,
            "total_pages": total_pages,
            "pages": extracted_pages,
            "full_text": combined_text,
            "error": None,
            "message": f"Successfully extracted text from {total_pages} page(s)."
        }

    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "total_pages": 0,
            "pages": [],
            "full_text": "",
            "error": f"Extraction failure: {str(e)}",
            "message": f"Failed to read PDF: {str(e)}"
        }
