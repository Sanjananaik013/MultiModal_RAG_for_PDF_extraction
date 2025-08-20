import streamlit as st
import requests
import base64
from typing import Dict

class MCPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def send_request(self, operation: str, payload: Dict, context: Dict = None) -> Dict:
        try:
            response = requests.post(
                f"{self.base_url}/mcp/",
                json={"operation": operation, "payload": payload, "context": context}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")  
            print(f"Response content: {response.content}")  
            return {"status": "error", "error": str(http_err), "response_content": response.content.decode('utf-8')}
        except ValueError as ve:
            print(f"Value error occurred: {ve}")  
            return {"status": "error", "error": "Invalid JSON response"}
        except Exception as e:
            print(f"An unexpected error occurred: {e}")  
            return {"status": "error", "error": str(e)}

st.title("📄 Smart PDF Analyzer")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = MCPClient("http://localhost:8000")

if "processed" not in st.session_state:
    st.session_state.processed = False

if "context" not in st.session_state:
    st.session_state.context = {}

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.processed:
    uploaded_file = st.file_uploader("📤 Upload PDF", type="pdf")

    if uploaded_file:
        st.session_state.pdf_bytes = uploaded_file.getvalue()
        st.session_state.context["filename"] = uploaded_file.name

        with st.spinner("📥 Ingesting PDF..."):
            file_b64 = base64.b64encode(st.session_state.pdf_bytes).decode("utf-8")
            result = st.session_state.client.send_request(
                operation="ingest_pdf",
                payload={"file": file_b64},
                context=st.session_state.context
            )

            if result.get("status") == "success":
                st.session_state.processed = True
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "✅ PDF ingested successfully. You can now ask questions!"
                })
                st.rerun()
            else:
                st.error(f"❌ Failed to ingest PDF: {result.get('error', 'Unknown error')}")

if st.session_state.processed:
    prompt = st.chat_input(" Ask about the PDF")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("🤔 Thinking..."):
            response = st.session_state.client.send_request(
                operation="query_pdf",
                payload={"question": prompt},
                context=st.session_state.context
            )

            answer_text = (
                response.get("result", {}).get("response", "⚠️ No response from server")
                if response.get("status") == "success"
                else f"❌ Error: {response.get('error', 'Unknown error')}"
            )

            st.session_state.messages.append({"role": "assistant", "content": answer_text})
            st.rerun()
