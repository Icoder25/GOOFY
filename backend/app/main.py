from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager
import time

from app.config import settings
from app.logger import setup_logging
from app.routers import health, commands, telemetry

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("goofy_backend_starting", version=settings.VERSION)
    yield
    logger.info("goofy_backend_shutting_down")


# Create FastAPI app
app = FastAPI(
    title="Goofy Backend API",
    description="Backend services for Goofy voice browser assistant",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing"""
    start_time = time.time()
    
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_ms=round(duration * 1000, 2),
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)},
        )


# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(commands.router, prefix="/api/v1", tags=["commands"])
app.include_router(telemetry.router, prefix="/api/v1", tags=["telemetry"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Goofy Backend API",
        "version": settings.VERSION,
        "status": "running",
    }
