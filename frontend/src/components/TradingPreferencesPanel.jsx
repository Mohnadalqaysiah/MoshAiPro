import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useMarkets from '../hooks/useMarkets'
import { Save, CheckCircle, AlertCircle, TrendingUp, Bell, Calculator } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TIMEFRAMES = ['15m', '30m', '1h', '4h', '1day']

// (2026-10-09) مستخرج من Profile.jsx — كان "إدارة رأس المال + حاسبة اللوت"
// و"تفضيلات الإشعارات" (الأزواج/الفريمات/الثقة) موجودين بصفحة /profile
// بس، بعيدين عن تبويب "الحساب" بالداشبورد نفسه. استُخرجا كمكوّن واحد
// يُعاد استخدامه بالاثنين بدل تكرار نفس المنطق (حفظ، حاسبة اللوت،
// تبديل الأزواج) بملفين منفصلين.
export default function TradingPreferencesPanel() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const { markets } = useMarkets()

  const [trading, setTrading] = useState({ account_balance: user?.account_balance || 10000, risk_percent: user?.risk_percent || 1.5 })
  const [prefs, setPrefs]     = useState({
    notify_watchlist:      user?.notify_watchlist      || [],
    notify_timeframes:     user?.notify_timeframes     || (user?.notify_timeframe ? [user.notify_timeframe] : ['1h']),
    notify_min_confidence: user?.notify_min_confidence ?? 65,
    notifications_enabled: user?.notifications_enabled !== false,
    language:              user?.language              || 'ar',
  })

  const [tradingMsg, setTradingMsg] = useState(null)
  const [prefsMsg,   setPrefsMsg]   = useState(null)
  const [loading,    setLoading]    = useState('')

  // نفس ديفلت "كل الأسواق مفعّلة افتراضياً" الموجود بـProfile.jsx أصلاً
  const [defaultedWatchlist, setDefaultedWatchlist] = useState(false)
  useEffect(() => {
    if (defaultedWatchlist || !markets.length) return
    if ((user?.notify_watchlist || []).length === 0) {
      setPrefs(p => ({ ...p, notify_watchlist: markets.map(m => m.symbol) }))
    }
    setDefaultedWatchlist(true)
  }, [markets, user, defaultedWatchlist])

  // فتح الصفحة بـ#watchlist يمرّر لقسم الأزواج ويومضه لحظة (نفس سلوك /profile)
  const [flashWatchlist, setFlashWatchlist] = useState(false)
  useEffect(() => {
    if (window.location.hash !== '#watchlist' || !markets.length) return
    const el = document.getElementById('watchlist')
    if (!el) return
    const t = setTimeout(() => {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      setFlashWatchlist(true)
      setTimeout(() => setFlashWatchlist(false), 2200)
    }, 250)
    return () => clearTimeout(t)
  }, [markets])

  // حاسبة اللوت
  const [lotPreview, setLotPreview] = useState(null)
  const [lotEntry,   setLotEntry]   = useState('')
  const [lotSl,      setLotSl]      = useState('')
  const [lotSymbol,  setLotSymbol]  = useState('XAUUSD')

  const Msg = ({ msg }) => msg ? (
    <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mt-3 ${
      msg.type === 'ok' ? 'bg-green-900/30 border border-green-700/40 text-green-400' : 'bg-red-900/30 border border-red-700/40 text-red-400'
    }`}>
      {msg.type === 'ok' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
      {msg.text}
    </div>
  ) : null

  const saveTradingSettings = async e => {
    e.preventDefault(); setLoading('trading'); setTradingMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/trading-settings`, trading)
      setTradingMsg({ type: 'ok', text: isAr ? 'تم حفظ إعدادات التداول' : 'Trading settings saved' })
    } catch (err) {
      setTradingMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
    } finally { setLoading('') }
  }

  const savePrefs = async e => {
    e.preventDefault(); setLoading('prefs'); setPrefsMsg(null)
    try {
      await axios.put(`${API}/api/v1/auth/preferences`, prefs)
      setPrefsMsg({ type: 'ok', text: isAr ? 'تم حفظ إعدادات الإشعارات' : 'Notification settings saved' })
    } catch (err) {
      setPrefsMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
    } finally { setLoading('') }
  }

  const toggleWatchlist = (m) => {
    setPrefs(p => ({
      ...p,
      notify_watchlist: p.notify_watchlist.includes(m)
        ? p.notify_watchlist.filter(x => x !== m)
        : [...p.notify_watchlist, m],
    }))
  }
  const selectAllWatchlist   = () => setPrefs(p => ({ ...p, notify_watchlist: markets.map(m => m.symbol) }))
  const deselectAllWatchlist = () => setPrefs(p => ({ ...p, notify_watchlist: [] }))

  const toggleTimeframe = (tf) => {
    if (tf === 'all') {
      setPrefs(p => ({ ...p, notify_timeframes: ['all'] }))
      return
    }
    setPrefs(p => {
      const current = p.notify_timeframes.filter(t => t !== 'all')
      const next = current.includes(tf) ? current.filter(t => t !== tf) : [...current, tf]
      return { ...p, notify_timeframes: next.length === 0 ? [tf] : next }
    })
  }

  const calcLot = () => {
    const entry = parseFloat(lotEntry)
    const sl    = parseFloat(lotSl)
    const bal   = trading.account_balance
    const risk  = trading.risk_percent
    if (!entry || !sl || entry === sl) { setLotPreview(null); return }
    const riskAmt = bal * (risk / 100)
    const pipDist = Math.abs(entry - sl)
    const pipVal  = lotSymbol === 'XAUUSD' ? 10 : lotSymbol === 'BTCUSD' ? 1 : lotSymbol.includes('JPY') || lotSymbol.includes('CHF') ? 8 : 10
    const lot = riskAmt / (pipDist * pipVal)
    setLotPreview(Math.max(0.01, Math.min(lot, 100)).toFixed(2))
  }

  return (
    <>
      {/* ── Trading Settings + Lot Calculator ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-400" /> {isAr ? 'إدارة رأس المال' : 'Capital Management'}
        </h2>
        <form onSubmit={saveTradingSettings} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'رأس المال ($)' : 'Account Balance ($)'}</label>
              <input type="number" min="100" step="100" value={trading.account_balance}
                onChange={e => setTrading(p => ({...p, account_balance: Number(e.target.value)}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                dir="ltr" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'نسبة المخاطرة (%)' : 'Risk % per Trade'}</label>
              <input type="number" min="0.1" max="5" step="0.1" value={trading.risk_percent}
                onChange={e => setTrading(p => ({...p, risk_percent: Number(e.target.value)}))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                dir="ltr" />
            </div>
          </div>
          <div className="bg-blue-900/10 border border-blue-800/30 rounded-lg p-3 text-xs text-gray-400">
            {isAr
              ? `مع ${trading.risk_percent}% مخاطرة على $${trading.account_balance}، الحد الأقصى للخسارة في الصفقة: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)}`
              : `With ${trading.risk_percent}% risk on $${trading.account_balance}, max loss per trade: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)}`}
          </div>
          <button type="submit" disabled={loading === 'trading'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Save size={14} /> {loading === 'trading' ? (isAr ? 'جاري الحفظ...' : 'Saving...') : (isAr ? 'حفظ الإعدادات' : 'Save Settings')}
          </button>
          <Msg msg={tradingMsg} />
        </form>

        {/* Lot Size Calculator */}
        <div className="mt-6 border-t border-gray-700 pt-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Calculator size={15} className="text-yellow-400" /> {isAr ? 'حاسبة اللوت' : 'Lot Size Calculator'}
          </h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'الزوج' : 'Symbol'}</label>
              <select value={lotSymbol} onChange={e => setLotSymbol(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-2 py-2 text-xs">
                {markets.map(m => <option key={m.symbol} value={m.symbol}>{m.symbol}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'سعر الدخول' : 'Entry'}</label>
              <input type="number" step="any" value={lotEntry}
                onChange={e => setLotEntry(e.target.value)} placeholder="e.g. 2050"
                className="w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-2 py-2 text-xs" dir="ltr" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">{isAr ? 'وقف الخسارة' : 'Stop Loss'}</label>
              <input type="number" step="any" value={lotSl}
                onChange={e => setLotSl(e.target.value)} placeholder="e.g. 2045"
                className="w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-2 py-2 text-xs" dir="ltr" />
            </div>
          </div>
          <button onClick={calcLot}
            className="mt-3 flex items-center gap-2 px-4 py-2 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-400 rounded-lg text-xs font-medium">
            <Calculator size={13} /> {isAr ? 'احسب اللوت' : 'Calculate Lot'}
          </button>
          {lotPreview && (
            <div className="mt-3 bg-yellow-900/20 border border-yellow-700/40 rounded-lg p-3 text-sm">
              <span className="text-gray-400">{isAr ? 'حجم اللوت المناسب:' : 'Recommended Lot Size:'} </span>
              <span className="text-yellow-400 font-bold text-lg">{lotPreview}</span>
              <span className="text-gray-500 text-xs mr-2">{isAr ? 'لوت' : 'lots'}</span>
              <div className="text-xs text-gray-500 mt-1">
                {isAr
                  ? `(خسارة محتملة: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)} = ${trading.risk_percent}% من رأس المال)`
                  : `(Max loss: $${(trading.account_balance * trading.risk_percent / 100).toFixed(2)} = ${trading.risk_percent}% of balance)`}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Notification Preferences ── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Bell size={16} className="text-blue-400" /> {isAr ? 'إعدادات إشعارات التيليجرام' : 'Telegram Notification Preferences'}
        </h2>
        <form onSubmit={savePrefs} className="space-y-5">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">{isAr ? 'تفعيل الإشعارات' : 'Enable Notifications'}</span>
            <button type="button" onClick={() => setPrefs(p => ({...p, notifications_enabled: !p.notifications_enabled}))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${prefs.notifications_enabled ? 'bg-blue-600' : 'bg-gray-600'}`}>
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${prefs.notifications_enabled ? (isAr ? '-translate-x-6' : 'translate-x-6') : (isAr ? '-translate-x-1' : 'translate-x-1')}`} />
            </button>
          </div>

          <div id="watchlist"
               className={`scroll-mt-24 rounded-xl transition-all duration-500 ${
                 flashWatchlist ? 'ring-2 ring-blue-500 bg-blue-500/5 p-3 -m-3' : ''
               }`}>
            <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
              <label className="block text-sm text-gray-400">
                {isAr ? 'الأزواج للمراقبة' : 'Markets to Watch'}
                <span className="text-gray-400 mr-1 text-xs">({prefs.notify_watchlist.length} {isAr ? 'مختار' : 'selected'})</span>
              </label>
              <div className="flex items-center gap-2">
                <button type="button" onClick={selectAllWatchlist}
                  className="text-xs px-2.5 py-1 rounded-lg border border-blue-700 text-blue-400 hover:bg-blue-900/30 transition-colors">
                  {isAr ? 'تحديد الكل' : 'Select All'}
                </button>
                <button type="button" onClick={deselectAllWatchlist}
                  className="text-xs px-2.5 py-1 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-700/40 transition-colors">
                  {isAr ? 'إلغاء التحديد' : 'Clear'}
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {markets.map(m => (
                <button key={m.symbol} type="button" onClick={() => toggleWatchlist(m.symbol)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    prefs.notify_watchlist.includes(m.symbol)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}>
                  {prefs.notify_watchlist.includes(m.symbol) ? '✓ ' : ''}{m.symbol}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">
              {isAr ? 'الفريمات الزمنية' : 'Timeframes'}
              <span className="text-gray-400 text-xs mr-1">
                ({prefs.notify_timeframes.includes('all')
                  ? (isAr ? 'الكل' : 'All')
                  : prefs.notify_timeframes.join(' · ')})
              </span>
            </label>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => toggleTimeframe('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  prefs.notify_timeframes.includes('all')
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}>
                {isAr ? 'كل الفريمات' : 'All TFs'}
              </button>
              {TIMEFRAMES.map(tf => (
                <button key={tf} type="button" onClick={() => toggleTimeframe(tf)}
                  disabled={prefs.notify_timeframes.includes('all')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-40 ${
                    !prefs.notify_timeframes.includes('all') && prefs.notify_timeframes.includes(tf)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}>
                  {tf}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">
              {isAr ? 'الحد الأدنى للثقة' : 'Min Confidence'}
              <span className="text-gray-400 text-xs mr-1">
                ({prefs.notify_min_confidence === 0
                  ? (isAr ? 'أي نسبة' : 'Any')
                  : `${prefs.notify_min_confidence}%+`})
              </span>
            </label>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => setPrefs(p => ({...p, notify_min_confidence: 0}))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  prefs.notify_min_confidence === 0
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}>
                {isAr ? 'كل النسب' : 'Any %'}
              </button>
              {[50, 55, 60, 65, 70, 75, 80].map(v => (
                <button key={v} type="button" onClick={() => setPrefs(p => ({...p, notify_min_confidence: v}))}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    prefs.notify_min_confidence === v
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}>
                  {v}%
                </button>
              ))}
            </div>
          </div>

          <div className="bg-gray-700/30 rounded-lg p-3 text-xs text-gray-400">
            {isAr
              ? 'سيراقب البوت الأزواج المختارة كل 15 دقيقة ويرسل تنبيهاً عند وجود إشارة BUY/SELL بنسبة ثقة أعلى من الحد المحدد.'
              : 'The bot will monitor selected pairs every 15 minutes and send an alert when a BUY/SELL signal appears above the minimum confidence threshold.'}
          </div>

          <button type="submit" disabled={loading === 'prefs'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition">
            <Save size={14} /> {loading === 'prefs' ? (isAr ? 'جاري الحفظ...' : 'Saving...') : (isAr ? 'حفظ التفضيلات' : 'Save Preferences')}
          </button>
          <Msg msg={prefsMsg} />
        </form>
      </div>
    </>
  )
}
