/**
 * ReviewForm (2026-10-17) — "اكتب رأيك" بصفحة الحساب (#review). متاح لمشترك مدفوع بعد 7 أيام من أول دفعة.
 * الخادم يتحقق من الأهلية (POST /api/v1/reviews)؛ أي تعديل يعيد الرأي "بانتظار المراجعة".
 */
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Star, MessageSquareQuote } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TAGS = [['gold', 'الذهب', 'Gold'], ['crypto', 'كريبتو', 'Crypto'], ['forex', 'فوركس', 'Forex'], ['stocks', 'الأسهم', 'Stocks'], ['learn', 'التعلّم', 'Learning']]
const STATUS = { pending: ['بانتظار المراجعة', 'Pending review', 'text-yellow-400'], approved: ['منشور', 'Published', 'text-green-400'], rejected: ['مرفوض', 'Rejected', 'text-red-400'] }

export default function ReviewForm({ isAr }) {
  const [info, setInfo] = useState(null)
  const [f, setF] = useState({ rating: 5, text: '', display_name: '', city: '', market_tag: 'gold', consent_public: false })
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = () => axios.get(`${API}/api/v1/reviews/mine`).then((r) => {
    setInfo(r.data)
    const rv = r.data.review
    if (rv) setF({ rating: rv.rating, text: rv.text, display_name: rv.display_name, city: rv.city || '', market_tag: rv.market_tag || 'gold', consent_public: true })
  }).catch(() => setInfo({ eligible: false, reason: 'error' }))
  useEffect(() => {
    load()
    if (window.location.hash === '#review') setTimeout(() => document.getElementById('review')?.scrollIntoView({ behavior: 'smooth' }), 400)
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setMsg(null)
    try {
      await axios.post(`${API}/api/v1/reviews`, f)
      setMsg({ ok: true, t: isAr ? 'شكراً! رأيك بانتظار المراجعة وسيظهر بعدها.' : 'Thank you! Your review is pending and will appear after review.' })
      load()
    } catch (err) {
      setMsg({ ok: false, t: err.response?.data?.detail || (isAr ? 'تعذّر الإرسال' : 'Could not submit') })
    } finally { setBusy(false) }
  }

  if (!info) return null
  const rv = info.review
  return (
    <div id="review" className="bg-gray-800 border border-gray-700 rounded-xl p-6">
      <h2 className="text-base font-semibold text-white mb-1 flex items-center gap-2">
        <MessageSquareQuote size={16} className="text-blue-400" /> {isAr ? 'رأيك في Qaffel' : 'Your review of Qaffel'}
      </h2>
      {!info.eligible && !rv ? (
        <p className="text-sm text-gray-400 leading-relaxed">
          {info.reason === 'too_soon'
            ? (isAr ? `يمكنك كتابة رأيك بعد ${info.days_left} يوم من اشتراكك، حتى يكون مبنياً على تجربة فعلية.` : `You can write a review in ${info.days_left} days, so it reflects real experience.`)
            : (isAr ? 'كتابة الرأي متاحة للمشتركين بعد 7 أيام من أول اشتراك مدفوع.' : 'Reviews are open to members 7 days after their first paid subscription.')}
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-4 mt-3">
          {rv && (
            <p className={`text-xs ${STATUS[rv.status]?.[2] || 'text-gray-400'}`}>
              {isAr ? 'حالة رأيك: ' : 'Status: '}{STATUS[rv.status]?.[isAr ? 0 : 1] || rv.status}
              {rv.status === 'rejected' && rv.reject_reason ? ` — ${rv.reject_reason}` : ''}
              {rv.status === 'approved' && (isAr ? ' · أي تعديل يعيده للمراجعة' : ' · editing sends it back for review')}
            </p>
          )}
          <div className="flex gap-1" role="radiogroup" aria-label={isAr ? 'التقييم' : 'Rating'}>
            {[1, 2, 3, 4, 5].map((k) => (
              <button key={k} type="button" onClick={() => setF({ ...f, rating: k })} aria-label={`${k}`} className="p-1">
                <Star size={24} className={k <= f.rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'} />
              </button>
            ))}
          </div>
          <textarea required minLength={20} maxLength={600} rows={4} value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })}
            placeholder={isAr ? 'اكتب تجربتك بصدق، الإيجابية والسلبية (20 إلى 600 حرف)' : 'Share your honest experience, good and bad (20–600 characters)'}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <div className="grid sm:grid-cols-2 gap-3">
            <input required minLength={2} maxLength={40} value={f.display_name} onChange={(e) => setF({ ...f, display_name: e.target.value })}
              placeholder={isAr ? 'الاسم المعروض (مثلاً: محمد ع.)' : 'Display name (e.g. Mohammed A.)'}
              className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm" />
            <input maxLength={40} value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })}
              placeholder={isAr ? 'المدينة (اختياري)' : 'City (optional)'}
              className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm" />
          </div>
          <div className="flex flex-wrap gap-2">
            {TAGS.map(([k, ar, en]) => (
              <button key={k} type="button" onClick={() => setF({ ...f, market_tag: k })}
                className={`text-xs px-3 py-1.5 rounded-full border ${f.market_tag === k ? 'border-blue-500 text-blue-300 bg-blue-900/30' : 'border-gray-600 text-gray-400'}`}>
                {isAr ? ar : en}
              </button>
            ))}
          </div>
          <label className="flex items-start gap-2 text-xs text-gray-400">
            <input type="checkbox" checked={f.consent_public} onChange={(e) => setF({ ...f, consent_public: e.target.checked })} className="mt-0.5" />
            {isAr ? 'أوافق على نشر رأيي باسمي المعروض في موقع Qaffel.' : 'I agree to publish my review under my display name on the Qaffel website.'}
          </label>
          <button type="submit" disabled={busy || !f.consent_public}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium text-white">
            {busy ? '...' : rv ? (isAr ? 'تحديث رأيي' : 'Update my review') : (isAr ? 'إرسال رأيي' : 'Submit review')}
          </button>
          {msg && <p className={`text-sm ${msg.ok ? 'text-green-400' : 'text-red-400'}`}>{msg.t}</p>}
        </form>
      )}
    </div>
  )
}
