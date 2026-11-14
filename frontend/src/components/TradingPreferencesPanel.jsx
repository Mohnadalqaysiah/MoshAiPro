import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useMarkets from '../hooks/useMarkets'
import PushToggle from './PushToggle'
import { Save, CheckCircle, AlertCircle, TrendingUp, Bell, Calculator } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// (2026-10-12) الفريمات التي يُصدر عليها المحرك إشارات فعلاً (SCAN_TIMEFRAMES
// بالبوت). 30m و1day كانا ظاهرين ولا تصدر عليهما إشارات — من اختارهما وحدهما
// لن تصله أي إشارة.
// (2026-11-09) 15m موقوف (timeframe_pause.py) فلا يُعرض للاختيار؛ يُعاد إلى القائمة حين يُعاد الفريم (migrate_15m_prefs.py --restore)
const TIMEFRAMES = ['1h', '4h']
const TF_LABEL = { '15m': { ar: '15 دقيقة', en: '15 min' }, '1h': { ar: 'ساعة', en: '1 hour' }, '4h': { ar: '4 ساعات', en: '4 hours' } }
// (2026-11-14) باقات التخصص — المفاتيح من recommended_prefs.PRESETS (نفس أسماء البوت: PRESET_NAMES)
const PRESET_TEXT = {
  metals: { icon: '🥇', ar: 'الذهب والمعادن', en: 'Gold & metals',
            sub_ar: 'عدد تقدر تتابعه كله', sub_en: 'A number you can follow in full' },
  crypto: { icon: '🪙', ar: 'الكريبتو', en: 'Crypto',
            sub_ar: 'لمن يتابع أكثر خلال اليوم', sub_en: 'For those who follow more during the day' },
  all:    { icon: '📊', ar: 'كل الأسواق', en: 'All markets',
            sub_ar: 'للمتفرغ — مخاطرة أصغر لكل صفقة', sub_en: 'Full-time — smaller risk per trade' },
}

// (2026-10-09) مستخرج من Profile.jsx — كان "إدارة رأس المال + حاسبة اللوت"
// و"تفضيلات الإشعارات" (الأزواج/الفريمات/الثقة) موجودين بصفحة /profile
// بس، بعيدين عن تبويب "الحساب" بالداشبورد نفسه. استُخرجا كمكوّن واحد
// يُعاد استخدامه بالاثنين بدل تكرار نفس المنطق (حفظ، حاسبة اللوت،
// تبديل الأزواج) بملفين منفصلين.
export default function TradingPreferencesPanel() {
  const { user, refreshUser } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const { markets } = useMarkets()

  const [trading, setTrading] = useState({ account_balance: user?.account_balance || 10000, risk_percent: user?.risk_percent || 1.5 })
  const [prefs, setPrefs]     = useState({
    notify_watchlist:      user?.notify_watchlist      || [],
    // (2026-10-12) الافتراضي "كل الفريمات" و"كل الإشارات" — كان ['1h'] و65%،
    // فيحفظهما لكل من ضغط حفظ دون أن يختارهما، ثم يُطبَّقان عليه فعلياً
    notify_timeframes:     user?.notify_timeframes?.length ? user.notify_timeframes : ['all'],
    notify_min_confidence: user?.notify_min_confidence ?? 0,
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
      // (2026-10-12) كل الأزواج محددة = "الكل" (قائمة فارغة) لا قائمة بأسمائها —
      // وإلا أي زوج يُضاف للمنصة لاحقاً لا يصل لهذا العميل لأن قائمته ثابتة.
      const allSelected = markets.length > 0 && markets.every(m => prefs.notify_watchlist.includes(m.symbol))
      await axios.put(`${API}/api/v1/auth/preferences`, {
        ...prefs,
        notify_watchlist: allSelected ? [] : prefs.notify_watchlist,
      })
      // بدونه تبقى بيانات الحساب بالذاكرة قديمة، فيرجع الاختيار القديم عند العودة للصفحة
      refreshUser?.().catch(() => {})
      setPrefsMsg({ type: 'ok', text: isAr ? 'تم حفظ إعدادات الإشعارات' : 'Notification settings saved' })
    } catch (err) {
      setPrefsMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
    } finally { setLoading('') }
  }

  // (2026-11-12) "الإعداد الموصى به" ← (2026-11-14) باقات التخصص — backend/app/services/recommended_prefs.py (DECISIONS.md 14/11).
  // الأرقام حية من السيرفر (آخر 30 يوماً) لا مكتوبة هنا. الانحراف من المحفوظ (user) لا من المسودة: عن ما يصل العميل الآن.
  const savedTfs  = (user?.notify_timeframes || []).filter(t => t !== 'all')
  const savedConf = user?.notify_min_confidence || 0
  const savedOff  = user?.notifications_enabled === false
  const deviates  = savedConf > 0 || savedTfs.length > 0 || savedOff
  const [presets, setPresets] = useState(null)
  const [recMsg, setRecMsg] = useState(null)
  const loadPresets = () => axios.get(`${API}/api/v1/auth/preferences/presets`).then(r => setPresets(r.data)).catch(() => {})
  useEffect(() => { loadPresets() }, [])
  const applyPreset = async (key) => {
    setLoading('rec:' + key); setRecMsg(null)
    try {
      const r = await axios.post(`${API}/api/v1/auth/preferences/recommended`, null, { params: { preset: key } })
      const syms = presets?.presets?.find(p => p.key === key)?.symbols || []
      setPrefs(p => ({ ...p, notify_watchlist: key === 'all' || !syms.length ? markets.map(m => m.symbol) : syms,
                       notify_timeframes: ['all'], notify_min_confidence: 0, notifications_enabled: true }))
      await refreshUser?.().catch(() => {})
      loadPresets()
      setRecMsg({ type: 'ok', text: isAr ? `تم — باقتك الآن: ${PRESET_TEXT[r.data.preset]?.ar}` : `Done — your package: ${PRESET_TEXT[r.data.preset]?.en}` })
    } catch (err) {
      setRecMsg({ type: 'err', text: err.response?.data?.detail || 'Error' })
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

  // (2026-10-12) بلاغ: لا يمكن اختيار فريم. الأزرار كانت معطّلة ما دام "كل الفريمات"
  // مفعّلاً، والضغط عليه لا يلغيه — وصار هو الافتراضي فعلق العميل. الآن: ضغط فريم
  // من وضع "الكل" يبدأ اختياراً جديداً به، وإلغاء آخر فريم يرجع لـ"الكل".
  const toggleTimeframe = (tf) => {
    if (tf === 'all') {
      setPrefs(p => ({ ...p, notify_timeframes: ['all'] }))
      return
    }
    setPrefs(p => {
      const current = p.notify_timeframes.filter(t => t !== 'all' && TIMEFRAMES.includes(t))
      const next = current.includes(tf) ? current.filter(t => t !== tf) : [...current, tf]
      return { ...p, notify_timeframes: next.length === 0 ? ['all'] : next }
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
      {/* (2026-10-31) جرس الإشعارات بهيدر الجوال فقط، فمفتاح إشعارات التطبيق هنا أيضاً لمن يستخدم الكمبيوتر */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <PushToggle />
      </div>
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Bell size={16} className="text-blue-400" /> {isAr ? 'إعدادات إشعارات التيليجرام' : 'Telegram Notification Preferences'}
        </h2>
        {/* (2026-11-12) الإعداد الموصى به ← (2026-11-14) باقات التخصص: نصيحة مرتّبة + 3 باقات بأرقام حية (recommended_prefs.py) */}
        <div className="mb-5 rounded-xl border border-emerald-700/40 bg-emerald-900/10 p-4">
          <div className="text-sm font-semibold text-white">
            ✨ {isAr ? 'اختر باقتك — من نتائج منصتنا الفعلية' : 'Pick your package — from our actual results'}
          </div>
          <p className="mt-1 text-xs text-gray-400 leading-relaxed">
            {(() => {
              const allPerDay = presets?.presets?.find(p => p.key === 'all')?.stats?.per_day
              const many = allPerDay ? (isAr ? `نحو ${Math.round(allPerDay)} إشارة يومياً` : `about ${Math.round(allPerDay)} signals a day`)
                                     : (isAr ? 'إشارات كثيرة يومياً' : 'many signals a day')
              return isAr
                ? `المنصة تُصدر ${many} على كل الأسواق، ولا أحد يتابعها كلها. اختر باقة تقدر تأخذ كل إشاراتها.`
                : `The platform issues ${many} across all markets, and nobody follows them all. Pick a package you can take in full.`
            })()}
          </p>

          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            {(presets?.presets || []).map(p => {
              const t = PRESET_TEXT[p.key]
              if (!t) return null
              const s = p.stats
              const isCurrent = presets?.current === p.key
              const isRec = presets?.recommended === p.key
              return (
                <div key={p.key}
                  className={`rounded-lg border p-3 flex flex-col gap-2 ${isRec ? 'border-emerald-500/60 bg-emerald-900/20' : 'border-gray-700 bg-gray-900/40'}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-white">{t.icon} {isAr ? t.ar : t.en}</span>
                    {isRec && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-600 text-white whitespace-nowrap">
                        {isAr ? 'الموصى به' : 'Recommended'}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-gray-400">{isAr ? t.sub_ar : t.sub_en}</div>
                  {s ? (
                    <div className="text-xs text-gray-300 leading-relaxed">
                      <div>{isAr ? `نحو ${s.per_day} إشارة يومياً` : `About ${s.per_day} signals a day`}</div>
                      <div>{isAr ? `الرابحة: ${s.win}% من الصفقات` : `Winners: ${s.win}% of trades`}</div>
                      <div>{isAr ? `أيام انتهت رابحة: ${s.pos_days}%` : `Days that ended positive: ${s.pos_days}%`}</div>
                    </div>
                  ) : (
                    <div className="text-xs text-gray-500">{isAr ? 'لا أرقام كافية بعد' : 'Not enough data yet'}</div>
                  )}
                  {isCurrent && !deviates ? (
                    <span className="mt-auto text-xs text-center px-2.5 py-1.5 rounded-lg bg-emerald-900/40 text-emerald-300">
                      ✓ {isAr ? 'باقتك الحالية' : 'Your current package'}
                    </span>
                  ) : (
                    <button type="button" onClick={() => applyPreset(p.key)} disabled={loading.startsWith('rec')}
                      className={`mt-auto text-xs px-3 py-1.5 rounded-lg font-medium transition disabled:opacity-50 ${
                        isRec ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-100'}`}>
                      {loading === 'rec:' + p.key ? (isAr ? 'جاري التطبيق...' : 'Applying...') : (isAr ? 'اختر هذه الباقة' : 'Choose this package')}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
          {presets && (
            <p className="mt-2 text-[11px] text-gray-500">
              {isAr
                ? `الأرقام لآخر ${presets.window_days} يوماً لمن أخذ كل إشارات الباقة، قبل السبريد، وتتحدّث تلقائياً.`
                : `Figures cover the last ${presets.window_days} days for someone taking every signal in the package, before spread, updated automatically.`}
              {presets.current === 'custom' && (isAr ? ' إعدادك الحالي تخصيص خاص.' : ' Your current setup is custom.')}
            </p>
          )}

          <ol className="mt-3 space-y-2 text-xs text-gray-300 leading-relaxed list-decimal ps-5">
            <li>
              <b className="text-white">{isAr ? 'خذ كل إشارات باقتك، لا بعضها.' : 'Take every signal in your package, not some.'}</b>{' '}
              {isAr
                ? 'الأرقام أعلاه لمن أخذ كل إشارات الباقة. انتقاء بعض إشارات كل الأسواق نتيجته شيء آخر.'
                : 'The figures above are for someone taking every signal. Picking a few signals from all markets is a different result.'}
            </li>
            <li>
              <b className="text-white">{isAr ? 'لا تضع حداً أدنى للثقة، ولا تحصر الفريم.' : 'Do not set a minimum confidence or limit the timeframe.'}</b>{' '}
              {isAr
                ? 'نسبة الثقة لا ترتّب الربح عندنا (قياس 12/11: إشارات 60-64% كانت أفضل من 65-69%)، وحد 65% كان سيحجب أكثر من نصف المجموع.'
                : 'Confidence does not rank profit here (Nov 12 study: 60-64% signals did better than 65-69%), and a 65% minimum would have hidden over half the total.'}
            </li>
            <li>
              <b className="text-white">{isAr ? 'ما يثبت ضعفه نوقفه نحن من المصدر.' : 'We pause what proves weak at the source.'}</b>{' '}
              {isAr
                ? 'لا تحتاج أن تفلتر بنفسك — ما يصلك اجتاز فحوصنا ومراقبتنا الأسبوعية.'
                : 'No need to filter yourself — what reaches you passed our checks and weekly monitoring.'}
            </li>
            <li>
              <b className="text-white">{isAr ? 'مخاطرة ثابتة لكل صفقة، بحجم يناسب باقتك.' : 'A fixed risk per trade, sized to your package.'}</b>{' '}
              {isAr
                ? 'نحو 1% مع الذهب والمعادن أو الكريبتو، و0.25-0.5% فقط إن أخذت كل الأسواق: إشارات اليوم الواحد قد تصل 20، وأسوأ يوم مرّ علينا خسر نحو 10 أضعاف مخاطرة الصفقة. استخدم الحاسبة أعلاه.'
                : 'About 1% with gold & metals or crypto, and only 0.25-0.5% if you take all markets: a single day can bring 20 signals, and our worst day lost about 10× the per-trade risk. Use the calculator above.'}
            </li>
          </ol>
          {deviates && (
            <div className="mt-3 rounded-lg border border-amber-700/40 bg-amber-900/10 px-3 py-2 text-xs text-amber-300 leading-relaxed">
              {isAr ? 'إعدادك الحالي يحجب عنك جزءاً من إشارات باقتك: ' : 'Your current setup hides part of your package signals: '}
              {[
                savedOff && (isAr ? 'الإشعارات متوقفة' : 'notifications are off'),
                savedConf > 0 && (isAr ? `حد ثقة ${savedConf}%` : `${savedConf}% minimum confidence`),
                savedTfs.length > 0 && (isAr ? `فريم ${savedTfs.map(t => TF_LABEL[t]?.ar || t).join(' و')} فقط`
                                              : `${savedTfs.map(t => TF_LABEL[t]?.en || t).join(' & ')} only`),
              ].filter(Boolean).join(isAr ? '، ' : ', ')}.
              {isAr ? ' اختيار أي باقة يزيل ذلك.' : ' Choosing any package clears this.'}
            </div>
          )}
          <p className="mt-2 text-[11px] text-gray-500">
            {isAr ? 'نتائج سابقة لا تضمن المستقبل. القرار لك ويمكنك التخصيص بالأسفل بأي وقت.'
                  : 'Past results do not guarantee the future. Your choice — customize below any time.'}
          </p>
          <Msg msg={recMsg} />
        </div>

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
                  : prefs.notify_timeframes.map(t => TF_LABEL[t] ? TF_LABEL[t][isAr ? 'ar' : 'en'] : t).join(' · ')})
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
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    !prefs.notify_timeframes.includes('all') && prefs.notify_timeframes.includes(tf)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}>
                  {TF_LABEL[tf] ? TF_LABEL[tf][isAr ? 'ar' : 'en'] : tf}
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

          {/* (2026-10-12) ملخص واضح لما سيصل العميل فعلاً بعد الحفظ */}
          <div className="bg-blue-900/20 border border-blue-800/40 rounded-lg p-3 text-xs text-gray-300 leading-relaxed">
            {!prefs.notifications_enabled ? (
              isAr ? '🔕 الإشعارات متوقفة — لن تصلك إشارات على تيليجرام.' : '🔕 Notifications are off — no Telegram signals.'
            ) : (
              <>
                <b className="text-white">{isAr ? 'ما سيصلك على تيليجرام:' : 'What you will receive on Telegram:'}</b>{' '}
                {isAr ? 'إشارات ' : 'Signals for '}
                <b>{prefs.notify_watchlist.length === 0 || prefs.notify_watchlist.length === markets.length
                  ? (isAr ? 'كل الأزواج' : 'all markets')
                  : (isAr ? `${prefs.notify_watchlist.length} زوجاً` : `${prefs.notify_watchlist.length} markets`)}</b>
                {isAr ? '، على ' : ', on '}
                <b>{prefs.notify_timeframes.includes('all')
                  ? (isAr ? 'كل الفريمات' : 'all timeframes')
                  : prefs.notify_timeframes.map(t => TF_LABEL[t] ? TF_LABEL[t][isAr ? 'ar' : 'en'] : t).join(isAr ? ' و' : ' & ')}</b>
                {isAr ? '، ' : ', '}
                <b>{prefs.notify_min_confidence === 0
                  ? (isAr ? 'بأي نسبة ثقة' : 'any confidence')
                  : (isAr ? `بثقة ${prefs.notify_min_confidence}% أو أكثر` : `${prefs.notify_min_confidence}%+ confidence`)}</b>.
                <div className="text-gray-400 mt-1">
                  {isAr
                    ? 'عدم اختيار أي زوج = كل الأزواج. تقدر تغيّر هذا بأي وقت، أو توقف إشارات زوج معيّن مباشرة من زر تحت الإشارة في تيليجرام.'
                    : 'No market selected = all markets. Change this any time, or mute a market straight from the button under a Telegram signal.'}
                </div>
              </>
            )}
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
