from pathlib import Path
import pdfplumber
from docx import Document as DocxDocument
from typing import Optional

class DocumentProcessorService:
    """Extract text from various document formats"""
    
    async def extract_text(self, file_path: str, file_type: str) -> str:
        """Extract text from document"""
        
        if file_type == "pdf":
            return await self._extract_from_pdf(file_path)
        elif file_type in ["docx", "doc"]:
            return await self._extract_from_docx(file_path)
        elif file_type == "txt":
            return await self._extract_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    
    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()