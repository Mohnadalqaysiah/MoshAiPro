"""
Mosh AI Pro v5 - Main FastAPI Application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import asyncio
import sys
import os
import uuid
import shutil

from app.config import get_settings
from app.database import init_db, get_db
from app.api import signals, markets, analytics, chat, auth, subscription, admin, bot, public_chat, analyses, affiliate, alerts, telegram_webhook
from app.services.gemini_engine import gemini_engine
from app.services.rate_limiter import twelvedata_client
from app.models.site_settings import SiteSettings
from sqlalchemy.orm import Session
from fastapi import Depends

settings = get_settings()


# ── Price Alert Background Checker ────────────────────────────────────────────
async def _price_alert_checker():
    """يفحص تنبيهات الأسعار كل 30 ثانية ويرسل إشعار تلغرام عند التفعيل"""
    import aiohttp
    from datetime import datetime, timezone
    from app.database import SessionLocal
    from app.models.price_alert import PriceAlert, AlertDirection
    from app.services.tv_price_feed import tv_feed

    SYMBOL_NAMES = {
        "XAUUSD": "🥇 الذهب", "XAGUSD": "🥈 الفضة",
        "BTCUSD": "₿ بيتكوين", "ETHUSD": "Ξ إيثريوم",
        "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY", "USDCHF": "USD/CHF",
        "NAS100": "📈 ناسداك", "US30": "📈 داو جونز",
        "SP500": "📈 S&P 500", "USOIL": "🛢 النفط",
    }

    while True:
        try:
            await asyncio.sleep(30)
            db = SessionLocal()
            try:
                pending = db.query(PriceAlert).filter(PriceAlert.triggered == False).all()
                if not pending:
                    continue

                for alert in pending:
                    price = tv_feed.get_price_sync(alert.symbol)
                    if not price:
                        continue

                    hit = (
                        (alert.direction == AlertDirection.ABOVE and price >= alert.target_price) or
                        (alert.direction == AlertDirection.BELOW and price <= alert.target_price)
                    )
                    if not hit:
                        continue

                    # تعليم التنبيه كمُفعَّل
                    alert.triggered    = True
                    alert.triggered_at = datetime.now(timezone.utc)
                    db.commit()

                    if not alert.telegram_id:
                        continue

                    # إرسال رسالة تلغرام
                    name  = SYMBOL_NAMES.get(alert.symbol, alert.symbol)
                    arrow = "📈" if alert.direction == AlertDirection.ABOVE else "📉"
                    note  = f"\n📝 {alert.note}" if alert.note else ""
                    msg   = (
                        f"🔔 *تنبيه السعر تم تفعيله!*\n\n"
                        f"{arrow} *{name}*\n"
                        f"السعر الحالي: `{price:,.2f}`\n"
                        f"السعر المستهدف: `{alert.target_price:,.2f}`{note}\n\n"
                        f"_تنبيه من Qaffel AI_"
                    )
                    token = settings.TELEGRAM_BOT_TOKEN
                    url   = f"https://api.telegram.org/bot{token}/sendMessage"
                    async with aiohttp.ClientSession() as sess:
                        await sess.post(url, json={
                            "chat_id":    alert.telegram_id,
                            "text":       msg,
                            "parse_mode": "Markdown",
                        }, timeout=aiohttp.ClientTimeout(total=10))
                    logger.info(f"🔔 Alert triggered: {alert.symbol} @ {price} (user {alert.user_id})")

            finally:
                db.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Price alert checker error: {e}")


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
    os.makedirs("/app/static/uploads", exist_ok=True)
    logger.success("✅ Database initialized")

    # بدء خدمة TradingView WebSocket (أسعار Spot حقيقية)
    try:
        from app.services.tv_price_feed import tv_feed
        await tv_feed.start()
        # انتظر قليلاً حتى تصل أسعار TV قبل أول طلب تحليل
        await asyncio.sleep(5)
    except Exception as _tv_err:
        logger.warning(f"⚠️ TradingView feed failed to start: {_tv_err} — will use fallback pricing")

    # تحميل أداء الإشارات من DB لضبط Dynamic RR
    try:
        from app.services.ai_engine_v5 import mosh_ai_engine_v5
        from app.database import SessionLocal
        _db = SessionLocal()
        try:
            mosh_ai_engine_v5.load_performance_from_db(_db)
        finally:
            _db.close()
    except Exception as _perf_err:
        logger.warning(f"Could not load performance from DB: {_perf_err}")

    # بدء مهمة تنبيهات الأسعار
    alert_task = asyncio.create_task(_price_alert_checker())
    logger.success("✅ Price alert checker started")

    yield

    alert_task.cancel()

    # Shutdown
    logger.info("👋 Shutting down Mosh AI Pro v5...")
    try:
        from app.services.tv_price_feed import tv_feed
        await tv_feed.stop()
    except Exception:
        pass


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


@app.get("/prices")
async def live_prices():
    """
    أسعار لحظية من كل المصادر للمقارنة — مفيد للتشخيص.
    يُظهر: TV Spot, yfinance Futures, الفارق (basis), مصدر التحليل.
    """
    import time as _time
    from app.services.tv_price_feed import tv_feed
    from app.services.smart_data import smart_data as _sd

    symbols = ["XAUUSD", "XAGUSD", "BTCUSD", "EURUSD", "GBPUSD"]
    result = {}
    for sym in symbols:
        tv_p    = tv_feed.get_price_sync(sym)
        yf_meta = _sd.get_realtime_price_with_meta(sym)
        yf_p    = yf_meta["price"] if yf_meta else None
        market_open = _sd.is_market_open(sym)
        entry = {
            "tv_spot":      round(float(tv_p), 5)  if tv_p  else None,
            "yfinance":     round(float(yf_p), 5)  if yf_p  else None,
            "yf_source":    yf_meta.get("source")  if yf_meta else None,
            "basis":        round(float(tv_p) - float(yf_p), 2) if tv_p and yf_p else None,
            "market_open":  market_open,
        }
        result[sym] = entry

    return {
        "tv_feed_alive": tv_feed.is_alive(),
        "prices": result,
    }


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


@app.get("/api/v1/settings/public")
async def public_settings(db: Session = Depends(get_db)):
    """إعدادات الموقع العامة (اسم + شعار) — متاح بدون تسجيل دخول"""
    _PUBLIC_KEYS = {"site_name", "site_logo_url", "telegram_bot_username"}
    rows = db.query(SiteSettings).filter(SiteSettings.key.in_(_PUBLIC_KEYS)).all()
    result = {r.key: r.value for r in rows}
    result.setdefault("site_name", "Qaffel AI")
    result.setdefault("site_logo_url", "")
    return result


@app.post("/api/v1/admin/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: dict = Depends(__import__('app.services.auth_service', fromlist=['get_admin_user']).get_admin_user),
):
    """رفع شعار الموقع — للمشرفين فقط"""
    allowed = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
    if file.content_type not in allowed:
        raise HTTPException(400, "نوع الملف غير مدعوم — PNG/JPG/GIF/WebP/SVG فقط")
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "png"
    fname = f"logo_{uuid.uuid4().hex[:8]}.{ext}"
    dest = f"/app/static/uploads/{fname}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    logo_url = f"/static/uploads/{fname}"
    row = db.query(SiteSettings).filter(SiteSettings.key == "site_logo_url").first()
    if row:
        row.value = logo_url
    else:
        db.add(SiteSettings(key="site_logo_url", value=logo_url, description="شعار الموقع"))
    db.commit()
    return {"url": logo_url}


# Include routers
app.mount("/static", StaticFiles(directory="/app/static"), name="static")
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(bot.router,          prefix="/api/v1/bot",           tags=["Bot"])
app.include_router(telegram_webhook.router, tags=["Telegram"])
app.include_router(subscription.router, prefix="/api/v1/subscription",  tags=["Subscription"])
app.include_router(admin.router,        prefix="/api/v1/admin",         tags=["Admin"])
app.include_router(signals.router,      prefix="/api/v1/signals",       tags=["Signals"])
app.include_router(markets.router,      prefix="/api/v1/markets",       tags=["Markets"])
app.include_router(analytics.router,    prefix="/api/v1/analytics",     tags=["Analytics"])
app.include_router(chat.router,         prefix="/api/v1/chat",          tags=["Chat"])
app.include_router(public_chat.router,  prefix="/api/v1/public",         tags=["Public"])
app.include_router(analyses.router,     prefix="/api/v1/analyses",        tags=["Analyses"])
app.include_router(affiliate.router,    prefix="/api/v1/affiliate",       tags=["Affiliate"])
app.include_router(alerts.router,       prefix="/api/v1/alerts",           tags=["Alerts"])


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
