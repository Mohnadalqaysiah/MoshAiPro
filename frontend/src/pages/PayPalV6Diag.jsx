import { useEffect, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * صفحة تشخيص مستقلة تماماً — لا تحمّل أي كود دفع تاني (لا PayPalInlineCheckout
 * ولا الـSDK الكلاسيكي). الهدف الوحيد: فحص أهلية Web SDK v6 الجديد
 * (createInstance/findEligibleMethods → isEligible('advanced_cards'))
 * بمعزل حقيقي.
 *
 * (2026-09-22) محاولتان سابقتان فشلتا بسببين مختلفين تماماً، وثّقتهما هون
 * حتى ما تُعاد المحاولة بنفس الطريقة لاحقاً:
 *   1. عزل بـiframe (srcdoc) → "No ack for postMessage: pixelReady":
 *      بكسل كشف الاحتيال الداخلي بسكربت v6 يحتاج نافذة top-level حقيقية،
 *      يرفض العمل داخل أي iframe متداخل مهما عُزل.
 *   2. تشغيله بنفس صفحة الدفع الحية (بعد الكلاسيكي) → "createInstance is
 *      not a function": الاثنان يكتبان على window.paypal بنفس الصفحة —
 *      سكربت v6 يتصرّف دفاعياً (لا يستبدل window.paypal الموجود أصلاً من
 *      sdk.js الكلاسيكي)، فلا يضيف createInstance إطلاقاً. مشكلة بنيوية
 *      (تشارك namespace)، لا مسألة ترتيب تحميل.
 *
 * الحل: صفحة top-level حقيقية بلا أي سكربت PayPal آخر إطلاقاً.
 */
export default function PayPalV6Diag() {
  const [status, setStatus] = useState('جاري التحقق من التوكن...')
  const [result, setResult] = useState(null) // { eligible, error }

  useEffect(() => {
    let cancelled = false

    ;(async () => {
      try {
        const { data } = await axios.get(`${API}/api/v1/subscription/paypal/browser-safe-token`)
        if (cancelled) return
        setStatus(`تم جلب التوكن (base_url=${data.base_url}) — جاري تحميل سكربت v6...`)

        const isSandbox = (data.base_url || '').includes('sandbox')
        const scriptSrc = isSandbox
          ? 'https://www.sandbox.paypal.com/web-sdk/v6/core'
          : 'https://www.paypal.com/web-sdk/v6/core'

        await new Promise((resolve, reject) => {
          const s = document.createElement('script')
          s.src = scriptSrc
          s.onload = resolve
          s.onerror = () => reject(new Error('فشل تحميل سكربت v6'))
          document.body.appendChild(s)
        })
        if (cancelled) return
        setStatus('السكربت تحمّل — جاري createInstance...')

        if (typeof window.paypal?.createInstance !== 'function') {
          throw new Error('window.paypal.createInstance غير موجودة بعد تحميل السكربت مباشرة (بلا أي كود تاني بالصفحة)')
        }

        const sdk = await window.paypal.createInstance({
          clientToken: data.access_token,
          components: ['card-fields'],
        })
        if (cancelled) return
        setStatus('createInstance نجح — جاري findEligibleMethods...')

        const methods = await sdk.findEligibleMethods()
        const eligible = methods.isEligible('advanced_cards')
        if (!cancelled) { setResult({ eligible, error: null }); setStatus('اكتمل الفحص.') }
      } catch (e) {
        if (!cancelled) {
          setResult({ eligible: null, error: e.response?.data?.detail || e.message })
          setStatus('فشل الفحص — شوف تفاصيل الخطأ بالأسفل.')
        }
      }
    })()

    return () => { cancelled = true }
  }, [])

  return (
    <div style={{ background: '#0a0a0a', color: '#facc15', minHeight: '100vh', padding: 24, fontFamily: 'monospace', fontSize: 13, direction: 'ltr' }}>
      <h1 style={{ color: '#fff', fontSize: 16, marginBottom: 16 }}>PayPal Web SDK v6 — Isolated Eligibility Check</h1>
      <p>status: {status}</p>
      <br />
      {result && (
        <>
          <p>advanced_cards isEligible(): <b style={{ color: result.eligible ? '#4ade80' : '#f87171' }}>{String(result.eligible)}</b></p>
          <p>error: {String(result.error)}</p>
        </>
      )}
    </div>
  )
}
