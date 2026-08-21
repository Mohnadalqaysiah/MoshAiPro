import { useState, useEffect } from 'react'
import { Clock, Zap } from 'lucide-react'
import { useLang } from '../contexts/LangContext'

const SESSIONS = [
  {
    id: 'asia',
    labelAr: 'آسيا 🌏',    labelEn: 'Asia 🌏',
    openUTC: 0,  closeUTC: 9,
    color:   { bg: 'bg-blue-500/10', text: 'text-blue-300', dot: 'bg-blue-400', badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30', bar: 'bg-blue-500' },
    marketsAr: 'JPY · AUD · NZD',
    marketsEn: 'JPY · AUD · NZD',
  },
  {
    id: 'london',
    labelAr: 'لندن 🏦',    labelEn: 'London 🏦',
    openUTC: 8,  closeUTC: 16,
    color:   { bg: 'bg-purple-500/10', text: 'text-purple-300', dot: 'bg-purple-400', badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30', bar: 'bg-purple-500' },
    marketsAr: 'EUR · GBP · ذهب',
    marketsEn: 'EUR · GBP · Gold',
  },
  {
    id: 'ny',
    labelAr: 'نيويورك 🗽',  labelEn: 'New York 🗽',
    openUTC: 13, closeUTC: 21,
    color:   { bg: 'bg-green-500/10', text: 'text-green-300', dot: 'bg-green-400', badge: 'bg-green-500/20 text-green-300 border-green-500/30', bar: 'bg-green-500' },
    marketsAr: 'USD · ذهب · نفط',
    marketsEn: 'USD · Gold · Oil',
  },
]

function getUTCMinutes() {
  const n = new Date()
  return n.getUTCHours() * 60 + n.getUTCMinutes()
}

function isOpen(s) {
  const m = getUTCMinutes()
  const open = s.openUTC * 60, close = s.closeUTC * 60
  return open < close ? (m >= open && m < close) : (m >= open || m < close)
}

function minutesUntil(targetUTCHour) {
  const diff = targetUTCHour * 60 - getUTCMinutes()
  return diff <= 0 ? diff + 1440 : diff
}

function fmtCountdown(mins, isAr) {
  const h = Math.floor(mins / 60), m = mins % 60
  if (isAr) return h > 0 ? `${h}س ${m}د` : `${m}د`
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function SessionsClock() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const [, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 30000)
    return () => clearInterval(t)
  }, [])

  const now = new Date()
  const utcH = now.getUTCHours(), utcM = now.getUTCMinutes()
  const utcStr = `${String(utcH).padStart(2, '0')}:${String(utcM).padStart(2, '0')} UTC`
  const utcFrac = utcH + utcM / 60
  const overlap = utcFrac >= 13 && utcFrac < 16   // London + NY

  return (
    <div className="bg-gray-900/60 border border-white/8 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center">
            <Clock size={15} className="text-indigo-400" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">
              {isAr ? 'جلسات التداول' : 'Trading Sessions'}
            </h3>
            <p className="text-xs text-gray-500">{utcStr}</p>
          </div>
        </div>
        {overlap && (
          <div className="flex items-center gap-1.5 text-[11px] bg-yellow-500/15 text-yellow-300 border border-yellow-500/30 px-2.5 py-1 rounded-full font-semibold">
            <Zap size={11} />
            {isAr ? 'تداخل لندن + NY ⚡' : 'London + NY Overlap ⚡'}
          </div>
        )}
      </div>

      {/* Sessions */}
      <div className="divide-y divide-white/4">
        {SESSIONS.map(s => {
          const open       = isOpen(s)
          const c          = s.color
          const minsLeft   = open ? minutesUntil(s.closeUTC) : minutesUntil(s.openUTC)
          const countdown  = fmtCountdown(minsLeft, isAr)
          const countLabel = open
            ? (isAr ? `يغلق خلال ${countdown}` : `Closes in ${countdown}`)
            : (isAr ? `يفتح خلال ${countdown}` : `Opens in ${countdown}`)

          // Progress bar — how far through the session (or gap)
          const sessionLen = (s.closeUTC - s.openUTC + 24) % 24 * 60 || 1440
          const elapsed    = open ? (sessionLen - minsLeft) : 0
          const pct        = open ? Math.round((elapsed / sessionLen) * 100) : 0

          return (
            <div key={s.id} className={`px-5 py-3.5 transition-colors ${open ? c.bg : ''}`}>
              <div className="flex items-center gap-3">
                {/* Dot */}
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  open ? c.dot + ' animate-pulse' : 'bg-gray-700'
                }`} />

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`font-semibold text-sm ${open ? c.text : 'text-gray-500'}`}>
                      {isAr ? s.labelAr : s.labelEn}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-bold ${
                      open ? c.badge : 'bg-gray-800/40 text-gray-400 border-gray-700/40'
                    }`}>
                      {open ? (isAr ? 'مفتوح' : 'OPEN') : (isAr ? 'مغلق' : 'CLOSED')}
                    </span>
                  </div>
                  <div className="text-[11px] text-gray-400">
                    {String(s.openUTC).padStart(2,'0')}:00 – {String(s.closeUTC).padStart(2,'0')}:00 UTC
                    &nbsp;·&nbsp;{isAr ? s.marketsAr : s.marketsEn}
                  </div>
                  {open && (
                    <div className="mt-1.5 h-1 bg-gray-800 rounded-full overflow-hidden w-full">
                      <div className={`h-full rounded-full ${c.bar} transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                  )}
                </div>

                {/* Countdown */}
                <span className={`text-xs font-medium flex-shrink-0 ${open ? c.text : 'text-gray-400'}`}>
                  {countLabel}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Best time tip */}
      <div className="px-5 py-3 border-t border-white/5 text-[11px] text-gray-400 flex items-center gap-2">
        <Clock size={11} className="text-indigo-400/60" />
        {isAr
          ? 'أفضل وقت للذهب: تداخل لندن + نيويورك (16:00–19:00 AST)'
          : 'Best Gold time: London + NY Overlap (13:00–16:00 UTC)'}
      </div>
    </div>
  )
}
