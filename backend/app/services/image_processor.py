import io
import hashlib
import base64
from pathlib import Path
from typing import Tuple, Dict, Any
from PIL import Image, ImageOps

class ImageProcessor:
    @staticmethod
    def compute_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def process_and_save(file_bytes: bytes, destination_path: Path) -> Dict[str, Any]:
        """
        Loads image, auto-rotates via EXIF, converts/optimizes if needed, 
        saves to disk, and returns metadata. Supports PNG, JPG, JPEG, WEBP, TIFF, BMP.
        """
        image = Image.open(io.BytesIO(file_bytes))
        
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass
            
        original_format = image.format or "PNG"
        width, height = image.size
        
        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")

        # Save with clean format
        save_format = "PNG" if image.mode == "RGBA" else "JPEG"
        if not destination_path.suffix:
            destination_path = destination_path.with_suffix(".png" if save_format == "PNG" else ".jpg")
            
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination_path, format=save_format, quality=95, optimize=True)
        
        file_size = destination_path.stat().st_size
        content_hash = ImageProcessor.compute_hash(file_bytes)

        return {
            "saved_path": str(destination_path),
            "width": width,
            "height": height,
            "original_format": original_format,
            "saved_format": save_format,
            "file_size": file_size,
            "content_hash": content_hash,
            "aspect_ratio": round(width / height, 2) if height > 0 else 1.0,
        }

    @staticmethod
    def get_clean_image_bytes(image_path: str) -> Tuple[bytes, str]:
        """
        Reads image file and returns (clean_bytes, mime_type).
        Converts TIFF, TIF, and BMP in-memory to PNG/JPEG bytes for universal Vision API
        compatibility without modifying the saved file on disk.
        """
        path = Path(image_path)
        if not path.exists():
            dummy = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
            return dummy, "image/png"

        suffix = path.suffix.lower()
        if suffix in (".tiff", ".tif", ".bmp"):
            with Image.open(path) as img:
                if img.mode not in ("RGB", "RGBA", "L"):
                    img = img.convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue(), "image/png"

        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        media_type = mime_map.get(suffix, "image/jpeg")

        with open(path, "rb") as f:
            data = f.read()
        return data, media_type

    @staticmethod
    def get_base64_image(image_path: str) -> Tuple[str, str]:
        """Returns (base64_string, media_type) with in-memory TIFF/BMP conversion."""
        clean_bytes, media_type = ImageProcessor.get_clean_image_bytes(image_path)
        encoded = base64.b64encode(clean_bytes).decode("utf-8")
        return encoded, media_type
