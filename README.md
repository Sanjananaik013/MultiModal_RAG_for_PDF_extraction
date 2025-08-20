📄 Smart PDF Analyzer

An application for intelligent PDF document analysis using OCR + Google Gemini AI.
Upload a PDF, and ask questions about diagrams, tables, graphs, or general content. The system extracts text using pytesseract, processes it with Gemini API, and provides contextual answers.

🚀 Features

    ✅ Upload any PDF file.

    📖 OCR-based text extraction from scanned PDFs (via pytesseract).

    🤖 AI-powered analysis using Google Gemini (google.generativeai).

    📊 Specialized responses for diagrams, tables, and general queries.

    🔄 Backend (FastAPI) + Frontend (Streamlit) integration.

    💬 Chat-like interface for querying PDFs.

Key Workflows

1. Ingest PDF (handle_ingest_pdf)

    Receives base64-encoded PDF and filename.

    Decodes and splits PDF into images (pdf2image).

    Applies OCR on each page image (pytesseract).

    Stores both images and extracted text in memory.

    Prevents re-ingestion of already-uploaded PDFs.

2. Query PDF (handle_query_pdf)

    Receives a user question.

    Uses Gemini to identify the most relevant page numbers.

    For each selected page:

        Chooses analysis mode (diagram, table, or general) based on question intent.

        Constructs a context-specific prompt using templates and sends it to the Gemini model.

        Returns structured responses, with each page's analysis shown separately.

3. Modular Node-Based LLM Prompt Routing

    The app creates three different "nodes" for:

        Diagram: Explains diagrams, lists component roles/connections, offers interpretation.

        Table: Returns only tables, avoids explanations, and strictly follows question intent.

        General: Directly answers non-diagram/non-table questions concisely.

    Each node combines page text and the user question into a tailored prompt.

4. FastAPI Endpoint

    Endpoint: POST /mcp/

        Accepts an MCPRequest (operation, payload, context).

        Delegates to the appropriate handler (ingest_pdf or query_pdf).

5. Logging and Error Handling

    All major operations are logged for debugging.

    Errors are caught, logged, and returned in a friendly format.
   

🖥️ How to Use

1. Start server-
   
     uvicorn main_mcp:app --reload
   
2. Start streamlit app in another terminal-
   
     streamlit run app.py
   
3. Upload the pdf and ENJOY!!
