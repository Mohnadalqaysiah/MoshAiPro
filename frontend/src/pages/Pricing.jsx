import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { Check, Zap, Star, Copy, CheckCircle, AlertCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DEFAULT_PLANS = [
  {
    key: 'weekly',
    name: 'الأسبوعية',
    price: 7,
    period: '/ أسبوع',
    color: 'blue',
    features: ['تحليل ICT/SMC كامل', 'وكيل الدردشة الذكي', 'تنبيهات Telegram', 'جميع الأزواج', 'دعم فني'],
  },
  {
    key: 'monthly',
    name: 'الشهرية',
    price: 30,
    period: '/ شهر',
    color: 'purple',
    popular: true,
    features: ['كل مزايا الأسبوعية', 'أولوية الدعم الفني', 'تقارير أسبوعية مفصّلة', 'وصول لجميع الأزواج', 'توفير 46%'],
  },
]

export default function Pricing() {
  const { user } = useAuth()
  const [selected, setSelected] = useState('monthly')
  const [txId, setTxId]         = useState('')
  const network = 'TRC20'
  const [step, setStep]         = useState('plan') // plan | pay | done
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [copied, setCopied]     = useState(false)
  const [WALLET, setWallet]     = useState('')
  const PLANS = DEFAULT_PLANS

  useEffect(() => {
    axios.get(`${API}/api/v1/subscription/plans`)
      .then(r => {
        if (r.data.wallet) setWallet(r.data.wallet)
      })
      .catch(() => setWallet('TVh8P92EEjr732frVRpxg1iE4GsfZpLM6E'))
  }, [])

  const copyWallet = () => {
    navigator.clipboard.writeText(WALLET)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const submitPayment = async () => {
    if (!txId.trim()) { setError('أدخل رقم المعاملة TxID'); return }
    setLoading(true); setError('')
    try {
      await axios.post(`${API}/api/v1/subscription/pay`, {
        plan: selected, tx_id: txId.trim(), network
      })
      setStep('done')
    } catch (err) {
      setError(err.response?.data?.detail || 'حدث خطأ. أعد المحاولة.')
    } finally {
      setLoading(false)
    }
  }

  const plan = PLANS.find(p => p.key === selected)

  return (
    <div className="min-h-screen bg-gray-950 px-4 py-12" dir="rtl">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-white">اختر باقتك</h1>
          <p className="text-gray-400 mt-2">ادفع بـ USDT مباشرة عبر Binance - تفعيل فوري</p>
        </div>

        {step === 'plan' && (
          <>
            {/* Plans */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {PLANS.map(p => (
                <div
                  key={p.key}
                  onClick={() => setSelected(p.key)}
                  className={`relative rounded-2xl border-2 p-6 cursor-pointer transition-all ${
                    selected === p.key
                      ? p.color === 'purple'
                        ? 'border-purple-500 bg-purple-900/10'
                        : 'border-blue-500 bg-blue-900/10'
                      : 'border-gray-700 bg-gray-900 hover:border-gray-600'
                  }`}
                >
                  {p.popular && (
                    <div className="absolute -top-3 right-4 bg-purple-600 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
                      <Star size={10} />
                      الأكثر شعبية
                    </div>
                  )}
                  <div className="flex items-end gap-1 mb-4">
                    <span className="text-3xl font-bold text-white">${p.price}</span>
                    <span className="text-gray-400 mb-1 text-sm">{p.period}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-4">{p.name}</h3>
                  <ul className="space-y-2">
                    {p.features.map(f => (
                      <li key={f} className="flex items-center gap-2 text-sm text-gray-300">
                        <Check size={14} className="text-green-400 flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            {!user ? (
              <div className="text-center">
                <p className="text-gray-400 mb-4">يجب تسجيل الدخول أولاً</p>
                <Link to="/register" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-semibold">
                  <Zap size={16} />
                  سجّل مجاناً ثم اشترك
                </Link>
              </div>
            ) : (
              <button
                onClick={() => setStep('pay')}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl text-sm flex items-center justify-center gap-2"
              >
                <Zap size={16} />
                المتابعة للدفع - ${plan?.price} USDT
              </button>
            )}
          </>
        )}

        {step === 'pay' && (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 max-w-lg mx-auto">
            <h2 className="text-lg font-semibold text-white mb-2">إتمام الدفع</h2>
            <p className="text-gray-400 text-sm mb-6">
              الباقة: <span className="text-white font-medium">{plan?.name}</span> —
              المبلغ: <span className="text-green-400 font-bold">${plan?.price} USDT</span>
            </p>

            {/* Wallet */}
            <div className="bg-gray-800 rounded-xl p-4 mb-6">
              <p className="text-xs text-gray-400 mb-2">أرسل USDT إلى هذا العنوان:</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs text-green-400 font-mono break-all">{WALLET}</code>
                <button onClick={copyWallet} className="text-gray-400 hover:text-white flex-shrink-0">
                  {copied ? <CheckCircle size={16} className="text-green-400" /> : <Copy size={16} />}
                </button>
              </div>
              <div className="mt-3">
                <span className="text-xs px-3 py-1 rounded-full border border-blue-500 text-blue-400 bg-blue-900/30">TRC20</span>
              </div>
              <p className="text-xs text-yellow-400 mt-3">
                ⚠️ أرسل المبلغ بالضبط ${plan?.price} USDT على شبكة TRC20 فقط
              </p>
            </div>

            {/* TxID */}
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-1.5">رقم المعاملة (TxID / Hash)</label>
              <input
                type="text"
                value={txId}
                onChange={e => setTxId(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                placeholder="0x..."
                dir="ltr"
              />
              <p className="text-xs text-gray-500 mt-1">أدخل الـ TxID من محفظة Binance بعد إرسال المبلغ</p>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm mb-4 bg-red-900/20 border border-red-700/30 rounded-lg px-3 py-2">
                <AlertCircle size={14} />
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep('plan')}
                className="flex-1 border border-gray-700 text-gray-400 hover:text-white py-2.5 rounded-xl text-sm"
              >
                رجوع
              </button>
              <button
                onClick={submitPayment}
                disabled={loading}
                className="flex-2 flex-1 bg-green-600 hover:bg-green-500 disabled:bg-green-900 text-white font-semibold py-2.5 rounded-xl text-sm"
              >
                {loading ? 'جاري الإرسال...' : 'تأكيد الدفع'}
              </button>
            </div>
          </div>
        )}

        {step === 'done' && (
          <div className="text-center bg-gray-900 border border-gray-800 rounded-2xl p-10 max-w-lg mx-auto">
            <CheckCircle size={48} className="text-green-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">تم استلام طلبك!</h2>
            <p className="text-gray-400 text-sm">
              سيتم التحقق من الدفع وتفعيل حسابك خلال 30 دقيقة. ستصلك رسالة تأكيد.
            </p>
            <Link to="/dashboard" className="mt-6 inline-block bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-semibold text-sm">
              العودة للمنصة
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
