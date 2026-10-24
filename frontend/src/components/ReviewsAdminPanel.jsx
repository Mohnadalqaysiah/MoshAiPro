/**
 * ReviewsAdminPanel (2026-10-17) — مراجعة آراء المشتركين + إدخال رأي حقيقي وصل خارج المنصة.
 * قاعدة: لا يُرفض رأي لأنه سلبي — الرفض للإساءة أو محتوى غير متعلق أو بيانات شخصية فقط (الخادم يطلب سبباً).
 */
import { useEffect, useState } from 'react'
import axios from 'axios'
import { RefreshCw, Star } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TABS = [['pending', 'بانتظار المراجعة'], ['approved', 'منشورة'], ['rejected', 'مرفوضة'], ['all', 'الكل']]
const REASONS = ['إساءة أو ألفاظ', 'محتوى غير متعلق بالمنصة', 'يحتوي بيانات شخصية', 'إعلان أو رابط']

// (2026-10-24) صورة/فيديو رأي من البوت — تُجلب عبر الخادم (رابط تيليجرام يحمل توكن البوت)، فـaxios+blob لا <img src>
function ReviewMedia({ id, type }) {
  const [url, setUrl] = useState(null)
  const [err, setErr] = useState(null)
  const show = () => axios.get(`${API}/api/v1/admin/reviews/${id}/media`, { responseType: 'blob' })
    .then((r) => setUrl(URL.createObjectURL(r.data))).catch((e) => setErr(e.response?.status === 502 ? 'تعذّر الجلب من تيليجرام' : 'خطأ'))
  if (url) return type === 'video'
    ? <video src={url} controls className="max-h-64 rounded-lg border border-gray-800" />
    : <img src={url} alt="" className="max-h-64 rounded-lg border border-gray-800" />
  return <button onClick={show} className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-200">
    {type === 'video' ? '🎬 عرض الفيديو' : '🖼 عرض الصورة'}{err && <span className="text-red-400"> — {err}</span>}
  </button>
}

const Stars = ({ n }) => <span className="inline-flex">{[1, 2, 3, 4, 5].map((k) => <Star key={k} size={13} className={k <= n ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'} />)}</span>

export default function ReviewsAdminPanel() {
  const [tab, setTab] = useState('pending')
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(null)
  const [reply, setReply] = useState({})
  const [imp, setImp] = useState({ display_name: '', rating: 5, text: '', market_tag: 'gold', source_note: 'رسالة تيليجرام', consent_confirmed: false })
  const [msg, setMsg] = useState('')

  const load = (t = tab) => axios.get(`${API}/api/v1/admin/reviews`, { params: { status: t } }).then((r) => setData(r.data)).catch((e) => setMsg(e.response?.data?.detail || e.message))
  useEffect(() => { load() }, [])

  const moderate = async (id, status, reject_reason) => {
    setBusy(id); setMsg('')
    try {
      const r = await axios.post(`${API}/api/v1/admin/reviews/${id}/moderate`, { status, admin_reply: reply[id] ?? undefined, reject_reason })
      // (2026-10-24) أول اعتماد يُنشر بالقناة — فشل النشر لا يُلغي الاعتماد لكن يُعرض هنا
      if (r.data?.channel === 'posted') setMsg('✅ اعتُمد ونُشر في قناة Qaffel')
      else if (r.data?.channel?.startsWith('failed')) setMsg(`⚠️ اعتُمد لكن تعذّر النشر بالقناة: ${r.data.channel.slice(8)}`)
      load()
    } catch (e) { setMsg(e.response?.data?.detail || e.message) } finally { setBusy(null) }
  }
  const doImport = async (e) => {
    e.preventDefault(); setMsg('')
    try {
      await axios.post(`${API}/api/v1/admin/reviews/import`, imp)
      setImp({ ...imp, display_name: '', text: '', consent_confirmed: false }); setMsg('✅ أُضيف ونُشر'); load()
    } catch (err) { setMsg(err.response?.data?.detail || err.message) }
  }

  const c = data?.counts || {}
  const approved = c.approved || 0
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold">آراء المشتركين</h2>
          <p className="text-xs text-gray-500 mt-1">
            المنشورة الآن: <b className="text-white">{approved}</b> · القسم يظهر بالصفحة الرئيسية عند 3 آراء منشورة، والمتوسط عند 10.
          </p>
        </div>
        <button onClick={() => load()} className="p-2 rounded-lg bg-gray-800 border border-gray-700"><RefreshCw size={14} /></button>
      </div>
      {msg && <div className="text-sm text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">{msg}</div>}

      <div className="flex gap-2 flex-wrap">
        {TABS.map(([k, l]) => (
          <button key={k} onClick={() => { setTab(k); load(k) }}
            className={`text-sm px-3 py-1.5 rounded-lg border ${tab === k ? 'border-blue-500 text-blue-400 bg-blue-900/20' : 'border-gray-700 text-gray-400'}`}>
            {l}{k !== 'all' && c[k] ? ` (${c[k]})` : ''}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {data?.items?.length === 0 && <p className="text-gray-500 text-sm">لا يوجد</p>}
        {data?.items?.map((r) => (
          <div key={r.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-3 text-sm">
                <Stars n={r.rating} />
                <b className="text-white">{r.display_name}</b>{r.city && <span className="text-gray-500">· {r.city}</span>}
                <span className="text-xs text-gray-500">{r.source === 'member' ? `مشترك · ${r.user_email || ''} · ${r.plan || ''}` : `مُدخل يدوياً · ${r.source_note}`}</span>
                {r.via === 'bot' && <span className="text-[11px] px-2 py-0.5 rounded-full bg-sky-900/40 text-sky-300 border border-sky-800">من البوت</span>}
                {r.anonymous && <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-800 text-gray-300 border border-gray-700">بدون اسم</span>}
                {r.status === 'approved' && <span className={`text-[11px] px-2 py-0.5 rounded-full border ${r.channel_posted ? 'bg-green-900/30 text-green-300 border-green-800' : 'bg-gray-800 text-gray-400 border-gray-700'}`}>{r.channel_posted ? 'منشور بالقناة' : 'غير منشور بالقناة'}</span>}
              </div>
              <span className="text-xs text-gray-500" dir="ltr">{r.created_at?.slice(0, 16).replace('T', ' ')}</span>
            </div>
            <p className="text-sm text-gray-200 leading-relaxed">{r.text}</p>
            {r.media_type && <ReviewMedia id={r.id} type={r.media_type} />}
            {r.reject_reason && <p className="text-xs text-red-400">سبب الرفض: {r.reject_reason}</p>}
            <textarea rows={2} placeholder="رد الفريق (اختياري — يظهر تحت الرأي)" defaultValue={r.admin_reply || ''}
              onChange={(e) => setReply({ ...reply, [r.id]: e.target.value })}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white" />
            <div className="flex flex-wrap gap-2 items-center">
              <button disabled={busy === r.id} onClick={() => moderate(r.id, 'approved')} className="text-xs px-3 py-1.5 rounded-lg bg-green-600/20 text-green-300 border border-green-600/40">
                {r.status === 'approved' ? 'حفظ الرد' : 'اعتماد ونشر'}
              </button>
              <select defaultValue="" onChange={(e) => e.target.value && moderate(r.id, 'rejected', e.target.value)}
                className="text-xs px-2 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-red-300">
                <option value="">رفض بسبب…</option>
                {REASONS.map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
              <span className="text-[11px] text-gray-500">الرأي السلبي يُنشر — الرفض فقط لهذه الأسباب.</span>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={doImport} className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
        <h3 className="font-semibold text-sm">إضافة رأي حقيقي وصلك خارج المنصة</h3>
        <p className="text-xs text-gray-500 leading-relaxed">
          مثل رسالة شكر من مشترك على تيليجرام. يظهر بعبارة "وصلنا عبر …" وبدون شارة "مشترك موثّق". انسخ كلامه كما هو، وبعد موافقته على النشر فقط.
        </p>
        <div className="grid sm:grid-cols-3 gap-2">
          <input required placeholder="الاسم المعروض (مثلاً: سارة م.)" value={imp.display_name} onChange={(e) => setImp({ ...imp, display_name: e.target.value })} className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white" />
          <input required placeholder="المصدر (رسالة تيليجرام…)" value={imp.source_note} onChange={(e) => setImp({ ...imp, source_note: e.target.value })} className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white" />
          <select value={imp.rating} onChange={(e) => setImp({ ...imp, rating: Number(e.target.value) })} className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white">
            {[5, 4, 3, 2, 1].map((k) => <option key={k} value={k}>{k} نجوم</option>)}
          </select>
        </div>
        <textarea required minLength={20} maxLength={600} rows={3} placeholder="نص الرأي كما كتبه صاحبه" value={imp.text} onChange={(e) => setImp({ ...imp, text: e.target.value })} className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white" />
        <label className="flex items-start gap-2 text-xs text-gray-300">
          <input type="checkbox" checked={imp.consent_confirmed} onChange={(e) => setImp({ ...imp, consent_confirmed: e.target.checked })} className="mt-0.5" />
          أؤكد أن هذا رأي حقيقي من شخص حقيقي، منقول كما كتبه، وأنه وافق على نشره.
        </label>
        <button type="submit" disabled={!imp.consent_confirmed} className="text-sm px-4 py-2 rounded-lg bg-blue-600 disabled:opacity-40 text-white">إضافة ونشر</button>
      </form>
    </div>
  )
}
