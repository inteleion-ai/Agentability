"""FastAPI application for Agentability platform.

Main API server providing REST endpoints for the Agentability observability platform.

Google Style Guide Compliant.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import decisions, metrics, conflicts
import uvicorn


# Create FastAPI app
app = FastAPI(
    title="Agentability API",
    description="Observability API for Production AI Agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(decisions.router)
app.include_router(metrics.router)
app.include_router(conflicts.router)


@app.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        Status message.
    """
    return {"status": "healthy", "service": "agentability-api"}


@app.get("/")
async def root():
    """Root endpoint.
    
    Returns:
        Welcome message.
    """
    return {
        "message": "Welcome to Agentability API",
        "docs": "/docs",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
