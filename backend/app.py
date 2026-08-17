import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from utils.pdf import extract_text_from_pdf
from utils.rag import (
    process_pdf_into_chunks,
    process_pdf_into_embeddings,
    process_pdf_into_faiss_index,
    search_similar_chunks
)

app = Flask(__name__)

# Configure CORS explicitly to support 127.0.0.1:5500, localhost:5500, and all frontend requests
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)


@app.after_request
def add_cors_headers(response):
    """Ensure CORS headers are present on all responses, including errors and preflights."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, X-Requested-With'
    return response


# Ensure uploads directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def index():
    return jsonify({
        "status": "Backend running",
        "message": "AI PDF Chat Backend is Running",
        "endpoints": {
            "health": "GET /",
            "upload": "POST /upload",
            "extract": "POST /extract",
            "chunk": "POST /chunk",
            "embed": "POST /embed",
            "index": "POST /index",
            "search": "POST /search"
        }
    }), 200


@app.route('/upload', methods=['POST', 'OPTIONS'])
@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        # Check if request contains file
        if 'file' not in request.files and 'pdf' not in request.files:
            return jsonify({
                "success": False,
                "filename": None,
                "message": "No file uploaded in request. Expected form field 'file' or 'pdf'."
            }), 400

        file = request.files.get('file') or request.files.get('pdf')

        # Check if file selection is empty
        if not file or file.filename == '':
            return jsonify({
                "success": False,
                "filename": None,
                "message": "No file selected"
            }), 400

        # Validate PDF file extension
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if not filename:
                filename = "uploaded_document.pdf"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            return jsonify({
                "success": True,
                "filename": filename,
                "message": "PDF uploaded successfully"
            }), 200

        return jsonify({
            "success": False,
            "filename": None,
            "message": "Invalid file type. Only PDF files are allowed."
        }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "filename": None,
            "message": f"Upload error: {str(e)}"
        }), 500


@app.route('/extract', methods=['POST', 'OPTIONS'])
@app.route('/api/extract', methods=['POST', 'OPTIONS'])
def extract_pdf_text():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json(silent=True) or request.form
        filename = data.get('filename') if data else None

        if not filename:
            return jsonify({
                "success": False,
                "filename": None,
                "number_of_pages": 0,
                "extracted_text": "",
                "pages": [],
                "message": "Filename parameter is missing"
            }), 400

        clean_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], clean_filename)

        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "filename": filename,
                "number_of_pages": 0,
                "extracted_text": "",
                "pages": [],
                "message": f"PDF file not found in uploads: {filename}"
            }), 404

        result = extract_text_from_pdf(filepath)

        if not result["success"]:
            return jsonify({
                "success": False,
                "filename": filename,
                "number_of_pages": result["total_pages"],
                "extracted_text": "",
                "pages": result["pages"],
                "message": result["message"]
            }), 400

        return jsonify({
            "success": True,
            "filename": filename,
            "number_of_pages": result["total_pages"],
            "extracted_text": result["full_text"],
            "pages": result["pages"],
            "message": result["message"]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "filename": None,
            "number_of_pages": 0,
            "extracted_text": "",
            "pages": [],
            "message": f"Extraction error: {str(e)}"
        }), 500


@app.route('/chunk', methods=['POST', 'OPTIONS'])
@app.route('/api/chunk', methods=['POST', 'OPTIONS'])
def chunk_pdf_text():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json(silent=True) or request.form
        filename = data.get('filename') if data else None

        if not filename:
            return jsonify({
                "success": False,
                "filename": None,
                "total_chunks": 0,
                "chunks": [],
                "message": "Filename parameter is missing"
            }), 400

        clean_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], clean_filename)

        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "filename": filename,
                "total_chunks": 0,
                "chunks": [],
                "message": f"PDF file not found in uploads: {filename}"
            }), 404

        chunk_size = int(data.get('chunk_size', 500)) if data else 500
        chunk_overlap = int(data.get('chunk_overlap', 100)) if data else 100

        result = process_pdf_into_chunks(filepath, chunk_size, chunk_overlap)

        if not result["success"]:
            return jsonify({
                "success": False,
                "filename": filename,
                "total_chunks": 0,
                "chunks": [],
                "message": result["message"]
            }), 400

        return jsonify({
            "success": True,
            "filename": filename,
            "total_chunks": result["total_chunks"],
            "chunks": result["chunks"],
            "message": result["message"]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "filename": None,
            "total_chunks": 0,
            "chunks": [],
            "message": f"Chunking error: {str(e)}"
        }), 500


@app.route('/embed', methods=['POST', 'OPTIONS'])
@app.route('/api/embed', methods=['POST', 'OPTIONS'])
def embed_pdf_chunks():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json(silent=True) or request.form
        filename = data.get('filename') if data else None

        if not filename:
            return jsonify({
                "success": False,
                "filename": None,
                "total_chunks": 0,
                "dimension": 0,
                "embeddings_count": 0,
                "chunks": [],
                "message": "Filename parameter is missing"
            }), 400

        clean_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], clean_filename)

        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "filename": filename,
                "total_chunks": 0,
                "dimension": 0,
                "embeddings_count": 0,
                "chunks": [],
                "message": f"PDF file not found in uploads: {filename}"
            }), 404

        chunk_size = int(data.get('chunk_size', 500)) if data else 500
        chunk_overlap = int(data.get('chunk_overlap', 100)) if data else 100

        result = process_pdf_into_embeddings(filepath, chunk_size, chunk_overlap)

        if not result["success"]:
            return jsonify({
                "success": False,
                "filename": filename,
                "total_chunks": 0,
                "dimension": 0,
                "embeddings_count": 0,
                "chunks": [],
                "message": result["message"]
            }), 400

        return_vectors = data.get('return_vectors', False) if data else False
        chunks_summary = []
        for c in result["chunks"]:
            item = {
                "chunk_id": c["chunk_id"],
                "page": c["page"],
                "text": c["text"],
                "embedding_dimension": len(c["embedding"])
            }
            if return_vectors:
                item["embedding"] = c["embedding"]
            chunks_summary.append(item)

        return jsonify({
            "success": True,
            "filename": filename,
            "total_chunks": result["total_chunks"],
            "dimension": result["dimension"],
            "embeddings_count": len(result["chunks"]),
            "chunks": chunks_summary,
            "message": result["message"]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "filename": None,
            "total_chunks": 0,
            "dimension": 0,
            "embeddings_count": 0,
            "chunks": [],
            "message": f"Embedding generation error: {str(e)}"
        }), 500


@app.route('/index', methods=['POST', 'OPTIONS'])
@app.route('/api/index', methods=['POST', 'OPTIONS'])
def create_pdf_faiss_index():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json(silent=True) or request.form
        filename = data.get('filename') if data else None

        if not filename:
            return jsonify({
                "success": False,
                "filename": None,
                "total_chunks": 0,
                "dimension": 0,
                "index_path": "",
                "metadata_path": "",
                "message": "Filename parameter is missing"
            }), 400

        clean_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], clean_filename)

        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "filename": filename,
                "total_chunks": 0,
                "dimension": 0,
                "index_path": "",
                "metadata_path": "",
                "message": f"PDF file not found in uploads: {filename}"
            }), 404

        chunk_size = int(data.get('chunk_size', 500)) if data else 500
        chunk_overlap = int(data.get('chunk_overlap', 100)) if data else 100

        result = process_pdf_into_faiss_index(filepath, chunk_size, chunk_overlap)

        if not result["success"]:
            return jsonify({
                "success": False,
                "filename": filename,
                "total_chunks": 0,
                "dimension": 0,
                "index_path": "",
                "metadata_path": "",
                "message": result["message"]
            }), 400

        return jsonify({
            "success": True,
            "filename": filename,
            "total_chunks": result["total_chunks"],
            "dimension": result["dimension"],
            "index_path": result["index_path"],
            "metadata_path": result["metadata_path"],
            "message": result["message"]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "filename": None,
            "total_chunks": 0,
            "dimension": 0,
            "index_path": "",
            "metadata_path": "",
            "message": f"FAISS index creation error: {str(e)}"
        }), 500


@app.route('/search', methods=['POST', 'OPTIONS'])
@app.route('/api/search', methods=['POST', 'OPTIONS'])
def search_pdf_chunks():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json(silent=True) or request.form
        if not data or 'question' not in data:
            return jsonify({
                "success": False,
                "question": "",
                "results": [],
                "number_of_results": 0,
                "message": "Missing 'question' in request body."
            }), 400

        question = data.get('question', '')
        if not question or not str(question).strip():
            return jsonify({
                "success": False,
                "question": "",
                "results": [],
                "number_of_results": 0,
                "message": "Question cannot be empty."
            }), 400

        top_k = int(data.get('top_k', 3)) if data.get('top_k') is not None else 3

        result = search_similar_chunks(question=str(question).strip(), top_k=top_k)

        if not result["success"]:
            status_code = 404 if "not found" in result.get("message", "").lower() else 400
            return jsonify({
                "success": False,
                "question": result.get("question", str(question).strip()),
                "results": [],
                "number_of_results": 0,
                "message": result.get("message", "Search failed.")
            }), status_code

        return jsonify({
            "success": True,
            "question": result["question"],
            "results": result["results"],
            "number_of_results": result["number_of_results"],
            "message": result.get("message", "Search completed successfully.")
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "question": "",
            "results": [],
            "number_of_results": 0,
            "message": f"Search error: {str(e)}"
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Not Found",
        "message": "The requested endpoint does not exist."
    }), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "success": False,
        "error": "Internal Server Error",
        "message": "An unexpected error occurred on the server."
    }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)





