import os
import numpy as np
from utils.pdf import extract_text_from_pdf

# Global model cache for SentenceTransformer
_EMBEDDING_MODEL = None
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


def get_embedding_model(model_name=DEFAULT_MODEL_NAME):
    """
    Lazy loads and caches the SentenceTransformer model.
    """
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL = SentenceTransformer(model_name)
    return _EMBEDDING_MODEL


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

        if len(page_text) <= chunk_size:
            chunks.append({
                "chunk_id": chunk_counter,
                "text": page_text,
                "page": page_num
            })
            chunk_counter += 1
        else:
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


def generate_embeddings_for_chunks(chunks, model_name=DEFAULT_MODEL_NAME):
    """
    Converts text chunks into numerical vector embeddings using SentenceTransformers.
    Preserves page numbers and original chunk text together with each embedding vector.

    :param chunks: list of dicts [{"chunk_id": int, "text": str, "page": int}]
    :param model_name: SentenceTransformer model name (default: "all-MiniLM-L6-v2")
    :return: dict with total_chunks, dimension, embedded_chunks, and float32 numpy_embeddings ready for FAISS
    """
    if not chunks:
        return {
            "success": False,
            "total_chunks": 0,
            "dimension": 0,
            "embedded_chunks": [],
            "numpy_embeddings": np.empty((0, 0), dtype=np.float32),
            "message": "No text chunks provided for embedding generation."
        }

    model = get_embedding_model(model_name)
    texts = [c["text"] for c in chunks]

    # Generate 384-dimensional dense vector embeddings
    raw_embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    numpy_embeddings = np.array(raw_embeddings, dtype=np.float32)

    dimension = int(numpy_embeddings.shape[1]) if numpy_embeddings.ndim > 1 else 0

    embedded_chunks = []
    for idx, chunk in enumerate(chunks):
        vec_list = numpy_embeddings[idx].tolist()
        embedded_chunks.append({
            "chunk_id": chunk.get("chunk_id", idx),
            "text": chunk.get("text", ""),
            "page": chunk.get("page", 1),
            "embedding": vec_list
        })

    return {
        "success": True,
        "total_chunks": len(embedded_chunks),
        "dimension": dimension,
        "embedded_chunks": embedded_chunks,
        "numpy_embeddings": numpy_embeddings,
        "message": f"Successfully generated {len(embedded_chunks)} embedding(s) of dimension {dimension} using model '{model_name}'."
    }


def process_pdf_into_embeddings(filepath, chunk_size=500, chunk_overlap=100):
    """
    Complete pipeline: PDF -> Text Extraction -> Chunking -> Vector Embeddings.
    """
    chunk_res = process_pdf_into_chunks(filepath, chunk_size, chunk_overlap)

    if not chunk_res["success"]:
        return {
            "success": False,
            "filename": chunk_res.get("filename"),
            "total_chunks": 0,
            "dimension": 0,
            "chunks": [],
            "message": chunk_res.get("message")
        }

    emb_res = generate_embeddings_for_chunks(chunk_res["chunks"])

    return {
        "success": True,
        "filename": chunk_res["filename"],
        "total_chunks": emb_res["total_chunks"],
        "dimension": emb_res["dimension"],
        "chunks": emb_res["embedded_chunks"],
        "message": f"Successfully generated {emb_res['total_chunks']} chunk embedding(s) of dimension {emb_res['dimension']}."
    }
