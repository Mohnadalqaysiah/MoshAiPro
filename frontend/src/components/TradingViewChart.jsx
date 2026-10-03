import { useEffect, useRef, useId } from 'react'
import { useLang } from '../contexts/LangContext'

// (2026-10-03) شارت TradingView الرسمي (Advanced Chart Widget) — عرض بصري
// بحت لا يلمس أي رقم عندنا. TradingView يرسم ويجلب بياناته بنفسه جوا
// الإطار الخاص فيه فقط؛ إشاراتنا (الدخول/الوقف/الأهداف/السعر الحالي
// المعروضة بمكان آخر بالصفحة) تبقى محسوبة ومعروضة تماماً كما هي الآن،
// من مصدرنا الخاص (tv_price_feed.py وغيره) بلا أي تغيير أو تفاعل مع هالمكوّن.
//
// نفس جدول الرموز المستخدَم فعلياً بـbackend/app/services/tv_price_feed.py
// (TV_SYMBOL_MAP) لموجز السعر الحي — مكرَّر هون عمداً (الفرونت بلا وصول
// لكود الباك-إند، نفس نمط تكرار _EXPIRY_HOURS بين bot.py وtelegram-bot/bot.py).
// لازم يبقى متطابقاً لو انضاف رمز جديد بالمصدر الأصلي.
const TV_SYMBOL_MAP = {
  XAUUSD: 'OANDA:XAUUSD', XAGUSD: 'OANDA:XAGUSD',
  BTCUSD: 'BINANCE:BTCUSDT', ETHUSD: 'BINANCE:ETHUSDT',
  BNBUSD: 'BINANCE:BNBUSDT', SOLUSD: 'BINANCE:SOLUSDT',
  XRPUSD: 'BINANCE:XRPUSDT', ADAUSD: 'BINANCE:ADAUSDT',
  DOGEUSD: 'BINANCE:DOGEUSDT',
  EURUSD: 'OANDA:EURUSD', GBPUSD: 'OANDA:GBPUSD', USDJPY: 'OANDA:USDJPY',
  USDCHF: 'OANDA:USDCHF', AUDUSD: 'OANDA:AUDUSD', USDCAD: 'OANDA:USDCAD',
  NZDUSD: 'OANDA:NZDUSD', EURGBP: 'OANDA:EURGBP', EURJPY: 'OANDA:EURJPY',
  GBPJPY: 'OANDA:GBPJPY',
  NAS100: 'NASDAQ:NDX', US30: 'DJ:DJI', SP500: 'SP:SPX', DXY: 'TVC:DXY',
  USOIL: 'NYMEX:CL1!', NATGAS: 'NYMEX:NG1!', BRENT: 'ICEEUR:LCO1!',
  XPTUSD: 'OANDA:XPTUSD', COPPER: 'COMEX:HG1!',
}

let scriptPromise = null
function loadTvScript() {
  if (window.TradingView) return Promise.resolve()
  if (scriptPromise) return scriptPromise
  scriptPromise = new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = 'https://s3.tradingview.com/tv.js'
    s.async = true
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
  return scriptPromise
}

export default function TradingViewChart({ symbol, height = 420 }) {
  const { lang } = useLang()
  const containerId = useId().replace(/:/g, '_')
  const widgetRef = useRef(null)

  const tvSymbol = TV_SYMBOL_MAP[(symbol || '').toUpperCase()]

  useEffect(() => {
    if (!tvSymbol) return
    let cancelled = false
    loadTvScript().then(() => {
      if (cancelled || !window.TradingView) return
      widgetRef.current = new window.TradingView.widget({
        container_id: containerId,
        symbol: tvSymbol,
        interval: '60',
        timezone: 'Etc/UTC',
        theme: 'dark',
        style: '1',
        locale: lang === 'ar' ? 'ar' : 'en',
        toolbar_bg: '#111827',
        autosize: true,
        hide_side_toolbar: true,
        allow_symbol_change: false,
        withdateranges: true,
      })
    }).catch(() => {})
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tvSymbol, containerId])

  if (!tvSymbol) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-500 bg-gray-900/50 rounded-xl" style={{ height }}>
        {lang === 'ar' ? 'لا يتوفر شارت لهذا الرمز حالياً' : 'Chart not available for this symbol yet'}
      </div>
    )
  }

  return (
    <div className="rounded-xl overflow-hidden border border-gray-700/60" style={{ height }}>
      <div id={containerId} className="w-full h-full" />
    </div>
  )
}
