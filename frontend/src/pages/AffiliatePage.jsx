import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import {
  Copy, CheckCircle, DollarSign, Users, TrendingUp, Star,
  Clock, AlertTriangle, RefreshCw, ArrowUpRight, Gift
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function AffiliatePage() {
  const { user }   = useAuth()
  const { lang }   = useLang()
  const isAr       = lang === 'ar'
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [copied, setCopied]     = useState(false)
  const [payoutAmt, setPayoutAmt] = useState('')
  const [payoutNote, setPayoutNote] = useState('')
  const [payoutSending, setPayoutSending] = useState(false)
  const [payoutMsg, setPayoutMsg] = useState(null)

  useEffect(() => { loadDashboard() }, [])

  const loadDashboard = async () => {
    setLoading(true)
    try {
      const r = await axios.get(`${API}/api/v1/affiliate/dashboard`)
      setData(r.data)
    } catch (e) {}
    finally { setLoading(false) }
  }

  const copyLink = () => {
    if (!data?.referral_link) return
    navigator.clipboard.writeText(data.referral_link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const requestPayout = async (e) => {
    e.preventDefault()
    setPayoutSending(true); setPayoutMsg(null)
    try {
      await axios.post(`${API}/api/v1/affiliate/payout-request`, {
        amount_usd: parseFloat(payoutAmt),
        note: payoutNote,
      })
      setPayoutMsg({ type: 'ok', text: isAr ? 'تم إرسال طلب السحب بنجاح' : 'Payout request submitted successfully' })
      setPayoutAmt(''); setPayoutNote('')
      loadDashboard()
    } catch (err) {
      setPayoutMsg({ type: 'err', text: err.response?.data?.detail || (isAr ? 'خطأ' : 'Error') })
    } finally { setPayoutSending(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <RefreshCw size={28} className="animate-spin text-blue-400" />
    </div>
  )

  if (!data) return (
    <div className="text-center py-24 text-gray-400">
      {isAr ? 'تعذّر تحميل البيانات' : 'Failed to load data'}
    </div>
  )

  const tierProgress = data.referrals_to_next_tier !== null
    ? Math.min(100, (data.total_referrals / (data.total_referrals + data.referrals_to_next_tier)) * 100)
    : 100

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center">
          <Gift size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">
            {isAr ? 'برنامج الإحالات' : 'Referral Program'}
          </h1>
          <p className="text-sm text-gray-400">
            {isAr ? 'شارك رابطك واربح عمولة على كل اشتراك' : 'Share your link and earn commission on every subscription'}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            icon: DollarSign,
            color: 'text-green-400',
            bg: 'bg-green-900/20 border-green-800/40',
            label: isAr ? 'رصيد معلّق' : 'Pending Balance',
            value: `$${data.pending_balance_usd.toFixed(2)}`,
          },
          {
            icon: CheckCircle,
            color: 'text-blue-400',
            bg: 'bg-blue-900/20 border-blue-800/40',
            label: isAr ? 'مدفوع' : 'Paid Out',
            value: `$${data.paid_out_usd.toFixed(2)}`,
          },
          {
            icon: Users,
            color: 'text-purple-400',
            bg: 'bg-purple-900/20 border-purple-800/40',
            label: isAr ? 'إجمالي الإحالات' : 'Total Referrals',
            value: data.total_referrals,
          },
          {
            icon: TrendingUp,
            color: 'text-yellow-400',
            bg: 'bg-yellow-900/20 border-yellow-800/40',
            label: isAr ? 'نسبة العمولة' : 'Commission Rate',
            value: `${data.commission_rate_pct}%`,
          },
        ].map(({ icon: Icon, color, bg, label, value }) => (
          <div key={label} className={`rounded-xl border p-4 ${bg}`}>
            <div className="flex items-center gap-2 mb-2">
              <Icon size={16} className={color} />
              <span className="text-xs text-gray-400">{label}</span>
            </div>
            <p className="text-xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      {/* Tier Card */}
      <div className={`rounded-xl border p-5 ${data.current_tier === 2 ? 'bg-gradient-to-br from-yellow-900/30 to-orange-900/20 border-yellow-700/40' : 'bg-gray-900 border-gray-800'}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Star size={18} className={data.current_tier === 2 ? 'text-yellow-400' : 'text-gray-400'} />
            <span className="font-semibold text-white">
              {data.current_tier === 2
                ? (isAr ? 'المستوى الذهبي — 15% عمولة' : 'Gold Tier — 15% Commission')
                : (isAr ? 'المستوى البرونزي — 5% عمولة' : 'Bronze Tier — 5% Commission')}
            </span>
          </div>
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${data.current_tier === 2 ? 'bg-yellow-500/20 text-yellow-300' : 'bg-gray-700 text-gray-300'}`}>
            {isAr ? `المستوى ${data.current_tier}` : `Tier ${data.current_tier}`}
          </span>
        </div>

        {data.referrals_to_next_tier !== null && (
          <>
            <div className="flex justify-between text-xs text-gray-400 mb-1.5">
              <span>{data.total_referrals} {isAr ? 'إحالة' : 'referrals'}</span>
              <span>{isAr ? `${data.referrals_to_next_tier} متبقي للذهبي` : `${data.referrals_to_next_tier} to Gold`}</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-blue-500 to-yellow-500 transition-all duration-500"
                style={{ width: `${tierProgress}%` }}
              />
            </div>
          </>
        )}

        {data.current_tier === 2 && (
          <p className="text-xs text-yellow-400/70 mt-2">
            {isAr ? '🏆 أنت في أعلى مستوى! تستمتع بعمولة 15% على كل إحالة.' : '🏆 You are at the highest tier! Enjoy 15% commission on every referral.'}
          </p>
        )}
      </div>

      {/* Referral Link */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">
          {isAr ? 'رابط الإحالة الخاص بك' : 'Your Referral Link'}
        </h2>
        <div className="flex gap-2">
          <div className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-blue-300 font-mono truncate" dir="ltr">
            {data.referral_link}
          </div>
          <button onClick={copyLink}
            className={`flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${copied ? 'bg-green-600 text-white' : 'bg-blue-600 hover:bg-blue-500 text-white'}`}>
            {copied ? <CheckCircle size={15} /> : <Copy size={15} />}
            {copied ? (isAr ? 'تم النسخ' : 'Copied!') : (isAr ? 'نسخ' : 'Copy')}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {isAr
            ? `كودك: ${data.affiliate_code} — شارك الرابط مع أصدقائك واربح ${data.commission_rate_pct}% من كل اشتراك`
            : `Your code: ${data.affiliate_code} — Share with friends and earn ${data.commission_rate_pct}% of every subscription`}
        </p>
      </div>

      {/* Payout Request */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-1">
          {isAr ? 'طلب سحب الأرباح' : 'Request Payout'}
        </h2>
        <p className="text-xs text-gray-500 mb-4">
          {isAr
            ? `الحد الأدنى للسحب $${data.min_payout_usd} — الرصيد المتاح: $${data.pending_balance_usd.toFixed(2)}`
            : `Minimum payout $${data.min_payout_usd} — Available balance: $${data.pending_balance_usd.toFixed(2)}`}
        </p>

        {payoutMsg && (
          <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mb-4 ${payoutMsg.type === 'ok' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>
            {payoutMsg.type === 'ok' ? <CheckCircle size={14} /> : <AlertTriangle size={14} />} {payoutMsg.text}
          </div>
        )}

        <form onSubmit={requestPayout} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'المبلغ (USDT)' : 'Amount (USDT)'}</label>
              <input
                type="number" step="0.01" min={data.min_payout_usd} max={data.pending_balance_usd}
                value={payoutAmt} onChange={e => setPayoutAmt(e.target.value)} required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                dir="ltr" placeholder={`${data.min_payout_usd}+`}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'ملاحظة (اختياري)' : 'Note (optional)'}</label>
              <input
                type="text" value={payoutNote} onChange={e => setPayoutNote(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder={isAr ? 'عنوان المحفظة أو ملاحظة' : 'Wallet address or note'}
              />
            </div>
          </div>
          <button
            type="submit" disabled={payoutSending || data.pending_balance_usd < data.min_payout_usd}
            className="flex items-center gap-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-all">
            {payoutSending ? <RefreshCw size={14} className="animate-spin" /> : <DollarSign size={14} />}
            {isAr ? 'إرسال طلب السحب' : 'Request Payout'}
          </button>
        </form>
      </div>

      {/* Referral History */}
      {data.referrals.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-gray-300">
              {isAr ? 'سجل الإحالات' : 'Referral History'}
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="px-4 py-3 text-right text-xs text-gray-400 font-medium">{isAr ? 'المستخدم' : 'User'}</th>
                  <th className="px-4 py-3 text-right text-xs text-gray-400 font-medium">{isAr ? 'الاشتراك' : 'Subscription'}</th>
                  <th className="px-4 py-3 text-right text-xs text-gray-400 font-medium">{isAr ? 'عمولتك' : 'Your Commission'}</th>
                  <th className="px-4 py-3 text-right text-xs text-gray-400 font-medium">{isAr ? 'التاريخ' : 'Date'}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {data.referrals.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-3 text-gray-300 font-mono text-xs">
                      {r.referred_user_email.replace(/(.{3}).*(@.*)/, '$1***$2')}
                    </td>
                    <td className="px-4 py-3 text-gray-300">${r.payment_amount_usd.toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <span className="text-green-400 font-semibold">+${r.commission_usd.toFixed(2)}</span>
                      <span className="text-xs text-gray-500 ms-1">T{r.tier}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs" dir="ltr">
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data.referrals.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <Users size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">{isAr ? 'لا توجد إحالات بعد — شارك رابطك الآن!' : 'No referrals yet — share your link now!'}</p>
          <button onClick={copyLink}
            className="mt-4 inline-flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors">
            <ArrowUpRight size={14} /> {isAr ? 'نسخ رابط الإحالة' : 'Copy Referral Link'}
          </button>
        </div>
      )}
    </div>
  )
}
