# 🚀 دليل البدء السريع - Mosh AI Pro v5

## ⚡ التشغيل في 5 دقائق

### الطريقة 1: Docker (الأسهل)

```bash
# 1. Clone المشروع
git clone <repository_url>
cd mosh-ai-pro-v5

# 2. ضبط المتغيرات البيئية
cp backend/.env.example backend/.env
# افتح backend/.env وضع API Keys الخاصة بك

# 3. تشغيل كل شيء
docker-compose up -d

# ✅ Backend: http://localhost:8000
# ✅ Frontend: http://localhost:3000
# ✅ Database: localhost:5432
```

---

### الطريقة 2: Manual Setup

#### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Setup database
python -c "from app.database import init_db; init_db()"

# Run
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend

# Install
npm install

# Run
npm run dev
```

---

## 🔑 الحصول على API Keys

### TwelveData API
1. زر https://twelvedata.com
2. سجل حساب مجاني
3. انسخ API Key
4. ضعه في `.env` → `TWELVEDATA_API_KEY=...`

### Finnhub API (Optional)
1. https://finnhub.io
2. Free tier متاح
3. `FINNHUB_API_KEY=...`

### Telegram Bot
1. أرسل `/newbot` لـ @BotFather
2. احصل على Token
3. `TELEGRAM_BOT_TOKEN=...`

---

## 🧪 اختبار النظام

### Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# Analyze XAUUSD
curl -X POST "http://localhost:8000/api/v1/signals/analyze?symbol=XAUUSD&timeframe=1h&advanced_mode=true"

# Get latest signals
curl http://localhost:8000/api/v1/signals/latest?limit=5
```

### Test Frontend

افتح المتصفح: `http://localhost:3000`

---

## 📊 نتيجة التحليل المتوقعة

```json
{
  "symbol": "XAUUSD",
  "ai_confidence_score": 82.5,
  "recommendation": "BUY",
  "trend": {
    "direction": "BULLISH",
    "strength": 75
  },
  "premium_discount": {
    "current_zone": "DISCOUNT",
    "bias": "BULLISH"
  },
  "wyckoff_analysis": {
    "phase": "ACCUMULATION",
    "action": "PREPARE_BUY"
  },
  "liquidity_analysis": {
    "equal_highs": [2650.5],
    "equal_lows": [2625.3],
    "bias": {
      "direction": "BULLISH",
      "strength": 70
    }
  },
  "entry_zones": [2630.0],
  "stop_loss": 2620.0,
  "take_profits": [2642.0, 2658.0],
  "risk_reward": 2.4
}
```

---

## 🛠️ استكشاف الأخطاء

### Database Connection Error
```bash
# تأكد من تشغيل PostgreSQL
sudo systemctl start postgresql

# أو في Docker
docker-compose up postgres
```

### API Rate Limit
```bash
# TwelveData: 8 requests/minute (Free)
# احسب معدل الطلبات في .env
TWELVEDATA_RATE_LIMIT=8
```

### Frontend Not Loading
```bash
# Clear cache
rm -rf node_modules
npm install
npm run dev
```

---

## 📚 الخطوات التالية

1. ✅ اقرأ `README.md` للوثائق الكاملة
2. ✅ جرب تحليل أسواق مختلفة
3. ✅ عدّل استراتيجيات AI في `backend/app/services/`
4. ✅ طور Frontend Dashboard
5. ✅ أضف Telegram Bot

---

## 🎯 أمثلة عملية

### Python Example

```python
import requests

# Analyze market
response = requests.post(
    "http://localhost:8000/api/v1/signals/analyze",
    params={
        "symbol": "BTCUSD",
        "timeframe": "4h",
        "advanced_mode": True
    }
)

data = response.json()

print(f"AI Score: {data['data']['ai_confidence_score']}")
print(f"Signal: {data['data']['recommendation']}")
print(f"Entry: {data['data']['entry_zones']}")
print(f"SL: {data['data']['stop_loss_zone']}")
print(f"TP: {data['data']['take_profit_zones']}")
```

### JavaScript Example

```javascript
const analyzeMarket = async () => {
  const response = await fetch(
    'http://localhost:8000/api/v1/signals/analyze?symbol=EURUSD&timeframe=1h&advanced_mode=true',
    { method: 'POST' }
  )
  
  const data = await response.json()
  console.log('AI Analysis:', data)
}
```

---

## 💡 نصائح مهمة

1. **Rate Limiting**: Free APIs محدودة — استخدم Caching
2. **Database**: احفظ نسخ احتياطية من التحليلات
3. **Logs**: راجع الـ Logs في حال حدوث أخطاء
4. **Testing**: اختبر على Demo Account أولاً

---

**جاهز للتداول الذكي! 🚀**
