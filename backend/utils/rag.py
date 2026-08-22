import os
import json
import numpy as np
import faiss
from utils.pdf import extract_text_from_pdf

# Global model cache for SentenceTransformer
_EMBEDDING_MODEL = None
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# Vectorstore directory paths
VECTORSTORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vectorstore"))
DEFAULT_INDEX_PATH = os.path.join(VECTORSTORE_DIR, "index.faiss")
DEFAULT_METADATA_PATH = os.path.join(VECTORSTORE_DIR, "metadata.json")


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


def create_faiss_index(numpy_embeddings):
    """
    Creates a FAISS IndexFlatL2 index and adds the generated embeddings.

    :param numpy_embeddings: 2D numpy array of shape (N, dimension) with dtype float32
    :return: faiss.IndexFlatL2 instance populated with vectors
    """
    if numpy_embeddings is None or numpy_embeddings.size == 0:
        raise ValueError("Cannot create FAISS index: numpy_embeddings is empty or None.")

    if not isinstance(numpy_embeddings, np.ndarray):
        numpy_embeddings = np.array(numpy_embeddings, dtype=np.float32)
    elif numpy_embeddings.dtype != np.float32:
        numpy_embeddings = numpy_embeddings.astype(np.float32)

    if numpy_embeddings.ndim != 2:
        raise ValueError(f"numpy_embeddings must be 2D array, got ndim={numpy_embeddings.ndim}")

    dimension = int(numpy_embeddings.shape[1])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.ascontiguousarray(numpy_embeddings))

    return index


def save_faiss_index_and_metadata(index, chunks, index_path=DEFAULT_INDEX_PATH, metadata_path=DEFAULT_METADATA_PATH, extra_info=None):
    """
    Saves the FAISS index file and corresponding chunk metadata JSON file inside vectorstore.
    Ensures every vector index (0 to N-1) maps directly to chunk_id, page, and text.

    :param index: faiss index instance
    :param chunks: list of chunk dicts [{"chunk_id": int, "page": int, "text": str}]
    :param index_path: file path for .faiss index
    :param metadata_path: file path for .json metadata
    :param extra_info: optional dict of additional document/index metadata
    :return: dict with paths and total chunk count
    """
    os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(metadata_path)), exist_ok=True)

    # Save FAISS index
    faiss.write_index(index, index_path)

    # Prepare clean serializable metadata mapping chunk_id, page, text
    clean_chunks = []
    for idx, c in enumerate(chunks):
        clean_chunks.append({
            "chunk_id": c.get("chunk_id", idx),
            "page": c.get("page", 1),
            "text": c.get("text", "")
        })

    metadata_payload = {
        "total_chunks": len(clean_chunks),
        "dimension": int(index.d),
        "chunks": clean_chunks
    }

    if extra_info and isinstance(extra_info, dict):
        metadata_payload.update(extra_info)

    # Save metadata JSON
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2, ensure_ascii=False)

    return {
        "index_path": index_path,
        "metadata_path": metadata_path,
        "total_chunks": len(clean_chunks),
        "dimension": int(index.d)
    }


def load_faiss_index_and_metadata(index_path=DEFAULT_INDEX_PATH, metadata_path=DEFAULT_METADATA_PATH):
    """
    Loads FAISS index and metadata from disk.

    :param index_path: path to .faiss file
    :param metadata_path: path to .json metadata file
    :return: dict with index instance, metadata dict, and chunks list
    """
    if not os.path.exists(index_path):
        return {
            "success": False,
            "message": f"FAISS index file not found at: {index_path}",
            "index": None,
            "chunks": []
        }

    if not os.path.exists(metadata_path):
        return {
            "success": False,
            "message": f"Metadata file not found at: {metadata_path}",
            "index": None,
            "chunks": []
        }

    index = faiss.read_index(index_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_payload = json.load(f)

    chunks = metadata_payload.get("chunks", [])

    return {
        "success": True,
        "index": index,
        "metadata": metadata_payload,
        "chunks": chunks,
        "total_chunks": index.ntotal,
        "dimension": index.d,
        "message": f"Successfully loaded FAISS index with {index.ntotal} vectors and metadata."
    }


def process_pdf_into_faiss_index(filepath, chunk_size=500, chunk_overlap=100, index_path=DEFAULT_INDEX_PATH, metadata_path=DEFAULT_METADATA_PATH):
    """
    Complete Phase 6 pipeline:
    PDF -> Extract text -> Create chunks -> Generate embeddings -> Create FAISS index -> Save index + metadata.
    """
    chunk_res = process_pdf_into_chunks(filepath, chunk_size, chunk_overlap)

    if not chunk_res["success"]:
        return {
            "success": False,
            "filename": chunk_res.get("filename"),
            "total_chunks": 0,
            "dimension": 0,
            "index_path": "",
            "metadata_path": "",
            "message": chunk_res.get("message")
        }

    emb_res = generate_embeddings_for_chunks(chunk_res["chunks"])

    if not emb_res["success"]:
        return {
            "success": False,
            "filename": chunk_res.get("filename"),
            "total_chunks": 0,
            "dimension": 0,
            "index_path": "",
            "metadata_path": "",
            "message": emb_res.get("message")
        }

    # Create FAISS IndexFlatL2 using the generated embedding vectors
    index = create_faiss_index(emb_res["numpy_embeddings"])

    # Save index and metadata to backend/vectorstore/
    save_info = save_faiss_index_and_metadata(
        index=index,
        chunks=emb_res["embedded_chunks"],
        index_path=index_path,
        metadata_path=metadata_path,
        extra_info={
            "filename": chunk_res["filename"],
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "model_name": DEFAULT_MODEL_NAME
        }
    )

    return {
        "success": True,
        "filename": chunk_res["filename"],
        "total_chunks": save_info["total_chunks"],
        "dimension": save_info["dimension"],
        "index_path": save_info["index_path"],
        "metadata_path": save_info["metadata_path"],
        "message": f"Successfully processed PDF, generated {save_info['total_chunks']} embeddings (dim {save_info['dimension']}), and saved FAISS index + metadata."
    }


def search_similar_chunks(question, top_k=3, index_path=DEFAULT_INDEX_PATH, metadata_path=DEFAULT_METADATA_PATH, model_name=DEFAULT_MODEL_NAME):
    """
    Phase 6 - Step 3: FAISS Similarity Search.
    Embeds the user question and performs similarity search on the FAISS index to retrieve the top_k most relevant chunks.

    :param question: query string from user
    :param top_k: number of top relevant chunks to retrieve (default: 3)
    :param index_path: path to .faiss file
    :param metadata_path: path to .json metadata file
    :param model_name: SentenceTransformer model name
    :return: dict with success, question, results, and number_of_results
    """
    if not question or not str(question).strip():
        return {
            "success": False,
            "question": question or "",
            "results": [],
            "number_of_results": 0,
            "message": "Question cannot be empty."
        }

    clean_question = str(question).strip()

    # Load FAISS index and metadata
    load_res = load_faiss_index_and_metadata(index_path, metadata_path)
    if not load_res["success"]:
        return {
            "success": False,
            "question": clean_question,
            "results": [],
            "number_of_results": 0,
            "message": load_res["message"]
        }

    index = load_res["index"]
    chunks = load_res["chunks"]

    if index.ntotal == 0 or len(chunks) == 0:
        return {
            "success": False,
            "question": clean_question,
            "results": [],
            "number_of_results": 0,
            "message": "FAISS index or metadata contains no chunks to search."
        }

    # Generate query embedding using the existing model
    model = get_embedding_model(model_name)
    query_emb = model.encode([clean_question], convert_to_numpy=True, show_progress_bar=False)
    query_emb = np.ascontiguousarray(query_emb, dtype=np.float32)

    # Determine k (cannot exceed available vectors)
    k = min(max(1, int(top_k)), index.ntotal)

    # FAISS L2 similarity search
    distances, indices = index.search(query_emb, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1 or idx >= len(chunks):
            continue
        chunk = chunks[idx]
        results.append({
            "chunk_id": chunk.get("chunk_id", int(idx)),
            "page": chunk.get("page", 1),
            "text": chunk.get("text", ""),
            "score": float(dist),
            "distance": float(dist)
        })

    return {
        "success": True,
        "question": clean_question,
        "results": results,
        "number_of_results": len(results),
        "message": f"Successfully retrieved {len(results)} relevant chunk(s)."
    }


def get_gemini_client():
    """Initializes and returns Google Gemini client using GEMINI_API_KEY from environment."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or not api_key.strip() or api_key.strip() == 'your_actual_gemini_api_key':
        return None, "GEMINI_API_KEY is NOT CONFIGURED (or using placeholder) in backend/.env"
    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())
        return client, None
    except Exception as e:
        return None, f"Failed to initialize Gemini SDK client: {str(e)}"


def generate_rag_answer(question, top_k=3, index_path=DEFAULT_INDEX_PATH, metadata_path=DEFAULT_METADATA_PATH, model_name=None):
    """
    Phase 7 - Step 2A: RAG Answer Generation Helper.
    Connects similarity search on FAISS vectorstore with Google Gemini AI generation.

    :param question: user question string
    :param top_k: number of relevant chunks to retrieve (default: 3)
    :param index_path: path to .faiss file
    :param metadata_path: path to .json metadata file
    :param model_name: Gemini model name (default: GEMINI_MODEL env var or 'gemini-3.6-flash')
    :return: dict with success, question, answer, sources, number_of_sources, and message
    """
    if not question or not str(question).strip():
        return {
            "success": False,
            "question": question or "",
            "answer": "",
            "sources": [],
            "number_of_sources": 0,
            "message": "Question cannot be empty."
        }

    clean_question = str(question).strip()

    # Step 1: Perform FAISS similarity search to retrieve top_k relevant chunks
    search_res = search_similar_chunks(
        question=clean_question,
        top_k=top_k,
        index_path=index_path,
        metadata_path=metadata_path
    )

    if not search_res.get("success"):
        return {
            "success": False,
            "question": clean_question,
            "answer": "",
            "sources": [],
            "number_of_sources": 0,
            "message": search_res.get("message", "FAISS search failed.")
        }

    retrieved_chunks = search_res.get("results", [])
    if not retrieved_chunks:
        return {
            "success": False,
            "question": clean_question,
            "answer": "The requested information was not found in the uploaded document.",
            "sources": [],
            "number_of_sources": 0,
            "message": "No relevant document chunks found for the given question."
        }

    # Step 2: Build context string from page text and page numbers
    context_blocks = []
    sources = []
    for idx, c in enumerate(retrieved_chunks, 1):
        page_num = c.get("page", 1)
        chunk_text = c.get("text", "").strip()
        context_blocks.append(f"[Source {idx} - Page {page_num}]\n{chunk_text}")

        sources.append({
            "chunk_id": c.get("chunk_id"),
            "page": page_num,
            "text": chunk_text,
            "score": c.get("score"),
            "distance": c.get("distance")
        })

    context_str = "\n\n".join(context_blocks)

    # Step 3: Construct Gemini prompt enforcing strict PDF context constraint
    prompt = f"""You are a helpful AI assistant that answers questions strictly based on the provided PDF context.

Instructions:
1. Answer the question using ONLY the provided PDF context below.
2. Do NOT invent, assume, or extrapolate any information that is not directly stated in the context.
3. If the answer is not present in the provided context, respond with: "The requested information was not found in the uploaded document."
4. Provide a clear, concise, and accurate answer.

Context from PDF:
{context_str}

User Question: {clean_question}

Answer:"""

    # Step 4: Initialize Gemini client
    client, err = get_gemini_client()
    if not client:
        return {
            "success": False,
            "question": clean_question,
            "answer": "",
            "sources": sources,
            "number_of_sources": len(sources),
            "message": err or "Gemini API client is not configured."
        }

    # Step 5: Determine Gemini model (default to GEMINI_MODEL env var or gemini-3.6-flash)
    if not model_name:
        model_name = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')

    # Step 6: Generate answer with Gemini
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        answer_text = response.text.strip() if response and hasattr(response, 'text') and response.text else ""

        return {
            "success": True,
            "question": clean_question,
            "answer": answer_text,
            "sources": sources,
            "number_of_sources": len(sources),
            "message": "Successfully generated RAG answer using Gemini."
        }
    except Exception as e:
        return {
            "success": False,
            "question": clean_question,
            "answer": "",
            "sources": sources,
            "number_of_sources": len(sources),
            "message": f"Gemini API call error: {str(e)}"
        }



