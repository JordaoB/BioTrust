"""
BioTrust Backend - FastAPI Main Application
Privacy-by-Design: No biometric data storage, real-time verification only
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import settings
from backend.database import connect_to_mongo, close_mongo_connection
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await connect_to_mongo()
    logger.info("Backend ready!")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down...")
    await close_mongo_connection()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Biometric Payment System with Privacy-by-Design Architecture",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== STATIC FILES (Frontend) ==========
# Serve static files (CSS, JS, images)
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
    logger.info(f"📁 Serving static files from: {web_dir}")
    
    # Serve index.html at /web route
    @app.get("/web", tags=["Frontend"])
    async def serve_frontend():
        """Serve the web frontend"""
        index_path = web_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Frontend not found"}
else:
    logger.warning(f"⚠️ Web directory not found: {web_dir}")

# ==============================================

# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """API health check"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "privacy": "No biometric data stored - Privacy-by-Design"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "liveness_detector": "available",
        "risk_engine": "available"
    }

# Import and register routes
from backend.routes import users, merchants, transactions, liveness, liveness_stream, auth, cards

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(cards.router, prefix="/api/users", tags=["Cards"])  # Nested under /api/users/{user_id}/cards
app.include_router(merchants.router, prefix="/api/merchants", tags=["Merchants"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(liveness.router, prefix="/api/liveness", tags=["Liveness Detection"])
app.include_router(liveness_stream.router, prefix="/api/liveness-stream", tags=["Liveness Stream"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
