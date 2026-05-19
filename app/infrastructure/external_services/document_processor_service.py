import io
import pdfplumber
from docx import Document as DocxDocument


class DocumentProcessorService:
    """Extract text from various document formats (operates on bytes, not filesystem paths)"""

    async def extract_text(self, file_content: bytes, file_type: str) -> str:
        if file_type == "pdf":
            return self._extract_from_pdf(file_content)
        elif file_type in ["docx", "doc"]:
            return self._extract_from_docx(file_content)
        elif file_type == "txt":
            return self._extract_from_txt(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_from_pdf(self, content: bytes) -> str:
        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts)

    def _extract_from_docx(self, content: bytes) -> str:
        doc = DocxDocument(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _extract_from_txt(self, content: bytes) -> str:
        return content.decode("utf-8")
