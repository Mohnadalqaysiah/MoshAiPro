import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useLang } from '../contexts/LangContext'
import { Sparkles, Check, X, Zap, TrendingUp, Bell, Layers } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const COPY = {
  trial_expired: {
    ar: { title: 'انتهت الفترة التجريبية', sub: 'أسبوعك المجاني خلص — اشترك للمتابعة واستقبال الإشارات على تيليجرام.' },
    en: { title: 'Your Free Trial Ended', sub: 'Your free week is over — subscribe to keep receiving signals on Telegram.' },
  },
  limit_reached: {
    ar: { title: 'استنفدت حصتك اليومية المجانية', sub: 'اشترك للحصول على تحليلات وإشارات غير محدودة على كل الأسواق.' },
    en: { title: "You've used your free daily quota", sub: 'Subscribe for unlimited analysis and signals across all markets.' },
  },
  premium: {
    ar: { title: 'هذه الميزة للمشتركين', sub: 'فعّل اشتراكك للوصول الكامل لكل أدوات المنصة.' },
    en: { title: 'This is a subscriber feature', sub: 'Activate your subscription for full access to every tool.' },
  },
}

const BENEFITS = {
  ar: [
    { icon: Bell,       text: 'إشارات فورية على تيليجرام — ذهب، فوركس، كريبتو، مؤشرات' },
    { icon: TrendingUp, text: 'تحليل ICT/SMC كامل: دخول، وقف، هدفان، ونسبة مخاطرة/عائد' },
    { icon: Layers,     text: 'أداة بناء الاستراتيجيات — تراقبها المنصة وترسل تنبيهاً عند تحققها' },
    { icon: Zap,        text: 'تحليلات غير محدودة على كل الأسواق' },
  ],
  en: [
    { icon: Bell,       text: 'Instant Telegram signals — Gold, Forex, Crypto, Indices' },
    { icon: TrendingUp, text: 'Full ICT/SMC analysis: entry, stop, two targets, R/R' },
    { icon: Layers,     text: 'Strategy Builder — the platform monitors it and alerts on trigger' },
    { icon: Zap,        text: 'Unlimited analysis across every market' },
  ],
}

export default function UpgradeModal({ open, onClose, reason = 'trial_expired' }) {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const navigate = useNavigate()
  const [plans, setPlans] = useState(null)

  useEffect(() => {
    if (!open || plans) return
    axios.get(`${API}/api/v1/subscription/plans`)
      .then(r => setPlans(r.data?.plans || null))
      .catch(() => {})
  }, [open, plans])

  useEffect(() => {
    if (!open) return
    const onKey = e => { if (e.key === 'Escape') onClose?.() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const c = (COPY[reason] || COPY.trial_expired)[isAr ? 'ar' : 'en']
  const benefits = BENEFITS[isAr ? 'ar' : 'en']
  const weekly  = plans?.weekly?.price_usd
  const monthly = plans?.monthly?.price_usd

  const goPricing = () => { onClose?.(); navigate('/pricing') }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4"
      style={{ background: 'rgba(4,5,7,0.78)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
      dir={isAr ? 'rtl' : 'ltr'}
      role="dialog"
      aria-modal="true"
    >
      <div
        onClick={e => e.stopPropagation()}
        className="relative w-full max-w-md rounded-3xl overflow-hidden q-panel border q-line"
        style={{ boxShadow: '0 30px 80px rgba(124,58,237,0.35)' }}
      >
        {/* glow header */}
        <div className="relative px-6 pt-7 pb-5 text-center overflow-hidden">
          <div
            className="absolute inset-x-0 -top-16 h-40 opacity-70 pointer-events-none"
            style={{ background: 'radial-gradient(circle, var(--q-acc2, #7C3AED) 0%, transparent 70%)' }}
          />
          <button
            onClick={onClose}
            className="absolute top-3 end-3 text-gray-400 hover:text-white p-1 rounded-lg"
            aria-label={isAr ? 'إغلاق' : 'Close'}
          >
            <X size={18} />
          </button>
          <div className="relative mx-auto w-14 h-14 rounded-2xl grid place-items-center mb-3"
            style={{ background: 'linear-gradient(135deg, var(--q-acc1,#FF4FD8), var(--q-acc2,#7C3AED))' }}>
            <Sparkles size={26} className="text-white" />
          </div>
          <h2 className="relative text-xl font-black text-white">{c.title}</h2>
          <p className="relative text-sm text-gray-300 mt-1.5 leading-relaxed">{c.sub}</p>
        </div>

        {/* benefits */}
        <div className="px-6 pb-2 space-y-2.5">
          {benefits.map((b, i) => (
            <div key={i} className="flex items-start gap-2.5 text-[13px] text-gray-200">
              <span className="mt-0.5 w-5 h-5 rounded-md grid place-items-center flex-shrink-0"
                style={{ background: 'var(--q-glass2, rgba(255,255,255,.09))' }}>
                <b.icon size={12} style={{ color: 'var(--q-acc3, #22D3EE)' }} />
              </span>
              <span>{b.text}</span>
            </div>
          ))}
        </div>

        {/* price chips */}
        {(weekly || monthly) && (
          <div className="px-6 pt-4 flex items-center justify-center gap-2.5">
            {weekly != null && (
              <div className="flex-1 text-center rounded-xl py-2.5 q-glass border q-line">
                <div className="text-[11px] text-gray-400">{isAr ? 'أسبوعي' : 'Weekly'}</div>
                <div className="text-lg font-bold text-white">${weekly}</div>
              </div>
            )}
            {monthly != null && (
              <div className="flex-1 text-center rounded-xl py-2.5 border"
                style={{ borderColor: 'var(--q-acc1,#FF4FD8)', background: 'linear-gradient(135deg, rgba(255,79,216,0.12), rgba(124,58,237,0.14))' }}>
                <div className="text-[11px]" style={{ color: 'var(--q-acc1,#FF4FD8)' }}>{isAr ? 'شهري — الأوفر' : 'Monthly — best value'}</div>
                <div className="text-lg font-bold text-white">${monthly}</div>
              </div>
            )}
          </div>
        )}

        {/* CTA */}
        <div className="px-6 pt-4 pb-6">
          <button
            onClick={goPricing}
            className="w-full q-cta text-white rounded-xl py-3 font-bold text-sm flex items-center justify-center gap-2 transition-all"
          >
            <Zap size={15} className="fill-white" />
            {isAr ? 'عرض الباقات والاشتراك' : 'View Plans & Subscribe'}
          </button>
          <button
            onClick={onClose}
            className="w-full text-gray-400 hover:text-white text-xs mt-2.5 py-1"
          >
            {isAr ? 'لاحقاً' : 'Later'}
          </button>
        </div>
      </div>
    </div>
  )
}
