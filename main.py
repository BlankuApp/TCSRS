"""
Topic-Centric SRS API - FastAPI Application
Main entry point for the API.

Environment Variables Required:
- SUPABASE_URL: Your Supabase project URL
- SUPABASE_KEY: Your Supabase anon/public key
- SUPABASE_JWT_SECRET: Your Supabase JWT secret (from Project Settings -> API -> JWT Secret)
- JWT_ALGORITHM: JWT algorithm (default: HS256)
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, ai, decks, review, topics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print("🚀 Starting Topic-Centric SRS API...")
    print("🔒 JWT Authentication: Enabled")
    print("🛡️  Row Level Security: Enabled")
    yield
    # Shutdown
    print("👋 Shutting down Topic-Centric SRS API...")


app = FastAPI(
    title="Topic-Centric SRS API",
    description="A modular REST API for Spaced Repetition System with topic-based organization and embedded cards. Secured with Supabase JWT authentication and Row Level Security.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
# TODO: Update allow_origins with your frontend URL for production
frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = [origin.strip() for origin in frontend_url.split(",") if origin.strip()] if frontend_url else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Configure with your frontend URL(s), comma-separated
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (cards router removed - operations now in topics router)
app.include_router(admin.router)
app.include_router(ai.router)
app.include_router(decks.router)
app.include_router(topics.router)
app.include_router(review.router)


@app.get("/", tags=["health"])
async def root():
    """Root endpoint - health check."""
    return {
        "message": "Topic-Centric SRS API",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
