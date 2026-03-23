import { useState } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { User, Mail, Phone, Lock, Save, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Profile() {
  const { user, token, refreshUser } = useAuth()

  const [profile, setProfile] = useState({ full_name: user?.full_name || '', phone_number: user?.phone_number || '' })
  const [pw, setPw]           = useState({ old_password: '', new_password: '', confirm: '' })
  const [trading, setTrading] = useState({ account_balance: user?.account_balance || 10000, risk_percent: user?.risk_percent || 1.5 })

  const [profileMsg, setProfileMsg] = useState(null)
  const [pwMsg, setPwMsg]           = useState(null)
  const [tradingMsg, setTradingMsg] = useState(null)
  const [loading, setLoading]       = useState('')

  const headers = { Authorization: `Bearer ${token}` }

  const saveProfile = async e => {
    e.preventDefault()
    setLoading('profile'); setProfileMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/profile`, profile, { headers })
      await refreshUser()
      setProfileMsg({ type: 'ok', text: 'تم حفظ البيانات الشخصية' })
    } catch (err) {
      setProfileMsg({ type: 'err', text: err.response?.data?.detail || 'خطأ في الحفظ' })
    } finally { setLoading('') }
  }

  const changePassword = async e => {
    e.preventDefault()
    if (pw.new_password !== pw.confirm) { setPwMsg({ type: 'err', text: 'كلمتا المرور غير متطابقتين' }); return }
    if (pw.new_password.length < 8) { setPwMsg({ type: 'err', text: 'كلمة المرور يجب أن تكون 8 أحرف+' }); return }
    setLoading('pw'); setPwMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/change-password`, { old_password: pw.old_password, new_password: pw.new_password }, { headers })
      setPwMsg({ type: 'ok', text: 'تم تغيير كلمة المرور بنجاح' })
      setPw({ old_password: '', new_password: '', confirm: '' })
    } catch (err) {
      setPwMsg({ type: 'err', text: err.response?.data?.detail || 'خطأ في تغيير كلمة المرور' })
    } finally { setLoading('') }
  }

  const saveTradingSettings = async e => {
    e.preventDefault()
    setLoading('trading'); setTradingMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/trading-settings`, trading, { headers })
      setTradingMsg({ type: 'ok', text: 'تم حفظ إعدادات التداول' })
    } catch (err) {
      setTradingMsg({ type: 'err', text: err.response?.data?.detail || 'خطأ في الحفظ' })
    } finally { setLoading('') }
  }

  const Msg = ({ msg }) => msg ? (
    <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mt-3 ${
      msg.type === 'ok' ? 'bg-green-900/30 border border-green-700/40 text-green-400' : 'bg-red-900/30 border border-red-700/40 text-red-400'
    }`}>
      {msg.type === 'ok' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
      {msg.text}
    </div>
  ) : null

  const planLabels = { trial: 'تجريبي', weekly: 'أسبوعي', monthly: 'شهري', banned: 'محظور' }
  const planColors = { trial: 'text-blue-400', weekly: 'text-green-400', monthly: 'text-purple-400', banned: 'text-red-400' }

  return (
    <div dir="rtl" className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-white">حسابي</h1>

      {/* Plan info */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex items-center gap-4">
        <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center">
          <User className="text-blue-400" size={22} />
        </div>
        <div>
          <p className="font-medium text-white">{user?.full_name || user?.email}</p>
          <p className="text-sm text-gray-400">{user?.email}</p>
          <p className="text-xs mt-1">
            الخطة: <span className={`font-semibold ${planColors[user?.plan] || 'text-gray-400'}`}>{planLabels[user?.plan] || user?.plan}</span>
            {user?.days_left !== null && user?.days_left !== undefined && (
              <span className="text-gray-500 mr-2">· {user.days_left} يوم متبقي</span>
            )}
          </p>
        </div>
      </div>

      {/* ── Personal Info ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <User size={16} className="text-blue-400" /> البيانات الشخصية
        </h2>
        <form onSubmit={saveProfile} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">الاسم الكامل</label>
            <input type="text" value={profile.full_name}
              onChange={e => setProfile(p => ({...p, full_name: e.target.value}))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="اسمك الكريم" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">البريد الإلكتروني</label>
            <div className="relative">
              <Mail size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-600" />
              <input type="email" value={user?.email} disabled
                className="w-full bg-gray-900/50 border border-gray-700 rounded-lg pr-9 pl-4 py-2.5 text-gray-500 text-sm cursor-not-allowed" />
            </div>
            <p className="text-xs text-gray-600 mt-1">لا يمكن تغيير البريد الإلكتروني</p>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">رقم الهاتف <span className="text-gray-600 text-xs">(اختياري)</span></label>
            <div className="relative">
              <Phone size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-600" />
              <input type="tel" value={profile.phone_number}
                onChange={e => setProfile(p => ({...p, phone_number: e.target.value}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg pr-9 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="+966 5x xxx xxxx" dir="ltr" />
            </div>
          </div>
          <button type="submit" disabled={loading === 'profile'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Save size={14} /> {loading === 'profile' ? 'جاري الحفظ...' : 'حفظ البيانات'}
          </button>
          <Msg msg={profileMsg} />
        </form>
      </div>

      {/* ── Change Password ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Lock size={16} className="text-blue-400" /> تغيير كلمة المرور
        </h2>
        <form onSubmit={changePassword} className="space-y-4">
          {[
            { key: 'old_password',  label: 'كلمة المرور الحالية', ph: '••••••••' },
            { key: 'new_password',  label: 'كلمة المرور الجديدة', ph: '8 أحرف+' },
            { key: 'confirm',       label: 'تأكيد كلمة المرور الجديدة', ph: '••••••••' },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-sm text-gray-400 mb-1.5">{f.label}</label>
              <input type="password" required value={pw[f.key]}
                onChange={e => setPw(p => ({...p, [f.key]: e.target.value}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={f.ph} dir="ltr" />
            </div>
          ))}
          <button type="submit" disabled={loading === 'pw'}
            className="flex items-center gap-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Lock size={14} /> {loading === 'pw' ? 'جاري التغيير...' : 'تغيير كلمة المرور'}
          </button>
          <Msg msg={pwMsg} />
        </form>
      </div>

      {/* ── Trading Settings ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-400" /> إعدادات التداول
        </h2>
        <form onSubmit={saveTradingSettings} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">رأس المال ($)</label>
            <input type="number" min="100" step="100" value={trading.account_balance}
              onChange={e => setTrading(p => ({...p, account_balance: Number(e.target.value)}))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              dir="ltr" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">نسبة المخاطرة (0.1% – 5%)</label>
            <input type="number" min="0.1" max="5" step="0.1" value={trading.risk_percent}
              onChange={e => setTrading(p => ({...p, risk_percent: Number(e.target.value)}))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              dir="ltr" />
          </div>
          <button type="submit" disabled={loading === 'trading'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Save size={14} /> {loading === 'trading' ? 'جاري الحفظ...' : 'حفظ الإعدادات'}
          </button>
          <Msg msg={tradingMsg} />
        </form>
      </div>
    </div>
  )
}
