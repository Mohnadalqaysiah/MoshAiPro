import { useState, useEffect } from 'react'
import axios from 'axios'
import { TrendingUp, TrendingDown, Activity, Zap, AlertCircle, RefreshCw } from 'lucide-react'

const API = 'http://localhost:8000'

const MARKETS = ['XAUUSD', 'BTCUSD', 'EURUSD', 'GBPUSD']

export default function Dashboard() {
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchSignals()
  }, [])

  const fetchSignals = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/signals/latest?limit=10`)
      setSignals(res.data.data || [])
    } catch (e) {
      // no signals yet
    }
  }

  const analyzeMarket = async (symbol) => {
    setAnalyzing(symbol)
    setError(null)
    try {
      const res = await axios.post(`${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=1h&advanced_mode=true`)
      const data = res.data.data
      setSignals(prev => [{ ...data, market: symbol, id: Date.now() }, ...prev.slice(0, 9)])
    } catch (e) {
      setError(`فشل تحليل ${symbol}: ${e.message}`)
    } finally {
      setAnalyzing(null)
    }
  }

  const getSignalColor = (rec) => {
    if (rec === 'BUY') return 'text-green-400'
    if (rec === 'SELL') return 'text-red-400'
    return 'text-gray-400'
  }

  const getSignalBg = (rec) => {
    if (rec === 'BUY') return 'bg-green-900/30 border-green-700'
    if (rec === 'SELL') return 'bg-red-900/30 border-red-700'
    return 'bg-gray-800 border-gray-700'
  }

  const getSignalAr = (rec) => {
    if (rec === 'BUY') return 'شراء'
    if (rec === 'SELL') return 'بيع'
    return 'مراقبة'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">لوحة التحكم</h1>
          <p className="text-gray-400 text-sm mt-1">تحليل الأسواق بالذكاء الاصطناعي</p>
        </div>
        <button
          onClick={fetchSignals}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
        >
          <RefreshCw size={14} />
          تحديث
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Quick Analyze */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Zap size={18} className="text-blue-400" />
          تحليل سريع
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {MARKETS.map(market => (
            <button
              key={market}
              onClick={() => analyzeMarket(market)}
              disabled={analyzing === market}
              className="py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {analyzing === market ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  جاري...
                </>
              ) : market}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'إجمالي الإشارات', value: signals.length, icon: <Activity size={20} />, color: 'text-blue-400' },
          { label: 'إشارات شراء', value: signals.filter(s => (s.recommendation || s.signal_type) === 'BUY').length, icon: <TrendingUp size={20} />, color: 'text-green-400' },
          { label: 'إشارات بيع', value: signals.filter(s => (s.recommendation || s.signal_type) === 'SELL').length, icon: <TrendingDown size={20} />, color: 'text-red-400' },
          { label: 'متوسط الثقة', value: signals.length ? Math.round(signals.reduce((a, s) => a + (s.ai_confidence_score || s.ai_confidence || 0), 0) / signals.length) + '%' : 'N/A', icon: <Zap size={20} />, color: 'text-yellow-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className={`${stat.color} mb-2`}>{stat.icon}</div>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
            <div className="text-gray-400 text-sm">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Recent Signals */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h2 className="text-white font-semibold mb-4">آخر الإشارات</h2>
        {signals.length === 0 ? (
          <p className="text-gray-500 text-center py-8">لا توجد إشارات. اضغط على زر التحليل أعلاه.</p>
        ) : (
          <div className="space-y-3">
            {signals.map((sig, i) => {
              const rec = sig.recommendation || sig.signal_type || 'WATCH'
              const confidence = sig.ai_confidence_score || sig.ai_confidence || 0
              const market = sig.market || sig.symbol || 'N/A'
              return (
                <div key={sig.id || i} className={`border rounded-lg p-4 ${getSignalBg(rec)}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-white font-bold">{market}</span>
                      <span className={`font-semibold ${getSignalColor(rec)}`}>{getSignalAr(rec)}</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-gray-400">ثقة: <span className="text-white font-medium">{confidence.toFixed ? confidence.toFixed(1) : confidence}%</span></span>
                      {sig.risk_reward && (
                        <span className="text-gray-400">R/R: <span className="text-white font-medium">{sig.risk_reward.toFixed ? sig.risk_reward.toFixed(2) : sig.risk_reward}x</span></span>
                      )}
                    </div>
                  </div>
                  {sig.entry_zones && sig.entry_zones.length > 0 && (
                    <div className="mt-2 text-sm text-gray-400">
                      دخول: <span className="text-white">{sig.entry_zones[0]}</span>
                      {sig.stop_loss_zone && <> | SL: <span className="text-red-400">{sig.stop_loss_zone}</span></>}
                      {sig.take_profit_zones && sig.take_profit_zones[0] && <> | TP1: <span className="text-green-400">{sig.take_profit_zones[0]}</span></>}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
