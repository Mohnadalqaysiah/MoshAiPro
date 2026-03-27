import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { TrendingUp, Mail, Lock, ShieldCheck, CheckCircle, AlertCircle, ArrowRight } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [step, setStep]       = useState(1) // 1=email, 2=otp+password, 3=done
  const [email, setEmail]     = useState('')
  const [otp, setOtp]         = useState('')
  const [newPw, setNewPw]     = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const sendOtp = async e => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await axios.post(`${API}/api/v1/auth/forgot-password`, { email })
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || 'حدث خطأ، حاول مجدداً')
    } finally { setLoading(false) }
  }

  const resetPassword = async e => {
    e.preventDefault()
    if (newPw !== confirmPw) { setError('كلمتا المرور غير متطابقتين'); return }
    if (newPw.length < 8)    { setError('كلمة المرور يجب أن تكون 8 أحرف على الأقل'); return }
    setLoading(true); setError('')
    try {
      await axios.post(`${API}/api/v1/auth/reset-password`, {
        email, otp, new_password: newPw
      })
      setStep(3)
    } catch (err) {
      setError(err.response?.data?.detail || 'رمز التحقق غير صحيح أو منتهي')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4" dir="rtl">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600 mb-4">
            <TrendingUp size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Qaffel <span className="text-blue-400">AI</span></h1>
          <p className="text-gray-400 text-sm mt-1">استعادة كلمة المرور</p>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {[1, 2, 3].map(s => (
            <div key={s} className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
              step === s ? 'bg-blue-600 text-white' :
              step > s  ? 'bg-green-600 text-white' :
              'bg-gray-800 text-gray-500'
            }`}>
              {step > s ? '✓' : s}
            </div>
          ))}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">

          {/* Step 1: Enter Email */}
          {step === 1 && (
            <>
              <h2 className="text-lg font-semibold text-white mb-2">أدخل بريدك الإلكتروني</h2>
              <p className="text-gray-400 text-sm mb-6">سنرسل لك رمز تحقق مكوّن من 6 أرقام</p>
              <form onSubmit={sendOtp} className="space-y-4">
                <div className="relative">
                  <Mail size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input type="email" required value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="example@email.com" dir="ltr" />
                </div>
                {error && <p className="text-red-400 text-sm flex items-center gap-1"><AlertCircle size={13}/> {error}</p>}
                <button type="submit" disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 transition">
                  {loading ? <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/> : <><Mail size={14}/> إرسال رمز التحقق</>}
                </button>
              </form>
            </>
          )}

          {/* Step 2: OTP + New Password */}
          {step === 2 && (
            <>
              <h2 className="text-lg font-semibold text-white mb-1">أدخل رمز التحقق</h2>
              <p className="text-gray-400 text-sm mb-1">
                أُرسل رمز مكوّن من 6 أرقام إلى <span className="text-blue-400">{email}</span>
              </p>
              <p className="text-yellow-600/80 text-xs mb-5 flex items-center gap-1">
                <span>⚠️</span> إذا لم تجد الرسالة، تحقق من مجلد Spam/Junk
              </p>
              <form onSubmit={resetPassword} className="space-y-4">
                {/* OTP */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">رمز التحقق</label>
                  <div className="relative">
                    <ShieldCheck size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input type="text" required maxLength={6} value={otp}
                      onChange={e => setOtp(e.target.value.replace(/\D/g,''))}
                      className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm text-center tracking-widest font-mono text-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="• • • • • •" dir="ltr" />
                  </div>
                </div>
                {/* New Password */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">كلمة المرور الجديدة</label>
                  <div className="relative">
                    <Lock size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input type="password" required minLength={8} value={newPw}
                      onChange={e => setNewPw(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="8 أحرف على الأقل" dir="ltr" />
                  </div>
                </div>
                {/* Confirm */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">تأكيد كلمة المرور</label>
                  <div className="relative">
                    <Lock size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input type="password" required value={confirmPw}
                      onChange={e => setConfirmPw(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="••••••••" dir="ltr" />
                  </div>
                </div>

                {error && <p className="text-red-400 text-sm flex items-center gap-1"><AlertCircle size={13}/> {error}</p>}

                <button type="submit" disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 transition">
                  {loading ? <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/> : <><ShieldCheck size={14}/> تأكيد وتغيير كلمة المرور</>}
                </button>

                <button type="button" onClick={() => { setStep(1); setError('') }}
                  className="w-full text-gray-500 hover:text-gray-300 text-sm py-1 transition">
                  لم تصلك الرسالة؟ إعادة الإرسال
                </button>
              </form>
            </>
          )}

          {/* Step 3: Success */}
          {step === 3 && (
            <div className="text-center space-y-4 py-4">
              <CheckCircle size={56} className="text-green-400 mx-auto" />
              <h2 className="text-xl font-bold text-white">تم تغيير كلمة المرور!</h2>
              <p className="text-gray-400 text-sm">يمكنك الآن تسجيل الدخول بكلمة المرور الجديدة.</p>
              <button onClick={() => navigate('/login')}
                className="mt-4 flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-xl text-sm font-medium mx-auto transition">
                <ArrowRight size={14}/> تسجيل الدخول
              </button>
            </div>
          )}

          <p className="text-center text-sm text-gray-500 mt-6">
            <Link to="/login" className="text-blue-400 hover:text-blue-300">العودة لتسجيل الدخول</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
