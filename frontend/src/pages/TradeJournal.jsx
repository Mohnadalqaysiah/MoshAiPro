import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import {
  BookOpen, Plus, TrendingUp, TrendingDown, CheckCircle,
  XCircle, Minus, RefreshCw, Trash2, ChevronDown, ChevronUp,
  X, DollarSign, Target, Activity, Trophy
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const RESULT_CFG = {
  OPEN: { labelAr: 'مفتوحة', labelEn: 'Open',       cls: 'bg-blue-500/15 text-blue-300 border-blue-500/30',   icon: Activity  },
  WIN:  { labelAr: 'رابحة',  labelEn: 'Win',         cls: 'bg-green-500/15 text-green-400 border-green-500/30', icon: CheckCircle },
  LOSS: { labelAr: 'خاسرة',  labelEn: 'Loss',        cls: 'bg-red-500/15 text-red-400 border-red-500/30',       icon: XCircle   },
  BE:   { labelAr: 'تعادل',  labelEn: 'Break-even',  cls: 'bg-gray-600/30 text-gray-400 border-gray-600/40',    icon: Minus     },
}

const STRATEGIES = ['', 'Order Block', 'FVG', 'Liquidity Sweep', 'BOS/CHOCH', 'Turtle Soup', 'ICT Killzone', 'OTE', 'Other']
const TIMEFRAMES  = ['', '15m', '30m', '1h', '4h', '1day']

// ── Add/Edit Form ──────────────────────────────────────────────────────────────
function EntryForm({ entry, onSave, onCancel, isAr }) {
  const blank = {
    symbol: '', direction: 'BUY', result: 'OPEN',
    entry_price: '', exit_price: '', stop_loss: '', take_profit: '',
    lot_size: '', pnl_pips: '', pnl_usd: '',
    notes: '', strategy: '', timeframe: '',
    opened_at: new Date().toISOString().slice(0, 16),
    closed_at: '',
  }
  const [form, setForm] = useState(entry ? {
    ...blank,
    ...entry,
    opened_at: entry.opened_at?.slice(0, 16) || blank.opened_at,
    closed_at: entry.closed_at?.slice(0, 16) || '',
  } : blank)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    if (!form.symbol) return setErr(isAr ? 'أدخل رمز السوق' : 'Enter a symbol')
    setSaving(true); setErr(null)
    try {
      const payload = {
        symbol:      form.symbol.toUpperCase(),
        direction:   form.direction,
        result:      form.result,
        entry_price: form.entry_price ? +form.entry_price : null,
        exit_price:  form.exit_price  ? +form.exit_price  : null,
        stop_loss:   form.stop_loss   ? +form.stop_loss   : null,
        take_profit: form.take_profit ? +form.take_profit : null,
        lot_size:    form.lot_size    ? +form.lot_size    : null,
        pnl_pips:    form.pnl_pips    ? +form.pnl_pips    : null,
        pnl_usd:     form.pnl_usd     ? +form.pnl_usd     : null,
        notes:       form.notes || null,
        strategy:    form.strategy || null,
        timeframe:   form.timeframe || null,
        opened_at:   form.opened_at  || null,
        closed_at:   form.closed_at  || null,
      }
      const token = localStorage.getItem('access_token')
      const headers = { Authorization: `Bearer ${token}` }
      if (entry?.id) {
        await axios.put(`${API}/api/v1/journal/${entry.id}`, payload, { headers })
      } else {
        await axios.post(`${API}/api/v1/journal`, payload, { headers })
      }
      onSave()
    } catch (e) {
      setErr(e.response?.data?.detail || (isAr ? 'خطأ في الحفظ' : 'Save failed'))
    } finally { setSaving(false) }
  }

  const F = ({ label, children }) => (
    <div>
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      {children}
    </div>
  )
  const inp = 'w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500'
  const sel = inp + ' cursor-pointer'

  return (
    <div className="bg-[#0d1420] border border-white/10 rounded-2xl p-5 space-y-4">
      <h3 className="font-bold text-white text-sm">
        {entry?.id
          ? (isAr ? 'تعديل الصفقة' : 'Edit Trade')
          : (isAr ? 'صفقة جديدة' : 'New Trade')}
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <F label={isAr ? 'الرمز' : 'Symbol'}>
          <input className={inp} placeholder="XAUUSD" value={form.symbol}
            onChange={e => set('symbol', e.target.value.toUpperCase())} />
        </F>
        <F label={isAr ? 'الاتجاه' : 'Direction'}>
          <select className={sel} value={form.direction} onChange={e => set('direction', e.target.value)}>
            <option value="BUY">{isAr ? 'شراء' : 'BUY'}</option>
            <option value="SELL">{isAr ? 'بيع' : 'SELL'}</option>
          </select>
        </F>
        <F label={isAr ? 'سعر الدخول' : 'Entry Price'}>
          <input type="number" step="any" className={inp} value={form.entry_price}
            onChange={e => set('entry_price', e.target.value)} />
        </F>
        <F label={isAr ? 'سعر الخروج' : 'Exit Price'}>
          <input type="number" step="any" className={inp} value={form.exit_price}
            onChange={e => set('exit_price', e.target.value)} />
        </F>
        <F label={isAr ? 'وقف الخسارة' : 'Stop Loss'}>
          <input type="number" step="any" className={inp} value={form.stop_loss}
            onChange={e => set('stop_loss', e.target.value)} />
        </F>
        <F label={isAr ? 'الهدف' : 'Take Profit'}>
          <input type="number" step="any" className={inp} value={form.take_profit}
            onChange={e => set('take_profit', e.target.value)} />
        </F>
        <F label={isAr ? 'حجم اللوت' : 'Lot Size'}>
          <input type="number" step="any" className={inp} value={form.lot_size}
            onChange={e => set('lot_size', e.target.value)} />
        </F>
        <F label={isAr ? 'الربح/الخسارة $' : 'P&L $'}>
          <input type="number" step="any" className={inp} value={form.pnl_usd}
            onChange={e => set('pnl_usd', e.target.value)} />
        </F>
        <F label={isAr ? 'النتيجة' : 'Result'}>
          <select className={sel} value={form.result} onChange={e => set('result', e.target.value)}>
            <option value="OPEN">{isAr ? 'مفتوحة' : 'Open'}</option>
            <option value="WIN">{isAr ? 'رابحة'  : 'Win'}</option>
            <option value="LOSS">{isAr ? 'خاسرة'  : 'Loss'}</option>
            <option value="BE">{isAr ? 'تعادل'   : 'Break-even'}</option>
          </select>
        </F>
        <F label={isAr ? 'الاستراتيجية' : 'Strategy'}>
          <select className={sel} value={form.strategy} onChange={e => set('strategy', e.target.value)}>
            {STRATEGIES.map(s => <option key={s} value={s}>{s || (isAr ? '—' : '—')}</option>)}
          </select>
        </F>
        <F label={isAr ? 'الفريم' : 'Timeframe'}>
          <select className={sel} value={form.timeframe} onChange={e => set('timeframe', e.target.value)}>
            {TIMEFRAMES.map(t => <option key={t} value={t}>{t || (isAr ? '—' : '—')}</option>)}
          </select>
        </F>
        <F label={isAr ? 'وقت الدخول' : 'Opened At'}>
          <input type="datetime-local" className={inp} value={form.opened_at}
            onChange={e => set('opened_at', e.target.value)} />
        </F>
      </div>

      <F label={isAr ? 'ملاحظات' : 'Notes'}>
        <textarea rows={3} className={inp + ' resize-none'} value={form.notes}
          placeholder={isAr ? 'لماذا دخلت هذه الصفقة؟ ما الذي رأيته؟' : 'Why did you enter? What did you see?'}
          onChange={e => set('notes', e.target.value)} />
      </F>

      {err && <p className="text-red-400 text-xs">{err}</p>}

      <div className="flex gap-3">
        <button
          onClick={submit} disabled={saving}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-sm font-semibold transition-all disabled:opacity-60"
        >
          {saving ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle size={14} />}
          {isAr ? 'حفظ' : 'Save'}
        </button>
        <button onClick={onCancel} className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl text-sm transition-colors">
          {isAr ? 'إلغاء' : 'Cancel'}
        </button>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function TradeJournal() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const token = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  const [entries,  setEntries]  = useState([])
  const [stats,    setStats]    = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editing,  setEditing]  = useState(null)
  const [filter,   setFilter]   = useState('')   // result filter
  const [expanded, setExpanded] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = filter ? `?result=${filter}` : ''
      const [e, s] = await Promise.all([
        axios.get(`${API}/api/v1/journal${params}`, { headers }),
        axios.get(`${API}/api/v1/journal/stats`,    { headers }),
      ])
      setEntries(e.data.entries || [])
      setStats(s.data)
    } catch {}
    setLoading(false)
  }, [filter, token])

  useEffect(() => { fetchData() }, [fetchData])

  const deleteEntry = async (id) => {
    if (!confirm(isAr ? 'حذف هذه الصفقة؟' : 'Delete this trade?')) return
    try {
      await axios.delete(`${API}/api/v1/journal/${id}`, { headers })
      fetchData()
    } catch {}
  }

  const STAT_CARDS = stats ? [
    { label: isAr ? 'إجمالي الصفقات' : 'Total Trades', value: stats.total,    icon: BookOpen,    color: 'text-blue-400'   },
    { label: isAr ? 'نسبة الربح'     : 'Win Rate',      value: `${stats.win_rate}%`, icon: Trophy, color: 'text-green-400' },
    { label: isAr ? 'إجمالي الربح'   : 'Total P&L',     value: `$${stats.total_pnl >= 0 ? '+' : ''}${stats.total_pnl}`, icon: DollarSign, color: stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
    { label: isAr ? 'أفضل سوق'       : 'Best Market',   value: stats.best_market || '—', icon: Target, color: 'text-yellow-400' },
  ] : []

  return (
    <div className="space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BookOpen size={22} className="text-blue-400" />
            {isAr ? 'يومية التداول' : 'Trade Journal'}
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            {isAr ? 'سجّل صفقاتك وتابع أداءك الشخصي' : 'Log your trades and track your personal performance'}
          </p>
        </div>
        <button
          onClick={() => { setShowForm(true); setEditing(null) }}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-sm font-semibold transition-all"
        >
          <Plus size={16} />
          {isAr ? 'صفقة جديدة' : 'New Trade'}
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {STAT_CARDS.map((s, i) => (
            <div key={i} className="bg-gray-800/60 border border-gray-700/50 rounded-2xl p-4">
              <s.icon size={18} className={s.color + ' mb-2'} />
              <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-gray-500 text-xs mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Win/Loss breakdown bar */}
      {stats && stats.closed > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/30 rounded-xl px-4 py-3 flex items-center gap-3">
          <span className="text-xs text-gray-500 w-14 flex-shrink-0">{isAr ? 'الأداء' : 'Record'}</span>
          <div className="flex-1 flex h-3 rounded-full overflow-hidden gap-0.5">
            <div className="bg-green-500 rounded-s-full" style={{ width: `${(stats.wins / stats.closed) * 100}%` }} />
            <div className="bg-gray-700" style={{ width: `${(stats.be / stats.closed) * 100}%` }} />
            <div className="bg-red-500 rounded-e-full" style={{ width: `${(stats.losses / stats.closed) * 100}%` }} />
          </div>
          <span className="text-xs text-gray-400 flex-shrink-0">
            {stats.wins}W · {stats.be}BE · {stats.losses}L
          </span>
        </div>
      )}

      {/* Add/Edit Form */}
      {(showForm || editing) && (
        <EntryForm
          entry={editing}
          isAr={isAr}
          onSave={() => { setShowForm(false); setEditing(null); fetchData() }}
          onCancel={() => { setShowForm(false); setEditing(null) }}
        />
      )}

      {/* Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-gray-600">{isAr ? 'فلتر:' : 'Filter:'}</span>
        {['', 'OPEN', 'WIN', 'LOSS', 'BE'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              filter === f
                ? 'bg-blue-600/20 text-blue-300 border-blue-500/40'
                : 'text-gray-500 border-gray-700/50 hover:text-gray-300 hover:border-gray-600'
            }`}
          >
            {f === '' ? (isAr ? 'الكل' : 'All') : (RESULT_CFG[f]?.[isAr ? 'labelAr' : 'labelEn'] || f)}
          </button>
        ))}
        <button onClick={fetchData} disabled={loading} className="ms-auto p-1.5 text-gray-600 hover:text-white transition-colors">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Entries List */}
      <div className="bg-gray-800/50 border border-gray-700/40 rounded-2xl overflow-hidden">
        {entries.length === 0 ? (
          <div className="py-16 text-center text-gray-600 text-sm">
            {isAr ? 'لا توجد صفقات بعد. أضف أولى صفقاتك!' : 'No trades yet. Add your first trade!'}
          </div>
        ) : (
          <div className="divide-y divide-gray-700/30">
            {entries.map(e => {
              const isBuy  = e.direction === 'BUY'
              const cfg    = RESULT_CFG[e.result] || RESULT_CFG.OPEN
              const Icon   = cfg.icon
              const isExp  = expanded === e.id

              return (
                <div key={e.id} className="hover:bg-gray-700/20 transition-colors">
                  {/* Row */}
                  <div className="flex items-center gap-3 px-4 py-3 cursor-pointer"
                    onClick={() => setExpanded(isExp ? null : e.id)}>
                    {/* Direction accent */}
                    <div className={`w-1 self-stretch rounded-full flex-shrink-0 ${isBuy ? 'bg-green-500' : 'bg-red-500'}`} />

                    {/* Symbol + direction */}
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="font-bold text-white text-sm">{e.symbol}</span>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${isBuy ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}`}>
                        {isBuy ? (isAr ? '▲ شراء' : '▲ BUY') : (isAr ? '▼ بيع' : '▼ SELL')}
                      </span>
                      {e.strategy && (
                        <span className="text-[10px] bg-gray-700/60 text-gray-400 px-1.5 py-0.5 rounded">{e.strategy}</span>
                      )}
                    </div>

                    {/* P&L */}
                    {e.pnl_usd != null && (
                      <span className={`text-sm font-bold flex-shrink-0 ${e.pnl_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {e.pnl_usd >= 0 ? '+' : ''}{e.pnl_usd}$
                      </span>
                    )}

                    {/* Result badge */}
                    <span className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-full border flex-shrink-0 ${cfg.cls}`}>
                      <Icon size={10} />{cfg[isAr ? 'labelAr' : 'labelEn']}
                    </span>

                    {/* Expand */}
                    {isExp ? <ChevronUp size={14} className="text-gray-600 flex-shrink-0" /> : <ChevronDown size={14} className="text-gray-600 flex-shrink-0" />}
                  </div>

                  {/* Expanded details */}
                  {isExp && (
                    <div className="px-4 pb-4 space-y-3">
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        {[
                          { l: isAr ? 'دخول' : 'Entry',   v: e.entry_price },
                          { l: isAr ? 'خروج' : 'Exit',    v: e.exit_price  },
                          { l: 'SL',                        v: e.stop_loss   },
                          { l: 'TP',                        v: e.take_profit },
                          { l: isAr ? 'لوت'  : 'Lot',     v: e.lot_size    },
                          { l: isAr ? 'فريم' : 'TF',      v: e.timeframe   },
                        ].filter(x => x.v != null).map(x => (
                          <div key={x.l} className="bg-gray-800/60 rounded-lg px-2.5 py-2">
                            <div className="text-gray-600 mb-0.5">{x.l}</div>
                            <div className="text-white font-mono font-semibold">{x.v}</div>
                          </div>
                        ))}
                      </div>
                      {e.notes && (
                        <p className="text-xs text-gray-500 bg-gray-800/40 rounded-xl px-3 py-2 leading-relaxed">
                          {e.notes}
                        </p>
                      )}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => { setEditing(e); setShowForm(false) }}
                          className="text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-3 py-1.5 rounded-lg transition-colors"
                        >
                          {isAr ? 'تعديل' : 'Edit'}
                        </button>
                        <button
                          onClick={() => deleteEntry(e.id)}
                          className="text-xs text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
                        >
                          <Trash2 size={11} /> {isAr ? 'حذف' : 'Delete'}
                        </button>
                        <span className="ms-auto text-[10px] text-gray-700">
                          {e.opened_at ? new Date(e.opened_at).toLocaleDateString('ar-EG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                      </div>
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
