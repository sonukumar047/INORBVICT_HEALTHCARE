# INORBVICT_HEALTHCARE


# AI Assistant (Flow + RAG)

A production‑ready, accessibility‑first chatbot that supports two powerful modes:
- Flow Mode: a guided, validation‑driven intake that collects name, email, phone, and a selected service.
- RAG Mode: Retrieval‑Augmented Generation over user‑uploaded documents (PDF/TXT). Upload once, then ask natural‑language questions grounded in those files.

The project is intentionally lightweight (no frontend frameworks), easy to run locally, and designed with best practices in separation of concerns, accessibility, and UTF‑8 correctness.

---

## 1) Directory Layout (mkdir + touch recipe)

This section helps bootstrap an empty repo into the exact structure used by the app. If the files already exist, skip the `touch` steps.


# Backend folders
mkdir -p backend/app/models
mkdir -p backend/app/routers
mkdir -p backend/app/services
mkdir -p backend/app/utils
mkdir -p backend/data/documents
mkdir -p backend/vector_db

# Frontend folders
mkdir -p frontend/static/css
mkdir -p frontend/static/js

# Backend files
touch backend/app/main.py
touch backend/app/models/chat.py
touch backend/app/models/flow.py
touch backend/app/routers/flow_chat.py
touch backend/app/routers/rag_chat.py
touch backend/app/services/flow_service.py
touch backend/app/services/rag_service.py
touch backend/app/services/vector_store.py
touch backend/app/utils/validation.py
touch backend/requirements.txt

# Frontend files
touch frontend/index.html
touch frontend/static/css/style.css
touch frontend/static/js/app.js
```

Resulting tree:

```
backend/
  app/
    main.py                         # FastAPI entrypoint; UTF-8 JSON by default
    models/
      chat.py                       # Request/response Pydantic models for chat
      flow.py                       # Flow step definitions and responses
    routers/
      flow_chat.py                  # Flow endpoints: /flow/start, /flow/chat/{id}
      rag_chat.py                   # RAG endpoints: /rag/start, /rag/upload, /rag/chat/{id}
    services/
      flow_service.py               # Full flow logic with validation and retry handling
      rag_service.py                # Simple RAG (keyword) or plug in vector_store
      vector_store.py               # Optional FAISS + HuggingFace embeddings wrapper
    utils/
      validation.py                 # Name/email/phone/service validation helpers
  data/
    documents/                      # Uploaded files (persisted)
  vector_db/                        # Vector index persistence (if FAISS used)
  requirements.txt                  # Python dependencies
frontend/
  index.html                        # Accessible HTML scaffold
  static/
    css/style.css                   # No inline CSS, responsive, focus-visible, ARIA friendly
    js/app.js                       # Mode handling, upload, chat, progress UI


---

## 2) What This App Solves (and How)

- Guided Intake without Friction
  - Users complete a clear path of questions in Flow Mode.
  - Each step validates input with helpful, human‑readable error messages.
  - A final summary modal consolidates the captured information for quick confirmation or handoff.

- Document‑Grounded Answers (RAG)
  - Users upload PDFs/TXTs. The backend extracts and chunks text (configurable).
  - Questions are answered by searching those chunks. A semantic vector store is available for higher relevance.
  - Upload once, then ask many questions. Useful for resumes, product docs, manuals, policies, and more.

- Real‑World Readiness
  - Accessibility is a first‑class requirement: labelled inputs, ARIA roles, visible focus states, screen‑reader‑only text for non‑visual cues.
  - Correct Content‑Type charset headers ensure UTF‑8 safety across platforms.
  - No inline CSS; everything is reusable and testable. A single JS file orchestrates a clean UI state machine.

---

## 3) Prerequisites

- Python 3.10+ (recommended)
- pip (Python package manager)
- Available ports:
  - 8000 for backend API
  - 3000 for frontend static server (or any other port preferred)

---

## 4) Install & Run

### 4.1 Backend (API)

cd backend

# Create & activate a virtual environment
# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1

# macOS/Linux
# python3 -m venv venv
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


Sanity check:
- Visit http://localhost:8000/health
- Expect a JSON response with status and charset: utf‑8

Key backend endpoints:
- POST /flow/start → returns session_id + message to begin Flow.
- POST /flow/chat/{session_id} → body: {"message":"..."}; returns step feedback or final summary.
- POST /rag/start → returns session_id + RAG instructions.
- POST /rag/upload → multipart/form-data with field name files (multiple allowed).
- POST /rag/chat/{session_id} → body: {"message":"..."}; answers grounded in uploaded files.

### 4.2 Frontend (Static)

cd frontend

# Serve static files on port 3000
python -m http.server 3000

# If 3000 is taken:
# python -m http.server 5500


Open:
- http://localhost:3000 (or the chosen port)

If the API does not run on localhost:8000, update the base URL in:
```
frontend/static/js/app.js  →  this.baseUrl = 'http://localhost:8000';
```

---

## 5) Using the App

### 5.1 Flow Mode (Guided Intake)
1. Click “Flow Mode” (left button).
2. Wait for the “Ready” status.
3. Provide values in the sequence requested:
   - Name: at least 2 characters (letters, spaces, hyphens, apostrophes).
   - Email: standard format (e.g., user@example.com).
   - Phone: Indian mobile; validates common formats and normalizes to +91.
   - Service: choose from supported options (e.g., consulting, development).
4. After the final step, a clean summary modal appears for confirmation.
5. Start over any time via the modal button.

What’s special:
- Clear hints explain validation rules before mistakes happen.
- Retry limits protect the session from endless invalid input loops.
- Session expiration triggers graceful restarts with helpful messaging.

### 5.2 RAG Mode (Upload + Ask)
1. Click “RAG Mode” (right button).
2. The upload panel appears.
3. Click “📁 Upload Documents” and select .pdf or .txt files (≤ 10MB each).
4. Watch the upload progress modal; upon completion, a summary of indexed chunks is shown.
5. Ask any question in the message box. Answers use uploaded content.

Tips for better answers:
- Prefer text‑based PDFs (image‑only PDFs require OCR, which is not included by default).
- Use concise questions with key terms from the documents.
- Consider enabling the optional FAISS vector store for semantic retrieval.

---

## 6) Architecture & Design Notes

- Separation of Concerns
  - Routers expose endpoints; services implement logic; models define payloads; utilities provide validation.
  - Frontend is pure HTML/CSS/JS; no heavy frameworks needed.

- Accessibility
  - Every form control has a label (visible or screen‑reader‑only), title, and where fitting, a placeholder.
  - ARIA roles used on dynamic regions (e.g., role="log", aria-live="polite") ensure screen reader compatibility.
  - Focus outlines and keyboard navigation are designed and tested.

- Encoding & Headers
  - JSON responses carry `application/json; charset=utf-8`.
  - Text file uploads re‑encoded to UTF‑8 where possible; PDFs handled in binary.

- Error Handling
  - Unhappy paths (invalid types, large files, undecodable text) return actionable error messages.
  - Frontend toasts show transient, color‑coded feedback; messages are also posted inline in chat for continuity.

---

## 7) Optional: Semantic Vector Store (FAISS)

This project ships with a simple keyword‑based search by default. For higher relevance:

1. Install extras:
   ```
   pip install langchain-community langchain-huggingface sentence-transformers faiss-cpu
   ```

2. backend/app/services/vector_store.py provides a minimal wrapper:
   - add_files(paths) splits and indexes documents with HuggingFace embeddings (defaults to `all-MiniLM-L6-v2`).
   - similarity_search(query, k) returns the best‑matching chunks with scores.
   - info() exposes index statistics.

3. Integrate into RAG service:
   - On upload: call `vector_store.add_files(paths)`.
   - On chat: call `vector_store.similarity_search(query)` and assemble the answer from top chunks.

This path keeps the interface identical for the frontend, while boosting answer quality.

---

## 8) Configuration & Limits

- Backend URL default: `http://localhost:8000` (change in `app.js`).
- Upload directory: `backend/data/documents` (auto‑created).
- Vector store directory: `backend/vector_db` (auto‑created).
- File types: `.pdf`, `.txt`
- Max file size: `10 MB` per file
- Flow session timeout and retry limits are configurable in `flow_service.py`.

---

## 9) Troubleshooting Guide

- Can’t connect / CORS:
  - Confirm the backend server is running and `/health` returns JSON.
  - Ensure the frontend `baseUrl` points to the correct backend host/port.

- Upload panel missing:
  - Switch to “RAG Mode”. The upload section is only visible in RAG.

- Accessibility audit: “Form elements must have labels”:
  - Ensure you’re using the provided `index.html`.
  - Confirm `for="messageInput"` and `for="fileInput"` are present and IDs match.
  - Titles and placeholders must remain intact.

- Charset warnings:
  - Inspect response headers; `Content-Type` should include `charset=utf-8`.
  - The backend sets this via a default JSON response class.

- Empty PDF extraction:
  - Some PDFs are scans (images). OCR is not bundled. Use text‑based PDFs or add OCR pipeline if required.

---

## 10) Stopping Services

- Backend:
  - `Ctrl + C` in the backend terminal.
  - `deactivate` to exit the virtual environment.
- Frontend:
  - `Ctrl + C` in the frontend terminal.


## 11) Credits

- Backend: FastAPI + Uvicorn
- Frontend: Vanilla HTML/CSS/JS
- Optional search: FAISS + sentence‑transformers via langchain‑community/langchain‑huggingface
