import { useState } from 'react'
import axios from 'axios'
import { Zap, RefreshCw, AlertCircle, Calculator, Eye, TrendingUp, TrendingDown } from 'lucide-react'
import useMarkets from '../hooks/useMarkets'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TIMEFRAMES = ['15m', '1h', '4h', '1day']

const T = {
  ar: {
    title: 'تحليل الإشارات', sub: 'تحليل متقدم بمحرك الذكاء الاصطناعي v5',
    market: 'السوق', timeframe: 'الإطار الزمني', analyze: 'تحليل الآن', analyzing: 'جاري التحليل...',
    conf: 'نسبة الثقة', currentPrice: 'السعر الحالي', entryZone: 'منطقة الدخول',
    sl: 'وقف الخسارة', tp1: 'هدف 1', tp2: 'هدف 2', tp3: 'هدف 3',
    rr: 'Risk/Reward', lot: 'حجم اللوت', balanceRisk: 'البالانس / المخاطرة',
    entryLevels: 'مستويات الدخول', analysis: 'تفاصيل التحليل',
    trend: 'الاتجاه', zone: 'المنطقة', liquidity: 'السيولة',
    buy: 'شراء', sell: 'بيع', wait: 'انتظار',
    watchZones: 'مناطق المراقبة',
    waitReason: 'لا توجد إشارة واضحة — انتظر تأكيد Sweep + Rejection',
    noSweep: 'لم يُكتشف Stop Hunt — السوق لم يمسح سيولة بعد',
    sweepNoReject: 'تم اكتساح سيولة لكن بدون رفض مؤكد — انتظر إغلاق شمعة رفض',
    nearestBSL: 'أقرب سيولة فوق السعر (BSL)',
    nearestSSL: 'أقرب سيولة تحت السعر (SSL)',
    nearestBullOB: 'Order Block صاعد',
    nearestBearOB: 'Order Block هابط',
    sweepSection: 'تحليل السيولة — Stop Hunt',
    sweepDetected: 'تم اكتشاف Stop Hunt',
    sweepNone: 'لا يوجد Stop Hunt',
    sweepType: 'النوع',
    sweepLevel: 'مستوى الاكتساح',
    sweepRejection: 'رفض مؤكد',
    sweepQuality: 'الجودة',
    sweepCandlesAgo: 'منذ (شمعات)',
    orderBlocks: 'Order Blocks',
    obBull: 'صاعد (دعم)',
    obBear: 'هابط (مقاومة)',
    futuresWarn: '⚠️ السعر من عقود الآجل — قد يختلف ±5 نقاط عن سعر Spot في منصتك',
  },
  en: {
    title: 'Signal Analysis', sub: 'Advanced analysis powered by AI Engine v5',
    market: 'Market', timeframe: 'Timeframe', analyze: 'Analyze Now', analyzing: 'Analyzing...',
    conf: 'Confidence', currentPrice: 'Current Price', entryZone: 'Entry Zone',
    sl: 'Stop Loss', tp1: 'Target 1', tp2: 'Target 2', tp3: 'Target 3',
    rr: 'Risk/Reward', lot: 'Lot Size', balanceRisk: 'Balance / Risk',
    entryLevels: 'Entry Levels', analysis: 'Analysis Details',
    trend: 'Trend', zone: 'Zone', liquidity: 'Liquidity',
    buy: 'BUY', sell: 'SELL', wait: 'WAIT',
    watchZones: 'Watch Zones',
    waitReason: 'No clear signal — wait for Sweep + Rejection confirmation',
    noSweep: 'No Stop Hunt detected — market has not swept liquidity yet',
    sweepNoReject: 'Liquidity swept but no rejection confirmed — wait for rejection candle close',
    nearestBSL: 'Nearest liquidity above price (BSL)',
    nearestSSL: 'Nearest liquidity below price (SSL)',
    nearestBullOB: 'Bullish Order Block',
    nearestBearOB: 'Bearish Order Block',
    sweepSection: 'Liquidity Analysis — Stop Hunt',
    sweepDetected: 'Stop Hunt Detected',
    sweepNone: 'No Stop Hunt',
    sweepType: 'Type',
    sweepLevel: 'Swept Level',
    sweepRejection: 'Rejection Confirmed',
    sweepQuality: 'Quality',
    sweepCandlesAgo: 'Candles Ago',
    orderBlocks: 'Order Blocks',
    obBull: 'Bullish (Support)',
    obBear: 'Bearish (Resistance)',
    futuresWarn: '⚠️ Price from futures contracts — may differ ±5 pips from Spot on your platform',
  },
}

const fmtPrice = (v, sym) =>
  typeof v === 'number' ? v.toFixed(sym === 'BTCUSD' ? 2 : 5) : (v ?? '—')

const qualityColor = { STRONG: 'text-green-400', MODERATE: 'text-yellow-400', WEAK: 'text-orange-400', NONE: 'text-gray-500' }

export default function Signals() {
  const { markets } = useMarkets()
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'
  const [symbol, setSymbol] = useState('XAUUSD')
  const [timeframe, setTimeframe] = useState('1h')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const analyze = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await axios.post(`${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=${timeframe}&advanced_mode=true`)
      setResult(res.data.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const rec = result?.recommendation
  const isWait = !rec || rec === 'WAIT'

  const recColors = { BUY: 'text-green-400', SELL: 'text-red-400', WAIT: 'text-yellow-400' }
  const recBgs   = { BUY: 'bg-green-900/20 border-green-600', SELL: 'bg-red-900/20 border-red-600', WAIT: 'bg-yellow-900/10 border-yellow-700' }
  const recLabel = { BUY: tx.buy, SELL: tx.sell, WAIT: tx.wait }

  // ── Sweep data ────────────────────────────────────────────────────────────
  const sweep     = result?.liquidity_sweep || result?.liquidity?.sweep_analysis || {}
  const hasBull   = sweep.has_bullish_sweep
  const hasBear   = sweep.has_bearish_sweep
  const hasAnySweep = hasBull || hasBear || sweep.ssl_sweep || sweep.bsl_sweep
  const sweepQuality = sweep.sweep_quality || 'NONE'

  // active sweep details (whichever direction was detected)
  const activeSweep = hasBull ? sweep.ssl_sweep : hasBear ? sweep.bsl_sweep : (sweep.ssl_sweep || sweep.bsl_sweep)
  const sweepTypeLabel = hasBull ? 'SSL (Stop Hunt تحت السعر)' : hasBear ? 'BSL (Stop Hunt فوق السعر)' : sweep.ssl_sweep ? 'SSL' : 'BSL'

  // ── Order Blocks ──────────────────────────────────────────────────────────
  const obs        = result?.order_blocks || {}
  const nearestBull = obs.nearest_bullish
  const nearestBear = obs.nearest_bearish

  // ── Liquidity levels ──────────────────────────────────────────────────────
  const liq        = result?.liquidity || {}
  const nearestBSL = liq.nearest_bsl
  const nearestSSL = liq.nearest_ssl

  // ── WAIT reason ───────────────────────────────────────────────────────────
  const gateReason = result?.sweep_gate_reason
  const waitMsg = gateReason === 'NO_SWEEP'
    ? tx.noSweep
    : gateReason === 'SWEEP_NO_REJECTION'
      ? tx.sweepNoReject
      : tx.waitReason

  return (
    <div className="space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      <div>
        <h1 className="text-2xl font-bold text-white">{tx.title}</h1>
        <p className="text-gray-400 text-sm mt-1">{tx.sub}</p>
      </div>

      {/* Controls */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-gray-400 text-sm mb-2 block">{tx.market}</label>
            <select
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm"
            >
              {markets.map(m => <option key={m.symbol} value={m.symbol}>{m.symbol} — {m.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-gray-400 text-sm mb-2 block">{tx.timeframe}</label>
            <select
              value={timeframe}
              onChange={e => setTimeframe(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm"
            >
              {TIMEFRAMES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={analyze}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? <><RefreshCw size={14} className="animate-spin" /> {tx.analyzing}</> : <><Zap size={14} /> {tx.analyze}</>}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-900/30 border border-red-700 rounded-xl text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">

          {/* ── Main Signal Card ── */}
          <div className={`border rounded-xl p-6 ${recBgs[rec] || 'bg-gray-800 border-gray-700'}`}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-gray-400 text-sm">{symbol} / {timeframe}</span>
                <div className={`text-3xl font-bold mt-1 ${recColors[rec] || 'text-gray-400'}`}>
                  {recLabel[rec] || rec}
                </div>
              </div>
              <div className="text-right">
                <div className="text-gray-400 text-sm">{tx.conf}</div>
                <div className="text-3xl font-bold text-white">{result.ai_confidence_score?.toFixed(1)}%</div>
              </div>
            </div>
            {/* WAIT reason banner */}
            {isWait && gateReason && (
              <div className="flex items-start gap-2 mt-2 p-3 bg-yellow-900/20 border border-yellow-700/40 rounded-lg text-yellow-400 text-sm">
                <Eye size={15} className="mt-0.5 shrink-0" />
                {waitMsg}
              </div>
            )}
          </div>

          {/* ── Details Grid ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* LEFT: Entry/SL/TP  OR  Watch Zones */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">

              {/* ── Current Price (always shown) ── */}
              {result.current_price != null && (
                <div className="pb-3 mb-3 border-b border-gray-700">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400 flex items-center gap-1.5">
                      {tx.currentPrice}
                      {result.price_source === 'finnhub_spot'
                        ? <span className="text-green-500 text-xs font-medium">{isAr ? '● مباشر' : '● Live'}</span>
                        : result.price_source?.includes('futures')
                          ? <span className="text-yellow-500 text-xs font-medium">{isAr ? '● آجل' : '● Delayed'}</span>
                          : <span className="text-blue-500 text-xs font-medium">{isAr ? '● مباشر' : '● Live'}</span>}
                    </span>
                    <span className="text-blue-300 font-mono font-semibold">
                      {fmtPrice(result.current_price, symbol)}
                      {result.price_fetched_at && (
                        <span className="text-gray-600 text-xs mr-1">
                          ({new Date(result.price_fetched_at).toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' })})
                        </span>
                      )}
                    </span>
                  </div>
                  {result.price_source?.includes('futures') && (
                    <p className="text-xs text-yellow-700/80 text-right mt-1">{tx.futuresWarn}</p>
                  )}
                </div>
              )}

              {/* ── WAIT: show Watch Zones only ── */}
              {isWait ? (
                <>
                  <h3 className="text-yellow-400 font-semibold mb-3 flex items-center gap-2">
                    <Eye size={15} /> {tx.watchZones}
                  </h3>
                  <div className="space-y-2 text-sm">
                    {nearestBSL?.price && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">{tx.nearestBSL}</span>
                        <span className="text-red-300 font-mono">{fmtPrice(nearestBSL.price, symbol)}</span>
                      </div>
                    )}
                    {nearestSSL?.price && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">{tx.nearestSSL}</span>
                        <span className="text-green-300 font-mono">{fmtPrice(nearestSSL.price, symbol)}</span>
                      </div>
                    )}
                    {nearestBull && (
                      <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                        <span className="text-gray-400">{tx.nearestBullOB}</span>
                        <span className="text-green-400 font-mono text-xs">
                          {fmtPrice(nearestBull.low, symbol)} → {fmtPrice(nearestBull.high, symbol)}
                        </span>
                      </div>
                    )}
                    {nearestBear && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">{tx.nearestBearOB}</span>
                        <span className="text-red-400 font-mono text-xs">
                          {fmtPrice(nearestBear.low, symbol)} → {fmtPrice(nearestBear.high, symbol)}
                        </span>
                      </div>
                    )}
                    {!nearestBSL && !nearestSSL && !nearestBull && !nearestBear && (
                      <p className="text-gray-600 text-xs">— لا توجد مناطق محددة حالياً —</p>
                    )}
                  </div>
                </>
              ) : (
                /* ── BUY / SELL: show Entry / SL / TP ── */
                <>
                  <h3 className="text-white font-semibold mb-3">{tx.entryLevels}</h3>
                  <div className="space-y-2 text-sm">
                    {/* Entry Zone */}
                    {(result.levels?.entry_zone_min || result.levels?.entry) && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">{tx.entryZone}</span>
                        <span className="text-white font-mono">
                          {result.levels.entry_zone_min && result.levels.entry_zone_max
                            ? `${result.levels.entry_zone_min} — ${result.levels.entry_zone_max}`
                            : result.levels.entry}
                        </span>
                      </div>
                    )}
                    {!result.levels?.entry && result.entry_zones?.map((e, i) => (
                      <div key={i} className="flex justify-between">
                        <span className="text-gray-400">منطقة دخول {i + 1}</span>
                        <span className="text-white font-mono">{e}</span>
                      </div>
                    ))}
                    {/* SL */}
                    {(result.levels?.stop_loss || result.stop_loss_zone) && (
                      <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                        <span className="text-gray-400">{tx.sl}</span>
                        <span className="text-red-400 font-mono">{result.levels?.stop_loss || result.stop_loss_zone}</span>
                      </div>
                    )}
                    {/* TP */}
                    {result.levels?.tp1 && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-gray-400">{tx.tp1}</span>
                          <span className="text-green-400 font-mono">{result.levels.tp1}</span>
                        </div>
                        {result.levels.tp2 && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">{tx.tp2}</span>
                            <span className="text-green-300 font-mono">{result.levels.tp2}</span>
                          </div>
                        )}
                        {result.levels.tp3 && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">{tx.tp3}</span>
                            <span className="text-green-200 font-mono">{result.levels.tp3}</span>
                          </div>
                        )}
                      </>
                    )}
                    {!result.levels?.tp1 && result.take_profit_zones?.map((tp, i) => (
                      <div key={i} className="flex justify-between">
                        <span className="text-gray-400">هدف {i + 1}</span>
                        <span className="text-green-400 font-mono">{tp}</span>
                      </div>
                    ))}
                    {/* R/R */}
                    {(result.risk_reward || result.levels?.risk_reward) && (
                      <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                        <span className="text-gray-400">Risk/Reward</span>
                        <span className="text-blue-400 font-mono">
                          {((result.levels?.risk_reward ?? result.risk_reward) || 0).toFixed(2)}x
                        </span>
                      </div>
                    )}
                    {/* Lot */}
                    {result.lot_size && (
                      <div className="flex justify-between border-t border-gray-700 pt-2 mt-2">
                        <span className="text-gray-400 flex items-center gap-1">
                          <Calculator size={12} /> {tx.lot}
                        </span>
                        <span className="text-yellow-400 font-mono font-semibold">{result.lot_size}</span>
                      </div>
                    )}
                    {result.account_balance && (
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600">{tx.balanceRisk}</span>
                        <span className="text-gray-500">${result.account_balance} · {result.risk_percent}%</span>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* RIGHT: Analysis */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <h3 className="text-white font-semibold mb-3">{tx.analysis}</h3>
              <div className="space-y-2 text-sm">
                {result.trend && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.trend}</span>
                    <span className="text-white">{result.trend.direction} ({result.trend.strength}%)</span>
                  </div>
                )}
                {result.wyckoff_analysis?.phase && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Wyckoff</span>
                    <span className="text-white">{result.wyckoff_analysis.phase}</span>
                  </div>
                )}
                {result.premium_discount?.current_zone && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.zone}</span>
                    <span className="text-white">{result.premium_discount.current_zone}</span>
                  </div>
                )}
                {result.killzone?.name && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Kill Zone</span>
                    <span className="text-white">{result.killzone.name}</span>
                  </div>
                )}
                {result.liquidity_analysis?.bias?.direction && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">{tx.liquidity}</span>
                    <span className="text-white">{result.liquidity_analysis.bias.direction}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── Sweep Analysis Card ── */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">{tx.sweepSection}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">

              {/* Status badge */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                    (hasBull || hasBear) ? 'bg-green-900/40 text-green-400 border border-green-700'
                    : hasAnySweep ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-700'
                    : 'bg-gray-700 text-gray-500 border border-gray-600'
                  }`}>
                    {(hasBull || hasBear) ? `✅ ${tx.sweepDetected}` : `❌ ${tx.sweepNone}`}
                  </span>
                  <span className={`text-xs font-semibold ${qualityColor[sweepQuality]}`}>
                    {sweepQuality}
                  </span>
                </div>

                {activeSweep && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-400">{tx.sweepType}</span>
                      <span className="text-white">{sweepTypeLabel}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">{tx.sweepLevel}</span>
                      <span className="text-blue-300 font-mono">{fmtPrice(activeSweep.level, symbol)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">{tx.sweepRejection}</span>
                      <span className={activeSweep.rejection_confirmed ? 'text-green-400' : 'text-red-400'}>
                        {activeSweep.rejection_confirmed ? '✅ نعم' : '❌ لا'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">{tx.sweepCandlesAgo}</span>
                      <span className="text-white">{activeSweep.candles_since}</span>
                    </div>
                  </>
                )}

                {/* BSL sweep info (no rejection) */}
                {!hasBull && !hasBear && sweep.bsl_sweep && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">BSL Sweep (بدون رفض)</span>
                    <span className="text-orange-400 font-mono">{fmtPrice(sweep.bsl_sweep.level, symbol)}</span>
                  </div>
                )}
                {!hasBull && !hasBear && sweep.ssl_sweep && !sweep.bsl_sweep && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">SSL Sweep (بدون رفض)</span>
                    <span className="text-orange-400 font-mono">{fmtPrice(sweep.ssl_sweep.level, symbol)}</span>
                  </div>
                )}
              </div>

              {/* Order Blocks */}
              <div className="space-y-2">
                <p className="text-gray-400 font-medium">{tx.orderBlocks}</p>
                {nearestBull ? (
                  <div className="flex justify-between items-center">
                    <span className="flex items-center gap-1 text-gray-400">
                      <TrendingUp size={12} className="text-green-400" /> {tx.obBull}
                    </span>
                    <span className="text-green-400 font-mono text-xs">
                      {fmtPrice(nearestBull.low, symbol)} → {fmtPrice(nearestBull.high, symbol)}
                    </span>
                  </div>
                ) : (
                  <p className="text-gray-600 text-xs">— لا يوجد OB صاعد قريب</p>
                )}
                {nearestBear ? (
                  <div className="flex justify-between items-center">
                    <span className="flex items-center gap-1 text-gray-400">
                      <TrendingDown size={12} className="text-red-400" /> {tx.obBear}
                    </span>
                    <span className="text-red-400 font-mono text-xs">
                      {fmtPrice(nearestBear.low, symbol)} → {fmtPrice(nearestBear.high, symbol)}
                    </span>
                  </div>
                ) : (
                  <p className="text-gray-600 text-xs">— لا يوجد OB هابط قريب</p>
                )}

                {/* OB in zone indicator */}
                {obs.in_bullish_ob && (
                  <p className="text-green-400 text-xs mt-1">⚡ السعر داخل Order Block صاعد</p>
                )}
                {obs.in_bearish_ob && (
                  <p className="text-red-400 text-xs mt-1">⚡ السعر داخل Order Block هابط</p>
                )}
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}
