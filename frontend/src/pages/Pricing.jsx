import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { Check, Zap, Star, Copy, CheckCircle, AlertCircle, Shield, Clock, ChevronDown, CreditCard, Loader2 } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import useFAQSchema from '../hooks/useFAQSchema'
import StripeInlineCheckout from '../components/StripeInlineCheckout'
import SpaceremitCheckout from '../components/SpaceremitCheckout'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const PRICING_FAQ_AR = [
  { q: 'ما الفرق بين الباقة الأسبوعية والشهرية؟', a: 'المزايا نفسها بالباقتين (تحليل ICT/SMC كامل، شات AI غير محدود، تنبيهات Telegram، كل الأزواج). الباقة الشهرية توفّر 46% مقارنة بالأسبوعي وتضيف أولوية دعم وتقارير أسبوعية مفصّلة ووصول مبكر للمزايا الجديدة.' },
  { q: 'هل الاشتراك يتجدد تلقائياً؟', a: 'لا. الاشتراك غير ملزم وينتهي تلقائياً في نهاية المدة (أسبوع أو شهر) بدون أي تجديد أو خصم إضافي — تقدر تشترك من جديد يدوياً وقتما تحب.' },
  { q: 'ما طرق الدفع المتاحة؟', a: 'ندفع حالياً عبر USDT (شبكة TRC20) مباشرة، والتسعير بالدولار الأمريكي. التفعيل فوري بعد التحقق من التحويل.' },
  { q: 'هل أقدر أرقّي من الباقة الأسبوعية للشهرية؟', a: 'نعم، تقدر تشترك بالباقة الشهرية في أي وقت حتى لو عندك اشتراك أسبوعي فعّال — الحساب نفسه يستمر بكل بياناتك وسجلّك.' },
]
const PRICING_FAQ_EN = [
  { q: 'What is the difference between the weekly and monthly plan?', a: 'Both plans include the same features (full ICT/SMC analysis, unlimited AI chat, Telegram alerts, all pairs). The monthly plan saves 46% versus weekly and adds priority support, detailed weekly reports, and early access to new features.' },
  { q: 'Does the subscription auto-renew?', a: 'No. Subscriptions are non-binding and expire automatically at the end of the period (week or month) with no renewal or extra charge — you can subscribe again manually whenever you like.' },
  { q: 'What payment methods are available?', a: 'We currently accept USDT (TRC20 network) directly, priced in US dollars. Activation is instant once the transfer is verified.' },
  { q: 'Can I upgrade from weekly to monthly?', a: 'Yes, you can subscribe to the monthly plan at any time even with an active weekly subscription — your account continues with all your data and history intact.' },
]

const T = {
  ar: {
    title: 'اختر باقتك',
    subtitle: 'ادفع بـ USDT مباشرة عبر Binance — تفعيل فوري',
    popular: 'الأكثر شعبية',
    proceedBtn: (price) => `المتابعة للدفع — $${price} USDT`,
    loginNote: 'يجب تسجيل الدخول أولاً للاشتراك',
    loginBtn: 'سجّل مجاناً ثم اشترك',
    payTitle: 'إتمام الدفع',
    planLabel: 'الباقة',
    amountLabel: 'المبلغ',
    sendToLabel: 'أرسل USDT إلى هذا العنوان:',
    copyBtn: 'نسخ',
    copiedBtn: 'تم النسخ',
    networkLabel: 'الشبكة',
    warning: (price) => `⚠️ أرسل المبلغ بالضبط $${price} USDT على شبكة TRC20 فقط`,
    txLabel: 'رقم المعاملة (TxID / Hash)',
    txPlaceholder: '0x...',
    txNote: 'أدخل الـ TxID من محفظة Binance بعد الإرسال',
    txRequired: 'أدخل رقم المعاملة TxID',
    backBtn: 'رجوع',
    confirmBtn: 'تأكيد الدفع',
    sendingBtn: 'جاري الإرسال...',
    stripeBtn: (price) => `ادفع الآن — $${price}`,
    stripePaying: 'جاري تنفيذ الدفع...',
    stripeRedirecting: 'جاري التحويل لصفحة الدفع...',
    orDivider: 'أو ادفع يدوياً بـ USDT',
    cryptoToggle: 'الدفع بعملة رقمية (USDT) بدلاً من ذلك',
    stripeInstant: 'تفعيل فوري تلقائي — بدون مغادرة الصفحة',
    secureBadge: 'دفع آمن ومشفّر بالكامل — مدعوم من Stripe',
    cardLoading: 'جاري تجهيز نموذج الدفع...',
    spaceremitTitle: 'طرق دفع محلية',
    spaceremitToggle: 'الدفع عبر Spaceremit بدلاً من ذلك',
    spaceremitInstant: 'تفعيل فوري تلقائي بعد تأكيد الدفع',
    doneTitle: 'تم استلام طلبك!',
    doneDesc: 'سيتم التحقق من الدفع وتفعيل حسابك خلال 30 دقيقة. ستصلك رسالة تأكيد.',
    doneTitleCard: 'تم تفعيل اشتراكك!',
    doneDescCard: 'دفعتك بالبطاقة تمّت وتم تفعيل باقتك فوراً. استمتع بالمنصة!',
    activatingTitle: 'تم الدفع بنجاح!',
    activatingDesc: 'جاري تفعيل اشتراكك الآن...',
    dashboardBtn: 'العودة للمنصة',
    guarantee: 'آمن ومشفّر',
    support: 'دعم 24/7',
    instant: 'تفعيل فوري',
  },
  en: {
    title: 'Choose Your Plan',
    subtitle: 'Pay with USDT via Binance — instant activation',
    popular: 'Most Popular',
    proceedBtn: (price) => `Continue to Payment — $${price} USDT`,
    loginNote: 'You must login first to subscribe',
    loginBtn: 'Register Free & Subscribe',
    payTitle: 'Complete Payment',
    planLabel: 'Plan',
    amountLabel: 'Amount',
    sendToLabel: 'Send USDT to this address:',
    copyBtn: 'Copy',
    copiedBtn: 'Copied!',
    networkLabel: 'Network',
    warning: (price) => `⚠️ Send exactly $${price} USDT on TRC20 network only`,
    txLabel: 'Transaction ID (TxID / Hash)',
    txPlaceholder: '0x...',
    txNote: 'Enter the TxID from Binance after sending',
    txRequired: 'Please enter the Transaction ID',
    backBtn: 'Back',
    confirmBtn: 'Confirm Payment',
    sendingBtn: 'Sending...',
    stripeBtn: (price) => `Pay Now — $${price}`,
    stripePaying: 'Processing payment...',
    stripeRedirecting: 'Redirecting to payment page...',
    orDivider: 'Or pay manually with USDT',
    cryptoToggle: 'Pay with crypto (USDT) instead',
    stripeInstant: 'Instant automatic activation — no page redirect',
    secureBadge: 'Fully secure & encrypted — powered by Stripe',
    cardLoading: 'Preparing payment form...',
    spaceremitTitle: 'Local payment methods',
    spaceremitToggle: 'Pay via Spaceremit instead',
    spaceremitInstant: 'Instant automatic activation once payment is confirmed',
    doneTitle: 'Request Received!',
    doneDesc: 'Payment will be verified and your account activated within 30 minutes.',
    doneTitleCard: 'Subscription Activated!',
    doneDescCard: 'Your card payment went through and your plan is active now. Enjoy the platform!',
    activatingTitle: 'Payment Successful!',
    activatingDesc: 'Activating your subscription now...',
    dashboardBtn: 'Go to Dashboard',
    guarantee: 'Secure & Encrypted',
    support: '24/7 Support',
    instant: 'Instant Activation',
  },
}

const DEFAULT_PLANS = [
  {
    key: 'weekly',
    nameAr: 'الأسبوعية',
    nameEn: 'Weekly',
    price: 7,
    periodAr: '/ أسبوع',
    periodEn: '/ week',
    popular: false,
    featuresAr: ['تحليل ICT/SMC كامل', 'شات AI غير محدود', 'تنبيهات Telegram', 'جميع الأزواج', 'تحليل متعدد الفريمات'],
    featuresEn: ['Full ICT/SMC Analysis', 'Unlimited AI Chat', 'Telegram Alerts', 'All Pairs', 'Multi-Timeframe Analysis'],
  },
  {
    key: 'monthly',
    nameAr: 'الشهرية',
    nameEn: 'Monthly',
    price: 30,
    periodAr: '/ شهر',
    periodEn: '/ month',
    popular: true,
    featuresAr: ['كل مزايا الأسبوعي', 'أولوية الدعم الفني', 'تقارير أسبوعية مفصّلة', 'وصول مبكر للمزايا الجديدة', 'توفير 46% مقارنة بالأسبوعي'],
    featuresEn: ['All Weekly Features', 'Priority Support', 'Detailed Weekly Reports', 'Early Access to New Features', 'Save 46% vs Weekly'],
  },
]

export default function Pricing() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'

  useSEO({
    title: isAr
      ? 'أسعار الاشتراك | Qaffel AI — $7 أسبوعي أو $30 شهري'
      : 'Pricing | Qaffel AI — $7/week or $30/month',
    description: isAr
      ? 'اشترك في Qaffel AI بـ $7/أسبوع أو $30/شهر. احصل على إشارات تداول ICT/SMC غير محدودة للذهب والبيتكوين والفوركس مباشرة على Telegram.'
      : 'Subscribe to Qaffel AI for $7/week or $30/month. Get unlimited ICT/SMC trading signals for Gold, Bitcoin and Forex delivered straight to Telegram.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'الأسعار' : 'Pricing', path: isAr ? '/pricing' : '/en/pricing' },
  ])
  useFAQSchema('ld-faq-pricing', isAr ? PRICING_FAQ_AR : PRICING_FAQ_EN)
  const t = T[lang] || T.ar

  const [selected, setSelected]   = useState('monthly')
  const [txId, setTxId]           = useState('')
  const network = 'TRC20'
  const [step, setStep]           = useState('plan')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [copied, setCopied]       = useState(false)
  const [WALLET, setWallet]       = useState('')
  const [PLANS, setPlans]         = useState(DEFAULT_PLANS)
  const [cardPaymentEnabled, setCardPaymentEnabled] = useState(false)
  const [spaceremitEnabled, setSpaceremitEnabled]     = useState(false)
  const [spaceremitPublicKey, setSpaceremitPublicKey] = useState('')
  const [showCrypto, setShowCrypto] = useState(false)
  const [showSpaceremit, setShowSpaceremit] = useState(false)
  const [paidVia, setPaidVia]     = useState('usdt')
  const [spaceremitAuthLink, setSpaceremitAuthLink] = useState('')  // fallback link if the auth popup was blocked
  const hasPrimaryMethod = cardPaymentEnabled || spaceremitEnabled

  // Stripe Elements — نموذج بطاقة مدمج داخل الصفحة
  const [clientSecret, setClientSecret]         = useState('')
  const [publishableKey, setPublishableKey]     = useState('')
  const [intentLoading, setIntentLoading]       = useState(false)

  useEffect(() => {
    axios.get(`${API}/api/v1/subscription/plans`)
      .then(r => {
        if (r.data.wallet) setWallet(r.data.wallet)
        setCardPaymentEnabled(!!r.data.card_payment_enabled)
        setSpaceremitEnabled(!!r.data.spaceremit_enabled)
        setSpaceremitPublicKey(r.data.spaceremit_public_key || '')
        if (r.data.plans) {
          setPlans(DEFAULT_PLANS.map(p => {
            const api = r.data.plans[p.key]
            if (!api) return p
            return {
              ...p,
              price: api.price_usd ?? p.price,
              nameAr: api.name ?? p.nameAr,
              nameEn: api.name_en ?? p.nameEn,
              featuresAr: api.features ?? p.featuresAr,
              featuresEn: api.features_en ?? p.featuresEn,
            }
          }))
        }
      })
      .catch(() => setWallet('TVh8P92EEjr732frVRpxg1iE4GsfZpLM6E'))
  }, [])

  const copyWallet = () => {
    navigator.clipboard.writeText(WALLET)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const submitPayment = async () => {
    if (!txId.trim()) { setError(t.txRequired); return }
    setLoading(true); setError('')
    try {
      await axios.post(`${API}/api/v1/subscription/pay`, {
        plan: selected, tx_id: txId.trim(), network
      })
      setStep('done')
    } catch (err) {
      setError(err.response?.data?.detail || (isAr ? 'حدث خطأ. أعد المحاولة.' : 'An error occurred. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  const startCardPayment = async (planKey) => {
    setIntentLoading(true); setError(''); setClientSecret(''); setPublishableKey('')
    try {
      const r = await axios.post(`${API}/api/v1/subscription/stripe/payment-intent`, { plan: planKey })
      setClientSecret(r.data.client_secret)
      setPublishableKey(r.data.publishable_key)
    } catch (err) {
      setError(err.response?.data?.detail || (isAr ? 'تعذّر تجهيز الدفع بالبطاقة. جرّب USDT بالأسفل.' : 'Could not start card payment. Try USDT below.'))
    } finally {
      setIntentLoading(false)
    }
  }

  const goToPay = () => {
    setStep('pay')
    if (cardPaymentEnabled) startCardPayment(selected)
  }

  const onStripeSuccess = async () => {
    setPaidVia('card')
    setStep('activating')
    // الويبهوك يفعّل الاشتراك بشكل غير متزامن — نستطلع الحالة لثوانٍ قليلة
    // كي تظهر شاشة النجاح بمجرد اكتمال التفعيل الفعلي، لا قبله.
    for (let i = 0; i < 8; i++) {
      await new Promise(res => setTimeout(res, 1200))
      try {
        const r = await axios.get(`${API}/api/v1/subscription/status`)
        if (r.data.plan === selected) break
      } catch { /* استمر بالاستطلاع */ }
    }
    setStep('done')
  }

  const onSpaceremitSuccess = async (spaceremitCode) => {
    setSpaceremitAuthLink('')
    setPaidVia('card')
    setStep('activating')
    try {
      await axios.post(`${API}/api/v1/subscription/spaceremit/verify`, {
        plan: selected, spaceremit_code: spaceremitCode,
      })
      setStep('done')
    } catch (err) {
      setError(err.response?.data?.detail || (isAr ? 'تعذّر تأكيد الدفع، حاول مرة أخرى' : 'Could not confirm payment, please try again'))
      setStep('pay')
    }
  }

  // (2026-09-06) نافذة التحقق الخارجية (SP_NEED_AUTH) تنفتح بـpopup بدل ما
  // تدمّر الصفحة — هاد الهاندلر شبكة أمان لما الـpopup يُغلق بدون ما نستلم
  // SP_SUCCESSFUL_PAYMENT صراحةً (مثلاً المستخدم قفلها يدوياً بعد ما شاف
  // النجاح بصفحة البنك). منستنى شوي نعطي الكولباك العادي أولوية، وبعدين
  // نتحقق من حالة الاشتراك فعلياً — الويبهوك (شبكة أمان تانية بالباك اند)
  // ممكن يكون فعّل الاشتراك أصلاً حتى لو الكود ما وصلنا بالفرونت.
  const onSpaceremitAuthClosed = async () => {
    await new Promise(res => setTimeout(res, 1200))
    if (step !== 'pay') return   // onSpaceremitSuccess تولّى الأمر أصلاً
    setPaidVia('card')
    setStep('activating')
    for (let i = 0; i < 8; i++) {
      await new Promise(res => setTimeout(res, 1200))
      try {
        const r = await axios.get(`${API}/api/v1/subscription/status`)
        if (r.data.plan === selected) { setStep('done'); return }
      } catch { /* استمر بالاستطلاع */ }
    }
    setError(isAr
      ? 'إذا أكملت الدفع فعلاً، قد يستغرق التفعيل دقيقة إضافية — حدّث الصفحة بعد قليل. إذا لم يُفعَّل، تواصل مع الدعم.'
      : "If you completed the payment, activation may take a moment — refresh shortly. If it's still not active, contact support.")
    setStep('pay')
  }

  const onSpaceremitAuthBlocked = (link) => setSpaceremitAuthLink(link)

  const plan = PLANS.find(p => p.key === selected)
  const planName = isAr ? plan?.nameAr : plan?.nameEn

  return (
    <PublicLayout>
      <div className="px-4 py-16 min-h-screen" dir={isAr ? 'rtl' : 'ltr'}>
        <div className="max-w-4xl mx-auto">

          {/* Header */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 q-glass px-4 py-1.5 rounded-full mb-4 text-sm" style={{ color: 'var(--q-acc3)' }}>
              <Zap size={12} />
              {isAr ? 'الباقات والأسعار' : 'Plans & Pricing'}
            </div>
            <h1 className="text-4xl font-bold text-white mb-3" style={{ textWrap: 'balance' }}>{t.title}</h1>
            <p className="text-gray-400">{t.subtitle}</p>

            {/* Trust badges */}
            <div className="flex items-center justify-center gap-6 mt-6 text-xs text-gray-500">
              <span className="flex items-center gap-1.5"><Shield size={13} className="text-emerald-400" /> {t.guarantee}</span>
              <span className="flex items-center gap-1.5"><Clock size={13} style={{ color: 'var(--q-acc3)' }} /> {t.support}</span>
              <span className="flex items-center gap-1.5"><Zap size={13} className="text-amber-400" /> {t.instant}</span>
            </div>
          </div>

          {step === 'plan' && (
            <>
              {/* Plans Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {PLANS.map(p => {
                  const isSelected = selected === p.key
                  const features = isAr ? p.featuresAr : p.featuresEn
                  const name = isAr ? p.nameAr : p.nameEn
                  const period = isAr ? p.periodAr : p.periodEn
                  return (
                    <div
                      key={p.key}
                      onClick={() => setSelected(p.key)}
                      className={`relative rounded-2xl border p-7 cursor-pointer transition-all duration-200 ${
                        isSelected ? 'shadow-xl' : 'q-glass q-glass-hover'
                      }`}
                      style={isSelected ? {
                        background: 'linear-gradient(135deg, rgba(255,79,216,0.14), rgba(124,58,237,0.16))',
                        borderColor: 'var(--q-acc1)',
                        boxShadow: '0 20px 45px rgba(124,58,237,0.25)',
                      } : undefined}
                    >
                      {/* Popular badge */}
                      {p.popular && (
                        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 q-cta text-white text-xs font-bold px-4 py-1 rounded-full flex items-center gap-1.5 shadow-lg">
                          <Star size={10} fill="white" />
                          {t.popular}
                        </div>
                      )}

                      {/* Selected indicator */}
                      {isSelected && (
                        <div className={`absolute top-4 ${isAr ? 'left-4' : 'right-4'} w-5 h-5 rounded-full grid place-items-center`} style={{ background: 'var(--q-acc1)' }}>
                          <Check size={12} className="text-white" strokeWidth={3} />
                        </div>
                      )}

                      {/* Price */}
                      <div className="mb-5">
                        <div className="flex items-end gap-1 mb-1">
                          <span className="text-5xl font-black text-white">
                            ${p.price}
                          </span>
                          <span className="text-gray-400 mb-2 text-sm">{period}</span>
                        </div>
                        <h3 className="text-lg font-bold text-white">{name}</h3>
                        {p.key === 'monthly' && (
                          <p className="text-xs text-gray-500 mt-1">
                            {isAr ? `≈ $${(p.price / 4).toFixed(2)} / أسبوع` : `≈ $${(p.price / 4).toFixed(2)} / week`}
                          </p>
                        )}
                      </div>

                      {/* Divider */}
                      <div className="border-t q-line mb-5" />

                      {/* Features */}
                      <ul className="space-y-2.5">
                        {features.map((f, i) => (
                          <li key={i} className="flex items-center gap-2.5 text-sm">
                            <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${isSelected ? '' : 'bg-gray-700/50'}`}
                                 style={isSelected ? { background: 'rgba(255,79,216,0.22)' } : undefined}>
                              <Check size={10} style={isSelected ? { color: 'var(--q-acc1)' } : undefined} className={isSelected ? '' : 'text-gray-400'} strokeWidth={3} />
                            </div>
                            <span className={isSelected ? 'text-gray-200' : 'text-gray-400'}>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )
                })}
              </div>

              {/* CTA */}
              {!user ? (
                <div className="text-center q-glass rounded-2xl p-8">
                  <p className="text-gray-400 mb-4">{t.loginNote}</p>
                  <Link to="/register" className="inline-flex items-center gap-2 q-cta text-white px-8 py-3 rounded-xl font-semibold transition-all hover:scale-105">
                    <Zap size={16} />
                    {t.loginBtn}
                  </Link>
                </div>
              ) : (
                <button
                  onClick={goToPay}
                  className="w-full q-cta text-white font-bold py-4 rounded-2xl text-base flex items-center justify-center gap-2 transition-all hover:scale-[1.02] shadow-xl"
                >
                  <Zap size={18} />
                  {t.proceedBtn(plan?.price)}
                </button>
              )}
            </>
          )}

          {step === 'pay' && (
            <div className="q-glass rounded-2xl p-8 max-w-lg mx-auto">
              <h2 className="text-xl font-bold text-white mb-1">{t.payTitle}</h2>
              <p className="text-gray-400 text-sm mb-6">
                {t.planLabel}: <span className="text-white font-medium">{planName}</span>
                {' · '}
                {t.amountLabel}: <span className="text-emerald-400 font-bold">${plan?.price}</span>
              </p>

              {error && (
                <div className="flex items-center gap-2 text-red-400 text-sm mb-4 bg-red-900/20 border border-red-700/30 rounded-xl px-3 py-2.5">
                  <AlertCircle size={14} />
                  {error}
                </div>
              )}

              {/* Card payment — primary, inline (Stripe Elements — no redirect) */}
              {cardPaymentEnabled && (
                <>
                  <div className="flex items-center gap-2 mb-3">
                    <CreditCard size={15} className="text-indigo-400" />
                    <span className="text-sm font-semibold text-gray-200">
                      {isAr ? 'الدفع بالبطاقة' : 'Pay by Card'}
                    </span>
                    <div className="flex items-center gap-1.5 ms-auto">
                      <span className="text-[10px] font-bold tracking-wide text-gray-400 border border-gray-700 rounded px-1.5 py-0.5">VISA</span>
                      <span className="text-[10px] font-bold tracking-wide text-gray-400 border border-gray-700 rounded px-1.5 py-0.5">Mastercard</span>
                      <span className="text-[10px] font-bold tracking-wide text-gray-400 border border-gray-700 rounded px-1.5 py-0.5">AMEX</span>
                    </div>
                  </div>

                  <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4 mb-3">
                    {intentLoading && (
                      <div className="flex items-center justify-center gap-2 py-8 text-gray-400 text-sm">
                        <Loader2 size={16} className="animate-spin" /> {t.cardLoading}
                      </div>
                    )}
                    {!intentLoading && clientSecret && (
                      <StripeInlineCheckout
                        clientSecret={clientSecret}
                        publishableKey={publishableKey}
                        payBtnLabel={t.stripeBtn(plan?.price)}
                        payingLabel={t.stripePaying}
                        onSuccess={onStripeSuccess}
                        isAr={isAr}
                      />
                    )}
                  </div>

                  <p className="text-xs text-gray-400 text-center mb-6">{t.stripeInstant}</p>
                </>
              )}

              {/* Spaceremit — local payment methods, alternative/secondary to Stripe */}
              {spaceremitEnabled && (
                <>
                  {cardPaymentEnabled && (
                    <button
                      onClick={() => setShowSpaceremit(s => !s)}
                      className="w-full flex items-center justify-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 py-2 mb-2 transition"
                    >
                      {t.spaceremitToggle}
                      <ChevronDown size={13} className={`transition-transform ${showSpaceremit ? 'rotate-180' : ''}`} />
                    </button>
                  )}
                  {(showSpaceremit || !cardPaymentEnabled) && (
                    <div className={cardPaymentEnabled ? 'pt-4 border-t border-gray-800 mb-3' : 'mb-3'}>
                      <div className="flex items-center gap-2 mb-3">
                        <CreditCard size={15} className="text-indigo-400" />
                        <span className="text-sm font-semibold text-gray-200">{t.spaceremitTitle}</span>
                      </div>
                      <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4 mb-2">
                        <SpaceremitCheckout
                          publicKey={spaceremitPublicKey}
                          amount={plan?.price}
                          buyerName={user?.full_name || user?.name || ''}
                          buyerEmail={user?.email || ''}
                          notes={`uid=${user?.id};plan=${selected}`}
                          onSuccess={onSpaceremitSuccess}
                          onError={(msg) => setError(msg)}
                          onAuthClosed={onSpaceremitAuthClosed}
                          onAuthBlocked={onSpaceremitAuthBlocked}
                          isAr={isAr}
                        />
                      </div>
                      {spaceremitAuthLink && (
                        <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-xl p-3 mb-2 text-center space-y-2">
                          <p className="text-xs text-yellow-300">
                            {isAr ? 'المتصفح منع فتح نافذة التحقق تلقائياً — افتحها بالتبويب التالي، أكمل الدفع، ثم ارجع هنا واضغط "تحقّقت من الدفع":' : 'Your browser blocked the verification pop-up — open it in the next tab, complete payment, then come back and click "I\'ve paid":'}
                          </p>
                          <div className="flex items-center justify-center gap-2">
                            <a
                              href={spaceremitAuthLink}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-block bg-yellow-600 hover:bg-yellow-500 text-white text-xs font-semibold px-4 py-2 rounded-lg"
                            >
                              {isAr ? 'فتح صفحة التحقق' : 'Open verification page'}
                            </a>
                            <button
                              onClick={onSpaceremitAuthClosed}
                              className="inline-block bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold px-4 py-2 rounded-lg"
                            >
                              {isAr ? 'تحقّقت من الدفع' : "I've paid"}
                            </button>
                          </div>
                        </div>
                      )}
                      <p className="text-xs text-gray-400 text-center mb-3">{t.spaceremitInstant}</p>
                    </div>
                  )}
                </>
              )}

              {hasPrimaryMethod && (
                <button
                  onClick={() => setShowCrypto(s => !s)}
                  className="w-full flex items-center justify-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 py-2 mb-2 transition"
                >
                  {t.cryptoToggle}
                  <ChevronDown size={13} className={`transition-transform ${showCrypto ? 'rotate-180' : ''}`} />
                </button>
              )}

              {/* Crypto (USDT) — secondary, collapsed by default when a primary method is available */}
              {(showCrypto || !hasPrimaryMethod) && (
                <div className={hasPrimaryMethod ? 'pt-2 border-t border-gray-800' : ''}>
                  {/* Wallet */}
                  <div className="bg-gray-800/80 border border-gray-700/50 rounded-xl p-4 mb-6 mt-4">
                    <p className="text-xs text-gray-400 mb-2">{t.sendToLabel}</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 text-xs text-green-400 font-mono break-all leading-relaxed">{WALLET}</code>
                      <button onClick={copyWallet} className="flex items-center gap-1 text-xs text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 px-2.5 py-1.5 rounded-lg flex-shrink-0 transition">
                        {copied ? <><CheckCircle size={13} className="text-green-400" /> {t.copiedBtn}</> : <><Copy size={13} /> {t.copyBtn}</>}
                      </button>
                    </div>
                    <div className="flex items-center gap-2 mt-3">
                      <span className="text-xs px-3 py-1 rounded-full border border-blue-500/50 text-blue-400 bg-blue-900/20 font-medium">
                        {t.networkLabel}: TRC20
                      </span>
                    </div>
                    <p className="text-xs text-yellow-400/90 mt-3 leading-relaxed">
                      {t.warning(plan?.price)}
                    </p>
                  </div>

                  {/* TxID */}
                  <div className="mb-5">
                    <label className="block text-sm text-gray-300 font-medium mb-1.5">{t.txLabel}</label>
                    <input
                      type="text"
                      value={txId}
                      onChange={e => setTxId(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono transition"
                      placeholder={t.txPlaceholder}
                      dir="ltr"
                    />
                    <p className="text-xs text-gray-500 mt-1.5">{t.txNote}</p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => setStep('plan')}
                      className="flex-1 border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 py-3 rounded-xl text-sm transition"
                    >
                      {t.backBtn}
                    </button>
                    <button
                      onClick={submitPayment}
                      disabled={loading}
                      className="flex-1 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 disabled:opacity-50 text-white font-bold py-3 rounded-xl text-sm transition"
                    >
                      {loading ? t.sendingBtn : t.confirmBtn}
                    </button>
                  </div>
                </div>
              )}

              {!showCrypto && hasPrimaryMethod && (
                <button
                  onClick={() => setStep('plan')}
                  className="w-full border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 py-3 rounded-xl text-sm transition"
                >
                  {t.backBtn}
                </button>
              )}
            </div>
          )}

          {step === 'activating' && (
            <div className="text-center q-glass rounded-2xl p-12 max-w-lg mx-auto">
              <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5" style={{ background: 'rgba(124,58,237,0.18)' }}>
                <Loader2 size={32} className="animate-spin" style={{ color: 'var(--q-acc2)' }} />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">{t.activatingTitle}</h2>
              <p className="text-gray-400 text-sm leading-relaxed">{t.activatingDesc}</p>
            </div>
          )}

          {step === 'done' && (
            <div className="text-center q-glass rounded-2xl p-12 max-w-lg mx-auto">
              <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-5">
                <CheckCircle size={36} className="text-emerald-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">{paidVia === 'card' ? t.doneTitleCard : t.doneTitle}</h2>
              <p className="text-gray-400 text-sm leading-relaxed">{paidVia === 'card' ? t.doneDescCard : t.doneDesc}</p>
              <Link to="/dashboard" className="mt-8 inline-flex items-center gap-2 q-cta text-white px-8 py-3 rounded-xl font-semibold text-sm transition">
                {t.dashboardBtn}
              </Link>
            </div>
          )}
        </div>
      </div>
    </PublicLayout>
  )
}
