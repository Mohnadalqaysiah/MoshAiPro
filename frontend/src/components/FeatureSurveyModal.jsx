import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { Lightbulb, X, Send } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function FeatureSurveyModal({ onDone }) {
  const { refreshUser } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'

  // (2026-09-27) السؤال والخيارات صارت قابلة للتعديل من لوحة الأدمن —
  // تُجلَب هون بدل نص ثابت بالكود (راجع GET /auth/feature-survey/active).
  const [survey, setSurvey]   = useState(null)
  const [loading, setLoading] = useState(true)

  const [selected, setSelected] = useState('')
  const [customText, setCustomText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    axios.get(`${API}/api/v1/auth/feature-survey/active`)
      .then(r => setSurvey(r.data?.active ? r.data : null))
      .catch(() => setSurvey(null))
      .finally(() => setLoading(false))
  }, [])

  const close = () => onDone?.()

  const skip = async () => {
    try { await axios.post(`${API}/api/v1/auth/feature-survey/skip`) } catch { /* noop */ }
    refreshUser?.()
    close()
  }

  const submit = async () => {
    if (!selected) {
      setError(isAr ? 'اختر إجابة واحدة على الأقل' : 'Please pick one option')
      return
    }
    setSending(true); setError('')
    try {
      await axios.post(`${API}/api/v1/auth/feature-survey/submit`, {
        selected_option: selected,
        custom_text: selected === 'other' ? customText.trim() : '',
      })
      refreshUser?.()
      close()
    } catch (e) {
      setError(e.response?.data?.detail || (isAr ? 'تعذّر الإرسال — حاول مرة أخرى' : 'Could not submit — try again'))
    } finally {
      setSending(false)
    }
  }

  // لا استطلاع نشط، أو لسا قيد التحميل — لا نعرض شيء (بدل شاشة فاضية تومض)
  if (loading || !survey) return null

  const options = survey.options || []

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4"
      style={{ background: 'rgba(4,5,7,0.78)', backdropFilter: 'blur(4px)' }}
      onClick={skip}
      dir={isAr ? 'rtl' : 'ltr'}
      role="dialog"
      aria-modal="true"
    >
      <div
        onClick={e => e.stopPropagation()}
        className="relative w-full max-w-md rounded-3xl overflow-hidden q-panel border q-line p-6"
        style={{ boxShadow: '0 30px 80px rgba(59,130,246,0.2)' }}
      >
        <button onClick={skip} className="absolute top-3 end-3 text-gray-400 hover:text-white p-1" aria-label={isAr ? 'تخطّي' : 'Skip'}>
          <X size={18} />
        </button>

        <div className="text-center mb-5">
          <div className="mx-auto w-14 h-14 rounded-2xl grid place-items-center mb-3 bg-blue-500/15 border border-blue-500/30">
            <Lightbulb size={26} className="text-blue-300" />
          </div>
          <h2 className="text-lg font-black text-white">{isAr ? 'ساعدنا نطور المنصة لك' : 'Help Us Improve the Platform'}</h2>
          <p className="text-sm text-gray-400 mt-1.5">
            {isAr ? survey.question_ar : survey.question_en}
          </p>
        </div>

        <div className="space-y-2 mb-4">
          {options.map(opt => (
            <label key={opt.key}
              className={`flex items-start gap-3 rounded-xl border px-3.5 py-3 cursor-pointer transition-colors ${
                selected === opt.key ? 'border-blue-500/60 bg-blue-500/10' : 'border-gray-700/60 hover:border-gray-600'
              }`}>
              <input
                type="radio" name="feature_survey_option" className="mt-0.5 accent-blue-500"
                checked={selected === opt.key}
                onChange={() => { setSelected(opt.key); setError('') }}
              />
              <span className="text-sm text-gray-200 leading-relaxed">{isAr ? opt.ar : opt.en}</span>
            </label>
          ))}
        </div>

        {selected === 'other' && (
          <input
            type="text" value={customText} maxLength={200}
            onChange={e => setCustomText(e.target.value)}
            placeholder={isAr ? 'اكتب اقتراحك هنا (اختياري)...' : 'Write your suggestion here (optional)...'}
            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-white mb-4 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        )}

        {error && <p className="text-red-400 text-xs mb-3 text-center">{error}</p>}

        <div className="flex items-center gap-2.5">
          <button onClick={skip} disabled={sending}
            className="flex-1 rounded-xl py-2.5 text-sm font-semibold text-gray-400 hover:text-white bg-gray-800/60 hover:bg-gray-800 disabled:opacity-50 transition-colors">
            {isAr ? 'تخطّي' : 'Skip'}
          </button>
          <button onClick={submit} disabled={sending}
            className="flex-[2] flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-bold bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white transition-colors">
            {sending ? '...' : <><Send size={14} />{isAr ? 'إرسال' : 'Submit'}</>}
          </button>
        </div>
      </div>
    </div>
  )
}
