import { useState, useMemo } from 'react'
import { loadStripe } from '@stripe/stripe-js'
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js'
import { Shield, Loader2 } from 'lucide-react'

// نموذج بطاقة مدمج داخل الصفحة (Stripe Elements) — بدون تحويل المستخدم
// لأي صفحة دفع خارجية. يُعاد استخدام نفس promise لـ loadStripe لكل مفتاح
// حتى لا يعاد تحميل مكتبة Stripe.js عند كل إعادة رسم.
const _stripePromiseCache = new Map()
function getStripePromise(publishableKey) {
  if (!_stripePromiseCache.has(publishableKey)) {
    _stripePromiseCache.set(publishableKey, loadStripe(publishableKey))
  }
  return _stripePromiseCache.get(publishableKey)
}

function CheckoutForm({ amountLabel, payBtnLabel, payingLabel, onSuccess, isAr }) {
  const stripe = useStripe()
  const elements = useElements()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!stripe || !elements) return
    setSubmitting(true)
    setError('')

    const { error: submitErr, paymentIntent } = await stripe.confirmPayment({
      elements,
      redirect: 'if_required',
      confirmParams: {
        return_url: `${window.location.origin}/pricing?stripe_return=1`,
      },
    })

    if (submitErr) {
      setError(submitErr.message || (isAr ? 'تعذّر إتمام الدفع، حاول مرة أخرى' : 'Payment failed, please try again'))
      setSubmitting(false)
      return
    }

    if (paymentIntent && paymentIntent.status === 'succeeded') {
      onSuccess()
      return
    }

    // بعض طرق الدفع تحتاج خطوة تحقق إضافية (نادر) — Stripe يتكفل بها هنا
    setSubmitting(false)
  }

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement options={{ layout: 'tabs' }} />

      {error && (
        <p className="text-red-400 text-xs mt-3">{error}</p>
      )}

      <button
        type="submit"
        disabled={!stripe || submitting}
        className="w-full mt-5 flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:opacity-60 text-white font-bold py-3.5 rounded-xl text-sm transition"
      >
        {submitting ? (
          <><Loader2 size={16} className="animate-spin" /> {payingLabel}</>
        ) : (
          payBtnLabel
        )}
      </button>

      <p className="text-xs text-gray-500 text-center mt-3 flex items-center justify-center gap-1">
        <Shield size={11} className="text-green-400" />
        {isAr ? 'دفع آمن ومشفّر بالكامل — مدعوم من Stripe' : 'Fully secure & encrypted — powered by Stripe'}
      </p>
    </form>
  )
}

export default function StripeInlineCheckout({ clientSecret, publishableKey, amountLabel, payBtnLabel, payingLabel, onSuccess, isAr }) {
  const stripePromise = useMemo(() => getStripePromise(publishableKey), [publishableKey])

  const options = useMemo(() => ({
    clientSecret,
    appearance: {
      theme: 'night',
      variables: {
        colorPrimary: '#6366f1',
        colorBackground: '#111827',
        colorText: '#e5e7eb',
        colorDanger: '#f87171',
        fontFamily: 'inherit',
        borderRadius: '10px',
      },
    },
  }), [clientSecret])

  if (!clientSecret || !publishableKey) return null

  return (
    <Elements stripe={stripePromise} options={options}>
      <CheckoutForm
        amountLabel={amountLabel}
        payBtnLabel={payBtnLabel}
        payingLabel={payingLabel}
        onSuccess={onSuccess}
        isAr={isAr}
      />
    </Elements>
  )
}
