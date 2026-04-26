import { useState, useEffect } from 'react'
import { Download, Share, X, Plus, Square } from 'lucide-react'

export default function PWAInstallBanner() {
  const [show, setShow]     = useState(false)
  const [platform, setPlatform] = useState(null) // 'android' | 'ios'
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [step, setStep]     = useState(0) // for iOS multi-step

  useEffect(() => {
    // Don't show if already dismissed
    if (localStorage.getItem('pwa-banner-dismissed')) return

    // Don't show if already installed (standalone mode)
    if (window.matchMedia('(display-mode: standalone)').matches) return
    if (window.navigator.standalone === true) return

    const ua = navigator.userAgent

    // Android / Chrome: capture beforeinstallprompt
    const handler = (e) => {
      e.preventDefault()
      setDeferredPrompt(e)
      setPlatform('android')
      setShow(true)
    }
    window.addEventListener('beforeinstallprompt', handler)

    // iOS Safari detection
    const isIOS = /iPhone|iPad|iPod/.test(ua)
    const isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|OPiOS|EdgiOS/.test(ua)
    if (isIOS && isSafari) {
      setPlatform('ios')
      setShow(true)
    }

    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  const dismiss = () => {
    setShow(false)
    localStorage.setItem('pwa-banner-dismissed', '1')
  }

  const installAndroid = async () => {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    if (outcome === 'accepted') {
      dismiss()
    }
  }

  if (!show) return null

  // ── iOS step-by-step guide ──────────────────────────────────────────────
  if (platform === 'ios') {
    const steps = [
      { icon: <Share size={20} className="text-blue-400" />, text: 'اضغط زر المشاركة في أسفل Safari' },
      { icon: <Plus size={20} className="text-green-400" />, text: 'اختر "إضافة إلى الشاشة الرئيسية"' },
      { icon: <Square size={20} className="text-purple-400" />, text: 'اضغط "إضافة" لتثبيت التطبيق' },
    ]
    return (
      <div className="fixed bottom-0 inset-x-0 z-50 p-3 pb-safe" dir="rtl">
        <div className="bg-gray-900 border border-indigo-500/40 rounded-2xl shadow-2xl overflow-hidden"
          style={{ boxShadow: '0 -4px 40px rgba(99,102,241,0.15)' }}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700/60">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
                <Download size={16} className="text-blue-400" />
              </div>
              <div>
                <p className="text-white font-bold text-sm">ثبّت التطبيق على iPhone</p>
                <p className="text-gray-400 text-xs">استمتع بتجربة تطبيق أصلي — مجاناً</p>
              </div>
            </div>
            <button onClick={dismiss} className="text-gray-500 hover:text-white p-1">
              <X size={16} />
            </button>
          </div>

          {/* Steps */}
          <div className="px-4 py-3 space-y-2">
            {steps.map((s, i) => (
              <div
                key={i}
                className={`flex items-center gap-3 p-2.5 rounded-xl transition-all duration-300 ${
                  step === i ? 'bg-white/5 border border-white/10' : 'opacity-50'
                }`}
                onClick={() => setStep(i)}
              >
                <div className="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0">
                  {s.icon}
                </div>
                <span className="text-sm text-gray-200">{s.text}</span>
                <span className="mr-auto text-xs text-gray-600 font-mono">{i + 1}</span>
              </div>
            ))}
          </div>

          {/* Step nav */}
          <div className="px-4 pb-4 flex gap-2">
            {step > 0 && (
              <button
                onClick={() => setStep(s => s - 1)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-xl text-sm"
              >
                السابق
              </button>
            )}
            {step < steps.length - 1 ? (
              <button
                onClick={() => setStep(s => s + 1)}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold"
              >
                التالي
              </button>
            ) : (
              <button
                onClick={dismiss}
                className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white rounded-xl text-sm font-semibold"
              >
                تم التثبيت ✓
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  // ── Android / Chrome one-tap install ───────────────────────────────────
  return (
    <div className="fixed bottom-0 inset-x-0 z-50 p-3 pb-safe" dir="rtl">
      <div className="bg-gray-900 border border-blue-500/40 rounded-2xl shadow-2xl flex items-center gap-3 px-4 py-3"
        style={{ boxShadow: '0 -4px 40px rgba(59,130,246,0.15)' }}>
        <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
          <Download size={18} className="text-blue-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white font-bold text-sm">ثبّت التطبيق</p>
          <p className="text-gray-400 text-xs truncate">استخدمه بدون متصفح — يعمل أوفلاين</p>
        </div>
        <button
          onClick={installAndroid}
          className="flex-shrink-0 bg-blue-600 hover:bg-blue-500 active:scale-95 text-white px-4 py-2 rounded-xl text-sm font-semibold transition-all"
        >
          تثبيت
        </button>
        <button onClick={dismiss} className="text-gray-500 hover:text-white p-1 flex-shrink-0">
          <X size={16} />
        </button>
      </div>
    </div>
  )
}
