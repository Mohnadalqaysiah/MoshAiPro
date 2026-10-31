import { Send } from 'lucide-react'

// (2026-10-31، طلب المالك) رابط القناة العامة بالداشبورد، لكل مستخدم حتى من ربط حسابه: الربط يخص البوت، والقناة منفصلة عنه.
const CHANNEL_URL = 'https://t.me/QaffelPlatform'

export default function TelegramChannelCard({ isAr }) {
  return (
    <a
      href={CHANNEL_URL}
      target="_blank"
      rel="noreferrer"
      dir={isAr ? 'rtl' : 'ltr'}
      className="flex items-center gap-3 rounded-2xl p-4 border q-line bg-gradient-to-br from-sky-500/10 to-cyan-500/5 hover:from-sky-500/15 transition-colors"
    >
      <span className="w-10 h-10 rounded-xl bg-[#229ED9]/20 grid place-items-center flex-shrink-0">
        <Send size={18} className="text-sky-300" />
      </span>
      <span className="flex-1 min-w-0">
        <span className="block text-white font-bold text-sm">{isAr ? 'تابع قناتنا على تيليجرام' : 'Follow our Telegram channel'}</span>
        <span className="block text-xs text-gray-300 truncate" dir="ltr" style={{ textAlign: isAr ? 'right' : 'left' }}>@QaffelPlatform</span>
      </span>
      <span className="flex-shrink-0 bg-[#229ED9] text-white rounded-xl px-3 py-2 text-xs font-semibold">{isAr ? 'متابعة' : 'Follow'}</span>
    </a>
  )
}
