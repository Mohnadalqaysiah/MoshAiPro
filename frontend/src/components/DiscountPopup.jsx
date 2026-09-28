import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { PartyPopper, X, Sparkles, ArrowLeft, ArrowRight } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DISMISS_KEY = 'qaffel_promo_dismissed_at'
const DISMISS_COOLDOWN_MS = 3 * 24 * 60 * 60 * 1000   // 3 أيام
const SHOW_DELAY_MS = 12000                            // ظهور مفاجئ لا فوري

// (2026-09-28) بوب أب خصم مفاجئ — الإعداد بالكامل من SiteSettings عبر
// GET /subscription/promo-popup (بلا نشر كود لتفعيله/تغيير رمزه/نسبته).
// حصراً لمستخدمي التجربة (trial) — الهدف تحويل أول اشتراك حقيقي، لا خصم
// لمشترك فعلي أصلاً.
export default function DiscountPopup() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const navigate = useNavigate()

  const [promo, setPromo] = useState(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!user || user.plan !== 'trial') return

    const lastDismissed = Number(localStorage.getItem(DISMISS_KEY) || 0)
    if (Date.now() - lastDismissed < DISMISS_COOLDOWN_MS) return

    let cancelled = false
    axios.get(`${API}/api/v1/subscription/promo-popup`)
      .then(r => {
        if (cancelled || !r.data?.enabled) return
        setPromo(r.data)
        const t = setTimeout(() => { if (!cancelled) setVisible(true) }, SHOW_DELAY_MS)
        return () => clearTimeout(t)
      })
      .catch(() => {})

    return () => { cancelled = true }
  }, [user])

  if (!visible || !promo) return null

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()))
    setVisible(false)
  }

  const claim = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()))
    navigate(`/pricing?coupon=${encodeURIComponent(promo.code)}&plan=${promo.plan}`)
  }

  const planLabel = isAr ? promo.plan_name : (promo.plan_name_en || promo.plan_name)
  const Arrow = isAr ? ArrowLeft : ArrowRight

  return (
    <div
      className="fixed inset-0 z-[75] flex items-center justify-center p-4"
      style={{ background: 'rgba(4,5,7,0.82)', backdropFilter: 'blur(4px)' }}
      onClick={dismiss}
      dir={isAr ? 'rtl' : 'ltr'}
      role="dialog"
      aria-modal="true"
    >
      <div
        onClick={e => e.stopPropagation()}
        className="relative w-full max-w-sm rounded-3xl overflow-hidden text-center"
        style={{
          background: 'linear-gradient(160deg, #1e1b4b 0%, #0B1020 55%, #0B1020 100%)',
          border: '1px solid rgba(139,92,246,0.35)',
          boxShadow: '0 30px 90px rgba(139,92,246,0.35), 0 0 0 1px rgba(255,255,255,0.03)',
        }}
      >
        {/* توهّج زخرفي */}
        <div className="absolute -top-16 -inset-x-10 h-40 opacity-40 blur-3xl"
          style={{ background: 'radial-gradient(60% 100% at 50% 0%, #8B5CF6, transparent)' }} />

        <button onClick={dismiss} className="absolute top-3 end-3 z-10 text-gray-400 hover:text-white p-1" aria-label={isAr ? 'إغلاق' : 'Close'}>
          <X size={18} />
        </button>

        <div className="relative px-6 pt-9 pb-7">
          <div className="mx-auto w-16 h-16 rounded-2xl grid place-items-center mb-4 animate-bounce"
            style={{ background: 'linear-gradient(135deg,#F59E0B,#EF4444)', boxShadow: '0 8px 30px rgba(239,68,68,0.4)' }}>
            <PartyPopper size={30} className="text-white" />
          </div>

          <p className="text-xs font-bold tracking-wider text-purple-300 flex items-center justify-center gap-1 mb-1">
            <Sparkles size={12} /> {isAr ? 'عرض خاص ومفاجئ' : 'A SPECIAL SURPRISE'}
          </p>
          <h2 className="text-3xl font-black text-white mb-1">
            {isAr ? `خصم ${promo.discount_percent}%` : `${promo.discount_percent}% OFF`}
          </h2>
          <p className="text-sm text-gray-400 mb-5">
            {isAr
              ? `على باقة ${planLabel} — لفترة محدودة`
              : `on the ${planLabel} plan — limited time`}
          </p>

          <div className="flex items-center justify-center gap-3 mb-6">
            <span className="text-gray-500 line-through text-lg">${promo.price_before}</span>
            <span className="text-emerald-400 font-black text-3xl">${promo.price_after}</span>
          </div>

          <button
            onClick={claim}
            className="w-full flex items-center justify-center gap-2 rounded-2xl py-3.5 text-base font-bold text-white transition-transform hover:scale-[1.02] active:scale-95"
            style={{
              background: 'linear-gradient(135deg,#8B5CF6,#EC4899)',
              boxShadow: '0 10px 30px rgba(236,72,153,0.35)',
            }}
          >
            {isAr ? 'فعّل العرض الآن' : 'Claim This Offer'}
            <Arrow size={18} />
          </button>

          <button onClick={dismiss} className="mt-3 text-xs text-gray-500 hover:text-gray-300 transition-colors">
            {isAr ? 'ليس الآن' : 'Not now'}
          </button>
        </div>
      </div>
    </div>
  )
}
