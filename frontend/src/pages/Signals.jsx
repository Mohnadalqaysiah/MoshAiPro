import { useState } from 'react'
import axios from 'axios'
import { Zap, RefreshCw, AlertCircle, Calculator } from 'lucide-react'
import useMarkets from '../hooks/useMarkets'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TIMEFRAMES = ['15m', '1h', '4h', '1day']

const T = {
  ar: {
    title: 'تحليل الإشارات', sub: 'تحليل متقدم بمحرك الذكاء الاصطناعي v5',
    market: 'السوق', timeframe: 'الإطار الزمني', analyze: 'تحليل الآن', analyzing: 'جاري التحليل...',
    conf: 'نسبة الثقة', currentPrice: 'السعر الحالي', entryZone: 'منطقة الدخول',
    sl: 'وقف الخسارة', tp1: 'هدف 1', tp2: 'هدف 2', tp3: 'هدف 3',
    rr: 'Risk/Reward', lot: 'حجم اللوت', balanceRisk: 'البالانس / المخاطرة',
    entryLevels: 'مستويات الدخول', analysis: 'تفاصيل التحليل',
    trend: 'الاتجاه', zone: 'المنطقة', liquidity: 'السيولة',
    buy: 'شراء', sell: 'بيع', watch: 'مراقبة',
    futuresWarn: '⚠️ السعر من عقود الآجل — قد يختلف ±5 نقاط عن سعر Spot في منصتك',
  },
  en: {
    title: 'Signal Analysis', sub: 'Advanced analysis powered by AI Engine v5',
    market: 'Market', timeframe: 'Timeframe', analyze: 'Analyze Now', analyzing: 'Analyzing...',
    conf: 'Confidence', currentPrice: 'Current Price', entryZone: 'Entry Zone',
    sl: 'Stop Loss', tp1: 'Target 1', tp2: 'Target 2', tp3: 'Target 3',
    rr: 'Risk/Reward', lot: 'Lot Size', balanceRisk: 'Balance / Risk',
    entryLevels: 'Entry Levels', analysis: 'Analysis Details',
    trend: 'Trend', zone: 'Zone', liquidity: 'Liquidity',
    buy: 'BUY', sell: 'SELL', watch: 'WATCH',
    futuresWarn: '⚠️ Price from futures contracts — may differ ±5 pips from Spot on your platform',
  },
}

export default function Signals() {
  const { markets } = useMarkets()
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'
  const [symbol, setSymbol] = useState('XAUUSD')
  const [timeframe, setTimeframe] = useState('1h')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const analyze = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await axios.post(`${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=${timeframe}&advanced_mode=true`)
      setResult(res.data.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const rec = result?.recommendation
  const recColors = { BUY: 'text-green-400', SELL: 'text-red-400', WATCH: 'text-gray-400' }
  const recBgs = { BUY: 'bg-green-900/20 border-green-600', SELL: 'bg-red-900/20 border-red-600', WATCH: 'bg-gray-700 border-gray-600' }
  const recLabel = { BUY: tx.buy, SELL: tx.sell, WATCH: tx.watch }

  return (
    <div className="space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      <div>
        <h1 className="text-2xl font-bold text-white">{tx.title}</h1>
        <p className="text-gray-400 text-sm mt-1">{tx.sub}</p>
      </div>

      {/* Controls */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-gray-400 text-sm mb-2 block" htmlFor="sig-market">{tx.market}</label>
            <select
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm"
            >
              {markets.map(m => <option key={m.symbol} value={m.symbol}>{m.symbol} — {m.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-sm mb-2 block">{tx.timeframe}</label>
            <select
              value={timeframe}
              onChange={e => setTimeframe(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm"
            >
              {TIMEFRAMES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={analyze}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? <><RefreshCw size={14} className="animate-spin" /> {tx.analyzing}</> : <><Zap size={14} /> {tx.analyze}</>}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-900/30 border border-red-700 rounded-xl text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Main Signal */}
          <div className={`border rounded-xl p-6 ${recBgs[rec] || 'bg-gray-800 border-gray-700'}`}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-gray-400 text-sm">{symbol} / {timeframe}</span>
                <div className={`text-3xl font-bold mt-1 ${recColors[rec] || 'text-gray-400'}`}>
                  {recLabel[rec] || rec}
                </div>
              </div>
              <div className="text-right">
                <div className="text-gray-400 text-sm">{tx.conf}</div>
                <div className="text-3xl font-bold text-white">{result.ai_confidence_score?.toFixed(1)}%</div>
              </div>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Entry / SL / TP */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <h3 className="text-white font-semibold mb-3">{tx.entryLevels}</h3>
              <div className="space-y-2 text-sm">
                {/* السعر الفوري الحالي */}
                {result.current_price != null && (
                  <div className="pb-2 border-b border-gray-700 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-400 flex items-center gap-1.5">
                        {tx.currentPrice}
                        {result.price_source === 'finnhub_spot'
                          ? <span className="text-green-500 text-xs font-medium">● spot</span>
                          : result.price_source?.includes('futures')
                            ? <span className="text-yellow-600 text-xs">● futures</span>
                            : <span className="text-blue-500 text-xs">● live</span>
                        }
                      </span>
                      <span className="text-blue-300 font-mono font-semibold">
                        {typeof result.current_price === 'number'
                          ? result.current_price.toFixed(symbol === 'BTCUSD' ? 2 : 5)
                          : result.current_price}
                        {result.price_fetched_at && (
                          <span className="text-gray-600 text-xs mr-1">
                            ({new Date(result.price_fetched_at).toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' })})
                          </span>
                        )}
                      </span>
                    </div>
                    {result.price_source?.includes('futures') && (
                      <p className="text-xs text-yellow-700/80 text-right">
                        {tx.futuresWarn}
                      </p>
                    )}
                  </div>
                )}
                {/* منطقة الدخول من ICT engine */}
                {(result.levels?.entry_zone_min || result.levels?.entry) && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.entryZone}</span>
                    <span className="text-white font-mono">
                      {result.levels.entry_zone_min && result.levels.entry_zone_max
                        ? `${result.levels.entry_zone_min} — ${result.levels.entry_zone_max}`
                        : result.levels.entry}
                    </span>
                  </div>
                )}
                {/* منطقة الدخول من Gemini (القديم) */}
                {!result.levels?.entry && result.entry_zones?.map((e, i) => (
                  <div key={i} className="flex justify-between">
                    <span className="text-gray-400">منطقة دخول {i+1}</span>
                    <span className="text-white font-mono">{e}</span>
                  </div>
                ))}
                {/* SL */}
                {(result.levels?.stop_loss || result.stop_loss_zone) && (
                  <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                    <span className="text-gray-400">{tx.sl}</span>
                    <span className="text-red-400 font-mono">{result.levels?.stop_loss || result.stop_loss_zone}</span>
                  </div>
                )}
                {/* TP من ICT engine */}
                {result.levels?.tp1 && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-400">{tx.tp1}</span>
                      <span className="text-green-400 font-mono">{result.levels.tp1}</span>
                    </div>
                    {result.levels.tp2 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">{tx.tp2}</span>
                        <span className="text-green-300 font-mono">{result.levels.tp2}</span>
                      </div>
                    )}
                    {result.levels.tp3 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">{tx.tp3}</span>
                        <span className="text-green-200 font-mono">{result.levels.tp3}</span>
                      </div>
                    )}
                  </>
                )}
                {/* TP من Gemini (القديم) */}
                {!result.levels?.tp1 && result.take_profit_zones?.map((tp, i) => (
                  <div key={i} className="flex justify-between">
                    <span className="text-gray-400">هدف {i+1}</span>
                    <span className="text-green-400 font-mono">{tp}</span>
                  </div>
                ))}
                {(result.risk_reward || result.levels?.risk_reward) && (
                  <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                    <span className="text-gray-400">Risk/Reward</span>
                    <span className="text-blue-400 font-mono">
                      {((result.levels?.risk_reward ?? result.risk_reward) || 0).toFixed(2)}x
                    </span>
                  </div>
                )}
                {result.lot_size && (
                  <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                    <span className="text-gray-400 flex items-center gap-1">
                      <Calculator size={12} /> {tx.lot}
                    </span>
                    <span className="text-yellow-400 font-mono font-semibold">{result.lot_size}</span>
                  </div>
                )}
                {result.account_balance && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">{tx.balanceRisk}</span>
                    <span className="text-gray-500">${result.account_balance} · {result.risk_percent}%</span>
                  </div>
                )}
              </div>
            </div>

            {/* Analysis */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <h3 className="text-white font-semibold mb-3">{tx.analysis}</h3>
              <div className="space-y-2 text-sm">
                {result.trend && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.trend}</span>
                    <span className="text-white">{result.trend.direction} ({result.trend.strength}%)</span>
                  </div>
                )}
                {result.wyckoff_analysis?.phase && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Wyckoff</span>
                    <span className="text-white">{result.wyckoff_analysis.phase}</span>
                  </div>
                )}
                {result.premium_discount?.current_zone && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.zone}</span>
                    <span className="text-white">{result.premium_discount.current_zone}</span>
                  </div>
                )}
                {result.killzone?.name && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Kill Zone</span>
                    <span className="text-white">{result.killzone.name}</span>
                  </div>
                )}
                {result.liquidity_analysis?.bias?.direction && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.liquidity}</span>
                    <span className="text-white">{result.liquidity_analysis.bias.direction}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
