"""
Telegram Webhook Handler
بدلاً من polling، نستقبل updates عبر webhook
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import asyncio
from telegram import Update
from loguru import logger

from app.database import get_db
from app.config import get_settings

router = APIRouter(prefix="/telegram", tags=["telegram"])
settings = get_settings()


@router.post("/webhook")
async def telegram_webhook(
    request_data: dict,
    x_bot_secret: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    استقبال updates من Telegram webhook
    """
    # التحقق من سر البوت
    if x_bot_secret != settings.BOT_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        # معالجة update من Telegram
        update_data = Update.de_json(request_data, None)
        
        # تمرير update إلى Bot (عبر aiohttp أو queue)
        # هذا يسمح بمعالجة updates بدون polling
        
        logger.debug(f"📨 Webhook received update: {update_data.update_id if update_data else 'null'}")
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}


@router.post("/set-webhook")
async def set_webhook(
    webhook_url: str,
    x_bot_secret: str = Header(None),
):
    """
    تسجيل webhook عند Telegram
    webhook_url: مثال: https://api.qaffel.com/api/v1/telegram/webhook
    """
    if x_bot_secret != settings.BOT_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
            async with session.post(api_url, json={"url": webhook_url}) as resp:
                result = await resp.json()
                logger.info(f"✅ Webhook registered: {result}")
                return result
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise HTTPException(500, str(e))


@router.post("/delete-webhook")
async def delete_webhook(
    x_bot_secret: str = Header(None),
):
    """
    حذف webhook (للعودة إلى polling)
    """
    if x_bot_secret != settings.BOT_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/deleteWebhook"
            async with session.post(api_url, json={"drop_pending_updates": True}) as resp:
                result = await resp.json()
                logger.info(f"✅ Webhook deleted: {result}")
                return result
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")
        raise HTTPException(500, str(e))
