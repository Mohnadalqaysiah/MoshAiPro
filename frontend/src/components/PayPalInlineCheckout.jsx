import { useEffect, useRef, useState } from 'react'
import { loadScript } from '@paypal/paypal-js'
import { Shield, Loader2 } from 'lucide-react'

// نموذج "الدفع بالبطاقة". المسار المفضَّل: حقول بطاقة مستضافة بلا أي
// شعار (PayPal Advanced Card Payments) — يحتاج تفعيل/أهلية خاصة من
// PayPal على الحساب (راجع DECISIONS.md 2026-09-19). **حالياً الحساب غير
// مؤهّل** فيسقط تلقائياً (`cardFields.isEligible() === false`) لزر
// PayPal القياسي (يبيّن شعار PayPal، يقبل بطاقات بلا حساب عبر خيار
// "Debit or Credit Card") كحل مؤقت يعمل بلا شرط أهلية. **لا حاجة لأي
// نشر إضافي لاحقاً:** فور موافقة PayPal على الحساب يتحول تلقائياً
// لحقول البطاقة بلا شعار بمجرد ما isEligible() يرجّع true.
const _sdkPromiseCache = new Map()
function getPayPalSdk(clientId) {
  if (!_sdkPromiseCache.has(clientId)) {
    _sdkPromiseCache.set(clientId, loadScript({
      'client-id': clientId,
      components: 'buttons,card-fields',
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
  // 'loading' | 'fields' (بلا شعار) | 'buttons' (زر PayPal القياسي، مؤقت) | 'error'
  const [mode, setMode]             = useState('loading')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]           = useState('')
  const [applePayAvailable, setApplePayAvailable] = useState(false)
  const cardFieldsRef     = useRef(null)
  const buttonsContainerRef = useRef(null)
  const buttonsInstanceRef  = useRef(null)
  const applePayContainerRef = useRef(null)
  const applePayInstanceRef  = useRef(null)

  useEffect(() => {
    if (!orderId || !clientId) return
    let cancelled = false
    setMode('loading'); setError('')

    getPayPalSdk(clientId).then((paypal) => {
      if (cancelled || !paypal) { setMode('error'); return }

      const handleApprove = async () => {
        try {
          await onSuccess()
        } catch {
          setError(isAr ? 'تعذّر تأكيد الدفع، حاول مرة أخرى' : 'Could not confirm payment, try again')
          setSubmitting(false)
        }
      }

      // ── Apple Pay — إضافي، مستقل عن الطريقة الأساسية بالأسفل ───────
      // يفحص أهليته بنفسه (جهاز/متصفح Apple + بطاقة محفوظة بـWallet +
      // تفعيل الحساب) ولا يعرض شيئاً لو غير مؤهَّل — بلا أي شرط إضافي
      // منّا، وبلا أثر على الطريقة الأساسية إن فشل أو لم يُدعَم.
      if (paypal.Buttons && applePayContainerRef.current) {
        try {
          const applePay = paypal.Buttons({
            fundingSource: paypal.FUNDING.APPLEPAY,
            style: { height: 45 },
            createOrder: () => Promise.resolve(orderId),
            onApprove: handleApprove,
            onError: (err) => {
              console.error('apple pay error', err)
              setError(isAr ? 'تعذّر إتمام الدفع عبر Apple Pay' : 'Apple Pay payment failed')
            },
          })
          if (applePay.isEligible()) {
            applePay.render(applePayContainerRef.current)
            applePayInstanceRef.current = applePay
            if (!cancelled) setApplePayAvailable(true)
          }
        } catch (e) {
          console.warn('apple pay unavailable', e)
        }
      }

      // ── المسار المفضَّل: حقول بطاقة بلا شعار ──────────────────────
      if (paypal.CardFields) {
        const cardFields = paypal.CardFields({
          style: FIELD_STYLE,
          createOrder: () => Promise.resolve(orderId),
          onApprove: handleApprove,
          onError: (err) => {
            console.error('card fields error', err)
            setError(isAr ? 'بيانات البطاقة غير صحيحة أو تعذّر إتمام الدفع' : 'Invalid card details or payment failed')
            setSubmitting(false)
          },
        })

        if (cardFields.isEligible()) {
          cardFields.NameField().render('#card-name-field')
          cardFields.NumberField().render('#card-number-field')
          cardFields.ExpiryField().render('#card-expiry-field')
          cardFields.CVVField().render('#card-cvv-field')
          cardFieldsRef.current = cardFields
          if (!cancelled) setMode('fields')
          return
        }
      }

      // ── بديل مؤقت: زر PayPal القياسي (يبيّن شعار PayPal) ──────────
      // buttonsContainerRef.current يجب أن يكون موجوداً دائماً بالـDOM
      // (لا مشروطاً بـmode==='buttons') — هذا الكولباك غير متزامن (بعد
      // تحميل السكربت)، فلو الحاوية كانت تُرسَم فقط عند mode==='buttons'
      // لبقيت null دائماً هنا (لسّا لم نبدّل mode بعد) ورمى استثناء صامت
      // يسقط لرسالة "تعذّر التحميل" — وهو بالضبط ما حدث بالإنتاج.
      if (paypal.Buttons && buttonsContainerRef.current) {
        const btnOpts = {
          style: { layout: 'vertical', shape: 'rect', height: 45, label: 'pay' },
          createOrder: () => Promise.resolve(orderId),
          onApprove: handleApprove,
          onError: (err) => {
            console.error('paypal buttons error', err)
            setError(isAr ? 'تعذّر إتمام الدفع، حاول مرة أخرى' : 'Payment failed, try again')
          },
        }

        // زر واحد فقط — "Debit or Credit Card" — بلا زر PayPal الأزرق ولا
        // Venmo/Pay Later مكدّسين تحته (السلوك الافتراضي لو لم يُحدَّد
        // fundingSource). لو هذا المصدر تحديداً غير مؤهَّل (نادر) نرجع
        // للسلوك الافتراضي بدل تعطيل الدفع كلياً.
        const cardOnly = paypal.Buttons({ ...btnOpts, fundingSource: paypal.FUNDING.CARD })
        buttonsInstanceRef.current = cardOnly.isEligible() ? cardOnly : paypal.Buttons(btnOpts)
        buttonsInstanceRef.current.render(buttonsContainerRef.current)
        if (!cancelled) setMode('buttons')
      } else if (!cancelled) {
        setMode('error')
      }
    }).catch((e) => {
      console.error('payment sdk load error', e)
      if (!cancelled) setMode('error')
    })

    return () => {
      cancelled = true
      if (buttonsInstanceRef.current?.close) {
        try { buttonsInstanceRef.current.close() } catch { /* تجاهل — العنصر قد يكون أُزيل أصلاً */ }
      }
      if (applePayInstanceRef.current?.close) {
        try { applePayInstanceRef.current.close() } catch { /* تجاهل */ }
      }
    }
  }, [orderId, clientId])

  const handleFieldsSubmit = async (e) => {
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

  // ملاحظة بنيوية: حاوية أزرار PayPal (buttonsContainerRef) تبقى بالـDOM
  // دائماً (بـ`hidden` لا بإزالتها من الشجرة) — الـeffect غير متزامن، فلو
  // كانت مشروطة بـmode==='buttons' لصار ref.current = null وقت محاولة
  // الرسم فيها (لأن mode لسّا 'loading' حينها)، ويرمي استثناء صامت.

  return (
    <div>
      {mode === 'error' && (
        <p className="text-red-400 text-sm text-center py-4">
          {isAr ? 'تعذّر تحميل نموذج الدفع، حاول لاحقاً أو جرّب طريقة أخرى بالأسفل' : 'Could not load the payment form, try again or use another method below'}
        </p>
      )}

      {/* Apple Pay — إضافي فوق الطريقة الأساسية، يظهر فقط لو مؤهّل فعلاً
          (جهاز Apple ببطاقة محفوظة + تفعيل الحساب). الحاوية تبقى بالـDOM
          دائماً لنفس سبب حاوية زر PayPal (راجع الملاحظة تحت) */}
      <div className={applePayAvailable && mode !== 'error' ? 'mb-3' : 'hidden'}>
        <div ref={applePayContainerRef} />
        <div className="flex items-center gap-3 my-3">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-[11px] text-gray-500">{isAr ? 'أو بالبطاقة' : 'or by card'}</span>
          <div className="flex-1 h-px bg-white/10" />
        </div>
      </div>

      <div className={mode === 'buttons' ? undefined : 'hidden'}>
        <div ref={buttonsContainerRef} />
        {error && <p className="text-red-400 text-xs mt-3 text-center">{error}</p>}
        <p className="text-xs text-gray-500 text-center mt-3 flex items-center justify-center gap-1">
          <Shield size={11} className="text-green-400" />
          {isAr ? 'دفع آمن ومشفّر بالكامل' : 'Fully secure & encrypted'}
        </p>
      </div>

      <form onSubmit={handleFieldsSubmit} className={mode === 'error' || mode === 'buttons' ? 'hidden' : undefined}>
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

        {mode === 'loading' && (
          <div className="flex items-center justify-center gap-2 py-4 text-gray-400 text-sm">
            <Loader2 size={16} className="animate-spin" />
            {isAr ? 'جاري تجهيز نموذج الدفع...' : 'Preparing payment form...'}
          </div>
        )}

        {error && <p className="text-red-400 text-xs mt-3">{error}</p>}

        <button
          type="submit"
          disabled={mode !== 'fields' || submitting}
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
    </div>
  )
}
