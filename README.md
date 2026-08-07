# 📄 AI-PDF-Chat-RAG

> An AI-powered PDF question-answering system using Retrieval-Augmented Generation (RAG) to process uploaded documents and generate context-aware answers.

---

## 📌 Overview

**AI-PDF-Chat-RAG** is an AI-driven document interaction application designed for Computer Science & Engineering (AI) project portfolios. Users can upload PDF documents and ask questions based on their content. The system leverages a Retrieval-Augmented Generation (RAG) pipeline to extract relevant information from the uploaded documents and generate precise, contextually grounded answers.

---

## ✨ Key Features

- 📤 **PDF Upload & Ingestion**: Upload PDF documents for extraction and processing.
- 🔍 **Retrieval-Augmented Generation (RAG)**: Retrieves relevant context from document chunks to eliminate generic responses.
- 💬 **Context-Aware Question Answering**: Delivers accurate answers directly based on the uploaded document's content.
- ⚡ **Interactive Document Chat**: Enables users to converse directly with their document data through a clean user interface.

---

## ⚙️ How the System Works (RAG Pipeline)

The system utilizes a standard RAG workflow to process documents and answer questions:

1. **Document Ingestion**: The user uploads a PDF document through the application interface.
2. **Text Processing & Chunking**: The text content is extracted from the PDF and split into smaller chunks.
3. **Embedding Generation & Vector Storage**: Document chunks are converted into numerical vector embeddings and stored in a vector store.
4. **Context Retrieval**: When a query is submitted, vector similarity search identifies the most relevant text chunks matching the user's question.
5. **Answer Generation**: The retrieved text passages and the query are passed to the language model to generate a context-aware answer.

---

## 🏗️ Project Architecture & Workflow

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│   User Query /    │ ──> │   Document Text   │ ──> │   Embedding &     │
│   PDF Upload      │     │   Chunking        │     │   Vector Store    │
└───────────────────┘     └───────────────────┘     └───────────────────┘
                                                              │
                                                              ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ Context-Aware     │ <── │ Answer Generation │ <── │ Relevant Context  │
│ Response Output   │     │ (RAG LLM Engine)  │     │ Retrieval         │
└───────────────────┘     └───────────────────┘     └───────────────────┘
```

---

## 📁 Folder Structure

```
AI-PDF-Chat-RAG/
├── backend/
│   ├── uploads/
│   ├── vectorstore/
│   ├── utils/
│   ├── templates/
│   ├── static/
│   ├── app.py
│   └── .env
├── frontend/
│   ├── assets/
│   ├── css/
│   ├── js/
│   └── index.html
├── docs/
│   ├── architecture.md
│   └── screenshots/
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Python
- **AI Architecture**: Retrieval-Augmented Generation (RAG), Vector Embeddings, Vector Store, LLM Question-Answering

---

## 🚀 Installation & Setup

### Prerequisites

- **Python 3.8+**
- **Git**

### Setup Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/2005shalini/ai-pdf-chat-rag.git
   cd AI-PDF-Chat-RAG
   ```

2. **Create & Activate a Virtual Environment**
   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   # venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Environment Variable Setup

Create a `.env` file in the `backend/` directory and configure your environment key-value pairs:

```env
# Backend Environment Configuration
PORT=5000
HOST=0.0.0.0
# Add required API keys below
# API_KEY=your_api_key_here
```

---

## 🔌 API Endpoints

*(Placeholders based on architecture design)*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/upload` | Upload PDF file for ingestion and vector indexing |
| `POST` | `/api/chat` | Query the PDF content and receive RAG-generated response |
| `GET` | `/api/status` | Check processing status of uploaded document |

---

## 💻 Usage Instructions

1. Navigate to the `backend/` directory and launch the server:
   ```bash
   python backend/app.py
   ```
2. Open `frontend/index.html` in your browser or run a local static web server.
3. Upload a PDF document through the application interface.
4. Type a question related to the document and receive context-aware responses.

---

## 🖼️ Screenshots

*(Placeholders - Add actual screenshots upon visual verification)*

| Application Dashboard / PDF Upload | Chat & QA Interface |
| :---: | :---: |
| ![Upload Interface Placeholder](docs/screenshots/upload-placeholder.png) | ![Chat Interface Placeholder](docs/screenshots/chat-placeholder.png) |

---

## 🔮 Future Improvements

- 📄 Support for multi-PDF querying across several documents.
- 🎯 Hybrid search (combining dense vector similarity with sparse keyword search).
- 📌 Page citation and highlight references in generated answers.
- 🔐 User authentication and chat session persistence.

---

## 👤 Author

- **Shalini Richhariya**
- GitHub: [@2005shalini](https://github.com/2005shalini)
- Project Repository: [AI-PDF-Chat-RAG](https://github.com/2005shalini/ai-pdf-chat-rag)
