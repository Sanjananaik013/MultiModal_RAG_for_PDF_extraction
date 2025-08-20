from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
import google.generativeai as genai
from pdf2image import convert_from_bytes
import pytesseract
import base64
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

DOC_STORE = {}
DOC_TEXT_STORE = {}

class MCPRequest(BaseModel):
    operation: str
    payload: Dict
    context: Optional[Dict] = None

class MCPResponse(BaseModel):
    status: str
    result: Optional[Dict] = None
    context: Optional[Dict] = None

class Node:
    def __init__(self, question_type: str, prompt_template: str, model):
        self.question_type = question_type
        self.prompt_template = prompt_template
        self.model = model  

    def generate_response(self, page_text: str, question: str) -> str:
        prompt = self.prompt_template.format(question=question, page_text=page_text)
        response = self.model.generate_content(prompt)
        return response.text.strip() if response.text else ""

class PDFAnalyzerService:
    def __init__(self):
        genai.configure(api_key="YOUR_API_KEY")
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.root_node = self.create_langraph()

    def create_langraph(self):
        diagram_node = Node(
            question_type="diagram",
            prompt_template="""
            Question: {question}
            Page text:
            \"\"\"{page_text}\"\"\"
            Please provide explanation related to the question as below step:
            1. Describe each component labels and its role in short and the connections between them in the diagram or graph.
            2. Provide a full interpretation of the diagram or graph in short.
            If the concept is a part of the page, then give only those concept ignoring other concepts in the same page.
            Dont give any basic representation.
            Never give page 1 and 2 analysis for any question.
            """,
            model=self.model
        )

        table_node = Node(
            question_type="table",
            prompt_template="""
            Question: {question}
            Page text:
            \"\"\"{page_text}\"\"\"
            Please provide only the table related to the question without any additional explanation.
            If user says give the table then give only the table without merging any columns , if user says explain the table then only explain the tables. If There is no explicit table name, then dont give that table.
            If the concept is a part of the page, then give only those concept ignoring other concepts in the same page.
            Never give page 1 and 2 analysis for any question.
            """,
            model=self.model
        )

        general_node = Node(
            question_type="general",
            prompt_template="""
            Question: {question}
            Page text:
            \"\"\"{page_text}\"\"\"
            Please provide a direct answer to the question based on the text provided.
            If the concept is a part of the page, then give only those concept ignoring other concepts in the same page.
            Never give page 1 and 2 analysis for any question.
            """,
            model=self.model
        )

        return {
            "diagram": diagram_node,
            "table": table_node,
            "general": general_node
        }

    def process_request(self, request: MCPRequest) -> MCPResponse:
        handler = getattr(self, f"handle_{request.operation}", None)

        if not handler:
            logger.error("Invalid operation requested: %s", request.operation)
            return MCPResponse(status="error", result={"error": "Invalid operation"})

        try:
            response = handler(request.payload, request.context)
            return MCPResponse(status="success", result=response, context=request.context)
        except Exception as e:
            logger.exception("Error processing request: %s", e)
            return MCPResponse(status="error", result={"error": str(e)})

    def handle_ingest_pdf(self, payload: Dict, context: Dict) -> Dict:
        try:
            filename = context["filename"]

            if filename in DOC_STORE:
                return {"message": "PDF already ingested in memory"}

            pdf_bytes = base64.b64decode(payload["file"])
            images = self._pdf_to_images(pdf_bytes)

            DOC_STORE[filename] = images
            DOC_TEXT_STORE[filename] = [self._extract_text_from_image(img) for img in images]

            return {"message": "PDF ingested successfully"}
        except Exception as e:
            logger.exception("Error ingesting PDF: %s", e)
            return {"error": str(e)}

    def handle_query_pdf(self, payload: Dict, context: Dict) -> Dict:
        try:
            filename = context["filename"]

            if filename not in DOC_STORE or filename not in DOC_TEXT_STORE:
                return {"error": "PDF not ingested"}

            question = payload.get("question", "")
            texts = DOC_TEXT_STORE[filename]
            relevant_pages = self._get_relevant_pages(texts, question)

            if not relevant_pages:
                return {"response": "No relevant pages found"}

            analysis = self._analyze_specific_pages(texts, question, relevant_pages)
            return {"response": analysis, "pages": relevant_pages}
        except Exception as e:
            logger.exception("Error querying PDF: %s", e)
            return {"error": str(e)}

    def _pdf_to_images(self, pdf_bytes: bytes) -> List:
        return convert_from_bytes(pdf_bytes)

    def _extract_text_from_image(self, img) -> str:
        return pytesseract.image_to_string(img)

    def _get_relevant_pages(self, texts: List[str], question: str) -> List[int]:
        prompt = f"""
        Given these document pages and this question:
        Question: {question}
        Pages: {texts}
        Return relevant page numbers (1-indexed) as comma-separated list:
        """
        response = self.model.generate_content(prompt)
        return [int(x) for x in response.text.split(',') if x.strip().isdigit()]

    def _analyze_specific_pages(self, texts: List[str], question: str, page_numbers: List[int]) -> str:
        full_response = ""

        for page_num in page_numbers:
            page_text = texts[page_num - 1]
            if "diagram" in question.lower():
                node = self.root_node["diagram"]
            elif "table" in question.lower():
                node = self.root_node["table"]
            else:
                node = self.root_node["general"]

            response = node.generate_response(page_text, question)

            if response:
                full_response += f"**Page {page_num} Analysis**:\n{response}\n\n"

        return full_response.strip()

@app.post("/mcp/")
async def handle_mcp_request(request: MCPRequest):
    service = PDFAnalyzerService()
    return service.process_request(request)
