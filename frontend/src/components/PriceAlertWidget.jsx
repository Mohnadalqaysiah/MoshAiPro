/**
 * PriceAlertWidget — تنبيهات الأسعار
 * إنشاء تنبيه عند وصول السعر لمستوى معين، وإرسال إشعار عبر تلغرام
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { Bell, BellOff, Plus, Trash2, ChevronRight, TrendingUp, TrendingDown, CheckCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SYMBOLS = [
  'XAUUSD','XAGUSD','BTCUSD','ETHUSD',
  'EURUSD','GBPUSD','USDJPY','USDCHF',
  'NAS100','US30','USOIL',
]
const SYMBOL_LABELS = {
  XAUUSD: '🥇 ذهب', XAGUSD: '🥈 فضة', BTCUSD: '₿ بيتكوين', ETHUSD: 'Ξ إيثريوم',
  EURUSD: 'EUR/USD', GBPUSD: 'GBP/USD', USDJPY: 'USD/JPY', USDCHF: 'USD/CHF',
  NAS100: '📈 ناسداك', US30: '📈 داو', USOIL: '🛢 نفط',
}

export default function PriceAlertWidget() {
  const [alerts,   setAlerts]   = useState([])
  const [loading,  setLoading]  = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [saving,   setSaving]   = useState(false)
  const [error,    setError]    = useState(null)

  const [form, setForm] = useState({
    symbol:       'XAUUSD',
    target_price: '',
    direction:    'above',
    note:         '',
  })

  const load = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/alerts`)
      setAlerts(res.data.alerts || [])
    } catch { /* silently */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await axios.post(`${API}/api/v1/alerts`, {
        ...form,
        target_price: parseFloat(form.target_price),
      })
      setShowForm(false)
      setForm({ symbol: 'XAUUSD', target_price: '', direction: 'above', note: '' })
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'حدث خطأ')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id) => {
    try {
      await axios.delete(`${API}/api/v1/alerts/${id}`)
      setAlerts(a => a.filter(x => x.id !== id))
    } catch { /* ignore */ }
  }

  const active    = alerts.filter(a => !a.triggered)
  const triggered = alerts.filter(a => a.triggered)

  if (loading) return (
    <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl p-5 animate-pulse h-24" />
  )

  return (
    <div className="bg-gradient-to-br from-amber-950/40 via-gray-900/80 to-gray-950/60 border border-amber-700/25 rounded-2xl overflow-hidden" dir="rtl">

      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer select-none"
        onClick={() => setExpanded(p => !p)}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 flex items-center justify-center rounded-xl bg-amber-500/15 border border-amber-500/25">
            <Bell size={16} className="text-amber-400" />
          </div>
          <div>
            <h3 className="text-white font-semibold text-sm">تنبيهات السعر</h3>
            <p className="text-amber-300/60 text-xs mt-0.5">إشعار فوري عند وصول السعر</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-white">{active.length}</span>
          <span className="text-xs text-gray-500">نشط</span>
          <ChevronRight
            size={16}
            className={`text-gray-500 transition-transform duration-200 ${expanded ? 'rotate-90' : '-rotate-90'}`}
          />
        </div>
      </div>

      {/* Expanded */}
      {expanded && (
        <div className="border-t border-gray-700/40 px-5 py-4 space-y-4">

          {/* قائمة التنبيهات النشطة */}
          {active.length > 0 && (
            <div className="space-y-2">
              {active.map(a => (
                <div key={a.id} className="flex items-center justify-between bg-gray-800/50 rounded-xl px-3 py-2.5 border border-gray-700/40">
                  <div className="flex items-center gap-2">
                    {a.direction === 'above'
                      ? <TrendingUp size={14} className="text-green-400" />
                      : <TrendingDown size={14} className="text-red-400" />}
                    <div>
                      <span className="text-white text-xs font-semibold">{SYMBOL_LABELS[a.symbol] || a.symbol}</span>
                      <span className="text-gray-400 text-xs mx-2">
                        {a.direction === 'above' ? 'فوق' : 'تحت'} {a.target_price.toLocaleString()}
                      </span>
                      {a.note && <span className="text-gray-500 text-xs">— {a.note}</span>}
                    </div>
                  </div>
                  <button
                    onClick={() => remove(a.id)}
                    className="text-gray-600 hover:text-red-400 transition-colors p-1"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {active.length === 0 && !showForm && (
            <p className="text-center text-gray-500 text-sm py-2">لا توجد تنبيهات نشطة</p>
          )}

          {/* نموذج الإضافة */}
          {showForm ? (
            <form onSubmit={submit} className="space-y-3 bg-gray-800/40 rounded-xl p-3 border border-gray-700/40">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">الرمز</label>
                  <select
                    value={form.symbol}
                    onChange={e => setForm(f => ({ ...f, symbol: e.target.value }))}
                    className="w-full bg-gray-700/60 border border-gray-600/50 rounded-lg px-2 py-2 text-white text-xs"
                  >
                    {SYMBOLS.map(s => (
                      <option key={s} value={s}>{SYMBOL_LABELS[s] || s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">الاتجاه</label>
                  <select
                    value={form.direction}
                    onChange={e => setForm(f => ({ ...f, direction: e.target.value }))}
                    className="w-full bg-gray-700/60 border border-gray-600/50 rounded-lg px-2 py-2 text-white text-xs"
                  >
                    <option value="above">📈 يرتفع فوق</option>
                    <option value="below">📉 ينخفض تحت</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">السعر المستهدف</label>
                <input
                  type="number"
                  step="any"
                  required
                  placeholder="مثال: 3400"
                  value={form.target_price}
                  onChange={e => setForm(f => ({ ...f, target_price: e.target.value }))}
                  className="w-full bg-gray-700/60 border border-gray-600/50 rounded-lg px-3 py-2 text-white text-xs placeholder-gray-500"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">ملاحظة (اختياري)</label>
                <input
                  type="text"
                  placeholder="مثال: مستوى مقاومة مهم"
                  value={form.note}
                  onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                  className="w-full bg-gray-700/60 border border-gray-600/50 rounded-lg px-3 py-2 text-white text-xs placeholder-gray-500"
                />
              </div>
              {error && (
                <p className="text-red-400 text-xs bg-red-900/20 rounded-lg px-3 py-2">{error}</p>
              )}
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-2 rounded-lg bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-600/30 text-xs font-semibold transition-all"
                >
                  {saving ? '...' : 'حفظ التنبيه'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 rounded-lg bg-gray-700/40 text-gray-400 text-xs border border-gray-600/30"
                >
                  إلغاء
                </button>
              </div>
            </form>
          ) : (
            <button
              onClick={() => setShowForm(true)}
              className="w-full py-2.5 rounded-xl border border-dashed border-amber-600/30 text-amber-400/70 hover:text-amber-300 hover:border-amber-500/50 text-xs flex items-center justify-center gap-2 transition-all"
            >
              <Plus size={13} /> إضافة تنبيه جديد
            </button>
          )}

          {/* آخر التنبيهات المُفعَّلة */}
          {triggered.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs text-gray-500">آخر التنبيهات المُفعَّلة</p>
              {triggered.slice(0, 3).map(a => (
                <div key={a.id} className="flex items-center gap-2 text-xs text-gray-500 bg-gray-800/30 rounded-lg px-3 py-2">
                  <CheckCircle size={12} className="text-green-500/70 flex-shrink-0" />
                  <span>{SYMBOL_LABELS[a.symbol] || a.symbol}</span>
                  <span>@</span>
                  <span>{a.target_price.toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}

        </div>
      )}
    </div>
  )
}
