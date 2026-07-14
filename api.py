# api.py
import tempfile
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from ingestion.pdf_loader import PDFLoader
from ingestion.raw_text_loader import RawTextLoader

app = FastAPI()
pdf_loader = PDFLoader()
text_loader = RawTextLoader()


class PasteInput(BaseModel):
    title: str = "Pasted Policy"
    text: str


@app.post("/analyze/pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    """Endpoint for uploading PDF files."""
    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        pdf_path = tmp.name

    chunks = pdf_loader.load(pdf_path)
    # Pass 'chunks' into the evaluation engine...
    return {"status": "success", "chunk_count": len(chunks)}


@app.post("/analyze/text")
async def analyze_text(payload: PasteInput):
    """Endpoint for directly pasted raw text."""
    chunks = text_loader.load(file_path=payload.text, source_name=payload.title)
    # Pass 'chunks' into the evaluation engine...
    return {"status": "success", "chunk_count": len(chunks)}