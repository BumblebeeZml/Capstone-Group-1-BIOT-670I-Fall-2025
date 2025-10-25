from mimetypes import guess_type
from PIL import Image
from PyPDF2 import PdfReader
from pathlib import Path

def extract_metadata(file_path: str) -> dict:
    metadata = {}
    mime_type = guess_type(file_path)[0] or ""

    if mime_type.startswith("image"):
        try:
            with Image.open(file_path) as img:
                metadata["resolution"] = f"{img.width}x{img.height}"
                metadata["format"] = img.format
        except Exception as e:
            metadata["error"] = f"Image metadata error: {e}"

    elif mime_type == "application/pdf":
        try:
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                metadata["pages"] = len(reader.pages)
        except Exception as e:
            metadata["error"] = f"PDF metadata error: {e}"

    metadata["mime_type"] = mime_type
    return metadata
