import os
import secrets
from typing import Dict, Any

def generate_secret_key() -> str:
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)

def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """Validate file extension"""
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in allowed_extensions

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def create_response(success: bool, message: str, data: Any = None) -> Dict[str, Any]:
    """Create standardized API response"""
    response = {
        "success": success,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response
