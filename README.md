# Mosh AI Pro v5 — منصة تداول ذكية متكاملة

نظام تحليل أسواق مالية يجمع **Smart Money Concepts** مع **Gemini AI**، مع واجهة ويب وبوت تلغرام عربي.

---

## المكونات

| المكون | التقنية | الحالة |
|--------|---------|--------|
| Backend API | FastAPI + PostgreSQL + Redis | ✅ |
| AI Engine v5 | SMC Analysis (OB, FVG, BOS, Wyckoff...) | ✅ |
| Chat Agent | Gemini 2.0 Flash | ✅ |
| Price Feed | TradingView WebSocket (OANDA Spot) | ✅ |
| Frontend | React + Vite + Tailwind | ✅ |
| Telegram Bot | python-telegram-bot (عربي) | ✅ |
| نظام التجربة | trial_analyses + trial_chat مع upgrade prompt | ✅ |
| قفل الاتجاه | Direction lock 4 ساعات (BUY↔SELL) | ✅ |

---

## البنية

```
mosh-ai-pro-v5/
├── backend/
│   ├── app/
│   │   ├── api/          # bot.py, admin.py, auth.py, signals.py...
│   │   ├── services/     # ai_engine_v5.py, chat_agent.py, tv_price_feed.py...
│   │   └── models/       # user.py, signal.py, site_settings.py...
│   ├── Dockerfile
│   └── .env.prod         # على السيرفر فقط
├── frontend/
├── telegram-bot/
│   └── bot.py
├── nginx/
│   └── nginx.conf
├── docker-compose.prod.yml
└── CLAUDE.md             # سياق للمطور + Claude Code
```

---

## النشر (Production)

السيرفر يستخدم **system nginx** لإدارة SSL وport 80 — لا يُشغَّل Docker nginx.

```bash
# على السيرفر
git pull origin main

# إعادة بناء backend فقط
docker compose -f docker-compose.prod.yml build --no-cache backend
docker compose -f docker-compose.prod.yml up -d backend

# تحقق من الحالة
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### الـ containers
```
moshapi_backend    ← FastAPI (127.0.0.1:8000)
moshapi_frontend   ← React  (127.0.0.1:8080)
moshapi_telegram   ← Telegram Bot
moshapi_postgres   ← PostgreSQL
moshapi_redis      ← Redis
```

---

## المتغيرات البيئية (backend/.env.prod)

```bash
DATABASE_URL=postgresql://user:pass@postgres:5432/moshaiprodb
REDIS_URL=redis://redis:6379/0
SECRET_KEY=...

# APIs
GEMINI_API_KEY=...          # aistudio.google.com
TWELVEDATA_API_KEY=...
FINNHUB_API_KEY=...
TELEGRAM_BOT_TOKEN=...

# الموقع
FRONTEND_URL=https://your-domain.com
```

---

## الأسعار

سلسلة الفولباك لضمان دقة السعر:
1. **TradingView WebSocket** (OANDA Spot) — مستمر مع كاش 10 دقائق
2. **yfinance** `XAUUSD=X` — OTC Spot مباشر عند انتهاء الكاش
3. **theoretical_carry** — fallback أخير (أقل دقة)

---

## نظام التجربة المجانية

- كل مستخدم جديد يحصل على عدد محدد من التحليلات والمحادثات
- الحدود تُضبط من لوحة الإدارة → Site Settings (`trial_analysis_limit` / `trial_chat_limit`)
- عند الاستنفاد → 403 → يظهر زر "اشترك الآن"

---

## الأسواق المدعومة

**معادن:** XAUUSD, XAGUSD  
**كريبتو:** BTCUSD, ETHUSD, BNBUSD, SOLUSD  
**فوركس:** EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP, EURJPY, GBPJPY  
**مؤشرات:** NAS100, US30, SP500  
**نفط:** USOIL

---

## تشخيص المشاكل

```bash
# logs الـ backend
docker logs moshapi_backend --tail=50 -f

# اختبار Gemini API
docker exec moshapi_backend python3 -c "
import urllib.request, json, os
key = os.environ.get('GEMINI_API_KEY','')
url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}'
data = json.dumps({'contents':[{'parts':[{'text':'hi'}]}]}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=10) as r:
    print('OK:', json.loads(r.read())['candidates'][0]['content']['parts'][0]['text'][:50])
"

# إذا nginx يتعطل
systemctl start nginx   # system nginx هو الصحيح
docker stop moshapi_nginx
```

---

**Built by MoshDev / Mohannad Algaisiah**  
للدعم: Telegram @MoshAI_Support
