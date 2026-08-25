import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Universal Multimodal Document Analyzer"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # LLM Settings (Hugging Face Multimodal Vision-Language API)
    HF_TOKEN: str = (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_API_KEY")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HUGGING_FACE_HUB_TOKEN")
        or ""
    )
    HF_MODEL: str = os.getenv("HF_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
    HF_FALLBACK_MODEL: str = "meta-llama/Llama-3.2-11B-Vision-Instruct"
    HF_MAX_RETRIES: int = 3
    HF_RETRY_DELAY: float = 2.0
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/doc_analyzer.db"
    
    # File Storage
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    SAMPLE_DIR: Path = BASE_DIR / "sample_images"
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: set = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
