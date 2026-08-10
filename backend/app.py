import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Ensure uploads directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/', methods=['GET'])
def index():
    return "AI PDF Chat Backend is Running"


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if request contains file
        if 'file' not in request.files and 'pdf' not in request.files:
            return jsonify({
                "success": False,
                "filename": None,
                "message": "No file uploaded in request"
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

