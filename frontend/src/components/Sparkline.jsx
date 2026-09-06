import { useEffect, useRef, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const _cache = new Map()   // "symbol:interval:limit" -> {closes, ts}
const CACHE_TTL = 60_000

/**
 * شمعات حقيقية من /markets/{symbol}/candles — لا بيانات وهمية. يُستخدم
 * بأماكن صغيرة (بطاقة إشارة) فقط، فيه كاش خفيف بالذاكرة (60 ثانية) حتى
 * لو ظهر نفس الرمز بأكثر من بطاقة ما يكرر الطلب.
 */
export default function Sparkline({ symbol, interval = '15m', limit = 30, className = '' }) {
  const [closes, setCloses] = useState(null)
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!symbol) return
    let alive = true
    const key = `${symbol}:${interval}:${limit}`
    const cached = _cache.get(key)
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      setCloses(cached.closes)
      return
    }
    axios.get(`${API}/api/v1/markets/${symbol}/candles?interval=${interval}&limit=${limit}`)
      .then(r => {
        const c = (r.data?.data || []).map(x => x.close)
        _cache.set(key, { closes: c, ts: Date.now() })
        if (alive) setCloses(c)
      })
      .catch(() => { if (alive) setCloses([]) })
    return () => { alive = false }
  }, [symbol, interval, limit])

  useEffect(() => {
    const cv = canvasRef.current
    if (!cv || !closes || closes.length < 2) return
    const dpr = window.devicePixelRatio || 1
    const w = cv.clientWidth, h = cv.clientHeight
    if (!w || !h) return
    cv.width = w * dpr; cv.height = h * dpr
    const g = cv.getContext('2d'); g.scale(dpr, dpr)
    const min = Math.min(...closes), max = Math.max(...closes), span = (max - min) || 1, pad = 6
    const x = i => i / (closes.length - 1) * w
    const y = v => h - pad - (v - min) / span * (h - pad * 2)
    g.clearRect(0, 0, w, h)
    const gr = g.createLinearGradient(0, 0, 0, h)
    gr.addColorStop(0, 'rgba(255,255,255,0.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)')
    g.beginPath(); g.moveTo(x(0), h)
    closes.forEach((v, i) => g.lineTo(x(i), y(v)))
    g.lineTo(x(closes.length - 1), h); g.closePath(); g.fillStyle = gr; g.fill()
    g.beginPath(); closes.forEach((v, i) => i ? g.lineTo(x(i), y(v)) : g.moveTo(x(i), y(v)))
    g.strokeStyle = 'rgba(255,255,255,0.9)'; g.lineWidth = 1.75; g.lineJoin = 'round'; g.stroke()
  }, [closes])

  if (closes && closes.length < 2) return null   // ما في بيانات كاندل لهالرمز — ما منرسم شي وهمي
  return <canvas ref={canvasRef} className={className} aria-label={`${symbol} ${interval} sparkline`} />
}
