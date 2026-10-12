import { useState } from 'react'
import axios from 'axios'
import { RefreshCw, Users } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// (2026-10-12) الحسابات المشتركة بنفس IP التسجيل — لكشف من يفتح حسابات متعددة
// (غالباً لتكرار الفترة التجريبية). مؤشر لا دليل: شبكات الجوال والعائلة
// والمقاهي تشترك بنفس IP، فالقرار بعد النظر بالتفاصيل.
const SUSP = {
  high:   { label: 'اشتباه عالٍ',  cls: 'bg-red-900/40 text-red-300 border-red-700/50' },
  medium: { label: 'اشتباه متوسط', cls: 'bg-amber-900/30 text-amber-300 border-amber-700/50' },
  low:    { label: 'اشتباه منخفض', cls: 'bg-gray-800 text-gray-400 border-gray-700' },
}
const fmt = d => d ? new Date(d).toLocaleString('ar-EG', { dateStyle: 'short', timeStyle: 'short' }) : '—'

export default function IpGroupsPanel({ onOpenUser }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen]       = useState({})

  const load = async () => {
    setLoading(true)
    try { const r = await axios.get(`${API}/api/v1/admin/ip-groups`); setData(r.data) }
    catch (_) { setData({ groups: [], error: true }) }
    finally { setLoading(false) }
  }

  if (!data) {
    return (
      <button onClick={load} disabled={loading}
        className="inline-flex items-center gap-2 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-200 px-3 py-1.5 rounded-lg transition">
        {loading ? <RefreshCw size={12} className="animate-spin" /> : <Users size={12} />}
        كشف الحسابات المتعددة (نفس IP)
      </button>
    )
  }

  return (
    <div className="w-full bg-gray-900 border border-gray-800 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <h3 className="text-sm font-semibold text-gray-200">
          الحسابات المشتركة بنفس IP التسجيل <span className="text-gray-500 font-normal">({data.count || 0} مجموعة)</span>
        </h3>
        <div className="flex gap-2">
          <button onClick={load} className="text-xs text-gray-400 hover:text-white flex items-center gap-1"><RefreshCw size={12} /> تحديث</button>
          <button onClick={() => setData(null)} className="text-xs text-gray-500 hover:text-white">إغلاق</button>
        </div>
      </div>
      <p className="text-[11px] text-gray-500 mb-3">
        مؤشر لا دليل: شبكات الجوال والعائلة والمكاتب قد تشترك بنفس IP. الاشتباه العالي = حسابان تجريبيان أو أكثر سُجّلا خلال 72 ساعة.
      </p>
      {data.error && <p className="text-xs text-red-400">تعذّر التحميل.</p>}
      {data.groups?.length === 0 && !data.error && <p className="text-xs text-gray-400">لا توجد حسابات تشترك بنفس IP.</p>}
      <div className="space-y-2 max-h-[60vh] overflow-y-auto">
        {(data.groups || []).map(g => {
          const s = SUSP[g.suspicion] || SUSP.low
          return (
            <div key={g.ip} className="bg-gray-800/50 rounded-lg">
              <button onClick={() => setOpen(o => ({ ...o, [g.ip]: !o[g.ip] }))}
                className="w-full flex items-center justify-between gap-2 flex-wrap px-3 py-2 text-xs text-right">
                <span className="font-mono text-gray-200">{g.ip}</span>
                <span className="flex items-center gap-2 flex-wrap">
                  <span className="text-gray-300">{g.count} حسابات</span>
                  {g.trial_accounts > 0 && <span className="text-gray-400">· {g.trial_accounts} تجريبي</span>}
                  <span className="text-gray-500">· خلال {g.span_hours < 48 ? `${g.span_hours} ساعة` : `${Math.round(g.span_hours / 24)} يوم`}</span>
                  {g.internal_ip
                    ? <span className="px-2 py-0.5 rounded-full border bg-blue-900/30 text-blue-300 border-blue-700/50">IP داخلي — خلل تمرير لا شخص</span>
                    : <span className={`px-2 py-0.5 rounded-full border ${s.cls}`}>{s.label}</span>}
                </span>
              </button>
              {open[g.ip] && (
                <div className="border-t border-gray-700/50 px-3 py-2 space-y-1">
                  {g.members.map(m => (
                    <div key={m.id} className="flex items-center justify-between gap-2 flex-wrap text-[11px]">
                      <button onClick={() => onOpenUser?.(m.id)} className="text-blue-300 hover:underline text-right">
                        {m.full_name || '—'} · {m.email}
                      </button>
                      <span className="text-gray-400 flex gap-2 flex-wrap">
                        <span>{m.plan}</span>
                        {m.telegram && <span>تيليجرام: {m.telegram}</span>}
                        {!m.verified && <span className="text-amber-400">غير مؤكَّد</span>}
                        {!m.active && <span className="text-red-400">معطّل</span>}
                        <span>سجّل {fmt(m.created_at)}</span>
                        <span>آخر ظهور {fmt(m.last_seen_at)}</span>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
