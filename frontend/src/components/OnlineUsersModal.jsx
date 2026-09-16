/**
 * OnlineUsersModal — من المتواجد على المنصة الآن
 * ================================================
 * معنى "متصل" مكتوب بالواجهة لا في تعليق: last_seen_at يُحدَّث بالطلبات
 * الموثّقة وحدها، فمن يفتح الصفحة ويتركها بلا تفاعل يسقط من القائمة،
 * ومستخدمو بوت تلغرام لا يظهرون. الرقم أدنى من الحضور الحقيقي لا أعلى.
 * إخفاء هذا القيد يجعل الزر يبدو عدّاد حضور وهو ليس كذلك.
 */
import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { X, RefreshCw, Users, Send } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const WINDOWS = [
  { sec: 300,   label: '5 دقائق' },
  { sec: 900,   label: '15 دقيقة' },
  { sec: 3600,  label: 'ساعة' },
  { sec: 86400, label: '24 ساعة' },
]

const ago = (s) => {
  if (s === null || s === undefined) return '—'
  if (s < 60) return `${s} ث`
  if (s < 3600) return `${Math.floor(s / 60)} د`
  if (s < 86400) return `${Math.floor(s / 3600)} س`
  return `${Math.floor(s / 86400)} ي`
}

const PLAN_STYLE = {
  BANNED:  'bg-red-900/40 text-red-300',
  TRIAL:   'bg-gray-700 text-gray-300',
  WEEKLY:  'bg-blue-900/40 text-blue-300',
  MONTHLY: 'bg-green-900/40 text-green-300',
}

export default function OnlineUsersModal({ onClose }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [win, setWin]         = useState(300)
  const [auto, setAuto]       = useState(true)
  const timer = useRef(null)

  const load = async (w = win) => {
    setLoading(true); setError(null)
    try {
      const r = await axios.get(`${API}/api/v1/admin/online-users`, {
        params: { window_sec: w },
      })
      setData(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(win) /* eslint-disable-next-line */ }, [win])

  useEffect(() => {
    if (!auto) return
    timer.current = setInterval(() => load(win), 30000)
    return () => clearInterval(timer.current)
  }, [auto, win]) // eslint-disable-line

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 p-4 overflow-y-auto"
      onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-3xl mt-10 mb-10"
        onClick={(e) => e.stopPropagation()}>

        {/* رأس */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <h2 className="font-bold">
              متصلون الآن
              {data && <span className="text-gray-400 font-normal text-sm"> ({data.count})</span>}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => load(win)} disabled={loading}
              className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition"
              title="تحديث">
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
            <button onClick={onClose}
              className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition">
              <X size={17} />
            </button>
          </div>
        </div>

        {/* أدوات */}
        <div className="px-5 py-3 border-b border-gray-700 flex flex-wrap items-center gap-3">
          <div className="flex items-center bg-gray-800 border border-gray-700 rounded-xl p-1">
            {WINDOWS.map((w) => (
              <button key={w.sec} onClick={() => setWin(w.sec)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  win === w.sec ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
                }`}>
                {w.label}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)}
              className="accent-blue-600" />
            تحديث تلقائي كل 30 ثانية
          </label>
          {data && Object.keys(data.by_plan || {}).length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap mr-auto">
              {Object.entries(data.by_plan).map(([plan, n]) => (
                <span key={plan}
                  className={`text-[11px] px-2 py-0.5 rounded-full ${PLAN_STYLE[plan] || 'bg-gray-700 text-gray-300'}`}>
                  {plan} {n}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* تعريف "متصل" — بالمتن لأن الزر بدونه يبدو عدّاد حضور */}
        <div className="mx-5 mt-3 text-[11px] text-gray-400 bg-gray-800/60 border border-gray-700 rounded-lg px-3 py-2 leading-relaxed">
          «متصل» = أرسل طلباً موثّقاً خلال المدة المختارة. فمن يفتح الصفحة ويتركها
          بلا تفاعل يسقط من القائمة رغم بقائه أمامها، ومن يستخدم بوت تلغرام فقط
          لا يظهر هنا إطلاقاً. <span className="text-gray-300">الرقم أدنى من الحضور
          الحقيقي لا أعلى.</span>
        </div>

        {/* المحتوى */}
        <div className="p-5">
          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-xl p-3 text-red-300 text-sm">
              {error}
            </div>
          )}

          {!error && data && data.count === 0 && (
            <div className="text-center py-10">
              <Users size={26} className="text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">لا أحد متصل خلال هذه المدة.</p>
              <p className="text-gray-600 text-xs mt-1">جرّب مدة أطول.</p>
            </div>
          )}

          {!error && data && data.count > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700">
                    {['المستخدم', 'الباقة', 'تلغرام', 'آخر نشاط'].map((h) => (
                      <th key={h} className="text-right pb-2 pr-3 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.users.map((u) => (
                    <tr key={u.id} className="border-b border-gray-800">
                      <td className="py-2.5 pr-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                            u.seconds_ago < 300 ? 'bg-green-400' : 'bg-gray-600'
                          }`} />
                          <div className="min-w-0">
                            <div className="text-white font-medium truncate">
                              {u.full_name || '—'}
                              {u.role === 'ADMIN' && (
                                <span className="mr-1.5 text-[10px] text-purple-400">مسؤول</span>
                              )}
                            </div>
                            <div className="text-gray-500 truncate" dir="ltr">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-2.5 pr-3">
                        <span className={`text-[11px] px-2 py-0.5 rounded-full ${
                          PLAN_STYLE[u.plan] || 'bg-gray-700 text-gray-300'
                        }`}>{u.plan}</span>
                      </td>
                      <td className="py-2.5 pr-3">
                        {u.telegram_id ? (
                          <span className="inline-flex items-center gap-1 text-blue-400">
                            <Send size={11} />
                            {u.telegram_username ? `@${u.telegram_username}` : 'مرتبط'}
                          </span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="py-2.5 pr-3 text-gray-400 font-mono">
                        منذ {ago(u.seconds_ago)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data && (
            <div className="mt-4 text-[11px] text-gray-600 text-left" dir="ltr">
              {String(data.generated_at).slice(11, 19)} UTC
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
