import { useState, useEffect } from 'react'
import { useLang } from '../contexts/LangContext'

// (2026-09-27) استطلاع الميزات: "عداد وقت متبقي لكل إشارة قبل ما تنتهي"
// (10 أصوات، أعلى طلب مع "الصفقات المرتبطة"). expires_at موجود بالـSignal
// من البداية، بس ما كان أي مكان بالواجهة يعرضه.
export default function ExpiryCountdown({ expiresAt, className = '' }) {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!expiresAt) return
    const id = setInterval(() => setNow(Date.now()), 30000)
    return () => clearInterval(id)
  }, [expiresAt])

  if (!expiresAt) return null

  const diffMs = new Date(expiresAt).getTime() - now
  if (diffMs <= 0) {
    return <span className={`text-gray-500 ${className}`}>{isAr ? '⏳ منتهية' : '⏳ Expired'}</span>
  }

  const totalMin = Math.floor(diffMs / 60000)
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  const label = h > 0
    ? (isAr ? `${h}س ${m}د متبقية` : `${h}h ${m}m left`)
    : (isAr ? `${m}د متبقية` : `${m}m left`)
  const urgent = diffMs < 30 * 60000

  return (
    <span className={`${urgent ? 'text-amber-400' : 'text-gray-400'} ${className}`}>
      ⏳ {label}
    </span>
  )
}
