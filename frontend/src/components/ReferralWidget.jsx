/**
 * ReferralWidget — بطاقة نقاط الإحالة التفاعلية
 * تُعرض في الـ Dashboard لتشجيع المستخدم على دعوة أصدقائه
 */
import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { Copy, CheckCircle, Gift, Users, Zap, ChevronRight, Sparkles } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ─── مكوّن عداد الأرقام المتحرك ────────────────────────────────────────────
function CountUp({ value, duration = 800 }) {
  const [display, setDisplay] = useState(0)
  const prev = useRef(0)

  useEffect(() => {
    const start = prev.current
    const end   = value
    if (start === end) return
    const steps   = 30
    const step    = (end - start) / steps
    const interval = duration / steps
    let current   = start
    const timer = setInterval(() => {
      current += step
      if ((step > 0 && current >= end) || (step < 0 && current <= end)) {
        setDisplay(end)
        prev.current = end
        clearInterval(timer)
      } else {
        setDisplay(Math.round(current))
      }
    }, interval)
    return () => clearInterval(timer)
  }, [value, duration])

  return <span>{display}</span>
}

// ─── دائرة التقدم ────────────────────────────────────────────────────────────
function CircleProgress({ pct, size = 80, stroke = 6, children }) {
  const r  = (size - stroke) / 2
  const c  = 2 * Math.PI * r
  const offset = c - (pct / 100) * c

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Track */}
        <circle cx={size/2} cy={size/2} r={r} fill="none"
          stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        {/* Progress */}
        <circle cx={size/2} cy={size/2} r={r} fill="none"
          stroke="url(#grad)" strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        <defs>
          <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#a78bfa" />
            <stop offset="100%" stopColor="#60a5fa" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  )
}

// ─── الـ Widget الرئيسي ───────────────────────────────────────────────────────
export default function ReferralWidget() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [copied,   setCopied]   = useState(false)
  const [redeeming,setRedeeming]= useState(false)
  const [redeemMsg,setRedeemMsg]= useState(null)
  const [expanded, setExpanded] = useState(false)

  const fetch = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/affiliate/points-summary`)
      setData(res.data)
    } catch { /* silently ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetch() }, [])

  const copyLink = () => {
    if (!data?.referral_link) return
    navigator.clipboard.writeText(data.referral_link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const redeem = async () => {
    setRedeeming(true)
    setRedeemMsg(null)
    try {
      const res = await axios.post(`${API}/api/v1/affiliate/redeem-points`)
      setRedeemMsg({ ok: true, text: res.data.message })
      await fetch()  // refresh
    } catch (e) {
      setRedeemMsg({ ok: false, text: e.response?.data?.detail || 'حدث خطأ' })
    } finally {
      setRedeeming(false)
      setTimeout(() => setRedeemMsg(null), 3500)
    }
  }

  if (loading) return (
    <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl p-5 animate-pulse h-32" />
  )
  if (!data) return null

  const {
    points = 0,
    analyses_available = 0,
    points_to_next = 0,
    progress_pct = 0,
    total_referrals = 0,
    referral_link = '',
    referral_code = '',
    points_per_register = 10,
    points_per_subscribe = 50,
    points_per_analysis = 20,
  } = data

  const canRedeem = points >= points_per_analysis

  return (
    <div className="bg-gradient-to-br from-violet-950/60 via-gray-900/80 to-blue-950/40 border border-violet-700/30 rounded-2xl overflow-hidden" dir="rtl">

      {/* ── Header ── */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer select-none"
        onClick={() => setExpanded(p => !p)}
      >
        <div className="flex items-center gap-3">
          {/* أيقونة جوهرة */}
          <div className="relative w-9 h-9 flex items-center justify-center rounded-xl bg-violet-500/20 border border-violet-500/30">
            <Sparkles size={16} className="text-violet-400" />
            {points > 0 && (
              <span className="absolute -top-1.5 -left-1.5 w-4 h-4 text-[10px] font-bold rounded-full bg-violet-500 text-white flex items-center justify-center leading-none">
                ✦
              </span>
            )}
          </div>
          <div>
            <h3 className="text-white font-semibold text-sm leading-tight">نقاط الإحالة</h3>
            <p className="text-violet-300/70 text-xs mt-0.5">
              ادعُ أصدقاءك واكسب تحليلات مجانية
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* عداد النقاط */}
          <div className="text-right">
            <p className="text-xl font-bold text-white leading-none">
              <CountUp value={points} />
            </p>
            <p className="text-xs text-violet-300/60 mt-0.5">نقطة</p>
          </div>
          <ChevronRight
            size={16}
            className={`text-gray-500 transition-transform duration-200 ${expanded ? 'rotate-90' : '-rotate-90'}`}
          />
        </div>
      </div>

      {/* ── شريط التقدم المضغوط ── */}
      <div className="px-5 pb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-gray-400">
            {canRedeem
              ? `🎉 لديك ${analyses_available} تحليل${analyses_available > 1 ? ' مجاني' : ' مجاني'} جاهز!`
              : `${points_to_next} نقطة للتحليل المجاني التالي`}
          </span>
          <span className="text-xs text-gray-500">{Math.round(progress_pct)}%</span>
        </div>
        <div className="h-1.5 bg-gray-700/60 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all duration-700"
            style={{ width: `${Math.min(progress_pct, 100)}%` }}
          />
        </div>
      </div>

      {/* ── المحتوى الموسّع ── */}
      {expanded && (
        <div className="border-t border-gray-700/40 px-5 py-5 space-y-5">

          {/* الإحصائيات */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { icon: <Users size={14} />, label: 'مدعوّون', value: total_referrals, color: 'text-blue-400' },
              { icon: <Zap size={14} />,   label: 'نقطة',    value: points,           color: 'text-violet-400' },
              { icon: <Gift size={14} />,  label: 'تحليلات', value: analyses_available, color: 'text-green-400' },
            ].map((s, i) => (
              <div key={i} className="bg-gray-800/50 rounded-xl p-3 text-center border border-gray-700/40">
                <div className={`flex justify-center mb-1 ${s.color}`}>{s.icon}</div>
                <p className="text-white font-bold text-lg leading-none"><CountUp value={s.value} /></p>
                <p className="text-gray-500 text-xs mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* دائرة التقدم */}
          <div className="flex items-center gap-5">
            <CircleProgress pct={Math.min(progress_pct, 100)} size={80} stroke={6}>
              <span className="text-white text-sm font-bold">{Math.round(progress_pct)}%</span>
            </CircleProgress>
            <div className="flex-1 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">عند التسجيل</span>
                <span className="text-violet-300 font-semibold">+{points_per_register} نقطة</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">عند الاشتراك</span>
                <span className="text-yellow-300 font-semibold">+{points_per_subscribe} نقطة</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">كل تحليل مجاني</span>
                <span className="text-green-300 font-semibold">{points_per_analysis} نقطة</span>
              </div>
            </div>
          </div>

          {/* رابط الإحالة */}
          <div>
            <p className="text-xs text-gray-400 mb-2">رابط الإحالة الخاص بك</p>
            <div className="flex items-center gap-2 bg-gray-800/70 border border-gray-700/50 rounded-xl px-3 py-2.5">
              <span className="flex-1 text-xs text-gray-300 font-mono truncate">{referral_link}</span>
              <button
                onClick={copyLink}
                className="flex-shrink-0 flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-violet-600/30 hover:bg-violet-600/50 text-violet-300 hover:text-white border border-violet-600/30 transition-all"
              >
                {copied
                  ? <><CheckCircle size={12} className="text-green-400" /> تم!</>
                  : <><Copy size={12} /> نسخ</>}
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-1.5">كود الإحالة: <span className="text-gray-400 font-mono">{referral_code}</span></p>
          </div>

          {/* زر الاستبدال */}
          {redeemMsg && (
            <div className={`text-xs px-3 py-2 rounded-lg ${redeemMsg.ok ? 'bg-green-900/40 text-green-300 border border-green-700/40' : 'bg-red-900/40 text-red-300 border border-red-700/40'}`}>
              {redeemMsg.text}
            </div>
          )}

          <button
            onClick={redeem}
            disabled={!canRedeem || redeeming}
            className={`w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2
              ${canRedeem
                ? 'bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white shadow-lg shadow-violet-900/30 hover:shadow-violet-700/40 active:scale-95'
                : 'bg-gray-700/40 text-gray-500 cursor-not-allowed border border-gray-700/40'
              }`}
          >
            {redeeming ? (
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
            ) : (
              <Gift size={15} />
            )}
            {canRedeem
              ? `استبدل ${points_per_analysis} نقطة بتحليل مجاني`
              : `تحتاج ${points_per_analysis} نقطة للاستبدال`}
          </button>

        </div>
      )}
    </div>
  )
}
