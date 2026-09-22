import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * فحص أهلية معزول لجيل ثالث من واجهات البطاقة المستضافة: `paypal.HostedFields`
 * (الأقدم، سابق لـCardFields — نفس منتج "Advanced Card Payments" على
 * خوادم PayPal لكن endpoint/API مختلف بالكود). راجع DECISIONS.md 22/09:
 * CardFields (classic sdk.js) وWeb SDK v6 كلاهما أعطيا isEligible()=false
 * بمعزل حقيقي — هذا الفحص الثالث لإغلاق أي احتمال باقٍ إن جيل API
 * بعينه (لا الحساب نفسه) وراء الرفض.
 *
 * صفحة منفصلة عمداً عن /paypal-v6-diag — تحميل sdk.js الكلاسيكي هنا
 * يملأ window.paypal، وWeb SDK v6 يتصرّف دفاعياً ولا يستبدله (نفس عطل
 * "createInstance is not a function" الموثَّق)، فلا يصح تشغيل الفحصين
 * بنفس تحميل الصفحة.
 */
export default function PayPalHostedFieldsDiag() {
  const [status, setStatus] = useState('جاري جلب إعدادات PayPal (client_id)...')
  const [result, setResult] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        // نفس /paypal/create-order يرجّع client_id — نطلب أوردر تجريبي فعلي
        // بأقل قيمة ممكنة، فقط للحصول على client_id الحالي من نفس مصدر
        // الحقيقة المستخدم بالدفع الحي (لوحة الإدارة)، لا نسخة مكرّرة بالكود.
        const token = localStorage.getItem('mosh_token')
        const res = await fetch(`${API}/api/v1/subscription/paypal/create-order`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: JSON.stringify({ plan: 'weekly' }),
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
        if (cancelled) return
        setStatus(`تم جلب client_id — جاري تحميل sdk.js (hosted-fields)...`)

        await new Promise((resolve, reject) => {
          const s = document.createElement('script')
          s.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(data.client_id)}&components=buttons,hosted-fields&currency=USD&intent=capture`
          s.onload = resolve
          s.onerror = () => reject(new Error('فشل تحميل sdk.js'))
          document.body.appendChild(s)
        })
        if (cancelled) return
        setStatus('السكربت تحمّل — جاري HostedFields.isEligible()...')

        if (!window.paypal?.HostedFields) {
          throw new Error('window.paypal.HostedFields غير موجودة بعد تحميل السكربت')
        }
        const eligible = window.paypal.HostedFields.isEligible()
        if (!cancelled) { setResult({ eligible, error: null }); setStatus('اكتمل الفحص.') }
      } catch (e) {
        if (!cancelled) { setResult({ eligible: null, error: e.message }); setStatus('فشل الفحص.') }
      }
    })()
    return () => { cancelled = true }
  }, [])

  return (
    <div style={{ background: '#0a0a0a', color: '#facc15', minHeight: '100vh', padding: 24, fontFamily: 'monospace', fontSize: 13, direction: 'ltr' }}>
      <h1 style={{ color: '#fff', fontSize: 16, marginBottom: 16 }}>PayPal HostedFields (legacy) — Isolated Eligibility Check</h1>
      <p>status: {status}</p>
      <br />
      {result && (
        <>
          <p>HostedFields.isEligible(): <b style={{ color: result.eligible ? '#4ade80' : '#f87171' }}>{String(result.eligible)}</b></p>
          <p>error: {String(result.error)}</p>
        </>
      )}
    </div>
  )
}
