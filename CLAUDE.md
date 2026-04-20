# CLAUDE.md — Mosh AI Pro v5

## نظرة عامة
منصة تداول ذكية متكاملة تجمع تحليل Smart Money Concepts مع Gemini AI.
تتكون من: Backend (FastAPI) + Frontend (React) + Telegram Bot + PostgreSQL + Redis.

---

## البنية والخدمات

```
backend/          FastAPI — المنطق الرئيسي، API، قاعدة البيانات
frontend/         React + Vite + Tailwind — لوحة التحكم
telegram-bot/     Python-telegram-bot — بوت تلغرام عربي
nginx/            Reverse proxy (system nginx على السيرفر، ليس Docker nginx)
```

---

## النشر على السيرفر

- السيرفر: `srv1263799` — مسار المشروع: `~/mosh-ai-pro`
- **system nginx** يتولى port 80/443 وSSL — **لا تشغّل Docker nginx**
- أسماء الـ containers: `moshapi_backend`, `moshapi_telegram`, `moshapi_postgres`, `moshapi_redis`, `moshapi_frontend`
- ملف الإعدادات: `backend/.env.prod`

### أوامر النشر الصحيحة
```bash
git pull origin main
docker compose -f docker-compose.prod.yml build --no-cache backend
docker compose -f docker-compose.prod.yml up -d backend
# لا تشغّل nginx من docker-compose
```

---

## الملفات المهمة

| الملف | الوظيفة |
|-------|---------|
| `backend/app/services/ai_engine_v5.py` | محرك التحليل الرئيسي |
| `backend/app/services/tv_price_feed.py` | أسعار TradingView WebSocket |
| `backend/app/services/chat_agent.py` | Gemini AI chat agent |
| `backend/app/api/bot.py` | API endpoints للبوت |
| `backend/app/api/admin.py` | لوحة الإدارة + إحصائيات الأداء |
| `backend/app/api/auth.py` | تسجيل المستخدمين + حدود التجربة |
| `telegram-bot/bot.py` | بوت تلغرام كامل |

---

## نظام الأسعار (Price Feed)

**سلسلة الفولباك:**
1. TradingView WebSocket (OANDA Spot) — `tv_feed` singleton
2. yfinance `XAUUSD=X` / `XAGUSD=X` — OTC Spot مباشر
3. theoretical_carry (أقل دقة، تجنّب إن أمكن)
4. currency-api / Finnhub

**إعدادات مهمة في `tv_price_feed.py`:**
- `_PRICE_CACHE_TTL = 600.0` — 10 دقائق (الذهب لا يتحرك كل ثانية)
- `_REFRESH_INTERVAL = 240.0` — refresh كل 4 دقائق بـ `quote_add_symbols`
- yfinance fallback في `get_price_sync()` عند انتهاء الكاش

---

## نظام التجربة المجانية (Trial)

- `trial_analyses_left` / `trial_chat_left` في جدول `users`
- الحدود تُقرأ من `SiteSettings` (مش hardcoded): مفاتيح `trial_analysis_limit` / `trial_chat_limit`
- عند استنفاد الكريدت → 403 → Frontend يعرض "اشترك الآن"
- تجديد شهري: يقرأ الحدود من SiteSettings

---

## قفل الاتجاه (Direction Lock)

في `telegram-bot/bot.py`:
- `DIRECTION_LOCK_MIN = 240` (4 ساعات)
- `last_alert[(uid, symbol)] = {"time": datetime, "direction": str}`
- منطق: نفس الاتجاه → `ALERT_COOLDOWN`، اتجاه معاكس → `DIRECTION_LOCK_MIN`
- ينطبق على: مراقبة الـ watchlist + broadcast الإشارات الجديدة

---

## الـ Watchlist

- `_VALID_SYMBOLS` = تقاطع كل رموز `CATEGORIES` الحالية
- تصفية عند التحميل من DB وعند المراقبة
- كل تغيير يستدعي `await _save_wl_to_db(uid, tgid)` فوراً

---

## حساب النقاط (_calc_points في admin.py)

| النوع | المضاعف |
|-------|---------|
| معادن (XAUUSD, XAGUSD...) | ×10 |
| كريبتو | ×1.0 |
| مؤشرات (NAS100, US30, SP500) | ×1.0 |
| نفط (USOIL, BRENT) | ×10 |
| JPY pairs | ×100 |
| فوركس عادي | ×10000 |

---

## Gemini API

- يستخدم HTTP مباشر (لا مكتبة Python) إلى `generativelanguage.googleapis.com`
- المفتاح في `.env.prod`: `GEMINI_API_KEY`
- نموذج: `gemini-2.0-flash`
- خطأ 429 = rate limit مؤقت (طبيعي في الخطة المجانية) — المفتاح صالح

---

## ملاحظات مهمة

- **لا تشغّل Docker nginx** — system nginx هو المسؤول عن SSL وport 80
- عند `docker compose up` كامل → أضف `--scale nginx=0` أو أبعد nginx من الأمر
- الـ backend يعمل على port `127.0.0.1:8000` (يصل إليه system nginx مباشرة)
