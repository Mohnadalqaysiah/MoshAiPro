/**
 * StrategyStatsPanel (2026-10-15، بُسّط 16/10 بطلب المالك) — إحصائيات باني الاستراتيجيات والقوالب للأدمن.
 * ثلاثة أسئلة فقط بلغة بسيطة: كم شخصاً يستخدم الباني؟ أي القوالب يختارون؟ من آخر المستخدمين؟
 * المصدر: GET /api/v1/admin/strategies/stats
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { RefreshCw } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const fmtDate = (iso) => (iso ? iso.slice(0, 10) : '—')

export default function StrategyStatsPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showAll, setShowAll] = useState(false)

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
  const used = (data?.templates || []).filter((t) => t.copies > 0)
  const tplName = Object.fromEntries((data?.templates || []).map((t) => [t.key, t.name]))
  const recent = (data?.recent || []).slice(0, showAll ? 100 : 15)

  const card = (value, label, color = 'text-white') => (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
      <div className={`text-3xl font-bold ${color}`}>{value ?? '—'}</div>
      <div className="text-sm text-gray-400 mt-1">{label}</div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">باني الاستراتيجيات والقوالب</h2>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> تحديث
        </button>
      </div>

      {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-3">{error}</div>}

      {s && (
        <>
          <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 text-sm text-gray-300 leading-7">
            <b className="text-white">{s.users_with_strategies}</b> مستخدم أنشأوا <b className="text-white">{s.strategies}</b> استراتيجية —
            {' '}<b className="text-amber-300">{s.from_templates}</b> منها نسخوها من القوالب الجاهزة و<b className="text-white">{s.custom}</b> بنوها بأنفسهم.
            {' '}المفعّلة الآن (تراقب السوق وترسل تنبيهات): <b className="text-emerald-400">{s.active}</b>.
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {card(s.users_with_strategies, 'مستخدم جرّبوا الباني')}
            {card(s.active, 'استراتيجية مفعّلة الآن', 'text-emerald-400')}
            {card(s.from_templates, 'نُسخت من القوالب', 'text-amber-300')}
            {card(s.backtest_users, 'مستخدم جرّبوا الباكتيست')}
          </div>
        </>
      )}

      {data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800">
            <div className="font-semibold text-sm">أي القوالب يختارها المستخدمون؟</div>
            <div className="text-xs text-gray-500 mt-0.5">الأكثر نسخاً أولاً. القوالب التي لم ينسخها أحد لا تظهر.</div>
          </div>
          {used.length === 0
            ? <div className="text-center text-gray-500 text-sm py-6">لم ينسخ أحد أي قالب بعد</div>
            : (
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-400 bg-gray-950/50">
                  <tr>
                    <th className="text-right px-4 py-2">القالب</th>
                    <th className="px-3 py-2">كم شخص نسخه</th>
                    <th className="px-3 py-2">كم شخص فعّله</th>
                  </tr>
                </thead>
                <tbody>
                  {used.map((t) => (
                    <tr key={t.key} className="border-t border-gray-800/70">
                      <td className="px-4 py-2.5 text-white">
                        {t.name}
                        {t.status === 'tested' && <span className="text-[11px] text-emerald-400 mr-2">✅ مُختبر</span>}
                      </td>
                      <td className="px-3 py-2.5 text-center font-semibold">{t.users}</td>
                      <td className="px-3 py-2.5 text-center text-emerald-400">{t.active}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {data && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 font-semibold text-sm">آخر من أنشأ استراتيجية</div>
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-400 bg-gray-950/50">
              <tr>
                <th className="text-right px-4 py-2">المستخدم</th>
                <th className="text-right px-3 py-2">من أين</th>
                <th className="px-3 py-2">مفعّلة؟</th>
                <th className="px-3 py-2">التاريخ</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0 && <tr><td colSpan={4} className="text-center text-gray-500 py-6">لا يوجد</td></tr>}
              {recent.map((r) => (
                <tr key={r.id} className="border-t border-gray-800/70">
                  <td className="px-4 py-2.5">
                    <div className="text-white text-xs" dir="ltr">{r.user_email || '—'}</div>
                    <div className="text-[11px] text-gray-500">{r.tier === 'full' ? 'مشترك كامل' : 'تجربة'}</div>
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    {r.template ? <span className="text-amber-300">قالب: {tplName[r.template] || r.template}</span>
                                : <span className="text-gray-300">بناها بنفسه</span>}
                  </td>
                  <td className="px-3 py-2.5 text-center">{r.status === 'ACTIVE' ? <span className="text-emerald-400">نعم</span> : <span className="text-gray-500">لا</span>}</td>
                  <td className="px-3 py-2.5 text-center text-xs text-gray-400" dir="ltr">{fmtDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {(data.recent || []).length > 15 && (
            <button onClick={() => setShowAll(!showAll)} className="w-full py-2.5 text-sm text-gray-400 hover:text-white border-t border-gray-800">
              {showAll ? 'عرض أقل' : `عرض الكل (${data.recent.length})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
