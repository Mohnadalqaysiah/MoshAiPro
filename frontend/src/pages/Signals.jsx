import { useState } from 'react'
import axios from 'axios'
import { Zap, RefreshCw, AlertCircle } from 'lucide-react'

const API = 'http://localhost:8000'
const MARKETS = ['XAUUSD', 'BTCUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
const TIMEFRAMES = ['15m', '1h', '4h', '1day']

export default function Signals() {
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
  const recAr = { BUY: 'شراء', SELL: 'بيع', WATCH: 'مراقبة' }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">تحليل الإشارات</h1>
        <p className="text-gray-400 text-sm mt-1">تحليل متقدم بمحرك الذكاء الاصطناعي v5</p>
      </div>

      {/* Controls */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-gray-400 text-sm mb-2 block">السوق</label>
            <select
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm"
            >
              {MARKETS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-sm mb-2 block">الإطار الزمني</label>
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
              {loading ? <><RefreshCw size={14} className="animate-spin" /> جاري التحليل...</> : <><Zap size={14} /> تحليل الآن</>}
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
                  {recAr[rec] || rec}
                </div>
              </div>
              <div className="text-right">
                <div className="text-gray-400 text-sm">نسبة الثقة</div>
                <div className="text-3xl font-bold text-white">{result.ai_confidence_score?.toFixed(1)}%</div>
              </div>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Entry / SL / TP */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <h3 className="text-white font-semibold mb-3">مستويات الدخول</h3>
              <div className="space-y-2 text-sm">
                {result.entry_zones?.map((e, i) => (
                  <div key={i} className="flex justify-between">
                    <span className="text-gray-400">منطقة دخول {i+1}</span>
                    <span className="text-white font-mono">{e}</span>
                  </div>
                ))}
                {result.stop_loss_zone && (
                  <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                    <span className="text-gray-400">وقف الخسارة</span>
                    <span className="text-red-400 font-mono">{result.stop_loss_zone}</span>
                  </div>
                )}
                {result.take_profit_zones?.map((tp, i) => (
                  <div key={i} className="flex justify-between">
                    <span className="text-gray-400">هدف {i+1}</span>
                    <span className="text-green-400 font-mono">{tp}</span>
                  </div>
                ))}
                {result.risk_reward && (
                  <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                    <span className="text-gray-400">Risk/Reward</span>
                    <span className="text-blue-400 font-mono">{result.risk_reward?.toFixed(2)}x</span>
                  </div>
                )}
              </div>
            </div>

            {/* Analysis */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <h3 className="text-white font-semibold mb-3">تفاصيل التحليل</h3>
              <div className="space-y-2 text-sm">
                {result.trend && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">الاتجاه</span>
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
                    <span className="text-gray-400">المنطقة</span>
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
                    <span className="text-gray-400">السيولة</span>
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
