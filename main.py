"""
Topic-Centric SRS API - FastAPI Application
Main entry point for the API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import decks, topics, cards, review


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print("🚀 Starting Topic-Centric SRS API...")
    yield
    # Shutdown
    print("👋 Shutting down Topic-Centric SRS API...")


app = FastAPI(
    title="Topic-Centric SRS API",
    description="A modular REST API for Spaced Repetition System with topic-based organization and weighted card sampling.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(decks.router)
app.include_router(topics.router)
app.include_router(cards.router)
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
