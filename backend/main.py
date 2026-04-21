from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from auth.router import router as auth_router
from companies.router import router as companies_router
from knowledge.router import router as knowledge_router
from analytics.router import router as analytics_router
from kiosk.router import router as kiosk_router

app = FastAPI(title="AIGITO API", version="1.0.0", description="AI Video Avatar for Offline Businesses")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded avatar images
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads" / "avatars"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/avatars", StaticFiles(directory=str(UPLOADS_DIR)), name="avatar-uploads")

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(companies_router, prefix="/api/companies", tags=["companies"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(kiosk_router, prefix="/api/kiosk", tags=["kiosk"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "aigito-backend"}
