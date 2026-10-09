import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useSiteSettings from '../hooks/useSiteSettings'
import { User, Mail, Phone, Lock, Save, CheckCircle, AlertCircle, Gift, Copy, ExternalLink, Users, DollarSign } from 'lucide-react'
import TradingPreferencesPanel from '../components/TradingPreferencesPanel'

import { subscriptionCta } from '../utils/subscriptionCta'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Profile() {
  const { user, token, refreshUser } = useAuth()
  const siteSettings = useSiteSettings()
  const { lang } = useLang()
  const isAr = lang === 'ar'

  const [profile, setProfile] = useState({ full_name: user?.full_name || '', phone_number: user?.phone_number || '' })
  const [pw, setPw]           = useState({ old_password: '', new_password: '', confirm: '' })

  const [profileMsg, setProfileMsg] = useState(null)
  const [pwMsg,      setPwMsg]      = useState(null)
  const [loading,    setLoading]    = useState('')

  // Affiliate state
  const [affiliate, setAffiliate] = useState(null)
  const [copied,    setCopied]    = useState(false)

  useEffect(() => {
    axios.get(`${API}/api/v1/affiliate/dashboard`)
      .then(r => setAffiliate(r.data))
      .catch(() => {})
  }, [])

  const copyLink = () => {
    if (!affiliate?.referral_link) return
    navigator.clipboard.writeText(affiliate.referral_link).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const headers = { Authorization: `Bearer ${token}` }

  const Msg = ({ msg }) => msg ? (
    <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mt-3 ${
      msg.type === 'ok' ? 'bg-green-900/30 border border-green-700/40 text-green-400' : 'bg-red-900/30 border border-red-700/40 text-red-400'
    }`}>
      {msg.type === 'ok' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
      {msg.text}
    </div>
  ) : null

  const saveProfile = async e => {
    e.preventDefault(); setLoading('profile'); setProfileMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/profile`, profile, { headers })
      await refreshUser()
      setProfileMsg({ type: 'ok', text: isAr ? 'تم حفظ البيانات الشخصية' : 'Profile saved' })
    } catch (err) {
      setProfileMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
    } finally { setLoading('') }
  }

  const changePassword = async e => {
    e.preventDefault()
    if (pw.new_password !== pw.confirm) { setPwMsg({ type: 'err', text: isAr ? 'كلمتا المرور غير متطابقتين' : 'Passwords do not match' }); return }
    if (pw.new_password.length < 8)    { setPwMsg({ type: 'err', text: isAr ? 'كلمة المرور يجب 8 أحرف+' : 'Password must be 8+ chars' }); return }
    setLoading('pw'); setPwMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/change-password`, { old_password: pw.old_password, new_password: pw.new_password }, { headers })
      setPwMsg({ type: 'ok', text: isAr ? 'تم تغيير كلمة المرور' : 'Password changed' })
      setPw({ old_password: '', new_password: '', confirm: '' })
    } catch (err) {
      setPwMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
    } finally { setLoading('') }
  }

  // (2026-10-06) اسم الباقة يُقرأ حياً من إعدادات الأدمن لو غيّره، وإلا الافتراضي
  const planLabels = {
    trial: isAr ? 'تجريبي' : 'Trial',
    weekly: siteSettings[`plan_weekly_name${isAr ? '' : '_en'}`] || (isAr ? 'أسبوعي' : 'Weekly'),
    monthly: siteSettings[`plan_monthly_name${isAr ? '' : '_en'}`] || (isAr ? 'شهري' : 'Monthly'),
    banned: isAr ? 'محظور' : 'Banned',
  }
  const planColors = { trial: 'text-blue-400', weekly: 'text-green-400', monthly: 'text-purple-400', banned: 'text-red-400' }

  return (
    <div dir={isAr ? 'rtl' : 'ltr'} className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-white">{isAr ? 'حسابي' : 'My Account'}</h1>

      {/* Plan info + مسار الدفع
          (2026-09-17) صفحة الحساب كانت بلا أي رابط للأسعار، وزر البطاقة
          الجانبية يوجّه إليها المشترك المدفوع — فيصل طريقاً مسدوداً.
          راجع utils/subscriptionCta. */}
      {(() => {
        const cta = subscriptionCta(user, isAr)
        const urgent = cta.tone === 'urgent'
        return (
          <div className={`bg-gray-800 border rounded-xl p-4 ${
            urgent ? 'border-amber-500/60' : 'border-gray-700'
          }`}>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center shrink-0">
                <User className="text-blue-400" size={22} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-medium text-white truncate">{user?.full_name || user?.email}</p>
                <p className="text-sm text-gray-400 truncate">{user?.email}</p>
                <p className="text-xs mt-1">
                  {isAr ? 'الخطة:' : 'Plan:'}{' '}
                  <span className={`font-semibold ${planColors[user?.plan] || 'text-gray-400'}`}>
                    {planLabels[user?.plan] || user?.plan}
                  </span>
                  {user?.days_left != null && (
                    <span className={`mr-2 ${urgent ? 'text-amber-400 font-semibold' : 'text-gray-500'}`}>
                      · {user.days_left} {isAr ? 'يوم متبقي' : 'days left'}
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap mt-4">
              <Link to={cta.to}
                className={`flex-1 min-w-[160px] text-center py-2.5 rounded-xl font-bold text-sm transition ${
                  urgent
                    ? 'bg-amber-500 hover:bg-amber-400 text-black'
                    : cta.tone === 'muted'
                    ? 'bg-white/10 hover:bg-white/15 text-gray-200'
                    : 'bg-blue-600 hover:bg-blue-500 text-white'
                }`}>
                {cta.to === '/profile' ? (isAr ? 'عرض الباقات' : 'View plans') : cta.label}
              </Link>
              {cta.to === '/profile' && (
                <Link to="/pricing"
                  className="flex-1 min-w-[160px] text-center py-2.5 rounded-xl font-bold text-sm bg-blue-600 hover:bg-blue-500 text-white transition">
                  {isAr ? 'تجديد مبكر' : 'Renew early'}
                </Link>
              )}
            </div>
          </div>
        )
      })()}

      {/* ── Personal Info ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <User size={16} className="text-blue-400" /> {isAr ? 'البيانات الشخصية' : 'Personal Info'}
        </h2>
        <form onSubmit={saveProfile} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'الاسم الكامل' : 'Full Name'}</label>
            <input type="text" value={profile.full_name}
              onChange={e => setProfile(p => ({...p, full_name: e.target.value}))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'البريد الإلكتروني' : 'Email'}</label>
            <div className="relative">
              <Mail size={14} className={`absolute ${isAr ? 'right' : 'left'}-3 top-1/2 -translate-y-1/2 text-gray-400`} />
              <input type="email" value={user?.email} disabled
                className={`w-full bg-gray-900/50 border border-gray-700 rounded-lg ${isAr ? 'pr-9 pl-4' : 'pl-9 pr-4'} py-2.5 text-gray-500 text-sm cursor-not-allowed`} />
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'رقم الهاتف' : 'Phone'} <span className="text-gray-400 text-xs">({isAr ? 'اختياري' : 'optional'})</span></label>
            <input type="tel" value={profile.phone_number}
              onChange={e => setProfile(p => ({...p, phone_number: e.target.value}))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              dir="ltr" />
          </div>
          <button type="submit" disabled={loading === 'profile'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Save size={14} /> {loading === 'profile' ? (isAr ? 'جاري الحفظ...' : 'Saving...') : (isAr ? 'حفظ البيانات' : 'Save')}
          </button>
          <Msg msg={profileMsg} />
        </form>
      </div>

      <TradingPreferencesPanel />

      {/* ── Affiliate / Referral ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Gift size={16} className="text-green-400" /> {isAr ? 'نظام الإحالة' : 'Referral Program'}
        </h2>

        {affiliate ? (
          <div className="space-y-4">
            {/* Tier badge */}
            <div className="flex flex-wrap gap-3">
              <div className={`px-4 py-2 rounded-xl text-sm font-bold border ${affiliate.current_tier === 2 ? 'bg-yellow-900/30 border-yellow-600 text-yellow-400' : 'bg-blue-900/30 border-blue-700 text-blue-400'}`}>
                {isAr ? `المرحلة ${affiliate.current_tier}` : `Tier ${affiliate.current_tier}`}
                {' · '}{affiliate.commission_rate_pct}%
                {affiliate.current_tier === 1 && affiliate.referrals_to_next_tier != null && (
                  <span className="text-xs font-normal opacity-70 mr-1">
                    ({affiliate.referrals_to_next_tier} {isAr ? 'للمرحلة التالية' : 'to Tier 2'})
                  </span>
                )}
              </div>
              <div className="bg-gray-700 px-4 py-2 rounded-xl text-sm">
                <span className="text-gray-400">{isAr ? 'الإحالات:' : 'Referrals:'} </span>
                <span className="text-white font-bold">{affiliate.total_referrals}</span>
              </div>
            </div>

            {/* Earnings */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-900 rounded-xl p-3">
                <p className="text-xs text-gray-400 mb-1">{isAr ? 'رصيد معلّق' : 'Pending Balance'}</p>
                <p className="text-green-400 font-bold text-lg">${affiliate.pending_balance_usd?.toFixed(2)}</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-3">
                <p className="text-xs text-gray-400 mb-1">{isAr ? 'إجمالي الأرباح' : 'Total Paid Out'}</p>
                <p className="text-white font-bold text-lg">${affiliate.paid_out_usd?.toFixed(2)}</p>
              </div>
            </div>
            {affiliate?.min_payout_usd != null && (
              <p className="text-xs text-gray-500 mt-1">
                * {isAr ? `الحد الأدنى للسحب: $${affiliate.min_payout_usd}` : `Minimum withdrawal: $${affiliate.min_payout_usd}`}
              </p>
            )}

            {/* Referral link */}
            <div>
              <p className="text-sm text-gray-400 mb-2">{isAr ? 'رابط الإحالة الخاص بك:' : 'Your referral link:'}</p>
              <div className="flex gap-2">
                <input readOnly value={affiliate.referral_link || ''}
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs text-blue-300 font-mono focus:outline-none"
                  dir="ltr" />
                <button onClick={copyLink}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${copied ? 'bg-green-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'}`}>
                  {copied ? <CheckCircle size={13} /> : <Copy size={13} />}
                  {copied ? (isAr ? 'تم!' : 'Copied!') : (isAr ? 'نسخ' : 'Copy')}
                </button>
              </div>
            </div>

            {/* Info */}
            <div className="bg-green-900/10 border border-green-800/30 rounded-xl p-3 text-xs text-gray-400 space-y-1">
              <p>• {isAr ? 'احصل على 5% عمولة من كل اشتراك مدفوع عبر رابطك' : 'Earn 5% commission on every paid subscription via your link'}</p>
              <p>• {isAr ? 'بعد 25 إحالة ناجحة، ترتفع العمولة إلى 15%' : 'After 25 successful referrals, your commission rises to 15%'}</p>
              <p>• {isAr ? 'يتم احتساب العمولة عند قبول الدفع من قبل الإدارة' : 'Commission is credited when admin approves the payment'}</p>
            </div>

            {/* Recent referrals table */}
            {affiliate.referrals?.length > 0 && (
              <div>
                <p className="text-sm text-gray-400 mb-2">{isAr ? 'آخر الإحالات:' : 'Recent referrals:'}</p>
                <div className="space-y-2">
                  {affiliate.referrals.slice(0, 5).map((r, i) => (
                    <div key={i} className="flex justify-between items-center bg-gray-900 rounded-lg px-3 py-2 text-xs">
                      <span className="text-gray-400">{r.referred_user_email}</span>
                      <span className="text-green-400 font-mono">+${r.commission_usd?.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-500 text-sm">
            {isAr ? 'جاري تحميل بيانات الإحالة...' : 'Loading affiliate data...'}
          </div>
        )}
      </div>

      {/* ── Change Password ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Lock size={16} className="text-blue-400" /> {isAr ? 'تغيير كلمة المرور' : 'Change Password'}
        </h2>
        <form onSubmit={changePassword} className="space-y-4">
          {[
            { key: 'old_password', label: isAr ? 'كلمة المرور الحالية'  : 'Current Password' },
            { key: 'new_password', label: isAr ? 'كلمة المرور الجديدة'  : 'New Password' },
            { key: 'confirm',      label: isAr ? 'تأكيد كلمة المرور'    : 'Confirm Password' },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-sm text-gray-400 mb-1.5">{f.label}</label>
              <input type="password" required value={pw[f.key]}
                onChange={e => setPw(p => ({...p, [f.key]: e.target.value}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                dir="ltr" />
            </div>
          ))}
          <button type="submit" disabled={loading === 'pw'}
            className="flex items-center gap-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Lock size={14} /> {loading === 'pw' ? (isAr ? 'جاري التغيير...' : 'Changing...') : (isAr ? 'تغيير كلمة المرور' : 'Change Password')}
          </button>
          <Msg msg={pwMsg} />
        </form>
      </div>
    </div>
  )
}
