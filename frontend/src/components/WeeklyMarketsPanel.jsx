/**
 * WeeklyMarketsPanel (2026-10-17) — الأداء الأسبوعي حسب السوق: مقياس المالك (الأسبوع × السوق بـR).
 * المصدر: GET /api/v1/admin/weekly-markets — نفس القرارات الموثّقة الفريدة التي تستخدمها كل التقارير.
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { RefreshCw } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const fmtR = (r) => `${r > 0 ? '+' : ''}${r}R`

function Cell({ c }) {
  if (!c || (!c.n && !c.be)) return <td className="px-3 py-2.5 text-center text-gray-700">—</td>
  const col = c.r > 0 ? 'text-emerald-400' : c.r < 0 ? 'text-red-400' : 'text-gray-400'
  const bg = c.r > 0 ? 'bg-emerald-500/5' : c.r < 0 ? 'bg-red-500/5' : ''
  return (
    <td className={`px-3 py-2.5 text-center ${bg}`}>
      <div className={`font-semibold ${col}`} dir="ltr">{c.n ? fmtR(c.r) : '0R'}</div>
      <div className="text-[11px] text-gray-500">
        {c.n} صفقة{c.win_rate != null && ` · ${c.win_rate}%`}{c.be ? ` · ⚖️${c.be}` : ''}
      </div>
    </td>
  )
}

export default function WeeklyMarketsPanel() {
  const [weeks, setWeeks] = useState(8)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = async (w = weeks) => {
    setLoading(true); setError('')
    try {
      const r = await axios.get(`${API}/api/v1/admin/weekly-markets?weeks=${w}`)
      setData(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const groups = data?.groups || []
  const rows = [...(data?.weeks || [])].reverse()

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold">الأداء الأسبوعي حسب السوق</h2>
          <p className="text-xs text-gray-500 mt-1">
            كل خانة: صافي R للأسبوع · عدد الصفقات · نسبة بلوغ الهدف الأول. الأسبوع حسب يوم صدور الصفقة.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {[4, 8, 12].map((w) => (
            <button key={w} onClick={() => { setWeeks(w); load(w) }}
              className={`text-xs px-3 py-1.5 rounded-lg border ${weeks === w ? 'border-blue-500 text-blue-400 bg-blue-900/20' : 'border-gray-700 text-gray-500'}`}>
              آخر {w} أسابيع
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
                <th className="text-right px-4 py-2.5">الأسبوع</th>
                {groups.map((g) => <th key={g.key} className="px-3 py-2.5">{g.name}</th>)}
                <th className="px-3 py-2.5 text-white">المجموع</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((w) => (
                <tr key={w.week} className="border-t border-gray-800/70">
                  <td className="px-4 py-2.5 whitespace-nowrap">
                    <div className="text-white text-xs font-semibold">
                      {w.week}{w.current && <span className="text-amber-400 font-normal"> · جارٍ</span>}
                      {w.week === data.tp1_cap_week && <span className="text-blue-400 font-normal"> · بداية الهدف القريب</span>}
                    </div>
                    <div className="text-[11px] text-gray-500" dir="ltr">{w.from.slice(5)} → {w.to.slice(5)}</div>
                  </td>
                  {groups.map((g) => <Cell key={g.key} c={w.cells[g.key]} />)}
                  <Cell c={w.cells._total} />
                </tr>
              ))}
            </tbody>
            <tfoot className="text-xs border-t-2 border-gray-700 bg-gray-950/40">
              <tr>
                <td className="px-4 py-2.5 text-gray-300">الأسابيع المكتملة</td>
                {[...groups.map((g) => g.key), '_total'].map((k) => {
                  const s = data.summary[k] || {}
                  return (
                    <td key={k} className="px-3 py-2.5 text-center">
                      <div className={s.total_r > 0 ? 'text-emerald-400' : s.total_r < 0 ? 'text-red-400' : 'text-gray-400'} dir="ltr">{fmtR(s.total_r ?? 0)}</div>
                      <div className="text-[11px] text-gray-500">✅ {s.weeks_won ?? 0} · ❌ {s.weeks_lost ?? 0}</div>
                    </td>
                  )
                })}
              </tr>
            </tfoot>
          </table>
        </div>
      )}
      <p className="text-[11px] text-gray-500 leading-relaxed">
        الرابحة = بلغت الهدف الأول. ⚖️ = أُغلقت على التأمين (0R، خارج النسبة). الأسبوع الجاري لا يدخل في سطر الأسابيع المكتملة،
        وأرقامه تتغيّر حتى تُغلق صفقاته. البيانات منذ 16/09 فقط (قبلها حلقة رصد معطوبة).
      </p>
    </div>
  )
}
