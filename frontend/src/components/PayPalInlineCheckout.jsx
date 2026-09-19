import { useEffect, useRef, useState } from 'react'
import { loadScript } from '@paypal/paypal-js'
import { Shield, Loader2 } from 'lucide-react'

// نموذج "الدفع بالبطاقة" — رقم/تاريخ/CVV بلا أي شعار أو اسم معالج ظاهر
// للعميل، بنفس مكان ومظهر نموذج البطاقة السابق بالضبط. يُعالَج بالخلفية
// عبر PayPal Advanced Card Payments (حقول بطاقة مستضافة). نُعيد استخدام
// نفس promise لتحميل السكربت لكل client_id حتى لا يعاد تحميله بكل رسم.
const _sdkPromiseCache = new Map()
function getPayPalSdk(clientId) {
  if (!_sdkPromiseCache.has(clientId)) {
    _sdkPromiseCache.set(clientId, loadScript({
      'client-id': clientId,
      components: 'card-fields',
      currency: 'USD',
      intent: 'capture',
    }))
  }
  return _sdkPromiseCache.get(clientId)
}

const FIELD_STYLE = {
  input: { color: '#e5e7eb', 'font-size': '14px', 'font-family': 'inherit' },
  '.invalid': { color: '#f87171' },
}

export default function PayPalInlineCheckout({
  orderId, clientId, payBtnLabel, payingLabel, onSuccess, isAr,
}) {
  const [ready, setReady]           = useState(false)
  const [eligible, setEligible]     = useState(true)
  const [loadError, setLoadError]   = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]           = useState('')
  const cardFieldsRef = useRef(null)

  useEffect(() => {
    if (!orderId || !clientId) return
    let cancelled = false
    setReady(false)

    getPayPalSdk(clientId).then((paypal) => {
      if (cancelled || !paypal?.CardFields) { setLoadError(true); return }

      const cardFields = paypal.CardFields({
        style: FIELD_STYLE,
        createOrder: () => Promise.resolve(orderId),
        onApprove: async () => {
          try {
            await onSuccess()
          } catch {
            setError(isAr ? 'تعذّر تأكيد الدفع، حاول مرة أخرى' : 'Could not confirm payment, try again')
            setSubmitting(false)
          }
        },
        onError: (err) => {
          console.error('card fields error', err)
          setError(isAr ? 'بيانات البطاقة غير صحيحة أو تعذّر إتمام الدفع' : 'Invalid card details or payment failed')
          setSubmitting(false)
        },
      })

      if (!cardFields.isEligible()) { setEligible(false); return }

      cardFields.NameField().render('#card-name-field')
      cardFields.NumberField().render('#card-number-field')
      cardFields.ExpiryField().render('#card-expiry-field')
      cardFields.CVVField().render('#card-cvv-field')

      cardFieldsRef.current = cardFields
      if (!cancelled) setReady(true)
    }).catch((e) => {
      console.error('payment sdk load error', e)
      if (!cancelled) setLoadError(true)
    })

    return () => { cancelled = true }
  }, [orderId, clientId])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!cardFieldsRef.current) return
    setSubmitting(true); setError('')
    try {
      await cardFieldsRef.current.submit()
      // النجاح يكمل داخل onApprove أعلاه
    } catch {
      setError(isAr ? 'تعذّر إتمام الدفع، تحقق من بيانات البطاقة' : 'Payment failed, check your card details')
      setSubmitting(false)
    }
  }

  if (!orderId || !clientId) return null

  if (loadError) {
    return (
      <p className="text-red-400 text-sm text-center py-4">
        {isAr ? 'تعذّر تحميل نموذج الدفع، حاول لاحقاً أو جرّب طريقة أخرى بالأسفل' : 'Could not load the payment form, try again or use another method below'}
      </p>
    )
  }

  if (!eligible) {
    return (
      <p className="text-amber-400 text-sm text-center py-4">
        {isAr ? 'الدفع بالبطاقة غير متاح حالياً، جرّب طريقة أخرى بالأسفل' : 'Card payment is unavailable right now, try another method below'}
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">{isAr ? 'الاسم على البطاقة' : 'Name on card'}</label>
          <div id="card-name-field" className="bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 min-h-[42px]" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">{isAr ? 'رقم البطاقة' : 'Card number'}</label>
          <div id="card-number-field" className="bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 min-h-[42px]" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">{isAr ? 'تاريخ الانتهاء' : 'Expiry'}</label>
            <div id="card-expiry-field" className="bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 min-h-[42px]" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">CVV</label>
            <div id="card-cvv-field" className="bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 min-h-[42px]" />
          </div>
        </div>
      </div>

      {!ready && (
        <div className="flex items-center justify-center gap-2 py-4 text-gray-400 text-sm">
          <Loader2 size={16} className="animate-spin" />
          {isAr ? 'جاري تجهيز نموذج الدفع...' : 'Preparing payment form...'}
        </div>
      )}

      {error && <p className="text-red-400 text-xs mt-3">{error}</p>}

      <button
        type="submit"
        disabled={!ready || submitting}
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
        {isAr ? 'دفع آمن ومشفّر بالكامل' : 'Fully secure & encrypted'}
      </p>
    </form>
  )
}
