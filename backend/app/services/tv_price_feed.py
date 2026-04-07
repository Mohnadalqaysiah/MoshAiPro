"""
TradingView WebSocket Price Feed
=================================
يجلب أسعار Spot حقيقية من TradingView — المصدر الأدق للتداول الفوري.

البروتوكول:
  - كل رسالة: ~m~{length}~m~{json_payload}
  - Heartbeat: ~m~N~m~~h~X  → يجب إعادة إرساله
  - التوثيق: unauthorized_user_token (بيانات عامة)
  - الأسعار: qsd → p[1].v.lp

الاستخدام:
  from app.services.tv_price_feed import tv_feed
  price = await tv_feed.get_price("XAUUSD")   # None إذا غير متاح
"""

import asyncio
import json
import random
import string
import time
from typing import Optional
from loguru import logger

# ─── رموز TradingView ────────────────────────────────────────────────────────
# OANDA يعطي أسعار Spot للذهب والفوركس — أدق مصدر مجاني
TV_SYMBOL_MAP: dict[str, str] = {
    "XAUUSD":  "OANDA:XAUUSD",
    "XAGUSD":  "OANDA:XAGUSD",
    "BTCUSD":  "BINANCE:BTCUSDT",
    "ETHUSD":  "BINANCE:ETHUSDT",
    "BNBUSD":  "BINANCE:BNBUSDT",
    "SOLUSD":  "BINANCE:SOLUSDT",
    "EURUSD":  "OANDA:EURUSD",
    "GBPUSD":  "OANDA:GBPUSD",
    "USDJPY":  "OANDA:USDJPY",
    "USDCHF":  "OANDA:USDCHF",
    "AUDUSD":  "OANDA:AUDUSD",
    "USDCAD":  "OANDA:USDCAD",
    "NZDUSD":  "OANDA:NZDUSD",
    "EURGBP":  "OANDA:EURGBP",
    "EURJPY":  "OANDA:EURJPY",
    "GBPJPY":  "OANDA:GBPJPY",
    "NAS100":  "NASDAQ:NDX",
    "US30":    "DJ:DJI",
    "SP500":   "SP:SPX",
    "USOIL":   "NYMEX:CL1!",
}

_TV_REVERSE_MAP: dict[str, str] = {v: k for k, v in TV_SYMBOL_MAP.items()}

_TV_URL = "wss://data.tradingview.com/socket.io/websocket"
_PRICE_CACHE_TTL  = 600.0  # ثانية — TV يرسل عند التغيير فقط، 10 دقائق كافية للذهب/فوركس
_RECONNECT_DELAY  = 5.0    # ثوانٍ انتظار قبل إعادة الاتصال
_REFRESH_INTERVAL = 240.0  # ثانية — إعادة اشتراك دورية لإجبار TV على إرسال أحدث سعر (4 دقائق)


def _rand_session() -> str:
    return "qs_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12))


def _pack(func: str, args: list) -> str:
    """تغليف رسالة بتنسيق TradingView"""
    payload = json.dumps({"m": func, "p": args}, separators=(",", ":"))
    return f"~m~{len(payload)}~m~{payload}"


class TVPriceFeed:
    """
    خدمة أسعار TradingView — WebSocket مستمر مع إعادة اتصال تلقائية.

    النمط:
      - asyncio task خلفي واحد يحافظ على الاتصال
      - يُخزّن آخر سعر في dict مع timestamp
      - get_price() يُعيد السعر المخزّن (أو None إذا قديم / غير متاح)
      - يبدأ الاتصال عند أول طلب (lazy init)
    """

    def __init__(self):
        self._prices: dict[str, tuple[float, float]] = {}   # sym → (price, ts)
        self._task: Optional[asyncio.Task] = None
        self._started = False
        self._session: Optional[str] = None

    # ─── Public API ───────────────────────────────────────────────────────────

    async def get_price(self, symbol: str) -> Optional[float]:
        """
        يُعيد سعر Spot الحالي (خلال 3 ثوانٍ) أو None إذا غير متاح.
        يبدأ الاتصال تلقائياً في أول استدعاء.
        """
        self._ensure_started()
        sym = symbol.upper()
        entry = self._prices.get(sym)
        if entry:
            price, ts = entry
            if time.monotonic() - ts <= _PRICE_CACHE_TTL:
                return price
        # انتظر لحظة للتحديث إذا الاتصال طازج
        await asyncio.sleep(0.1)
        entry = self._prices.get(sym)
        if entry:
            price, ts = entry
            if time.monotonic() - ts <= _PRICE_CACHE_TTL:
                return price
        return None

    def get_price_sync(self, symbol: str) -> Optional[float]:
        """
        نسخة متزامنة (Sync) — للاستخدام من كود غير async.
        لا تبدأ الاتصال ولا تنتظر — فقط تُعيد ما هو مخزّن.
        """
        sym = symbol.upper()
        entry = self._prices.get(sym)
        if entry:
            price, ts = entry
            if time.monotonic() - ts <= _PRICE_CACHE_TTL:
                return price
        return None

    def is_alive(self) -> bool:
        return self._task is not None and not self._task.done()

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def _ensure_started(self):
        """يبدأ الـ task عند الحاجة فقط (lazy)"""
        if not self._started or (self._task and self._task.done()):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self._task = loop.create_task(self._run_forever())
                    self._started = True
            except RuntimeError:
                pass  # لا يوجد loop — سيُبدأ لاحقاً

    async def start(self):
        """يُستدعى من lifespan لبدء الاتصال مبكراً"""
        if not self._started:
            self._task = asyncio.create_task(self._run_forever())
            self._started = True
            logger.info("📡 TradingView price feed started")

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # ─── WebSocket Loop ───────────────────────────────────────────────────────

    async def _run_forever(self):
        """حلقة إعادة الاتصال — تعمل للأبد ما لم تُلغَ"""
        while True:
            try:
                await self._connect_and_stream()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"📡 TV WebSocket error: {e} — reconnecting in {_RECONNECT_DELAY}s")
                await asyncio.sleep(_RECONNECT_DELAY)

    async def _connect_and_stream(self):
        """الاتصال الفعلي وتدفق الأسعار"""
        import websockets

        self._session = _rand_session()
        headers = {
            "Origin": "https://www.tradingview.com",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        async with websockets.connect(
            _TV_URL,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            logger.success("📡 TradingView WebSocket connected")

            # ── إعداد الجلسة ─────────────────────────────────────────────
            await ws.send(_pack("set_auth_token", ["unauthorized_user_token"]))
            await ws.send(_pack("quote_create_session", [self._session]))
            await ws.send(_pack("quote_set_fields", [self._session, "lp", "ch", "chp"]))

            # ── الاشتراك في كل الرموز ─────────────────────────────────────
            for tv_sym in TV_SYMBOL_MAP.values():
                await ws.send(_pack("quote_add_symbols", [self._session, tv_sym]))
                await asyncio.sleep(0.02)  # تجنب rate limiting

            logger.info(f"📡 Subscribed to {len(TV_SYMBOL_MAP)} symbols")

            # ── حلقة الاستقبال مع refresh دوري ───────────────────────────
            last_refresh = asyncio.get_event_loop().time()
            async for raw_msg in ws:
                self._handle_message(ws, raw_msg)
                # كل 4 دقائق: إعادة اشتراك لإجبار TV على إرسال أحدث سعر
                now = asyncio.get_event_loop().time()
                if now - last_refresh >= _REFRESH_INTERVAL:
                    last_refresh = now
                    try:
                        for tv_sym in TV_SYMBOL_MAP.values():
                            await ws.send(_pack("quote_fast_symbols", [self._session, tv_sym]))
                            await asyncio.sleep(0.01)
                        logger.debug(f"📡 TV price refresh triggered for {len(TV_SYMBOL_MAP)} symbols")
                    except Exception as _ref_e:
                        logger.debug(f"📡 TV refresh error: {_ref_e}")

    def _handle_message(self, ws, raw: str):
        """معالجة رسالة واحدة من TradingView"""
        # Heartbeat — يجب الرد بنفس الرسالة
        if "~h~" in raw:
            # جدولة الرد بدون انتظار (الـ event loop يتولى ذلك)
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(ws.send(raw))
            except Exception:
                pass
            return

        # تحليل الرسائل المتعددة في نفس الحزمة
        parts = raw.split("~m~")
        # كل رسالة: ~m~{len}~m~{json} → parts = ['', len, json, len, json, ...]
        i = 2
        while i < len(parts):
            try:
                msg_text = parts[i]
                if not msg_text or msg_text.startswith("~h~"):
                    i += 2
                    continue
                msg = json.loads(msg_text)
                if msg.get("m") == "qsd":
                    self._extract_price(msg)
            except (json.JSONDecodeError, IndexError):
                pass
            i += 2

    def _extract_price(self, msg: dict):
        """استخراج السعر من رسالة qsd"""
        try:
            params = msg.get("p", [])
            if len(params) < 2:
                return
            data = params[1]
            tv_sym = data.get("n", "")
            status = data.get("s", "")
            if status != "ok":
                return
            v = data.get("v", {})
            lp = v.get("lp")
            if lp is None or float(lp) <= 0:
                return
            our_sym = _TV_REVERSE_MAP.get(tv_sym)
            if our_sym:
                self._prices[our_sym] = (float(lp), time.monotonic())
                logger.debug(f"📈 TV [{our_sym}]: {lp}")
        except Exception:
            pass


# ─── Singleton ───────────────────────────────────────────────────────────────
tv_feed = TVPriceFeed()
