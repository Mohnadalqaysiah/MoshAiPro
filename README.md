# 🚀 Mosh AI Pro v5 - Advanced Trading Analysis System

## 📌 نظرة عامة

**Mosh AI Pro v5** هو نظام تداول ذكي متكامل يجمع بين:
- ✅ **محرك ذكاء اصطناعي متقدم** (AI Engine v5)
- ✅ **استراتيجيات Smart Money Concepts** (SMC)
- ✅ **تحليل Wyckoff Cycles**
- ✅ **Equal Highs/Lows Liquidity Detection**
- ✅ **Premium/Discount Zones**
- ✅ **Volume Intelligence**
- ✅ **Killzones Timing**
- ✅ **BOS Analysis** (Internal/External)
- ✅ **Breaker Blocks Detection**
- ✅ **Backend API** (FastAPI)
- ✅ **Telegram Bot** (Arabic Interface)
- ✅ **Web Dashboard** (React)

---

## 🏗️ المعمارية الكاملة

```
┌────────────────────────────────────────────────────────────┐
│                    MOSH AI PRO V5                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │ Telegram │◄──►│ Web App  │◄──►│ REST API │           │
│  │   Bot    │    │Dashboard │    │ Backend  │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│                                        │                  │
│                        ┌───────────────┴────────┐         │
│                        │   AI ENGINE v5         │         │
│                        │  (Smart Money Core)    │         │
│                        └───────────┬────────────┘         │
│                                    │                      │
│  ┌────────────┬──────────┬─────────┴─────┬────────────┐  │
│  │  Wyckoff   │Liquidity │Premium/       │ Killzones  │  │
│  │  Cycles    │ Engine   │Discount       │  Timing    │  │
│  └────────────┴──────────┴───────────────┴────────────┘  │
│                                                            │
│  ┌────────────┬──────────┬───────────┬──────────────┐    │
│  │   Volume   │   BOS    │ Breaker   │ Time/Price   │    │
│  │   Intel    │ Analyzer │  Blocks   │   Theory     │    │
│  └────────────┴──────────┴───────────┴──────────────┘    │
│                                                            │
│                   ┌──────────────────┐                    │
│                   │  PostgreSQL DB   │                    │
│                   └──────────────────┘                    │
└────────────────────────────────────────────────────────────┘
```

---

## 📦 الميزات الرئيسية

### 🤖 محرك الذكاء الاصطناعي v5

1. **Wyckoff Cycle Analysis**
   - Accumulation Detection
   - Distribution Detection
   - Markup/Markdown Phases
   - Spring & Upthrust Events

2. **Premium/Discount Zones**
   - Fibonacci 50% Analysis
   - Buy/Sell Zone Detection
   - Equilibrium Identification

3. **Advanced Liquidity Engine**
   - Equal Highs Detection
   - Equal Lows Detection
   - Liquidity Pools Mapping
   - Liquidity Grabs/Sweeps

4. **Volume Intelligence**
   - Volume Profile (POC, VAH, VAL)
   - Volume Delta Analysis
   - Volume Climax Detection
   - Buy/Sell Pressure

5. **Killzones Timing**
   - Asia Session (00:00-08:00 UTC)
   - London Session (08:00-16:00 UTC)
   - New York Session (13:00-22:00 UTC)
   - Optimal Entry Times

6. **BOS (Break of Structure)**
   - Internal BOS
   - External BOS
   - CHoCH (Change of Character)

7. **Breaker Blocks**
   - Failed Order Blocks
   - Mitigation Zones
   - Rejection Blocks

---

## 🛠️ التثبيت والإعداد

### المتطلبات الأساسية

- Python 3.10+
- PostgreSQL 14+
- Node.js 18+
- Redis (اختياري للكاشينج)

### 1️⃣ Backend Setup

```bash
# Clone repository
git clone <repository_url>
cd mosh-ai-pro-v5/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# ✏️ Edit .env with your API keys and database config

# Initialize database
python -c "from app.database import init_db; init_db()"

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2️⃣ Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### 3️⃣ Telegram Bot Setup

```bash
cd ../telegram-bot

# Install dependencies
pip install -r requirements.txt

# Setup bot token in .env
# Run bot
python bot.py
```

---

## 🔑 إعدادات البيئة (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/moshaiprodb

# API Keys
TWELVEDATA_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Security
SECRET_KEY=your-secret-key-change-in-production

# AI Engine Features (Enable/Disable)
ENABLE_WYCKOFF_ANALYSIS=True
ENABLE_LIQUIDITY_ENGINE=True
ENABLE_VOLUME_INTELLIGENCE=True
ENABLE_KILLZONES=True
ENABLE_PREMIUM_DISCOUNT=True
ENABLE_BREAKER_BLOCKS=True
```

---

## 📡 API Endpoints

### Signals

```bash
# Analyze Market
POST /api/v1/signals/analyze
{
  "symbol": "XAUUSD",
  "timeframe": "1h",
  "advanced_mode": true
}

# Get Latest Signals
GET /api/v1/signals/latest?limit=10

# Get Signal Details
GET /api/v1/signals/{signal_id}
```

### Markets

```bash
# List Supported Markets
GET /api/v1/markets/list

# Get Current Price
GET /api/v1/markets/{symbol}/price

# Get Candle Data
GET /api/v1/markets/{symbol}/candles?interval=1h&limit=100
```

### Analytics

```bash
# Performance Metrics
GET /api/v1/analytics/performance

# Market Statistics
GET /api/v1/analytics/market/{market}/stats
```

---

## 🎯 كيفية الاستخدام

### عبر API

```python
import requests

# Analyze Gold Market
response = requests.post(
    "http://localhost:8000/api/v1/signals/analyze",
    params={
        "symbol": "XAUUSD",
        "timeframe": "1h",
        "advanced_mode": True
    }
)

analysis = response.json()
print(f"AI Score: {analysis['data']['ai_confidence_score']}")
print(f"Recommendation: {analysis['data']['recommendation']}")
```

### عبر Telegram Bot

```
/start - بدء البوت
/market - اختيار السوق
/analyze - تحليل السوق الحالي
/settings - الإعدادات
```

### عبر Web Dashboard

1. افتح المتصفح: `http://localhost:3000`
2. اختر السوق من القائمة
3. شاهد التحليل الفوري
4. استعرض التوصيات النشطة

---

## 📊 مثال على النتائج

```json
{
  "symbol": "XAUUSD",
  "ai_confidence_score": 85.4,
  "recommendation": "BUY",
  "trend": {
    "direction": "BULLISH",
    "strength": 78
  },
  "premium_discount": {
    "current_zone": "DISCOUNT",
    "recommendation": "STRONG_BUY_ZONE"
  },
  "wyckoff_analysis": {
    "phase": "ACCUMULATION",
    "action": "PREPARE_BUY"
  },
  "liquidity_analysis": {
    "equal_highs": [2650.5, 2652.3],
    "equal_lows": [2625.8, 2626.1],
    "liquidity_grabs": [
      {
        "type": "SELL_SIDE_GRAB",
        "direction": "BULLISH"
      }
    ]
  },
  "killzones": {
    "current_session": "LONDON",
    "is_optimal_time": true
  },
  "entry_zones": [2630.5],
  "stop_loss": 2620.0,
  "take_profits": [2640.0, 2655.0],
  "risk_reward": 2.5
}
```

---

## 🔧 التطوير المتقدم

### إضافة سوق جديد

1. افتح `app/config.py`
2. أضف السوق في `MARKET_CONFIG`:

```python
"ETHUSD": {
    "name": "Ethereum",
    "name_ar": "الإيثيريوم",
    "symbol": "ETH/USD",
    "tick_size": 0.01,
    "min_move": 1.0
}
```

### تعديل الاستراتيجيات

كل استراتيجية في ملف منفصل:
- `wyckoff_engine.py`
- `premium_discount.py`
- `liquidity_engine_v2.py`
- `volume_intelligence_v2.py`
- `killzones_engine.py`
- `bos_analyzer.py`
- `breaker_blocks.py`

---

## 📈 خارطة الطريق المستقبلية

- [ ] Auto-Trading Integration (MT5/Binance)
- [ ] Mobile App (React Native)
- [ ] TradingView Webhooks
- [ ] Multi-Language Support
- [ ] Backtesting Engine
- [ ] ML Model Training Pipeline
- [ ] Risk Management Dashboard
- [ ] Social Trading Features

---

## 🤝 المساهمة

لتقديم مساهمات:
1. Fork المشروع
2. أنشئ branch جديد
3. قم بالتعديلات
4. أرسل Pull Request

---

## 📄 الترخيص

هذا المشروع مملوك لـ **MoshDev / Mohannad Algaisiah**

---

## 📞 الدعم والتواصل

- **Twitter/X**: @MoshDev
- **Email**: support@moshdev.com
- **Telegram**: @MoshAI_Support

---

## ⚠️ تنويه

هذا النظام مصمم **للأغراض التعليمية والتحليلية فقط**.
التداول في الأسواق المالية يحمل مخاطر عالية.
استخدم النظام على مسؤوليتك الخاصة.

---

**Built with ❤️ by MoshDev**
