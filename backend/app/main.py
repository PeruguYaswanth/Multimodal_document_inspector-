from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.routers import documents, query, sample_data



import os
api_key = os.environ.get("ANTHROPIC_API_KEY")

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    or_configured = bool(settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip())
    print(f"[STARTUP] Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print("[STARTUP] Provider: OpenRouter")
    print(f"[STARTUP] OpenRouter API key configured: {or_configured}")
    print(f"[STARTUP] OpenRouter model: {settings.OPENROUTER_MODEL}")
    yield
    print("[SHUTDOWN] Stopping document analyzer backend")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontend-seven-indol-89.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files for Uploads preview
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Include Routers
app.include_router(documents.router, prefix=settings.API_PREFIX)
app.include_router(query.router, prefix=settings.API_PREFIX)
app.include_router(sample_data.router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ai_provider": "openrouter",
        "model": settings.OPENROUTER_MODEL,
        "openrouter_configured": bool(settings.OPENROUTER_API_KEY),
        "openai_configured": bool(settings.OPENROUTER_API_KEY),
        "anthropic_configured": bool(settings.ANTHROPIC_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
