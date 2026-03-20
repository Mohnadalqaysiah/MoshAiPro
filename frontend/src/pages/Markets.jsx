import { useState, useEffect } from 'react'
import axios from 'axios'
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'

const API = 'http://localhost:8000'

const MARKETS = [
  { symbol: 'XAUUSD', name: 'الذهب', emoji: '🥇' },
  { symbol: 'BTCUSD', name: 'بيتكوين', emoji: '₿' },
  { symbol: 'EURUSD', name: 'يورو/دولار', emoji: '💶' },
  { symbol: 'GBPUSD', name: 'جنيه/دولار', emoji: '💷' },
  { symbol: 'USDJPY', name: 'دولار/ين', emoji: '💴' },
  { symbol: 'USDCHF', name: 'دولار/فرنك', emoji: '🇨🇭' },
]

export default function Markets() {
  const [results, setResults] = useState({})
  const [loading, setLoading] = useState({})

  const analyzeMarket = async (symbol) => {
    setLoading(prev => ({ ...prev, [symbol]: true }))
    try {
      const res = await axios.post(`${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=1h&advanced_mode=true`)
      setResults(prev => ({ ...prev, [symbol]: res.data.data }))
    } catch (e) {
      setResults(prev => ({ ...prev, [symbol]: { error: true } }))
    } finally {
      setLoading(prev => ({ ...prev, [symbol]: false }))
    }
  }

  const analyzeAll = () => {
    MARKETS.forEach(m => analyzeMarket(m.symbol))
  }

  const getRecColor = (rec) => {
    if (rec === 'BUY') return 'text-green-400'
    if (rec === 'SELL') return 'text-red-400'
    return 'text-gray-400'
  }

  const getRecAr = (rec) => {
    if (rec === 'BUY') return 'شراء'
    if (rec === 'SELL') return 'بيع'
    return 'مراقبة'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">الأسواق</h1>
          <p className="text-gray-400 text-sm mt-1">نظرة عامة على جميع الأسواق</p>
        </div>
        <button
          onClick={analyzeAll}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
        >
          <RefreshCw size={14} />
          تحليل الكل
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {MARKETS.map(market => {
          const data = results[market.symbol]
          const isLoading = loading[market.symbol]
          const rec = data?.recommendation

          return (
            <div key={market.symbol} className="bg-gray-800 border border-gray-700 rounded-xl p-5 hover:border-gray-500 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{market.emoji}</span>
                  <div>
                    <div className="text-white font-bold">{market.symbol}</div>
                    <div className="text-gray-400 text-xs">{market.name}</div>
                  </div>
                </div>
                {data && !data.error && (
                  <div className={`font-bold ${getRecColor(rec)}`}>
                    {getRecAr(rec)}
                  </div>
                )}
              </div>

              {isLoading && (
                <div className="flex items-center justify-center py-4 text-gray-400 text-sm gap-2">
                  <RefreshCw size={14} className="animate-spin" />
                  جاري التحليل...
                </div>
              )}

              {!isLoading && data && !data.error && (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">نسبة الثقة</span>
                    <span className="text-white font-medium">{data.ai_confidence_score?.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">الاتجاه</span>
                    <span className="text-white">{data.trend?.direction}</span>
                  </div>
                  {data.entry_zones?.[0] && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">دخول</span>
                      <span className="text-white font-mono text-xs">{data.entry_zones[0]}</span>
                    </div>
                  )}
                  {data.stop_loss_zone && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">SL</span>
                      <span className="text-red-400 font-mono text-xs">{data.stop_loss_zone}</span>
                    </div>
                  )}
                  {data.take_profit_zones?.[0] && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">TP1</span>
                      <span className="text-green-400 font-mono text-xs">{data.take_profit_zones[0]}</span>
                    </div>
                  )}
                </div>
              )}

              {!isLoading && data?.error && (
                <p className="text-red-400 text-xs text-center py-2">فشل التحليل</p>
              )}

              {!isLoading && !data && (
                <button
                  onClick={() => analyzeMarket(market.symbol)}
                  className="w-full py-2 text-blue-400 hover:text-blue-300 text-sm border border-blue-800 hover:border-blue-600 rounded-lg transition-colors"
                >
                  تحليل
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
