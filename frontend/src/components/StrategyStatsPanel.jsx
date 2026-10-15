/**
 * StrategyStatsPanel (2026-10-15) — إحصائيات باني الاستراتيجيات والقوالب للأدمن.
 * من يستخدم الباني، أي القوالب تُنسخ وتُفعَّل وتُختبر، وآخر الاستراتيجيات المنشأة.
 * المصدر: GET /api/v1/admin/strategies/stats
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { RefreshCw } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STATUS = {
  tested:   ['مُختبر', 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'],
  testing:  ['قيد الاختبار', 'text-amber-400 bg-amber-500/10 border-amber-500/30'],
  negative: ['سلبي', 'text-red-400 bg-red-500/10 border-red-500/30'],
}
const STRAT_STATUS = { ACTIVE: ['مفعّلة', 'text-emerald-400'], DRAFT: ['مسودة', 'text-gray-400'], DISABLED: ['موقوفة', 'text-gray-500'] }

const fmt = (iso) => (iso ? iso.replace('T', ' ').slice(0, 16) : '—')

export default function StrategyStatsPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const r = await axios.get(`${API}/api/v1/admin/strategies/stats`)
      setData(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  const s = data?.summary
  const tile = (label, value, sub) => (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-2xl font-bold text-white">{value ?? '—'}</div>
      <div className="text-xs text-gray-400 mt-1">{label}</div>
      {sub && <div className="text-[11px] text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
  const recent = (data?.recent || []).filter((r) =>
    filter === 'all' ? true : filter === 'template' ? !!r.template : filter === 'custom' ? !r.template : r.status === 'ACTIVE')
  const tplName = Object.fromEntries((data?.templates || []).map((t) => [t.key, t.name]))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">باني الاستراتيجيات والقوالب</h2>
          <p className="text-xs text-gray-500 mt-1">من يستخدم الباني، أي القوالب تُنسخ وتُفعَّل، وكم باكتيست يُشغَّل.</p>
        </div>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> تحديث
        </button>
      </div>

      {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-3">{error}</div>}

      {s && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {tile('مستخدمون لديهم استراتيجية', s.users_with_strategies,
            `تجربة/محدود ${s.users_by_tier?.limited || 0} · وصول كامل ${s.users_by_tier?.full || 0}`)}
          {tile('استراتيجيات', s.strategies, `مفعّلة الآن ${s.active}`)}
          {tile('من القوالب الجاهزة', s.from_templates, `من بناء المستخدم ${s.custom} · مرات النسخ ${s.template_copies_total}`)}
          {tile('باكتيست', s.backtests_total, `آخر 7 أيام ${s.backtests_7d} · مستخدمون ${s.backtest_users}`)}
          {tile('إطلاقات (7 أيام)', s.triggers_7d, 'مرات اكتمال شروط استراتيجيات المستخدمين')}
        </div>
      )}

      {data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 font-semibold text-sm">القوالب الجاهزة</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-400 bg-gray-950/50">
                <tr>
                  <th className="text-right px-4 py-2">القالب</th>
                  <th className="text-right px-3 py-2">الحالة</th>
                  <th className="px-3 py-2">مرات النسخ</th>
                  <th className="px-3 py-2">مستخدمون</th>
                  <th className="px-3 py-2">موجودة الآن</th>
                  <th className="px-3 py-2">مفعّلة</th>
                  <th className="px-3 py-2">باكتيست</th>
                  <th className="px-3 py-2">إطلاقات 7 أيام</th>
                </tr>
              </thead>
              <tbody>
                {data.templates.map((t) => {
                  const [lbl, cls] = STATUS[t.status] || STATUS.testing
                  return (
                    <tr key={t.key} className="border-t border-gray-800/70">
                      <td className="px-4 py-2 text-white">{t.name}</td>
                      <td className="px-3 py-2"><span className={`text-[11px] px-2 py-0.5 rounded border ${cls}`}>{lbl}</span></td>
                      <td className="px-3 py-2 text-center font-semibold">{t.copies}</td>
                      <td className="px-3 py-2 text-center">{t.users}</td>
                      <td className="px-3 py-2 text-center">{t.existing}</td>
                      <td className="px-3 py-2 text-center text-emerald-400">{t.active}</td>
                      <td className="px-3 py-2 text-center">{t.backtests}</td>
                      <td className="px-3 py-2 text-center">{t.triggers_7d}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex flex-wrap items-center justify-between gap-2">
            <span className="font-semibold text-sm">آخر الاستراتيجيات (حتى 100)</span>
            <div className="flex gap-1.5">
              {[['all', 'الكل'], ['template', 'من قالب'], ['custom', 'بناء المستخدم'], ['active', 'مفعّلة']].map(([k, l]) => (
                <button key={k} onClick={() => setFilter(k)}
                  className={`text-xs px-2.5 py-1 rounded-lg border ${filter === k ? 'bg-blue-600/20 border-blue-500/50 text-blue-300' : 'bg-gray-800 border-gray-700 text-gray-400'}`}>
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-400 bg-gray-950/50">
                <tr>
                  <th className="text-right px-4 py-2">المستخدم</th>
                  <th className="text-right px-3 py-2">الاستراتيجية</th>
                  <th className="text-right px-3 py-2">المصدر</th>
                  <th className="px-3 py-2">الرمز</th>
                  <th className="px-3 py-2">الحالة</th>
                  <th className="px-3 py-2">باكتيست</th>
                  <th className="px-3 py-2">إطلاقات 7 أيام</th>
                  <th className="px-3 py-2">أُنشئت</th>
                </tr>
              </thead>
              <tbody>
                {recent.length === 0 && (
                  <tr><td colSpan={8} className="text-center text-gray-500 py-6">لا يوجد</td></tr>
                )}
                {recent.map((r) => {
                  const [sl, sc] = STRAT_STATUS[r.status] || [r.status, 'text-gray-400']
                  return (
                    <tr key={r.id} className="border-t border-gray-800/70">
                      <td className="px-4 py-2">
                        <div className="text-white text-xs" dir="ltr">{r.user_email || '—'}</div>
                        <div className="text-[11px] text-gray-500">{r.user_plan} · {r.tier === 'full' ? 'وصول كامل' : 'تجربة/محدود'}</div>
                      </td>
                      <td className="px-3 py-2 text-white text-xs">{r.name}</td>
                      <td className="px-3 py-2 text-xs">{r.template ? <span className="text-amber-300">قالب: {tplName[r.template] || r.template}</span> : <span className="text-gray-400">بناء المستخدم</span>}</td>
                      <td className="px-3 py-2 text-center text-xs" dir="ltr">{(r.symbols || []).join(', ') || '—'}</td>
                      <td className={`px-3 py-2 text-center text-xs ${sc}`}>{sl}</td>
                      <td className="px-3 py-2 text-center">{r.backtests}</td>
                      <td className="px-3 py-2 text-center">{r.triggers_7d}</td>
                      <td className="px-3 py-2 text-center text-xs text-gray-400" dir="ltr">{fmt(r.created_at)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
