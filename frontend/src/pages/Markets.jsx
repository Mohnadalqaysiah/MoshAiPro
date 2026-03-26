import { useState } from 'react'
import axios from 'axios'
import { RefreshCw, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import useMarkets from '../hooks/useMarkets'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const T = {
  ar: {
    title: 'الأسواق', sub: 'نظرة عامة على جميع الأسواق',
    analyzeAll: 'تحليل الكل', analyze: 'تحليل',
    analyzing: 'جاري التحليل...', failed: 'فشل التحليل',
    conf: 'نسبة الثقة', trend: 'الاتجاه', entry: 'دخول',
    buy: 'شراء', sell: 'بيع', watch: 'مراقبة',
  },
  en: {
    title: 'Markets', sub: 'Overview of all markets',
    analyzeAll: 'Analyze All', analyze: 'Analyze',
    analyzing: 'Analyzing...', failed: 'Analysis failed',
    conf: 'Confidence', trend: 'Trend', entry: 'Entry',
    buy: 'BUY', sell: 'SELL', watch: 'WATCH',
  },
}

export default function Markets() {
  const { markets } = useMarkets()
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'
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

  const analyzeAll = () => markets.forEach(m => analyzeMarket(m.symbol))

  const recColor = { BUY: 'text-green-400', SELL: 'text-red-400', WATCH: 'text-gray-400', WAIT: 'text-gray-400' }
  const recLabel = { BUY: tx.buy, SELL: tx.sell, WATCH: tx.watch, WAIT: tx.watch }

  return (
    <div className="space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{tx.title}</h1>
          <p className="text-gray-400 text-sm mt-1">{tx.sub}</p>
        </div>
        <button
          onClick={analyzeAll}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
        >
          <RefreshCw size={14} />
          {tx.analyzeAll}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {markets.map(market => {
          const data = results[market.symbol]
          const isLoading = loading[market.symbol]
          const rec = data?.recommendation

          return (
            <div key={market.symbol} className="bg-gray-800 border border-gray-700 rounded-xl p-5 hover:border-gray-500 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div>
                    <div className="text-white font-bold text-sm">{market.symbol}</div>
                    <div className="text-gray-400 text-xs">{isAr ? (market.name_ar || market.name) : market.name}</div>
                  </div>
                </div>
                {data && !data.error && rec && (
                  <div className={`text-sm font-bold ${recColor[rec] || 'text-gray-400'}`}>
                    {recLabel[rec] || rec}
                  </div>
                )}
              </div>

              {isLoading && (
                <div className="flex items-center justify-center py-4 text-gray-400 text-sm gap-2">
                  <RefreshCw size={14} className="animate-spin" />
                  {tx.analyzing}
                </div>
              )}

              {!isLoading && data && !data.error && (
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.conf}</span>
                    <span className={`font-medium ${data.ai_confidence_score >= 75 ? 'text-green-400' : data.ai_confidence_score >= 60 ? 'text-yellow-400' : 'text-gray-300'}`}>
                      {data.ai_confidence_score?.toFixed(1)}%
                    </span>
                  </div>
                  {data.trend?.direction && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">{tx.trend}</span>
                      <span className="text-white">{data.trend.direction}</span>
                    </div>
                  )}
                  {(data.levels?.entry_zone_min || data.entry_zones?.[0]) && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">{tx.entry}</span>
                      <span className="text-white font-mono">{data.levels?.entry_zone_min || data.entry_zones[0]}</span>
                    </div>
                  )}
                  {(data.levels?.stop_loss || data.stop_loss_zone) && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">SL</span>
                      <span className="text-red-400 font-mono">{data.levels?.stop_loss || data.stop_loss_zone}</span>
                    </div>
                  )}
                  {(data.levels?.tp1 || data.take_profit_zones?.[0]) && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">TP1</span>
                      <span className="text-green-400 font-mono">{data.levels?.tp1 || data.take_profit_zones[0]}</span>
                    </div>
                  )}
                </div>
              )}

              {!isLoading && data?.error && (
                <p className="text-red-400 text-xs text-center py-2">{tx.failed}</p>
              )}

              {!isLoading && !data && (
                <button
                  onClick={() => analyzeMarket(market.symbol)}
                  className="w-full py-2 text-blue-400 hover:text-blue-300 text-sm border border-blue-800 hover:border-blue-600 rounded-lg transition-colors"
                >
                  {tx.analyze}
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
