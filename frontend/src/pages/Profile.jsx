import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useMarkets from '../hooks/useMarkets'
import { User, Mail, Phone, Lock, Save, CheckCircle, AlertCircle, TrendingUp, Bell, Calculator, Gift, Copy, ExternalLink, Users, DollarSign } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TIMEFRAMES = ['15m','1h','4h','1day']

export default function Profile() {
  const { user, token, refreshUser } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const { markets } = useMarkets()

  const [profile, setProfile] = useState({ full_name: user?.full_name || '', phone_number: user?.phone_number || '' })
  const [pw, setPw]           = useState({ old_password: '', new_password: '', confirm: '' })
  const [trading, setTrading] = useState({ account_balance: user?.account_balance || 10000, risk_percent: user?.risk_percent || 1.5 })
  const [prefs, setPrefs]     = useState({
    notify_watchlist:      user?.notify_watchlist      || [],
    notify_timeframe:      user?.notify_timeframe      || '1h',
    notify_min_confidence: user?.notify_min_confidence || 65,
    notifications_enabled: user?.notifications_enabled !== false,
    language:              user?.language              || 'ar',
  })

  const [profileMsg, setProfileMsg] = useState(null)
  const [pwMsg,      setPwMsg]      = useState(null)
  const [tradingMsg, setTradingMsg] = useState(null)
  const [prefsMsg,   setPrefsMsg]   = useState(null)
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

  // حساسبة اللوت (preview)
  const [lotPreview, setLotPreview] = useState(null)
  const [lotEntry,   setLotEntry]   = useState('')
  const [lotSl,      setLotSl]      = useState('')
  const [lotSymbol,  setLotSymbol]  = useState('XAUUSD')

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

  const saveTradingSettings = async e => {
    e.preventDefault(); setLoading('trading'); setTradingMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/trading-settings`, trading, { headers })
      setTradingMsg({ type: 'ok', text: isAr ? 'تم حفظ إعدادات التداول' : 'Trading settings saved' })
    } catch (err) {
      setTradingMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
    } finally { setLoading('') }
  }

  const savePrefs = async e => {
    e.preventDefault(); setLoading('prefs'); setPrefsMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/preferences`, prefs)
      setPrefsMsg({ type: 'ok', text: isAr ? 'تم حفظ إعدادات الإشعارات' : 'Notification settings saved' })
    } catch (err) {
      setPrefsMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
    } finally { setLoading('') }
  }

  const toggleWatchlist = (m) => {
    setPrefs(p => ({
      ...p,
      notify_watchlist: p.notify_watchlist.includes(m)
        ? p.notify_watchlist.filter(x => x !== m)
        : [...p.notify_watchlist, m],
    }))
  }

  // حساب اللوت
  const calcLot = () => {
    const entry = parseFloat(lotEntry)
    const sl    = parseFloat(lotSl)
    const bal   = trading.account_balance
    const risk  = trading.risk_percent
    if (!entry || !sl || entry === sl) { setLotPreview(null); return }
    const riskAmt = bal * (risk / 100)
    const pipDist = Math.abs(entry - sl)
    const pipVal  = lotSymbol === 'XAUUSD' ? 10 : lotSymbol === 'BTCUSD' ? 1 : lotSymbol.includes('JPY') || lotSymbol.includes('CHF') ? 8 : 10
    const lot = riskAmt / (pipDist * pipVal)
    setLotPreview(Math.max(0.01, Math.min(lot, 100)).toFixed(2))
  }

  const planLabels = { trial: isAr ? 'تجريبي' : 'Trial', weekly: isAr ? 'أسبوعي' : 'Weekly', monthly: isAr ? 'شهري' : 'Monthly', banned: isAr ? 'محظور' : 'Banned' }
  const planColors = { trial: 'text-blue-400', weekly: 'text-green-400', monthly: 'text-purple-400', banned: 'text-red-400' }

  return (
    <div dir={isAr ? 'rtl' : 'ltr'} className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-white">{isAr ? 'حسابي' : 'My Account'}</h1>

      {/* Plan info */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex items-center gap-4">
        <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center">
          <User className="text-blue-400" size={22} />
        </div>
        <div>
          <p className="font-medium text-white">{user?.full_name || user?.email}</p>
          <p className="text-sm text-gray-400">{user?.email}</p>
          <p className="text-xs mt-1">
            {isAr ? 'الخطة:' : 'Plan:'} <span className={`font-semibold ${planColors[user?.plan] || 'text-gray-400'}`}>{planLabels[user?.plan] || user?.plan}</span>
            {user?.days_left != null && (
              <span className="text-gray-500 mr-2">· {user.days_left} {isAr ? 'يوم متبقي' : 'days left'}</span>
            )}
          </p>
        </div>
      </div>

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
              <Mail size={14} className={`absolute ${isAr ? 'right' : 'left'}-3 top-1/2 -translate-y-1/2 text-gray-600`} />
              <input type="email" value={user?.email} disabled
                className={`w-full bg-gray-900/50 border border-gray-700 rounded-lg ${isAr ? 'pr-9 pl-4' : 'pl-9 pr-4'} py-2.5 text-gray-500 text-sm cursor-not-allowed`} />
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'رقم الهاتف' : 'Phone'} <span className="text-gray-600 text-xs">({isAr ? 'اختياري' : 'optional'})</span></label>
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

      {/* ── Trading Settings + Lot Calculator ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-400" /> {isAr ? 'إدارة رأس المال' : 'Capital Management'}
        </h2>
        <form onSubmit={saveTradingSettings} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'رأس المال ($)' : 'Account Balance ($)'}</label>
              <input type="number" min="100" step="100" value={trading.account_balance}
                onChange={e => setTrading(p => ({...p, account_balance: Number(e.target.value)}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                dir="ltr" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'نسبة المخاطرة (%)' : 'Risk % per Trade'}</label>
              <input type="number" min="0.1" max="5" step="0.1" value={trading.risk_percent}
                onChange={e => setTrading(p => ({...p, risk_percent: Number(e.target.value)}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                dir="ltr" />
            </div>
          </div>
          <div className="bg-blue-900/10 border border-blue-800/30 rounded-lg p-3 text-xs text-gray-400">
            {isAr
              ? `مع ${trading.risk_percent}% مخاطرة على $${trading.account_balance}، الحد الأقصى للخسارة في الصفقة: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)}`
              : `With ${trading.risk_percent}% risk on $${trading.account_balance}, max loss per trade: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)}`}
          </div>
          <button type="submit" disabled={loading === 'trading'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Save size={14} /> {loading === 'trading' ? (isAr ? 'جاري الحفظ...' : 'Saving...') : (isAr ? 'حفظ الإعدادات' : 'Save Settings')}
          </button>
          <Msg msg={tradingMsg} />
        </form>

        {/* Lot Size Calculator */}
        <div className="mt-6 border-t border-gray-700 pt-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Calculator size={15} className="text-yellow-400" /> {isAr ? 'حاسبة اللوت' : 'Lot Size Calculator'}
          </h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'الزوج' : 'Symbol'}</label>
              <select value={lotSymbol} onChange={e => setLotSymbol(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-2 py-2 text-xs">
                {markets.map(m => <option key={m.symbol} value={m.symbol}>{m.symbol}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'سعر الدخول' : 'Entry'}</label>
              <input type="number" step="any" value={lotEntry}
                onChange={e => setLotEntry(e.target.value)} placeholder="e.g. 2050"
                className="w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-2 py-2 text-xs" dir="ltr" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'وقف الخسارة' : 'Stop Loss'}</label>
              <input type="number" step="any" value={lotSl}
                onChange={e => setLotSl(e.target.value)} placeholder="e.g. 2045"
                className="w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-2 py-2 text-xs" dir="ltr" />
            </div>
          </div>
          <button onClick={calcLot}
            className="mt-3 flex items-center gap-2 px-4 py-2 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-400 rounded-lg text-xs font-medium">
            <Calculator size={13} /> {isAr ? 'احسب اللوت' : 'Calculate Lot'}
          </button>
          {lotPreview && (
            <div className="mt-3 bg-yellow-900/20 border border-yellow-700/40 rounded-lg p-3 text-sm">
              <span className="text-gray-400">{isAr ? 'حجم اللوت المناسب:' : 'Recommended Lot Size:'} </span>
              <span className="text-yellow-400 font-bold text-lg">{lotPreview}</span>
              <span className="text-gray-500 text-xs mr-2">{isAr ? 'لوت' : 'lots'}</span>
              <div className="text-xs text-gray-500 mt-1">
                {isAr
                  ? `(خسارة محتملة: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)} = ${trading.risk_percent}% من رأس المال)`
                  : `(Max loss: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)} = ${trading.risk_percent}% of balance)`}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Notification Preferences ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Bell size={16} className="text-blue-400" /> {isAr ? 'إعدادات إشعارات التيليجرام' : 'Telegram Notification Preferences'}
        </h2>
        <form onSubmit={savePrefs} className="space-y-5">
          {/* Enable/Disable */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">{isAr ? 'تفعيل الإشعارات' : 'Enable Notifications'}</span>
            <button type="button" onClick={() => setPrefs(p => ({...p, notifications_enabled: !p.notifications_enabled}))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${prefs.notifications_enabled ? 'bg-blue-600' : 'bg-gray-600'}`}>
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${prefs.notifications_enabled ? (isAr ? '-translate-x-6' : 'translate-x-6') : (isAr ? '-translate-x-1' : 'translate-x-1')}`} />
            </button>
          </div>

          {/* Watchlist */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              {isAr ? 'الأزواج للمراقبة' : 'Markets to Watch'}
              <span className="text-gray-600 mr-1 text-xs">({prefs.notify_watchlist.length} {isAr ? 'مختار' : 'selected'})</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {markets.map(m => (
                <button key={m.symbol} type="button" onClick={() => toggleWatchlist(m.symbol)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    prefs.notify_watchlist.includes(m.symbol)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}>
                  {prefs.notify_watchlist.includes(m.symbol) ? '✓ ' : ''}{m.symbol}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'الفريم الزمني' : 'Timeframe'}</label>
              <select value={prefs.notify_timeframe} onChange={e => setPrefs(p => ({...p, notify_timeframe: e.target.value}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
                {TIMEFRAMES.map(tf => <option key={tf} value={tf}>{tf}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'الحد الأدنى للثقة' : 'Min Confidence'}</label>
              <select value={prefs.notify_min_confidence} onChange={e => setPrefs(p => ({...p, notify_min_confidence: Number(e.target.value)}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
                {[50,55,60,65,70,75,80].map(v => <option key={v} value={v}>{v}%</option>)}
              </select>
            </div>
          </div>

          <div className="bg-gray-700/30 rounded-lg p-3 text-xs text-gray-400">
            {isAr
              ? 'سيراقب البوت الأزواج المختارة كل 15 دقيقة ويرسل تنبيهاً عند وجود إشارة BUY/SELL بنسبة ثقة أعلى من الحد المحدد.'
              : 'The bot will monitor selected pairs every 15 minutes and send an alert when a BUY/SELL signal appears above the minimum confidence threshold.'}
          </div>

          <button type="submit" disabled={loading === 'prefs'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Save size={14} /> {loading === 'prefs' ? (isAr ? 'جاري الحفظ...' : 'Saving...') : (isAr ? 'حفظ التفضيلات' : 'Save Preferences')}
          </button>
          <Msg msg={prefsMsg} />
        </form>
      </div>

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
