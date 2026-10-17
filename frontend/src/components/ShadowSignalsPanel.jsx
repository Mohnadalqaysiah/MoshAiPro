/**
 * ShadowSignalsPanel (2026-10-17) — صفقات الظل: ما حسبته المنصة ولم ترسله لأحد (مراجعة داخلية فقط).
 * كريبتو العطلة، قواعد الرفض بتجربتها الصامتة، وقوالب الذهب بتجربة الظل. المصدر: GET /api/v1/admin/shadow-signals
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { RefreshCw } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const OUTCOME = {
  TP2_HIT: ['هدف 2 🏆', 'text-purple-300'], TP1_HIT: ['هدف 1 ✅', 'text-blue-300'], TP1_BE: ['هدف 1 ثم تعادل', 'text-blue-300'],
  EXPIRED_TP1: ['هدف 1 ثم انتهت', 'text-blue-300'], SL_HIT: ['وقف ❌', 'text-red-300'], EXPIRED: ['انتهت المدة', 'text-gray-400'],
  EXPIRED_PROFIT: ['انتهت بربح', 'text-gray-300'], EXPIRED_LOSS: ['انتهت بخسارة', 'text-gray-400'],
  NOT_TRIGGERED: ['لم يتفعّل', 'text-gray-500'], NO_DATA: ['بلا بيانات', 'text-gray-600'],
}
const fmt = (iso) => (iso ? iso.replace('T', ' ').slice(5, 16) : '—')

export default function ShadowSignalsPanel() {
  const [days, setDays] = useState(30)
  const [reason, setReason] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = async (o = {}) => {
    const d = o.days ?? days, r = o.reason ?? reason, p = o.page ?? page
    setLoading(true); setError('')
    try {
      const q = new URLSearchParams({ days: d, page: p, page_size: 50 })
      if (r) q.set('reason', r)
      const res = await axios.get(`${API}/api/v1/admin/shadow-signals?${q}`)
      setData(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1
  const verdict = (b) => {
    if (b.avg_r == null) return <span className="text-gray-500">لا نتائج بعد</span>
    if (b.reason.startsWith('tpl:')) return <span className={b.avg_r > 0 ? 'text-emerald-400' : 'text-red-400'}>{b.avg_r > 0 ? 'القالب رابح حتى الآن' : 'القالب خاسر حتى الآن'}</span>
    return b.avg_r < 0
      ? <span className="text-emerald-400">المنع كان صحيحاً (منع خاسرات)</span>
      : <span className="text-amber-400">المنع حجب رابحات حتى الآن</span>
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold">صفقات الظل</h2>
          <p className="text-xs text-gray-500 mt-1">صفقات حسبتها المنصة ولم ترسلها لأحد — لنعرف: لو أرسلناها، هل كانت ستربح؟</p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30, 60].map((d) => (
            <button key={d} onClick={() => { setDays(d); setPage(1); load({ days: d, page: 1 }) }}
              className={`text-xs px-3 py-1.5 rounded-lg border ${days === d ? 'border-blue-500 text-blue-400 bg-blue-900/20' : 'border-gray-700 text-gray-500'}`}>
              {d} يوم
            </button>
          ))}
          <button onClick={() => load()} disabled={loading} className="p-2 rounded-lg bg-gray-800 border border-gray-700">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-3">{error}</div>}

      {data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-400 bg-gray-950/60">
              <tr>
                <th className="text-right px-4 py-2.5">السبب</th>
                <th className="px-3 py-2.5">صفقات</th>
                <th className="px-3 py-2.5">قُيّمت</th>
                <th className="px-3 py-2.5">رابحة / خاسرة</th>
                <th className="px-3 py-2.5">المجموع</th>
                <th className="px-3 py-2.5">المتوسط</th>
                <th className="text-right px-3 py-2.5">ماذا يعني حتى الآن</th>
              </tr>
            </thead>
            <tbody>
              {data.summary.length === 0 && <tr><td colSpan={7} className="text-center text-gray-500 py-6">لا صفقات ظل بهذه الفترة</td></tr>}
              {data.summary.map((b) => (
                <tr key={b.reason} onClick={() => { const r = reason === b.reason ? '' : b.reason; setReason(r); setPage(1); load({ reason: r, page: 1 }) }}
                  className={`border-t border-gray-800/70 cursor-pointer hover:bg-gray-800/40 ${reason === b.reason ? 'bg-blue-900/20' : ''}`}>
                  <td className="px-4 py-2.5 text-white text-xs">{b.label}</td>
                  <td className="px-3 py-2.5 text-center">{b.total}</td>
                  <td className="px-3 py-2.5 text-center text-gray-400">{b.evaluated}{b.pending ? <span className="text-gray-600"> (+{b.pending} بانتظار)</span> : ''}</td>
                  <td className="px-3 py-2.5 text-center"><span className="text-emerald-400">{b.wins}</span> / <span className="text-red-400">{b.losses}</span></td>
                  <td className={`px-3 py-2.5 text-center font-semibold ${b.r > 0 ? 'text-emerald-400' : b.r < 0 ? 'text-red-400' : 'text-gray-400'}`} dir="ltr">{b.r > 0 ? '+' : ''}{b.r}R</td>
                  <td className="px-3 py-2.5 text-center" dir="ltr">{b.avg_r != null ? `${b.avg_r > 0 ? '+' : ''}${b.avg_r}R` : '—'}</td>
                  <td className="px-3 py-2.5 text-xs">{verdict(b)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-2 text-[11px] text-gray-500 border-t border-gray-800">
            اضغط على سبب لعرض صفقاته فقط. الحكم النهائي بمراجعة 30/10 بقواعد مسجّلة (30 صفقة على الأقل وثبات بالنصفين) — الأرقام المبكرة مؤشر لا حكم.
          </div>
        </div>
      )}

      {data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <div className="px-4 py-3 border-b border-gray-800 text-sm font-semibold">
            الصفقات {reason ? `— ${data.summary.find((b) => b.reason === reason)?.label || reason}` : '— كل الأسباب'} ({data.total})
          </div>
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-400 bg-gray-950/60">
              <tr>
                <th className="text-right px-4 py-2">الوقت (UTC)</th>
                <th className="text-right px-3 py-2">السبب</th>
                <th className="px-3 py-2">الرمز</th>
                <th className="px-3 py-2">الاتجاه</th>
                <th className="px-3 py-2">الدخول</th>
                <th className="px-3 py-2">الوقف</th>
                <th className="px-3 py-2">TP1</th>
                <th className="px-3 py-2">النتيجة</th>
                <th className="px-3 py-2">R</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((s) => {
                const [ol, oc] = OUTCOME[s.outcome] || [s.outcome ? s.outcome : '⏳ بانتظار التقييم', 'text-gray-500']
                return (
                  <tr key={s.id} className="border-t border-gray-800/70">
                    <td className="px-4 py-2 text-xs text-gray-400" dir="ltr">{fmt(s.created_at)}</td>
                    <td className="px-3 py-2 text-xs text-gray-300">{s.label}</td>
                    <td className="px-3 py-2 text-center text-white">{s.market} <span className="text-gray-500 text-xs">{s.timeframe}</span></td>
                    <td className={`px-3 py-2 text-center ${s.side === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>{s.side === 'BUY' ? 'شراء' : 'بيع'}</td>
                    <td className="px-3 py-2 text-center font-mono text-xs" dir="ltr">{s.entry}</td>
                    <td className="px-3 py-2 text-center font-mono text-xs" dir="ltr">{s.sl}</td>
                    <td className="px-3 py-2 text-center font-mono text-xs" dir="ltr">{s.tp1}</td>
                    <td className={`px-3 py-2 text-center text-xs ${oc}`}>{ol}</td>
                    <td className={`px-3 py-2 text-center ${s.r > 0 ? 'text-emerald-400' : s.r < 0 ? 'text-red-400' : 'text-gray-500'}`} dir="ltr">{s.r != null ? `${s.r > 0 ? '+' : ''}${Number(s.r).toFixed(2)}` : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {pages > 1 && (
            <div className="flex items-center justify-center gap-3 py-3 border-t border-gray-800 text-sm">
              <button disabled={page <= 1} onClick={() => { setPage(page - 1); load({ page: page - 1 }) }} className="px-3 py-1 rounded bg-gray-800 disabled:opacity-40">السابق</button>
              <span className="text-gray-400">{page} / {pages}</span>
              <button disabled={page >= pages} onClick={() => { setPage(page + 1); load({ page: page + 1 }) }} className="px-3 py-1 rounded bg-gray-800 disabled:opacity-40">التالي</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
