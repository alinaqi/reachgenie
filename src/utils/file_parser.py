import io
from typing import BinaryIO
from docx import Document
from PyPDF2 import PdfReader
import logging

logger = logging.getLogger(__name__)

class FileParser:
    @staticmethod
    def parse_docx(file_content: BinaryIO) -> str:
        """Parse .docx file content"""
        try:
            doc = Document(file_content)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error parsing docx file: {str(e)}")
            raise ValueError(f"Failed to parse docx file: {str(e)}")

    @staticmethod
    def parse_pdf(file_content: BinaryIO) -> str:
        """Parse .pdf file content"""
        try:
            pdf = PdfReader(file_content)
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error parsing pdf file: {str(e)}")
            raise ValueError(f"Failed to parse pdf file: {str(e)}")

    @staticmethod
    def parse_txt(file_content: bytes) -> str:
        """Parse .txt file content"""
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return file_content.decode('latin-1')
            except Exception as e:
                logger.error(f"Error parsing txt file: {str(e)}")
                raise ValueError(f"Failed to parse txt file: {str(e)}")

    @classmethod
    def parse_file(cls, file_content: bytes, file_extension: str) -> str:
        """
        Parse file content based on file extension
        
        Args:
            file_content: Binary content of the file
            file_extension: File extension (e.g., '.pdf', '.docx')
            
        Returns:
            Extracted text content from the file
        """
        file_extension = file_extension.lower()
        
        if file_extension == '.docx':
            return cls.parse_docx(io.BytesIO(file_content))
        elif file_extension == '.pdf':
            return cls.parse_pdf(io.BytesIO(file_content))
        elif file_extension == '.txt':
            return cls.parse_txt(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}") 