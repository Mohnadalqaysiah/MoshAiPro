/**
 * TelegramLinkStep — (2026-11-09) شاشة "خطوة أخيرة" بعد التسجيل: ربط تيليجرام.
 *
 * القياس (diag_link_funnel.py): 95% ممن يربطون يربطون خلال ساعة من التسجيل، فلحظة التسجيل هي الفرصة.
 * كان الربط خطوة ثالثة بجولة تعريف تُتخطّى، ومستخدم Google (مفعَّل تلقائياً) لا يرى نافذة التفعيل التي
 * فيها خيار تيليجرام — فيربط أقل. هنا خطوة واضحة لكل جديد، مع QR لمن فتح من الكمبيوتر.
 * تُغلق تلقائياً عند اكتمال الربط (يُفحص /me كل بضع ثوانٍ وهي مفتوحة).
 */
import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { QRCodeSVG } from 'qrcode.react'
import { CheckCircle2, Send, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const T = {
  ar: {
    title: 'خطوة أخيرة: اربط تيليجرام',
    sub: 'لتصلك الإشارات وتحذيرات الأخبار لحظة صدورها، حتى والمنصة مغلقة.',
    points: ['الإشارة تصلك فوراً بالدخول والوقف والأهداف', 'تحذير قبل الأخبار المهمة', 'ضغطة واحدة — يفتح البوت، ثم اضغط Start'],
    btn: 'ربط تيليجرام',
    qr: 'أو امسح الرمز بكاميرا جوالك',
    later: 'لاحقاً',
    waiting: 'بانتظار الضغط على Start في البوت…',
    done: 'تم الربط ✅ ستصلك الإشارات على تيليجرام',
  },
  en: {
    title: 'One step left: link Telegram',
    sub: 'So signals and news alerts reach you the moment they are issued, even with the platform closed.',
    points: ['Signals arrive instantly with entry, stop and targets', 'A heads-up before major news', 'One tap — it opens the bot, then press Start'],
    btn: 'Link Telegram',
    qr: 'Or scan the code with your phone camera',
    later: 'Later',
    waiting: 'Waiting for you to press Start in the bot…',
    done: 'Linked ✅ signals will reach you on Telegram',
  },
}

export default function TelegramLinkStep({ onClose }) {
  const { user, refreshUser } = useAuth()
  const { lang } = useLang()
  const t = T[lang === 'en' ? 'en' : 'ar']
  const [link, setLink] = useState('')
  const [opened, setOpened] = useState(false)
  const linked = !!user?.telegram_linked
  const refreshRef = useRef(refreshUser)
  refreshRef.current = refreshUser
  const desktop = typeof window !== 'undefined' && window.matchMedia('(min-width: 768px) and (pointer: fine)').matches

  useEffect(() => {
    axios.get(`${API}/api/v1/auth/telegram-link`).then(r => setLink(r.data.link || '')).catch(() => {})
  }, [])

  // فحص الربط وهي مفتوحة: أسرع بعد فتح البوت
  useEffect(() => {
    if (linked) return
    const id = setInterval(() => { Promise.resolve(refreshRef.current?.()).catch(() => {}) }, opened ? 4000 : 10000)
    return () => clearInterval(id)
  }, [opened, linked])

  useEffect(() => {
    if (!linked) return
    const id = setTimeout(onClose, 2500)
    return () => clearTimeout(id)
  }, [linked, onClose])

  return (
    <div className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" dir={lang === 'en' ? 'ltr' : 'rtl'}>
      <div className="relative w-full max-w-md rounded-2xl bg-gray-900 border border-white/10 shadow-2xl p-6">
        <button onClick={onClose} aria-label={t.later}
          className="absolute top-3 end-3 w-8 h-8 grid place-items-center rounded-lg text-gray-500 hover:text-gray-200 hover:bg-white/5">
          <X size={16} />
        </button>

        <div className="w-12 h-12 rounded-2xl bg-[#229ED9]/15 grid place-items-center mb-4">
          <Send size={22} className="text-[#229ED9]" />
        </div>
        <h2 className="text-white text-lg font-extrabold mb-1">{t.title}</h2>
        <p className="text-gray-400 text-sm leading-relaxed mb-4">{t.sub}</p>

        {linked ? (
          <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm p-3">
            <CheckCircle2 size={18} /> {t.done}
          </div>
        ) : (
          <>
            <ul className="space-y-1.5 mb-5">
              {t.points.map(p => (
                <li key={p} className="flex items-start gap-2 text-sm text-gray-300">
                  <CheckCircle2 size={15} className="text-[#229ED9] mt-0.5 flex-shrink-0" /> {p}
                </li>
              ))}
            </ul>

            <a href={link || undefined} target="_blank" rel="noopener noreferrer"
              onClick={() => setOpened(true)}
              className={`flex items-center justify-center gap-2 w-full rounded-xl py-3 font-bold text-white bg-[#229ED9] hover:bg-[#1c8cc2] transition-colors ${link ? '' : 'opacity-60 pointer-events-none'}`}>
              <Send size={16} /> {t.btn}
            </a>

            {desktop && link && (
              <div className="mt-4 flex flex-col items-center gap-2">
                <div className="bg-white p-2.5 rounded-xl"><QRCodeSVG value={link} size={132} /></div>
                <span className="text-xs text-gray-500">{t.qr}</span>
              </div>
            )}

            {opened && <p className="mt-3 text-center text-xs text-gray-400 animate-pulse">{t.waiting}</p>}

            <button onClick={onClose} className="mt-4 w-full text-center text-sm text-gray-500 hover:text-gray-300">
              {t.later}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
