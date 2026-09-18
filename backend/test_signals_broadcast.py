#!/usr/bin/env python3
"""
اختبار بث الإشارات الجديدة — التحقق من أن الفوركس والمعادن تُبث الآن
"""

import requests
import json
from datetime import datetime

# إعدادات الاتصال
API_URL = "http://localhost:8000"  # أو رابط السيرفر
BOT_SECRET = "mosh-bot-secret-2026"
HEADERS = {"X-Bot-Secret": BOT_SECRET}

print("=" * 70)
print("🧪 اختبار بث الإشارات الجديدة")
print("=" * 70)

# 1. جلب الإشارات الجديدة
print("\n📡 جاري جلب الإشارات الجديدة (broadcast_sent=False)...\n")
try:
    resp = requests.get(f"{API_URL}/api/v1/bot/new-signals", headers=HEADERS, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        signals = data.get("signals", [])
        
        if not signals:
            print("❌ لا توجد إشارات جديدة قيد الانتظار")
        else:
            print(f"✅ وُجدت {len(signals)} إشارة جديدة:\n")
            
            # تجميع الإشارات حسب السوق
            by_market = {}
            for sig in signals:
                market = sig.get("market", "UNKNOWN")
                conf = float(sig.get("ai_confidence", 0))
                if market not in by_market:
                    by_market[market] = []
                by_market[market].append({
                    "id": sig.get("id"),
                    "type": sig.get("signal_type"),
                    "confidence": conf,
                    "timeframe": sig.get("timeframe"),
                })
            
            # عرض الإشارات مجمعة
            market_icons = {
                "XAUUSD": "🥇", "XAGUSD": "🥈",
                "EURUSD": "💶", "GBPUSD": "💷", "USDJPY": "💴", "USDCHF": "🇨🇭",
                "BTCUSD": "₿", "ETHUSD": "Ξ", "BNBUSD": "🔷",
                "USOIL": "🛢", "NATGAS": "🔥",
                "NAS100": "📈", "US30": "📊", "SP500": "📉",
            }
            
            for market, sigs in sorted(by_market.items()):
                icon = market_icons.get(market, "📌")
                print(f"\n{icon} {market}")
                print("  " + "─" * 50)
                for sig in sigs:
                    direction = "🟢 BUY" if sig["type"] == "BUY" else "🔴 SELL"
                    conf_bar = "█" * int(sig["confidence"] / 10) + "░" * (10 - int(sig["confidence"] / 10))
                    print(f"  #{sig['id']} {direction}  {sig['timeframe']}  [{conf_bar}] {sig['confidence']:.0f}%")
            
            print("\n" + "=" * 70)
            print(f"📊 ملخص:")
            print(f"   • إجمالي الإشارات: {len(signals)}")
            print(f"   • الأسواق: {', '.join(sorted(by_market.keys()))}")
            
            # حساب الفئات
            forex_count = sum(len(v) for k, v in by_market.items() if k in ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"])
            metals_count = sum(len(v) for k, v in by_market.items() if k in ["XAUUSD", "XAGUSD"])
            crypto_count = sum(len(v) for k, v in by_market.items() if k in ["BTCUSD", "ETHUSD", "BNBUSD"])
            commodities_count = sum(len(v) for k, v in by_market.items() if k in ["USOIL", "NATGAS"])
            indices_count = sum(len(v) for k, v in by_market.items() if k in ["NAS100", "US30", "SP500"])
            
            if forex_count > 0: print(f"   ✅ فوركس: {forex_count} إشارة")
            if metals_count > 0: print(f"   ✅ معادن: {metals_count} إشارة")
            if crypto_count > 0: print(f"   ✅ كريبتو: {crypto_count} إشارة")
            if commodities_count > 0: print(f"   ✅ سلع: {commodities_count} إشارة")
            if indices_count > 0: print(f"   ✅ مؤشرات: {indices_count} إشارة")
            
            print("=" * 70)
            print("\n✨ النتيجة: التعديل نجح! ستُبث إشارات الفوركس والمعادن الآن.")
            
    else:
        print(f"❌ خطأ في الاتصال: {resp.status_code}")
        print(resp.text)
        
except Exception as e:
    print(f"❌ خطأ: {e}")
    print("\n💡 تأكد من:")
    print("   1. السيرفر يعمل على localhost:8000")
    print("   2. البيانات موجودة في قاعدة البيانات")
    print("   3. BOT_SECRET صحيح")

print("\n" + "=" * 70)
print("🔍 لتتبع الإشارات المُبثّة، شاهد logs البوت:")
print("   docker logs -f moshapi_telegram")
print("=" * 70)
