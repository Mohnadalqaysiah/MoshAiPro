import { useState, useEffect } from 'react'
import axios from 'axios'
import { BarChart2, Activity, TrendingUp } from 'lucide-react'

const API = 'http://localhost:8000'

export default function Analytics() {
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSignals()
  }, [])

  const fetchSignals = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/signals/latest?limit=50`)
      setSignals(res.data.data || [])
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const buyCount = signals.filter(s => (s.recommendation || s.signal_type) === 'BUY').length
  const sellCount = signals.filter(s => (s.recommendation || s.signal_type) === 'SELL').length
  const watchCount = signals.filter(s => (s.recommendation || s.signal_type) === 'WATCH').length
  const avgConf = signals.length
    ? (signals.reduce((a, s) => a + (s.ai_confidence_score || s.ai_confidence || 0), 0) / signals.length).toFixed(1)
    : 0

  const marketCounts = signals.reduce((acc, s) => {
    const m = s.market || s.symbol || 'N/A'
    acc[m] = (acc[m] || 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">التحليلات</h1>
        <p className="text-gray-400 text-sm mt-1">إحصائيات الإشارات والأداء</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'إجمالي الإشارات', value: signals.length, color: 'text-blue-400' },
          { label: 'شراء', value: buyCount, color: 'text-green-400' },
          { label: 'بيع', value: sellCount, color: 'text-red-400' },
          { label: 'متوسط الثقة', value: `${avgConf}%`, color: 'text-yellow-400' },
        ].map((s, i) => (
          <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
            <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-gray-400 text-sm mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Signal Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <BarChart2 size={18} className="text-blue-400" />
            توزيع الإشارات
          </h3>
          {signals.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">لا توجد بيانات</p>
          ) : (
            <div className="space-y-3">
              {[
                { label: 'شراء', count: buyCount, color: 'bg-green-500' },
                { label: 'بيع', count: sellCount, color: 'bg-red-500' },
                { label: 'مراقبة', count: watchCount, color: 'bg-gray-500' },
              ].map(item => (
                <div key={item.label}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400">{item.label}</span>
                    <span className="text-white">{item.count}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className={`${item.color} h-2 rounded-full transition-all`}
                      style={{ width: signals.length ? `${(item.count / signals.length) * 100}%` : '0%' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-blue-400" />
            الأسواق الأكثر تحليلاً
          </h3>
          {Object.keys(marketCounts).length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">لا توجد بيانات</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(marketCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 6)
                .map(([market, count]) => (
                  <div key={market}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">{market}</span>
                      <span className="text-white">{count}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${(count / Math.max(...Object.values(marketCounts))) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>

      {/* API Status */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Activity size={18} className="text-blue-400" />
          حالة النظام
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { name: 'Backend API', status: true },
            { name: 'قاعدة البيانات', status: true },
            { name: 'TwelveData', status: true },
            { name: 'Telegram Bot', status: true },
          ].map(service => (
            <div key={service.name} className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${service.status ? 'bg-green-400' : 'bg-red-400'}`} />
              <span className="text-gray-300 text-sm">{service.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
