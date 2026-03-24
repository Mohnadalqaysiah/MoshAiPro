"""
Mosh AI Pro v5 - Main FastAPI Application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import get_settings
from app.database import init_db
from app.api import signals, markets, analytics, chat, auth, subscription, admin, bot, public_chat
from app.services.gemini_engine import gemini_engine
from app.services.rate_limiter import twelvedata_client

settings = get_settings()

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Mosh AI Pro v5...")
    init_db()
    logger.success("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Mosh AI Pro v5...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Advanced AI-Powered Trading Analysis System",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "ai_engine": "v5.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/status")
async def system_status():
    """حالة النظام والـ API Keys"""
    rl_status = twelvedata_client.get_status()
    return {
        "status": "running",
        "gemini": {
            "enabled": gemini_engine.enabled,
            "model": "gemini-2.0-flash",
            "status": "🟢 فعّال" if gemini_engine.enabled else "🔴 غير مفعّل (لا يوجد API Key)",
        },
        "twelvedata": {
            "rate_limit": f"{settings.TWELVEDATA_RATE_LIMIT} req/min",
            "tokens_available": rl_status["remaining_tokens"],
            "total_api_calls": rl_status["rate_limiter"]["total_requests"],
            "cache_hits": rl_status["rate_limiter"]["cached_requests"],
            "cache_savings": f"{rl_status['rate_limiter']['savings_pct']}%",
            "cached_symbols": rl_status["cache"]["cached_symbols"],
        }
    }


# Include routers
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(bot.router,          prefix="/api/v1/bot",           tags=["Bot"])
app.include_router(subscription.router, prefix="/api/v1/subscription",  tags=["Subscription"])
app.include_router(admin.router,        prefix="/api/v1/admin",         tags=["Admin"])
app.include_router(signals.router,      prefix="/api/v1/signals",       tags=["Signals"])
app.include_router(markets.router,      prefix="/api/v1/markets",       tags=["Markets"])
app.include_router(analytics.router,    prefix="/api/v1/analytics",     tags=["Analytics"])
app.include_router(chat.router,         prefix="/api/v1/chat",          tags=["Chat"])
app.include_router(public_chat.router,  prefix="/api/v1/public",         tags=["Public"])


# WebSocket endpoint for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"📡 WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"📡 WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or process
            await websocket.send_json({"message": "received", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
