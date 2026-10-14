"""
(2026-10-14) تشخيص مباشر: لماذا لا يصدر المحرك إشارة الآن لرمز معيّن؟

بلاغ: الذهب أعطى إشارة واحدة منذ الاثنين (كان 3.4/يوم قبل فلاتر 10/10). سجلات الحاوية لا تحتفظ
بتفاصيل التحليل (مستوى السجل) وتُمسح بكل إعادة نشر، فنحلّل **الآن** ونطبع قرار كل فريم وسببه.
لا يحفظ أي إشارة ولا يرسل شيئاً (analyze_market وحده لا يحفظ — الحفظ بمسارات API فقط).

    docker exec moshapi_backend python diag_why_no_signal.py [الرموز=XAUUSD,XAGUSD]
"""
import sys
import asyncio

SYMS = [s.strip().upper() for s in (sys.argv[1] if len(sys.argv) > 1 else "XAUUSD,XAGUSD").split(",")]


async def main():
    from app.services.ai_engine_v5 import mosh_ai_engine_v5 as E
    for sym in SYMS:
        res = await E.analyze_market_multi_tf(sym, ["15m", "1h", "4h"], force_refresh=True)
        print(f"══ {sym} ══  السعر: {next((r.get('current_price') for r in res.values() if r.get('current_price')), '?')}")
        for tf, a in res.items():
            cal = a.get("calibration_params") or {}
            lv = a.get("levels") or {}
            pre = a.get("_pre_reject_rec")
            print(f"  {tf:<4} القرار: {a.get('recommendation')}"
                  + (f" (كان {pre} ورُفض)" if pre and pre != a.get('recommendation') else "")
                  + f" | السبب: {a.get('rejection_reason') or a.get('no_trade_reason') or '—'}")
            print(f"       اتجاه 4h: {a.get('commodity_4h_trend', '—')} | هيكل الفريم: {(a.get('market_structure') or {}).get('trend')}"
                  f" | HTF: {(a.get('htf_context') or {}).get('trend')} | حالة السوق: {cal.get('market_state')} / تقلب {cal.get('volatility')}"
                  f" | ثقة {a.get('ai_confidence_score')}")
            if a.get("recommendation") in ("BUY", "SELL"):
                print(f"       ✅ إشارة: دخول {lv.get('entry')} وقف {lv.get('stop_loss')} TP1 {lv.get('tp1')} TP2 {lv.get('tp2')}"
                      + (" (TP1 قُرّب لـ1R)" if a.get("tp1_capped") else ""))
        print()


if __name__ == "__main__":
    asyncio.run(main())
