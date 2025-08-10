import hashlib
from typing import List, Optional
from pathlib import Path
import PyPDF2
from io import BytesIO

def calculate_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of content"""
    return hashlib.sha256(content).hexdigest()

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")

def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from TXT file"""
    try:
        return file_content.decode('utf-8')
    except UnicodeDecodeError:
        # Try other encodings
        for encoding in ['latin-1', 'cp1252']:
            try:
                return file_content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Unable to decode text file")

def process_document(filename: str, file_content: bytes) -> tuple[str, str]:
    """Process document and return text content and hash"""
    file_ext = Path(filename).suffix.lower()
    
    if file_ext == '.pdf':
        text = extract_text_from_pdf(file_content)
    elif file_ext == '.txt':
        text = extract_text_from_txt(file_content)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    content_hash = calculate_hash(file_content)
    return text, content_hash

def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            last_period = text.rfind('.', max(start, end - 100), end)
            last_newline = text.rfind('\n', max(start, end - 100), end)
            
            break_point = max(last_period, last_newline)
            if break_point > start:
                end = break_point + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks
