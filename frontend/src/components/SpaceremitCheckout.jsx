import { useEffect, useRef, useState } from 'react'

// Spaceremit's SDK expects globals (SP_PUBLIC_KEY, SP_FORM_ID, ...) and callback
// functions defined on `window` before its script tag loads, then reads/writes
// the DOM form directly (adds a hidden SP_payment_code input, fires
// SP_SUCCESSFUL_PAYMENT). We load the script once and re-point the callbacks
// via refs so each mount/plan-change doesn't re-inject the script.
const SPACEREMIT_SCRIPT_SRC = 'https://spaceremit.com/api/v2/js_script/spaceremit.js'
let scriptLoadPromise = null
function loadSpaceremitScript() {
  if (scriptLoadPromise) return scriptLoadPromise
  scriptLoadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SPACEREMIT_SCRIPT_SRC}"]`)
    if (existing) { resolve(); return }
    const s = document.createElement('script')
    s.src = SPACEREMIT_SCRIPT_SRC
    s.async = true
    s.onload = resolve
    s.onerror = () => { scriptLoadPromise = null; reject(new Error('spaceremit script failed to load')) }
    document.body.appendChild(s)
  })
  return scriptLoadPromise
}

export default function SpaceremitCheckout({
  publicKey, amount, currency = 'USD', buyerName, buyerEmail, buyerPhone, notes,
  onSuccess, onError, isAr,
}) {
  const [ready, setReady] = useState(false)
  const onSuccessRef = useRef(onSuccess)
  const onErrorRef   = useRef(onError)
  onSuccessRef.current = onSuccess
  onErrorRef.current   = onError

  useEffect(() => {
    window.SP_PUBLIC_KEY        = publicKey
    window.SP_FORM_ID           = '#spaceremit-form'
    window.SP_SELECT_RADIO_NAME = 'sp-pay-type-radio'
    window.LOCAL_METHODS_BOX_STATUS  = true
    window.LOCAL_METHODS_PARENT_ID   = '#spaceremit-local-methods-pay'
    window.CARD_BOX_STATUS      = false  // معطّل حالياً من Spaceremit — طرق الدفع المحلية فقط
    window.CARD_BOX_PARENT_ID   = '#spaceremit-card-pay'  // لازم يضل معرَّف حتى لو الكارد معطّل — السكربت بيرجع له بغض النظر عن الحالة
    window.SP_FORM_AUTO_SUBMIT_WHEN_GET_CODE = true

    window.SP_SUCCESSFUL_PAYMENT = (code) => onSuccessRef.current?.(code)
    window.SP_FAILD_PAYMENT      = () => onErrorRef.current?.(isAr ? 'فشلت عملية الدفع' : 'Payment failed')
    window.SP_RECIVED_MESSAGE    = (message) => onErrorRef.current?.(message)
    window.SP_NEED_AUTH          = (targetAuthLink) => { if (targetAuthLink) window.location.href = targetAuthLink }

    let cancelled = false
    loadSpaceremitScript()
      .then(() => { if (!cancelled) setReady(true) })
      .catch(() => { if (!cancelled) onErrorRef.current?.(isAr ? 'تعذّر تحميل بوابة الدفع' : 'Could not load payment gateway') })

    return () => { cancelled = true }
  }, [publicKey, isAr])

  return (
    <form id="spaceremit-form" onSubmit={(e) => e.preventDefault()}>
      <input type="hidden" name="amount" defaultValue={amount} />
      <input type="hidden" name="currency" defaultValue={currency} />
      <input type="hidden" name="fullname" defaultValue={buyerName || ''} />
      <input type="hidden" name="email" defaultValue={buyerEmail || ''} />
      <input type="hidden" name="phone" defaultValue={buyerPhone || ''} />
      <input type="hidden" name="notes" defaultValue={notes || ''} />

      <div className="sp-one-type-select mb-4">
        <label className="flex items-center gap-2 text-sm text-gray-300 mb-2 cursor-pointer">
          <input type="radio" name="sp-pay-type-radio" value="local-methods-pay" id="sp_local_methods_radio" defaultChecked />
          {isAr ? 'طرق دفع محلية' : 'Local payment methods'}
        </label>
        <div id="spaceremit-local-methods-pay" />
      </div>

      {/* الكارد معطّل من طرف Spaceremit — بلا radio ولا label، بس الحاوية لازم تضل موجودة */}
      <div id="spaceremit-card-pay" className="hidden" />

      <button
        type="submit"
        disabled={!ready}
        className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:opacity-60 text-white font-bold py-3.5 rounded-xl text-sm transition"
      >
        {isAr ? 'ادفع الآن' : 'Pay now'}
      </button>
    </form>
  )
}
