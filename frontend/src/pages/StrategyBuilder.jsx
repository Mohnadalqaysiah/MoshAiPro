import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  Search, Plus, X, ChevronDown, ChevronRight, Copy, Trash2, Power,
  Edit3, Eye, Play, Send, Bot, Link2, Check, AlertTriangle, Sparkles,
  Activity, Layers, Target, CandlestickChart, Percent, BarChart3, Gauge,
  Waves, Clock, GitBranch, ShieldCheck, RefreshCw, Undo2, Redo2, Save,
  Radio, TrendingUp, ArrowLeft, Loader2, ListChecks, FileText, Zap,
  SlidersHorizontal, MonitorDot, FolderOpen, Hammer, Ban,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// أنواع الشروط المربوطة فعليًا بمحرك التحليل الحقيقي (ai_engine_v5) —
// نفس القائمة الموجودة بـ backend/app/services/strategy_engine.py::SUPPORTED_CONDITION_TYPES
const IMPLEMENTED_TYPES = new Set([
  "bos", "choch", "ob", "fvg", "liquidity", "eqh", "eql", "premium", "killzone",
  "london", "newyork", "asian", "killzones",
  "rsi", "macd", "ema", "stoch", "atrv",
]);

/* =========================================================================
   DESIGN TOKENS — Qaffel / Premium Fintech Trading Terminal
========================================================================= */
const C = {
  bg: "#07080B",
  bgGrad: "linear-gradient(180deg,#0A0C10 0%,#07080B 100%)",
  surface: "#0F1116",
  surfaceHi: "#151822",
  surfaceGlass: "rgba(21,24,34,0.6)",
  border: "#1E222D",
  borderSoft: "#171A23",
  gold: "#C9A667",
  goldBright: "#E4C589",
  goldSoft: "rgba(201,166,103,0.13)",
  teal: "#2FD8C4",
  tealSoft: "rgba(47,216,196,0.13)",
  red: "#E5555C",
  redSoft: "rgba(229,85,92,0.13)",
  purple: "#8B7CF6",
  purpleSoft: "rgba(139,124,246,0.13)",
  blue: "#6FA0FF",
  blueSoft: "rgba(111,160,255,0.13)",
  text: "#EDEEF3",
  sub: "#8B92A5",
  muted: "#545B6B",
};
const FD = "'Sora', system-ui, sans-serif";
const FB = "'Inter', system-ui, sans-serif";
const FM = "'JetBrains Mono', ui-monospace, monospace";

let _id = 1;
const nextId = () => `n${_id++}`;

/* =========================================================================
   MOCK MARKET DATA
========================================================================= */
const SYMBOL_POOL = [
  { s: "XAU/USD", base: 2412.4, dp: 2 },
  { s: "EUR/USD", base: 1.0842, dp: 4 },
  { s: "GBP/USD", base: 1.2715, dp: 4 },
  { s: "BTC/USD", base: 64230, dp: 0 },
  { s: "ETH/USD", base: 3140, dp: 1 },
  { s: "NAS100", base: 18620, dp: 1 },
  { s: "US30", base: 39840, dp: 0 },
  { s: "USOIL", base: 78.4, dp: 2 },
];
const fmtPrice = (sym, val) => {
  const meta = SYMBOL_POOL.find((x) => x.s === sym) || { dp: 2 };
  return Number(val).toFixed(meta.dp);
};
const basePrice = (sym) => (SYMBOL_POOL.find((x) => x.s === sym) || { base: 100 }).base;

const TIMEFRAMES = ["1m", "5m", "15m", "1H", "4H", "1D"];
const TF_MODES = ["نفس الفريم", "فريم أعلى", "فريم مخصص"];

/* =========================================================================
   CONDITION CATALOG — 11 schools
========================================================================= */
const CAT = [
  { id: "indicators", label: "مؤشرات فنية", en: "Technical Indicators", icon: Activity, color: C.teal, w: 10,
    items: [
      ["rsi", "RSI", "مؤشر القوة النسبية — تشبع شرائي/بيعي"],
      ["macd", "MACD", "تقاطع خط الإشارة مع MACD"],
      ["ema", "EMA", "المتوسط المتحرك الأسي"],
      ["sma", "SMA", "المتوسط المتحرك البسيط"],
      ["stoch", "Stochastic", "مذبذب الزخم العشوائي"],
      ["bbands", "Bollinger Bands", "ملامسة/اختراق نطاقات بولنجر"],
      ["atr", "ATR", "متوسط المدى الحقيقي"],
      ["adx", "ADX", "قوة الاتجاه"],
      ["volume", "Volume", "قراءة الحجم اللحظية"],
      ["vwap", "VWAP", "متوسط السعر الموزون بالحجم"],
    ]},
  { id: "smc", label: "ICT / SMC", en: "ICT / SMC", icon: Layers, color: C.gold, w: 18,
    items: [
      ["bos", "BOS", "Break of Structure — كسر هيكل"],
      ["choch", "CHoCH", "Change of Character — تغيّر طابع"],
      ["mss", "MSS", "Market Structure Shift"],
      ["ob", "Order Block", "منطقة أوامر مؤسساتية"],
      ["breaker", "Breaker Block", "كتلة كاسرة بعد فشل OB"],
      ["fvg", "FVG", "Fair Value Gap — فجوة سعرية"],
      ["ifvg", "IFVG", "Inversion FVG"],
      ["liquidity", "Liquidity Sweep", "سحب سيولة قبل الانعكاس"],
      ["eqh", "Equal Highs", "قمم متساوية"],
      ["eql", "Equal Lows", "قيعان متساوية"],
      ["premium", "Premium/Discount", "منطقة علاوة أو خصم"],
      ["dealing", "Dealing Range", "نطاق التداول المؤسساتي"],
      ["killzone", "Kill Zone", "نافذة زمنية عالية النشاط"],
    ]},
  { id: "price", label: "سعر ومستويات", en: "Price Action", icon: Target, color: C.blue, w: 14,
    items: [
      ["support", "Support", "ارتداد من دعم"],
      ["resistance", "Resistance", "رفض من مقاومة"],
      ["breakout", "Breakout", "اختراق مستوى"],
      ["retest", "Retest", "إعادة اختبار مستوى مخترق"],
      ["trendbreak", "Trendline Break", "كسر خط اتجاه"],
      ["hh", "Higher High", "قمة أعلى"],
      ["hl", "Higher Low", "قاع أعلى"],
      ["lh", "Lower High", "قمة أدنى"],
      ["ll", "Lower Low", "قاع أدنى"],
    ]},
  { id: "candles", label: "أنماط الشموع", en: "Candlestick", icon: CandlestickChart, color: "#E08FD8", w: 8,
    items: [
      ["bull_engulf", "Bullish Engulfing", "ابتلاعية صعودية"],
      ["bear_engulf", "Bearish Engulfing", "ابتلاعية هبوطية"],
      ["pinbar", "Pin Bar", "شمعة رفض بذيل طويل"],
      ["hammer", "Hammer", "مطرقة انعكاسية"],
      ["shootingstar", "Shooting Star", "نجمة هابطة"],
      ["doji", "Doji", "تردد السوق"],
      ["morningstar", "Morning Star", "نجمة الصباح"],
      ["eveningstar", "Evening Star", "نجمة المساء"],
      ["marubozu", "Marubozu", "شمعة بلا ظلال"],
    ]},
  { id: "fibonacci", label: "فيبوناتشي", en: "Fibonacci", icon: Percent, color: "#F0B86E", w: 9,
    items: [
      ["fib236", "0.236", "مستوى تصحيح ضحل"],
      ["fib382", "0.382", "تصحيح ثانوي"],
      ["fib5", "0.5", "منتصف الحركة"],
      ["fib618", "0.618", "النسبة الذهبية"],
      ["fib705", "0.705", "منطقة OTE"],
      ["fib786", "0.786", "تصحيح عميق"],
      ["fibext", "Extension", "امتداد فيبوناتشي للأهداف"],
    ]},
  { id: "volume", label: "الحجم وتدفق الأوامر", en: "Volume / Order Flow", icon: BarChart3, color: "#6FE0A0", w: 8,
    items: [
      ["volspike", "Volume Spike", "ارتفاع حجم مفاجئ"],
      ["volavg", "Volume Above Average", "حجم أعلى من المتوسط"],
      ["voldelta", "Volume Delta", "فرق حجم الشراء والبيع"],
      ["buypressure", "Buying Pressure", "ضغط شرائي واضح"],
      ["sellpressure", "Selling Pressure", "ضغط بيعي واضح"],
    ]},
  { id: "momentum", label: "الزخم", en: "Momentum", icon: Gauge, color: "#7CC7FF", w: 9,
    items: [
      ["rsidiv", "RSI Divergence", "دايفرجنس على RSI"],
      ["macddiv", "MACD Divergence", "دايفرجنس على MACD"],
      ["mominc", "Momentum Increase", "تسارع الزخم"],
      ["momdec", "Momentum Decrease", "تباطؤ الزخم"],
    ]},
  { id: "volatility", label: "التذبذب", en: "Volatility", icon: Waves, color: "#9AA7FF", w: 7,
    items: [
      ["atrv", "ATR", "قراءة التذبذب الحالية"],
      ["highvol", "High Volatility", "تذبذب مرتفع"],
      ["lowvol", "Low Volatility", "تذبذب منخفض"],
      ["volexp", "Volatility Expansion", "توسع التذبذب"],
      ["volcomp", "Volatility Compression", "انضغاط التذبذب"],
    ]},
  { id: "sessions", label: "الجلسات والوقت", en: "Sessions & Time", icon: Clock, color: "#F0C24E", w: 6,
    items: [
      ["london", "London Session", "جلسة لندن"],
      ["newyork", "New York Session", "جلسة نيويورك"],
      ["asian", "Asian Session", "الجلسة الآسيوية"],
      ["killzones", "Kill Zones", "نوافذ التقلب العالي"],
      ["specificday", "Specific Day", "يوم محدد بالأسبوع"],
      ["specifictime", "Specific Time", "وقت محدد باليوم"],
      ["marketopen", "Market Open", "افتتاح السوق"],
      ["sesshl", "Session High/Low", "أعلى/أدنى الجلسة"],
    ]},
  { id: "structure", label: "هيكل السوق", en: "Market Structure", icon: GitBranch, color: C.purple, w: 15,
    items: [
      ["trend", "Trend", "اتجاه صاعد/هابط"],
      ["range", "Range", "سوق عرضي"],
      ["structhh", "Higher High", "استمرار صعودي"],
      ["structll", "Lower Low", "استمرار هبوطي"],
      ["structbreak", "Structure Break", "كسر هيكلي عام"],
      ["consolidation", "Consolidation", "تجميع"],
      ["expansion", "Expansion", "توسع حركي"],
    ]},
  { id: "risk", label: "إدارة المخاطر", en: "Risk / Trade Mgmt", icon: ShieldCheck, color: "#FF9F6E", w: 5,
    items: [
      ["minrr", "Minimum RR", "أقل نسبة مخاطرة/عائد"],
      ["maxrr", "Maximum RR", "أعلى نسبة مخاطرة/عائد"],
      ["sldist", "Stop Loss Distance", "مسافة وقف الخسارة"],
      ["tpdist", "Take Profit Distance", "مسافة جني الأرباح"],
      ["riskpct", "Risk %", "نسبة المخاطرة من الرصيد"],
      ["maxspread", "Max Spread", "أعلى سبريد مسموح"],
      ["maxtrades", "Max Trades / Day", "أقصى صفقات يوميًا"],
      ["cooldown", "Cooldown", "فترة انتظار بين الصفقات"],
    ]},
];
const CAT_BY_ID = Object.fromEntries(CAT.map((c) => [c.id, c]));
const ALL_ITEMS = CAT.flatMap((c) => c.items.map(([type, label, desc]) => ({ catId: c.id, type, label, desc })));

const TABS = [
  { id: "build", label: "البناء", icon: Hammer },
  { id: "logic", label: "المنطق والسكور", icon: SlidersHorizontal },
  { id: "simulation", label: "المحاكاة", icon: Play },
  { id: "telegram", label: "تلجرام", icon: Bot },
  { id: "monitoring", label: "المراقبة الحية", icon: MonitorDot },
  { id: "saved", label: "المحفوظة", icon: FolderOpen },
];

/* =========================================================================
   DEMO PRESET — "London Gold Liquidity Reversal"
========================================================================= */
function buildDemoState() {
  const gA = { id: "gA", name: "Market Structure", logic: "AND", atLeast: 1, collapsed: false };
  const gB = { id: "gB", name: "Entry Confirmation", logic: "OR", atLeast: 1, collapsed: false };
  const gC = { id: "gC", name: "Session Filter", logic: "AND", atLeast: 1, collapsed: false };
  const mk = (groupId, catId, type, label, tf, value) => ({
    id: nextId(), groupId, catId, type, label,
    timeframe: tf, tfMode: "نفس الفريم",
    value, weight: CAT_BY_ID[catId].w, enabled: true, not: false,
  });
  const conditions = [
    mk("gA", "structure", "trend", "HTF Trend Bullish", "1D", "صاعد"),
    mk("gA", "smc", "liquidity", "Liquidity Sweep", "1H", "قمة"),
    mk("gA", "smc", "bos", "BOS", "15m", "صعودي"),
    mk("gB", "smc", "fvg", "FVG", "15m", "امتلاء 50%"),
    mk("gB", "smc", "ob", "Order Block", "15m", "طلب"),
    mk("gC", "sessions", "london", "London Session", "15m", "نشطة"),
  ];
  return { groups: [gA, gB, gC], conditions };
}

/* =========================================================================
   SMALL UI PRIMITIVES
========================================================================= */
const Pill = ({ children, color, bg, border, style, ...rest }) => (
  <span
    style={{ color, background: bg, border: `1px solid ${border || color}`, fontSize: 11, ...style }}
    className="px-2 py-0.5 rounded-full inline-flex items-center gap-1"
    {...rest}
  >
    {children}
  </span>
);

const IconBtn = ({ icon: Icon, onClick, color, title, size = 13 }) => (
  <button onClick={onClick} title={title} style={{ color: color || C.muted }} className="hover:opacity-80 p-1 rounded-md">
    <Icon size={size} />
  </button>
);

const Toggle = ({ on, onClick, colorOn = C.teal }) => (
  <button
    onClick={onClick}
    style={{ background: on ? `${colorOn}33` : C.surfaceHi, border: `1px solid ${on ? colorOn : C.border}` }}
    className="w-8 h-[18px] rounded-full relative transition-colors flex items-center"
  >
    <span
      style={{ background: on ? colorOn : C.muted, transform: on ? "translateX(-15px)" : "translateX(-1px)" }}
      className="w-3.5 h-3.5 rounded-full absolute right-0 transition-transform"
    />
  </button>
);

function Sparkline({ color = C.teal, seed = 1, width = 64, height = 22 }) {
  const pts = useMemo(() => {
    let v = 50, arr = [];
    let s = seed;
    for (let i = 0; i < 18; i++) {
      s = (s * 9301 + 49297) % 233280;
      v += (s / 233280 - 0.5) * 22;
      v = Math.max(5, Math.min(95, v));
      arr.push(v);
    }
    return arr;
  }, [seed]);
  const pathD = pts
    .map((v, i) => `${i === 0 ? "M" : "L"} ${(i / (pts.length - 1)) * width} ${height - (v / 100) * height}`)
    .join(" ");
  return (
    <svg width={width} height={height}>
      <path d={pathD} fill="none" stroke={color} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" opacity="0.85" />
    </svg>
  );
}

function ScoreRing({ pct, size = 58, color }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={C.border} strokeWidth="5" />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="5" strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * circ} ${circ}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dasharray .4s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center" style={{ fontFamily: FM, fontSize: size * 0.24, color }}>
        {pct}%
      </div>
    </div>
  );
}

function Modal({ title, children, onClose, danger }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(4,5,7,0.72)" }}>
      <div style={{ background: C.surfaceHi, border: `1px solid ${danger ? C.red : C.border}`, maxWidth: 440, width: "100%" }} className="rounded-2xl p-5 fade-in">
        <div className="flex items-center justify-between mb-3">
          <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 15, color: danger ? C.red : C.text }} className="flex items-center gap-2">
            {danger && <AlertTriangle size={16} />}
            {title}
          </div>
          <button onClick={onClose} style={{ color: C.muted }}><X size={16} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* =========================================================================
   MAIN COMPONENT
========================================================================= */
export default function StrategyBuilder() {
  const { user } = useAuth();
  const tgConnected = !!user?.telegram_linked;

  const [activeTab, setActiveTab] = useState("build");
  const [strategyName, setStrategyName] = useState("استراتيجية جديدة");
  const [symbols, setSymbols] = useState(["XAU/USD"]);
  const [timeframes, setTimeframes] = useState(["1H", "15m", "5m"]);

  const [groups, setGroups] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [currentStrategyId, setCurrentStrategyId] = useState(null);
  const [activeGroupId, setActiveGroupId] = useState(null);
  const [activeCat, setActiveCat] = useState("smc");
  const [search, setSearch] = useState("");

  const [minScore, setMinScore] = useState(70);
  const [triggerActions, setTriggerActions] = useState({ createSignal: true, sendTelegram: true, monitorEntry: true });
  const [execCfg, setExecCfg] = useState({ entry: "Market", sl: "Below Swing Low", tp: "Risk/Reward", rr: "2" });

  const [tgChannel, setTgChannel] = useState("");
  const [tgFields, setTgFields] = useState({ entry: true, sl: true, tp: true, rr: true, confidence: true, conditions: true, chart: false });

  const [sim, setSim] = useState({ status: "idle", results: [] });
  const [monitor, setMonitor] = useState({ active: false, events: [], lastScan: null });

  const [saved, setSaved] = useState([]);
  const [savedLoading, setSavedLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [viewTarget, setViewTarget] = useState(null);
  const [toast, setToast] = useState(null);

  const loadSaved = useCallback(async () => {
    setSavedLoading(true);
    try {
      const r = await axios.get(`${API}/api/v1/strategies`);
      setSaved(r.data.strategies || []);
    } catch {
      // تُعرض حالة فارغة بأمان — لا نخترع بيانات
    } finally {
      setSavedLoading(false);
    }
  }, []);

  useEffect(() => { loadSaved(); }, [loadSaved]);

  const history = useRef([]);
  const historyIdx = useRef(-1);
  const suppressHistory = useRef(false);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2400);
  };

  /* ---------------- history (mock undo/redo) ---------------- */
  const pushHistory = useCallback((g, c) => {
    if (suppressHistory.current) return;
    const snap = JSON.stringify({ g, c });
    history.current = history.current.slice(0, historyIdx.current + 1);
    history.current.push(snap);
    historyIdx.current = history.current.length - 1;
  }, []);
  useEffect(() => { pushHistory(groups, conditions); }, []); // eslint-disable-line

  const mutate = (nextGroups, nextConditions) => {
    setGroups(nextGroups);
    setConditions(nextConditions);
    pushHistory(nextGroups, nextConditions);
  };

  const undo = () => {
    if (historyIdx.current <= 0) return showToast("لا يوجد ما يمكن التراجع عنه");
    historyIdx.current -= 1;
    const snap = JSON.parse(history.current[historyIdx.current]);
    suppressHistory.current = true;
    setGroups(snap.g); setConditions(snap.c);
    suppressHistory.current = false;
    showToast("تم التراجع");
  };
  const redo = () => {
    if (historyIdx.current >= history.current.length - 1) return showToast("لا يوجد ما يمكن الإعادة");
    historyIdx.current += 1;
    const snap = JSON.parse(history.current[historyIdx.current]);
    suppressHistory.current = true;
    setGroups(snap.g); setConditions(snap.c);
    suppressHistory.current = false;
    showToast("تمت الإعادة");
  };

  /* ---------------- group ops ---------------- */
  const addGroup = () => {
    const g = { id: nextId(), name: `مجموعة ${groups.length + 1}`, logic: "AND", atLeast: 1, collapsed: false };
    const ng = [...groups, g];
    mutate(ng, conditions);
    setActiveGroupId(g.id);
  };
  const renameGroup = (id, name) => mutate(groups.map((g) => (g.id === id ? { ...g, name } : g)), conditions);
  const setGroupLogic = (id, logic) => mutate(groups.map((g) => (g.id === id ? { ...g, logic } : g)), conditions);
  const setGroupAtLeast = (id, n) => mutate(groups.map((g) => (g.id === id ? { ...g, atLeast: n } : g)), conditions);
  const toggleCollapse = (id) => setGroups((prev) => prev.map((g) => (g.id === id ? { ...g, collapsed: !g.collapsed } : g)));
  const duplicateGroup = (id) => {
    const g = groups.find((x) => x.id === id);
    const ng2 = { ...g, id: nextId(), name: `${g.name} (نسخة)` };
    const members = conditions.filter((c) => c.groupId === id).map((c) => ({ ...c, id: nextId(), groupId: ng2.id }));
    mutate([...groups, ng2], [...conditions, ...members]);
    showToast("تم نسخ المجموعة");
  };
  const deleteGroup = (id) => {
    mutate(groups.filter((g) => g.id !== id), conditions.filter((c) => c.groupId !== id));
    if (activeGroupId === id) setActiveGroupId(null);
    showToast("تم حذف المجموعة");
  };

  /* ---------------- condition ops ---------------- */
  const addCondition = (item) => {
    if (!activeGroupId) return showToast("أنشئ مجموعة أولًا أو اخترها");
    const cat = CAT_BY_ID[item.catId];
    const c = {
      id: nextId(), groupId: activeGroupId, catId: item.catId, type: item.type, label: item.label,
      timeframe: "15m", tfMode: "نفس الفريم", value: "", weight: cat.w, enabled: true, not: false,
    };
    mutate(groups, [...conditions, c]);
  };
  const removeCondition = (id) => mutate(groups, conditions.filter((c) => c.id !== id));
  const updateCondition = (id, patch) => mutate(groups, conditions.map((c) => (c.id === id ? { ...c, ...patch } : c)));
  const duplicateCondition = (id) => {
    const c = conditions.find((x) => x.id === id);
    mutate(groups, [...conditions, { ...c, id: nextId() }]);
  };
  const resetCondition = (id) => {
    const c = conditions.find((x) => x.id === id);
    updateCondition(id, { value: "", weight: CAT_BY_ID[c.catId].w, not: false });
  };
  const clearStrategy = () => {
    mutate([], []);
    setActiveGroupId(null);
    setCurrentStrategyId(null);
    showToast("تم مسح الاستراتيجية");
  };

  const loadDemoIntoEditor = () => {
    const demo = buildDemoState();
    mutate(demo.groups, demo.conditions);
    setActiveGroupId(demo.groups[0]?.id || null);
    setCurrentStrategyId(null);
    showToast("تم تحميل استراتيجية تجريبية — عدّلها ثم احفظها لتصبح حقيقية");
  };

  const filteredItems = useMemo(() => {
    const pool = ALL_ITEMS.filter((it) => it.catId === activeCat);
    if (!search.trim()) return pool;
    const q = search.trim().toLowerCase();
    return ALL_ITEMS.filter((it) => it.label.toLowerCase().includes(q) || it.desc.includes(q));
  }, [activeCat, search]);

  /* ---------------- derived: score / summary ---------------- */
  const enabledConditions = conditions.filter((c) => c.enabled);
  const totalWeight = Math.min(100, enabledConditions.reduce((a, c) => a + Number(c.weight || 0), 0));
  const schoolsUsed = new Set(enabledConditions.map((c) => c.catId)).size;
  const scoreBreakdown = [...enabledConditions].sort((a, b) => b.weight - a.weight);

  const whenText = groups
    .filter((g) => conditions.some((c) => c.groupId === g.id))
    .map((g) => {
      const members = conditions.filter((c) => c.groupId === g.id);
      const joiner = g.logic === "AND" ? " و " : g.logic === "OR" ? " أو " : ` (٢+ من ${members.length}) `;
      return `(${members.map((m) => (m.not ? `NOT ${m.label}` : m.label)).join(joiner)})`;
    })
    .join(" و ");

  /* ---------------- live price (real, falls back to a reference price if unavailable) ---------------- */
  const [livePrice, setLivePrice] = useState(null);
  useEffect(() => {
    const sym = symbols[0];
    if (!sym) { setLivePrice(null); return; }
    let stop = false;
    axios.get(`${API}/api/v1/markets/${sym.replace("/", "")}/price`)
      .then((r) => { if (!stop) setLivePrice(r.data?.data?.price ?? null); })
      .catch(() => { if (!stop) setLivePrice(null); });
    return () => { stop = true; };
  }, [symbols]);

  /* ---------------- execution preview ---------------- */
  const execPreview = useMemo(() => {
    const sym = symbols[0] || "XAU/USD";
    const bp = livePrice ?? basePrice(sym);
    const dist = bp * 0.003;
    const entry = bp + dist * 0.4;
    const sl = execCfg.sl.includes("ATR") ? entry - dist * 1.2 : entry - dist;
    const rr = Number(execCfg.rr) || 2;
    const tp1 = entry + (entry - sl) * rr;
    const tp2 = entry + (entry - sl) * rr * 1.6;
    return {
      entry: fmtPrice(sym, entry), sl: fmtPrice(sym, sl),
      tp1: fmtPrice(sym, tp1), tp2: fmtPrice(sym, tp2), sym,
    };
  }, [symbols, execCfg, livePrice]);

  /* ---------------- telegram template ---------------- */
  const tgTemplate = useMemo(() => {
    const lines = [];
    lines.push("━━━━━━━━━━━━━━");
    lines.push("🔥 STRATEGY TRIGGERED");
    lines.push("");
    lines.push(`${symbols[0] || "XAU/USD"}`);
    lines.push(`${timeframes[timeframes.length - 1] || "15M"}`);
    lines.push("");
    lines.push("Direction:");
    lines.push("🟢 LONG");
    if (tgFields.entry) { lines.push(""); lines.push("Entry:"); lines.push(execPreview.entry); }
    if (tgFields.sl) { lines.push(""); lines.push("Stop Loss:"); lines.push(execPreview.sl); }
    if (tgFields.tp) { lines.push(""); lines.push("Take Profit:"); lines.push(execPreview.tp1); }
    if (tgFields.rr) { lines.push(""); lines.push("RR:"); lines.push(`1:${execCfg.rr}`); }
    if (tgFields.confidence) { lines.push(""); lines.push("Confidence:"); lines.push(`${totalWeight}%`); }
    if (tgFields.conditions) {
      lines.push(""); lines.push("Signals:");
      enabledConditions.slice(0, 6).forEach((c) => lines.push(`✓ ${c.label}`));
    }
    if (tgFields.chart) { lines.push(""); lines.push("📊 Chart Snapshot: (mock)"); }
    lines.push("━━━━━━━━━━━━━━");
    return lines.join("\n");
  }, [symbols, timeframes, tgFields, execPreview, execCfg, totalWeight, enabledConditions]);

  /* ---------------- strategy payload (matches backend StrategyIn) ---------------- */
  const buildPayload = () => ({
    name: strategyName, symbols, timeframes, minScore, triggerActions, execCfg,
    tgChannel, tgFields, groups, conditions,
  });

  /* ---------------- simulation (REAL — evaluates against live analyze_market()) ---------------- */
  const runSimulation = async () => {
    if (enabledConditions.length === 0) return showToast("أضف شروطًا قبل تشغيل المحاكاة");
    setSim({ status: "scanning", results: [] });
    try {
      const res = currentStrategyId
        ? await axios.post(`${API}/api/v1/strategies/${currentStrategyId}/evaluate`)
        : await axios.post(`${API}/api/v1/strategies/evaluate-preview`, buildPayload());
      const results = (res.data.results || []).map((r) => ({
        symbol: r.symbol,
        matched: (r.matched || []).map((m) => ({ ...m })),
        unsupported: r.unsupported || [],
        score: r.score ?? 0,
        triggered: !!r.triggered,
        price: r.price != null ? fmtPrice(r.symbol, r.price) : "—",
        error: r.error || null,
      }));
      setSim({ status: "done", results });
    } catch (e) {
      setSim({ status: "idle", results: [] });
      showToast(e.response?.data?.detail || "فشل تشغيل المحاكاة");
    }
  };

  /* ---------------- live monitor (REAL — polls saved trigger events) ---------------- */
  useEffect(() => {
    if (activeTab !== "monitoring" || !currentStrategyId) return;
    let stopped = false;
    const poll = async () => {
      try {
        const r = await axios.get(`${API}/api/v1/strategies/${currentStrategyId}/events?limit=15`);
        if (stopped) return;
        setMonitor({
          active: r.data.status === "ACTIVE",
          events: (r.data.events || []).map((e) => ({
            id: e.id,
            time: e.createdAt ? new Date(e.createdAt).toLocaleTimeString("ar-EG") : "",
            msg: `${e.symbol} — Score ${e.score}${e.triggered ? " — ✓ TRIGGERED" : ""}${e.telegramSent ? " — Telegram Alert Sent ✓" : ""}`,
          })),
          lastScan: r.data.events?.[0]?.createdAt ? new Date(r.data.events[0].createdAt).toLocaleTimeString("ar-EG") : null,
        });
      } catch { /* تُترك الحالة كما هي عند فشل الاستطلاع */ }
    };
    poll();
    const id = setInterval(poll, 10000);
    return () => { stopped = true; clearInterval(id); };
  }, [activeTab, currentStrategyId]);

  const toggleMonitor = async () => {
    if (!currentStrategyId) return showToast("احفظ الاستراتيجية أولًا لتفعيل المراقبة الحقيقية");
    const next = monitor.active ? "DISABLED" : "ACTIVE";
    try {
      await axios.put(`${API}/api/v1/strategies/${currentStrategyId}/status`, { status: next });
      setMonitor((m) => ({ ...m, active: next === "ACTIVE" }));
      await loadSaved();
      showToast(next === "ACTIVE" ? "تم تفعيل المراقبة — يفحصها الخادم كل 5 دقائق" : "تم إيقاف المراقبة");
    } catch {
      showToast("فشل تحديث حالة المراقبة");
    }
  };

  /* ---------------- save / load strategies (REAL — DB-backed) ---------------- */
  const saveStrategy = async (activate) => {
    if (conditions.length === 0) return showToast("أضف شروطًا قبل الحفظ");
    setSaving(true);
    try {
      let id = currentStrategyId;
      if (id) {
        await axios.put(`${API}/api/v1/strategies/${id}`, buildPayload());
      } else {
        const res = await axios.post(`${API}/api/v1/strategies`, buildPayload());
        id = res.data.id;
        setCurrentStrategyId(id);
      }
      if (activate) {
        await axios.put(`${API}/api/v1/strategies/${id}/status`, { status: "ACTIVE" });
      }
      await loadSaved();
      showToast(activate ? "تم الحفظ والتفعيل" : "تم حفظ المسودة");
    } catch (e) {
      showToast(e.response?.data?.detail || "فشل الحفظ");
    } finally {
      setSaving(false);
    }
  };

  const loadStrategy = async (rec) => {
    try {
      const r = await axios.get(`${API}/api/v1/strategies/${rec.id}`);
      const d = r.data;
      setGroups(d.groups); setConditions(d.conditions);
      setSymbols(d.symbols?.length ? d.symbols : symbols);
      setTimeframes(d.timeframes?.length ? d.timeframes : timeframes);
      setStrategyName(d.name); setMinScore(d.minScore);
      setTriggerActions(d.triggerActions); setExecCfg(d.execCfg);
      setTgChannel(d.tgChannel || ""); setTgFields(d.tgFields);
      setCurrentStrategyId(d.id);
      setActiveGroupId(d.groups[0]?.id || null);
      setActiveTab("build");
      showToast("تم تحميل الاستراتيجية للتحرير");
    } catch {
      showToast("فشل تحميل الاستراتيجية");
    }
  };

  const duplicateSaved = async (rec) => {
    try {
      await axios.post(`${API}/api/v1/strategies/${rec.id}/duplicate`);
      await loadSaved();
      showToast("تم نسخ الاستراتيجية");
    } catch {
      showToast("فشل نسخ الاستراتيجية");
    }
  };

  const toggleSavedStatus = async (rec) => {
    const next = rec.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
    try {
      await axios.put(`${API}/api/v1/strategies/${rec.id}/status`, { status: next });
      await loadSaved();
    } catch {
      showToast("فشل تحديث الحالة");
    }
  };

  const confirmDelete = async () => {
    try {
      await axios.delete(`${API}/api/v1/strategies/${deleteTarget.id}`);
      if (currentStrategyId === deleteTarget.id) setCurrentStrategyId(null);
      await loadSaved();
      showToast("تم حذف الاستراتيجية");
    } catch {
      showToast("فشل حذف الاستراتيجية");
    } finally {
      setDeleteTarget(null);
    }
  };

  const sendTestTelegramAlert = async () => {
    if (!currentStrategyId) return showToast("احفظ الاستراتيجية أولًا");
    if (!tgConnected) return showToast("اربط حساب Telegram أولًا من صفحة الملف الشخصي");
    try {
      const r = await axios.post(`${API}/api/v1/strategies/${currentStrategyId}/telegram/test`);
      showToast(r.data.message || "تم الإرسال ✅");
    } catch (e) {
      showToast(e.response?.data?.detail || "فشل إرسال التنبيه");
    }
  };

  const toggleSymbol = (s) => setSymbols((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  const toggleTf = (t) => setTimeframes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));

  /* =======================================================================
     RENDER
  ======================================================================= */
  return (
    <div dir="rtl" style={{ background: C.bgGrad, color: C.text, fontFamily: FB, minHeight: "100vh" }} className="w-full">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; }
        input, select, textarea { outline: none; font-family: inherit; }
        input:focus, select:focus { box-shadow: 0 0 0 2px ${C.goldSoft}; border-color: ${C.gold} !important; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 4px; }
        .fade-in { animation: fadeIn .22s ease both; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(3px);} to {opacity:1; transform:none;} }
        @keyframes pulseDot { 0%,100% { opacity:1; } 50% { opacity:.35; } }
        @keyframes glowPulse { 0%,100% { box-shadow: 0 0 0 0 ${C.goldSoft}; } 50% { box-shadow: 0 0 14px 2px ${C.goldSoft}; } }
        @keyframes shimmer { 0% { background-position: -300px 0; } 100% { background-position: 300px 0; } }
        .skeleton { background: linear-gradient(90deg, ${C.surfaceHi} 0%, ${C.border} 50%, ${C.surfaceHi} 100%); background-size: 300px 100%; animation: shimmer 1.4s infinite; }
        .tab-underline { position: relative; }
        .scroll-thin::-webkit-scrollbar { width: 5px; }
      `}</style>

      {/* ============ TOP OVERVIEW BAR ============ */}
      <header style={{ borderBottom: `1px solid ${C.border}`, background: "rgba(7,8,11,0.92)" }} className="sticky top-0 z-30 backdrop-blur">
        <div className="px-4 md:px-8 py-3 flex flex-wrap items-center gap-3 justify-between max-w-[1500px] mx-auto">
          <div className="flex items-center gap-2.5">
            <div style={{ background: C.goldSoft, border: `1px solid ${C.gold}` }} className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0">
              <Sparkles size={16} color={C.gold} />
            </div>
            <div>
              <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 14.5 }}>Qaffel Strategy Terminal</div>
              <div style={{ color: C.sub, fontSize: 10.5, fontFamily: FM }}>LIVE — SMC/ICT مربوطة بمحرك التحليل الحقيقي</div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-[11px]" style={{ fontFamily: FM }}>
            <Pill color={C.sub} bg="transparent" border={C.border}>Conditions: {conditions.length}</Pill>
            <Pill color={C.sub} bg="transparent" border={C.border}>Groups: {groups.length}</Pill>
            <Pill color={totalWeight >= minScore ? C.teal : C.gold} bg={totalWeight >= minScore ? C.tealSoft : C.goldSoft} border={totalWeight >= minScore ? C.teal : C.gold}>
              Confidence {totalWeight}%
            </Pill>
            <Pill color={C.teal} bg={C.tealSoft} border={C.teal}>
              <span style={{ animation: "pulseDot 1.6s infinite" }}>●</span> ACTIVE
            </Pill>
            <Pill color={tgConnected ? C.teal : C.muted} bg={tgConnected ? C.tealSoft : "transparent"} border={tgConnected ? C.teal : C.border}>
              <Bot size={11} /> {tgConnected ? "TELEGRAM CONNECTED" : "TELEGRAM OFFLINE"}
            </Pill>
          </div>
        </div>

        {/* tabs */}
        <div className="px-4 md:px-8 max-w-[1500px] mx-auto flex items-center gap-1 overflow-x-auto scroll-thin">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                style={{ color: active ? C.gold : C.sub, borderBottom: `2px solid ${active ? C.gold : "transparent"}` }}
                className="tab-underline flex items-center gap-1.5 px-3 py-2.5 text-[13px] whitespace-nowrap"
              >
                <Icon size={14} />
                {t.label}
              </button>
            );
          })}
        </div>
      </header>

      <div className="max-w-[1500px] mx-auto px-4 md:px-8 py-5">
        {/* ============ VISUAL FLOW RIBBON ============ */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-4 mb-1 scroll-thin">
          {["Market Context", "Liquidity", "Structure", "Confirmation", "Entry", "Risk", "Telegram"].map((s, i, arr) => (
            <React.Fragment key={s}>
              <div
                style={{ background: C.surface, border: `1px solid ${C.borderSoft}`, color: C.sub, fontFamily: FM, fontSize: 10.5 }}
                className="px-2.5 py-1.5 rounded-lg whitespace-nowrap"
              >
                {s}
              </div>
              {i < arr.length - 1 && <ArrowLeft size={12} color={C.muted} />}
            </React.Fragment>
          ))}
        </div>

        {/* ============ TAB: BUILD ============ */}
        {activeTab === "build" && (
          <div className="grid grid-cols-1 lg:grid-cols-[270px_1fr] gap-5">
            {/* ---- library ---- */}
            <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-3 h-fit lg:sticky lg:top-32">
              <div className="relative mb-3">
                <Search size={13} style={{ position: "absolute", right: 10, top: 10, color: C.muted }} />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="ابحث عن شرط..."
                  style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.text, paddingRight: 30 }}
                  className="w-full rounded-lg py-2 pl-3 text-[12.5px]"
                />
              </div>

              {!search && (
                <div className="flex flex-col gap-1 mb-3 max-h-[220px] overflow-auto scroll-thin">
                  {CAT.map((cat) => {
                    const Icon = cat.icon;
                    const active = activeCat === cat.id;
                    return (
                      <button
                        key={cat.id}
                        onClick={() => setActiveCat(cat.id)}
                        style={{ background: active ? `${cat.color}1A` : "transparent", border: `1px solid ${active ? cat.color : "transparent"}`, color: active ? cat.color : C.sub }}
                        className="flex items-center justify-between px-3 py-2 rounded-xl text-[13px] text-right"
                      >
                        <span className="flex items-center gap-2"><Icon size={14} /> {cat.label}</span>
                        <span style={{ fontFamily: FM, fontSize: 10, color: C.muted }}>{cat.items.length}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              <div style={{ borderTop: `1px solid ${C.borderSoft}` }} className="pt-3 flex flex-col gap-1.5 max-h-[360px] overflow-auto scroll-thin">
                {filteredItems.map((item) => {
                  const cat = CAT_BY_ID[item.catId];
                  return (
                    <button
                      key={item.catId + item.type}
                      onClick={() => addCondition(item)}
                      style={{ background: C.surfaceHi, border: `1px solid ${C.border}` }}
                      className="group flex items-start justify-between gap-2 px-3 py-2.5 rounded-xl text-right hover:opacity-90"
                    >
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span style={{ width: 5, height: 5, borderRadius: 99, background: cat.color }} />
                          <span style={{ fontSize: 12.5, fontWeight: 500 }}>{item.label}</span>
                          {!IMPLEMENTED_TYPES.has(item.type) && (
                            <span title="غير مربوط بمحرك التحليل الحقيقي بعد" style={{ color: C.muted, fontSize: 9, border: `1px solid ${C.border}` }} className="px-1 py-0.5 rounded">تجريبي</span>
                          )}
                        </div>
                        <div style={{ color: C.muted, fontSize: 10.5 }} className="mt-0.5">{item.desc}</div>
                      </div>
                      <Plus size={13} style={{ color: C.gold, marginTop: 2, flexShrink: 0 }} />
                    </button>
                  );
                })}
                {filteredItems.length === 0 && (
                  <div style={{ color: C.muted }} className="text-center text-[12px] py-6">لا توجد نتائج مطابقة</div>
                )}
              </div>
            </div>

            {/* ---- canvas ---- */}
            <div className="flex flex-col gap-4">
              {/* meta */}
              <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-4 flex flex-col gap-3">
                <input
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, fontFamily: FD, fontWeight: 600, color: C.text }}
                  className="rounded-lg px-3 py-2 text-sm"
                />
                <div className="flex flex-wrap gap-1.5">
                  {SYMBOL_POOL.map((m) => (
                    <button
                      key={m.s}
                      onClick={() => toggleSymbol(m.s)}
                      style={{ background: symbols.includes(m.s) ? C.goldSoft : C.surfaceHi, border: `1px solid ${symbols.includes(m.s) ? C.gold : C.border}`, color: symbols.includes(m.s) ? C.gold : C.sub, fontFamily: FM }}
                      className="px-2.5 py-1 rounded-lg text-[11px]"
                    >
                      {m.s}
                    </button>
                  ))}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {TIMEFRAMES.map((t) => (
                    <button
                      key={t}
                      onClick={() => toggleTf(t)}
                      style={{ background: timeframes.includes(t) ? C.tealSoft : C.surfaceHi, border: `1px solid ${timeframes.includes(t) ? C.teal : C.border}`, color: timeframes.includes(t) ? C.teal : C.sub, fontFamily: FM }}
                      className="px-2.5 py-1 rounded-lg text-[11px]"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* toolbar */}
              <div className="flex flex-wrap items-center gap-2">
                <button onClick={addGroup} style={{ background: C.goldSoft, border: `1px solid ${C.gold}`, color: C.gold }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12.5px]">
                  <Plus size={13} /> مجموعة جديدة
                </button>
                <IconBtn icon={Undo2} onClick={undo} title="تراجع" />
                <IconBtn icon={Redo2} onClick={redo} title="إعادة" />
                <IconBtn icon={RefreshCw} onClick={clearStrategy} title="مسح الكل" color={C.red} />
                <div className="flex-1" />
                <button disabled={saving} onClick={() => saveStrategy(false)} style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.text, opacity: saving ? 0.6 : 1 }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12.5px]">
                  {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} حفظ كمسودة
                </button>
                <button disabled={saving} onClick={() => saveStrategy(true)} style={{ background: C.gold, color: "#1A1200", fontWeight: 600, opacity: saving ? 0.6 : 1, animation: conditions.length && !saving ? "glowPulse 2.6s infinite" : "none" }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12.5px]">
                  {saving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} حفظ وتفعيل
                </button>
              </div>

              {/* group chips (select active target) */}
              {groups.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {groups.map((g) => (
                    <button
                      key={g.id}
                      onClick={() => setActiveGroupId(g.id)}
                      style={{ background: activeGroupId === g.id ? C.tealSoft : "transparent", border: `1px dashed ${activeGroupId === g.id ? C.teal : C.border}`, color: activeGroupId === g.id ? C.teal : C.sub }}
                      className="px-2.5 py-1 rounded-full text-[11px]"
                    >
                      إضافة إلى: {g.name}
                    </button>
                  ))}
                </div>
              )}

              {/* groups list */}
              {groups.length === 0 && (
                <div style={{ background: C.surface, border: `1px dashed ${C.border}`, color: C.muted }} className="rounded-2xl py-12 flex flex-col items-center gap-3 text-sm">
                  <Layers size={22} />
                  أنشئ مجموعة أولى، ثم أضف شروطًا من المكتبة على اليمين
                  <button onClick={loadDemoIntoEditor} style={{ background: C.goldSoft, border: `1px solid ${C.gold}`, color: C.gold }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px]">
                    <Sparkles size={12} /> جرّب استراتيجية تجريبية جاهزة
                  </button>
                </div>
              )}

              {groups.map((g) => {
                const members = conditions.filter((c) => c.groupId === g.id);
                return (
                  <div key={g.id} style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl overflow-hidden fade-in">
                    <div style={{ background: C.surfaceHi, borderBottom: g.collapsed ? "none" : `1px solid ${C.borderSoft}` }} className="flex items-center justify-between px-3.5 py-2.5">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <button onClick={() => toggleCollapse(g.id)} style={{ color: C.sub }}>
                          {g.collapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
                        </button>
                        <input
                          value={g.name}
                          onChange={(e) => renameGroup(g.id, e.target.value)}
                          style={{ background: "transparent", color: C.text, fontFamily: FD, fontWeight: 600, fontSize: 13 }}
                          className="min-w-0 flex-1"
                        />
                        <span style={{ color: C.muted, fontFamily: FM, fontSize: 10.5 }}>{members.length} شروط</span>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {["AND", "OR", "AT_LEAST"].map((lg) => (
                          <button
                            key={lg}
                            onClick={() => setGroupLogic(g.id, lg)}
                            style={{ background: g.logic === lg ? C.goldSoft : "transparent", border: `1px solid ${g.logic === lg ? C.gold : C.border}`, color: g.logic === lg ? C.gold : C.muted, fontFamily: FM }}
                            className="px-2 py-0.5 rounded-md text-[10.5px]"
                          >
                            {lg === "AT_LEAST" ? "X of Y" : lg}
                          </button>
                        ))}
                        {g.logic === "AT_LEAST" && (
                          <input
                            type="number" min={1} max={Math.max(1, members.length)}
                            value={g.atLeast}
                            onChange={(e) => setGroupAtLeast(g.id, Number(e.target.value))}
                            style={{ width: 34, background: C.bg, border: `1px solid ${C.border}`, color: C.gold, fontFamily: FM }}
                            className="rounded-md px-1 py-0.5 text-[11px] text-center"
                          />
                        )}
                        <IconBtn icon={Copy} onClick={() => duplicateGroup(g.id)} title="نسخ المجموعة" />
                        <IconBtn icon={Trash2} onClick={() => deleteGroup(g.id)} title="حذف المجموعة" color={C.red} />
                      </div>
                    </div>

                    {!g.collapsed && (
                      <div className="p-3 flex flex-col gap-2">
                        {members.length === 0 && <div style={{ color: C.muted, fontSize: 12 }} className="text-center py-4">لا شروط بعد في هذه المجموعة</div>}
                        {members.map((c, i) => {
                          const cat = CAT_BY_ID[c.catId];
                          return (
                            <React.Fragment key={c.id}>
                              {i > 0 && (
                                <div className="flex justify-center">
                                  <span style={{ color: C.muted, fontFamily: FM, fontSize: 10 }}>
                                    {g.logic === "AND" ? "AND" : g.logic === "OR" ? "OR" : "•"}
                                  </span>
                                </div>
                              )}
                              <div
                                style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, borderInlineStart: `3px solid ${cat.color}`, opacity: c.enabled ? 1 : 0.45 }}
                                className="rounded-xl p-2.5 flex flex-wrap items-center gap-2"
                              >
                                <Pill color={cat.color} bg={`${cat.color}1A`} border={cat.color} style={{ fontSize: 10 }}>{cat.label}</Pill>
                                {!IMPLEMENTED_TYPES.has(c.type) && (
                                  <span title="غير مربوط بمحرك التحليل الحقيقي بعد — لا يُحتسب بالسكور" style={{ color: C.muted, fontSize: 9, border: `1px solid ${C.border}` }} className="px-1 py-0.5 rounded">تجريبي</span>
                                )}
                                <input
                                  value={c.label}
                                  onChange={(e) => updateCondition(c.id, { label: e.target.value })}
                                  style={{ background: "transparent", color: C.text, fontWeight: 500, fontSize: 12.5, width: Math.max(70, c.label.length * 7) }}
                                />
                                <select
                                  value={c.timeframe}
                                  onChange={(e) => updateCondition(c.id, { timeframe: e.target.value })}
                                  style={{ background: C.bg, border: `1px solid ${C.border}`, color: C.sub, fontFamily: FM, fontSize: 10.5 }}
                                  className="rounded-md px-1.5 py-1"
                                >
                                  {TIMEFRAMES.map((t) => <option key={t}>{t}</option>)}
                                </select>
                                <select
                                  value={c.tfMode}
                                  onChange={(e) => updateCondition(c.id, { tfMode: e.target.value })}
                                  style={{ background: C.bg, border: `1px solid ${C.border}`, color: C.muted, fontSize: 10 }}
                                  className="rounded-md px-1.5 py-1"
                                >
                                  {TF_MODES.map((t) => <option key={t}>{t}</option>)}
                                </select>
                                <input
                                  value={c.value}
                                  placeholder="قيمة / وصف"
                                  onChange={(e) => updateCondition(c.id, { value: e.target.value })}
                                  style={{ background: C.bg, border: `1px solid ${C.border}`, color: C.text, fontFamily: FM, fontSize: 11, width: 90 }}
                                  className="rounded-md px-2 py-1"
                                />
                                <div className="flex items-center gap-1" style={{ color: C.muted, fontSize: 10.5 }}>
                                  Weight
                                  <input
                                    type="number" value={c.weight}
                                    onChange={(e) => updateCondition(c.id, { weight: Number(e.target.value) })}
                                    style={{ width: 40, background: C.bg, border: `1px solid ${C.border}`, color: C.gold, fontFamily: FM }}
                                    className="rounded-md px-1 py-0.5 text-[11px] text-center"
                                  />
                                </div>
                                <button
                                  onClick={() => updateCondition(c.id, { not: !c.not })}
                                  style={{ background: c.not ? C.redSoft : "transparent", border: `1px solid ${c.not ? C.red : C.border}`, color: c.not ? C.red : C.muted, fontSize: 10 }}
                                  className="px-1.5 py-0.5 rounded-md flex items-center gap-1"
                                  title="عكس الشرط (NOT)"
                                >
                                  <Ban size={10} /> NOT
                                </button>
                                <div className="flex items-center gap-1 mr-auto">
                                  <Toggle on={c.enabled} onClick={() => updateCondition(c.id, { enabled: !c.enabled })} />
                                  <IconBtn icon={Copy} onClick={() => duplicateCondition(c.id)} title="تكرار" />
                                  <IconBtn icon={RefreshCw} onClick={() => resetCondition(c.id)} title="إعادة تعيين" />
                                  <IconBtn icon={X} onClick={() => removeCondition(c.id)} title="حذف" color={C.red} />
                                </div>
                              </div>
                            </React.Fragment>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ============ TAB: LOGIC & SCORE ============ */}
        {activeTab === "logic" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* score */}
            <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5">
              <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 14.5 }} className="mb-4 flex items-center gap-2">
                <Zap size={15} color={C.gold} /> Strategy Confidence
              </div>
              <div className="flex items-center gap-4 mb-4">
                <ScoreRing pct={totalWeight} color={totalWeight >= minScore ? C.teal : C.gold} size={78} />
                <div>
                  <div style={{ color: C.sub, fontSize: 12 }}>مدارس مدمجة: {schoolsUsed}</div>
                  <div style={{ color: C.sub, fontSize: 12 }}>شروط فعّالة: {enabledConditions.length}</div>
                  <div className="flex items-center gap-2 mt-2">
                    <span style={{ color: C.muted, fontSize: 11.5 }}>الحد الأدنى للتفعيل</span>
                    <input
                      type="number" value={minScore} min={0} max={100}
                      onChange={(e) => setMinScore(Number(e.target.value))}
                      style={{ width: 50, background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.gold, fontFamily: FM }}
                      className="rounded-md px-1.5 py-0.5 text-[12px] text-center"
                    />
                    <span style={{ color: C.muted, fontSize: 11.5 }}>/ 100</span>
                  </div>
                </div>
              </div>

              <div style={{ background: C.surfaceHi, border: `1px solid ${C.borderSoft}` }} className="rounded-lg h-2 overflow-hidden mb-4 relative">
                <div style={{ width: `${totalWeight}%`, background: `linear-gradient(90deg, ${C.teal}, ${C.gold})`, height: "100%", transition: "width .4s" }} />
                <div style={{ left: `${minScore}%`, borderRight: `2px dashed ${C.red}` }} className="absolute top-0 bottom-0" />
              </div>

              <div style={{ color: C.sub, fontSize: 11 }} className="uppercase tracking-wide mb-2">Breakdown</div>
              <div className="flex flex-col gap-1.5 max-h-[240px] overflow-auto scroll-thin">
                {scoreBreakdown.length === 0 && <div style={{ color: C.muted, fontSize: 12 }}>لا توجد شروط بعد</div>}
                {scoreBreakdown.map((c) => (
                  <div key={c.id} className="flex items-center justify-between text-[12.5px]">
                    <span>{c.not ? `NOT ${c.label}` : c.label}</span>
                    <span style={{ color: C.gold, fontFamily: FM }}>+{c.weight}</span>
                  </div>
                ))}
              </div>
              <div style={{ borderTop: `1px solid ${C.borderSoft}`, fontFamily: FM }} className="mt-2 pt-2 flex justify-between text-[13px]">
                <span style={{ color: C.sub }}>Total</span>
                <span style={{ color: C.gold, fontWeight: 600 }}>{totalWeight} / 100</span>
              </div>
            </div>

            {/* trigger + execution */}
            <div className="flex flex-col gap-5">
              <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5">
                <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 14.5 }} className="mb-3 flex items-center gap-2">
                  <ListChecks size={15} color={C.teal} /> Trigger Logic
                </div>
                <div style={{ color: C.muted, fontSize: 10.5 }} className="uppercase mb-1">WHEN</div>
                <div style={{ background: C.bg, border: `1px solid ${C.borderSoft}`, color: C.sub, fontFamily: FM, fontSize: 11.5, lineHeight: 1.8 }} className="rounded-lg p-3 mb-3">
                  {whenText || "لا شروط بعد"} {whenText && <><br />و Score ≥ {minScore}</>}
                </div>
                <div style={{ color: C.muted, fontSize: 10.5 }} className="uppercase mb-1">THEN</div>
                <div className="flex flex-col gap-1.5">
                  {[
                    ["createSignal", "Create Signal"],
                    ["sendTelegram", "Send Telegram Alert"],
                    ["monitorEntry", "Monitor Entry"],
                  ].map(([key, label]) => (
                    <div key={key} className="flex items-center justify-between text-[12.5px]">
                      <span>{label}</span>
                      <Toggle on={triggerActions[key]} onClick={() => setTriggerActions((p) => ({ ...p, [key]: !p[key] }))} />
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5">
                <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 14.5 }} className="mb-3 flex items-center gap-2">
                  <Target size={15} color={C.blue} /> Strategy Execution
                </div>
                <div className="grid grid-cols-3 gap-2 mb-3">
                  {[
                    ["entry", "Entry", ["Market", "Limit", "Breakout", "Retest", "Custom"]],
                    ["sl", "Stop Loss", ["Below Swing Low", "ATR", "Fixed %", "Fixed Points", "Manual"]],
                    ["tp", "Take Profit", ["Risk/Reward", "Previous High/Low", "Liquidity", "Fibonacci", "Manual"]],
                  ].map(([key, label, opts]) => (
                    <div key={key}>
                      <div style={{ color: C.muted, fontSize: 10.5 }} className="mb-1">{label}</div>
                      <select
                        value={execCfg[key]}
                        onChange={(e) => setExecCfg((p) => ({ ...p, [key]: e.target.value }))}
                        style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.text, fontSize: 11.5 }}
                        className="w-full rounded-md px-2 py-1.5"
                      >
                        {opts.map((o) => <option key={o}>{o}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
                {execCfg.tp === "Risk/Reward" && (
                  <div className="flex items-center gap-2 mb-3">
                    <span style={{ color: C.muted, fontSize: 11.5 }}>RR</span>
                    <input value={execCfg.rr} onChange={(e) => setExecCfg((p) => ({ ...p, rr: e.target.value }))} style={{ width: 50, background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.gold, fontFamily: FM }} className="rounded-md px-1.5 py-1 text-[12px] text-center" />
                  </div>
                )}
                <div style={{ background: C.bg, border: `1px solid ${C.borderSoft}`, fontFamily: FM }} className="rounded-lg p-3 text-[12px] flex flex-col gap-1">
                  <div className="flex justify-between"><span style={{ color: C.sub }}>ENTRY →</span><span>{execPreview.entry}</span></div>
                  <div className="flex justify-between"><span style={{ color: C.red }}>SL →</span><span>{execPreview.sl}</span></div>
                  <div className="flex justify-between"><span style={{ color: C.teal }}>TP1 →</span><span>{execPreview.tp1}</span></div>
                  <div className="flex justify-between"><span style={{ color: C.teal }}>TP2 →</span><span>{execPreview.tp2}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============ TAB: SIMULATION ============ */}
        {activeTab === "simulation" && (
          <div className="flex flex-col gap-4">
            <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 15 }}>Market Scan</div>
                <div style={{ color: C.sub, fontSize: 12 }}>محاكاة تحقق شروط الاستراتيجية عبر {SYMBOL_POOL.length} أسواق</div>
              </div>
              <button
                onClick={runSimulation}
                disabled={sim.status === "scanning"}
                style={{ background: C.gold, color: "#1A1200", fontWeight: 600 }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm"
              >
                {sim.status === "scanning" ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                SIMULATE STRATEGY
              </button>
            </div>

            {sim.status === "scanning" && (
              <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5 flex flex-col gap-2">
                <div style={{ color: C.gold, fontSize: 12.5 }} className="flex items-center gap-2 mb-2">
                  <Loader2 size={13} className="animate-spin" /> جاري فحص الأسواق...
                </div>
                {SYMBOL_POOL.map((m) => <div key={m.s} className="skeleton h-8 rounded-lg" />)}
              </div>
            )}

            {sim.status === "done" && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-xl p-3 text-center">
                    <div style={{ fontFamily: FM, fontSize: 20, color: C.text }}>{sim.results.length}</div>
                    <div style={{ color: C.sub, fontSize: 11 }}>Scanned</div>
                  </div>
                  <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-xl p-3 text-center">
                    <div style={{ fontFamily: FM, fontSize: 20, color: C.teal }}>
                      {sim.results.filter((r) => r.matched.some((m) => m.hit)).length}
                    </div>
                    <div style={{ color: C.sub, fontSize: 11 }}>Conditions matched</div>
                  </div>
                  <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-xl p-3 text-center">
                    <div style={{ fontFamily: FM, fontSize: 20, color: C.gold }}>{sim.results.filter((r) => r.triggered).length}</div>
                    <div style={{ color: C.sub, fontSize: 11 }}>Potential signals</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {sim.results.map((r) => (
                    <div key={r.symbol} style={{ background: C.surface, border: `1px solid ${r.triggered ? C.gold : C.border}` }} className="rounded-2xl p-4 fade-in">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span style={{ fontFamily: FD, fontWeight: 600, fontSize: 13.5 }}>{r.symbol}</span>
                          <Sparkline seed={r.symbol.length + r.score} color={r.triggered ? C.gold : C.muted} />
                        </div>
                        <Pill color={r.triggered ? C.gold : C.muted} bg={r.triggered ? C.goldSoft : "transparent"} border={r.triggered ? C.gold : C.border}>
                          {r.triggered ? "TRIGGERED" : "WAITING"}
                        </Pill>
                      </div>
                      {r.error ? (
                        <div style={{ color: C.red, fontSize: 11.5 }} className="mb-2">{r.error}</div>
                      ) : (
                        <>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {r.matched.slice(0, 8).map((m) => (
                              <span key={m.id} style={{ color: m.hit ? C.teal : C.muted, fontSize: 10.5, fontFamily: FM }} className="flex items-center gap-0.5">
                                {m.hit ? <Check size={10} /> : <X size={10} />} {m.label}
                              </span>
                            ))}
                          </div>
                          {r.unsupported?.length > 0 && (
                            <div style={{ color: C.gold, fontSize: 10 }} className="mb-2 flex items-center gap-1">
                              <AlertTriangle size={10} /> {r.unsupported.length} شرط غير مدعوم بعد (لم يُحتسب)
                            </div>
                          )}
                          <div className="flex items-center justify-between" style={{ fontFamily: FM, fontSize: 11 }}>
                            <span style={{ color: C.sub }}>Price {r.price}</span>
                            <span style={{ color: r.score >= minScore ? C.gold : C.sub }}>Score {r.score}</span>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}

            {sim.status === "idle" && (
              <div style={{ background: C.surface, border: `1px dashed ${C.border}`, color: C.muted }} className="rounded-2xl py-14 flex flex-col items-center gap-2 text-sm">
                <Radio size={22} />
                اضغط SIMULATE STRATEGY لفحص حقيقي للأسواق مقابل محرك التحليل
              </div>
            )}
          </div>
        )}

        {/* ============ TAB: TELEGRAM ============ */}
        {activeTab === "telegram" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 14.5 }} className="flex items-center gap-2">
                  <Bot size={16} color={tgConnected ? C.teal : C.muted} /> Telegram Notification
                </div>
                {tgConnected ? (
                  <span
                    style={{ background: C.tealSoft, border: `1px solid ${C.teal}`, color: C.teal }}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px]"
                  >
                    <Link2 size={11} /> متصل
                  </span>
                ) : (
                  <Link
                    to="/profile"
                    style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.sub }}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] hover:opacity-90"
                  >
                    <Link2 size={11} /> اربط حسابك الآن
                  </Link>
                )}
              </div>

              <label style={{ color: C.sub, fontSize: 11 }}>Channel / Chat ID <span style={{ color: C.muted }}>(اختياري — فارغ = يُرسل لحسابك المرتبط)</span></label>
              <input value={tgChannel} onChange={(e) => setTgChannel(e.target.value)} style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.text, fontFamily: FM }} className="w-full rounded-lg px-3 py-2 text-sm mt-1 mb-4" />

              <div style={{ color: C.sub, fontSize: 11 }} className="mb-2">Include in message</div>
              <div className="grid grid-cols-2 gap-2 mb-4">
                {[
                  ["entry", "Entry"], ["sl", "SL"], ["tp", "TP"], ["rr", "RR"],
                  ["confidence", "Confidence"], ["conditions", "Conditions"], ["chart", "Chart Snapshot"],
                ].map(([k, l]) => (
                  <button
                    key={k}
                    onClick={() => setTgFields((p) => ({ ...p, [k]: !p[k] }))}
                    style={{ background: tgFields[k] ? C.goldSoft : "transparent", border: `1px solid ${tgFields[k] ? C.gold : C.border}`, color: tgFields[k] ? C.gold : C.sub }}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11.5px] justify-center"
                  >
                    {tgFields[k] ? <Check size={12} /> : <span style={{ width: 12 }} />} {l}
                  </button>
                ))}
              </div>

              <button
                onClick={sendTestTelegramAlert}
                style={{ background: C.gold, color: "#1A1200", fontWeight: 600 }}
                className="w-full rounded-lg py-2.5 text-sm flex items-center justify-center gap-2"
              >
                <Send size={14} /> Send Test Alert
              </button>
              {!currentStrategyId && (
                <p style={{ color: C.muted, fontSize: 10.5 }} className="text-center mt-2">احفظ الاستراتيجية أولًا لتفعيل الإرسال الحقيقي</p>
              )}
            </div>

            <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5">
              <div style={{ color: C.sub, fontSize: 11 }} className="uppercase tracking-wide mb-2">Message Template Preview</div>
              <pre
                style={{ background: C.bg, border: `1px solid ${C.borderSoft}`, color: C.sub, fontFamily: FM, fontSize: 11.5, whiteSpace: "pre-wrap", lineHeight: 1.75 }}
                className="rounded-lg p-3.5 max-h-[420px] overflow-auto scroll-thin"
              >
{tgTemplate}
              </pre>
            </div>
          </div>
        )}

        {/* ============ TAB: MONITORING ============ */}
        {activeTab === "monitoring" && (
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-5">
            <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5 h-fit">
              <div className="flex items-center gap-2 mb-3">
                <span style={{ width: 8, height: 8, borderRadius: 99, background: monitor.active ? C.teal : C.muted, animation: monitor.active ? "pulseDot 1.4s infinite" : "none" }} />
                <span style={{ fontFamily: FD, fontWeight: 600, fontSize: 14.5 }}>Strategy Status</span>
              </div>
              <Pill color={monitor.active ? C.teal : C.muted} bg={monitor.active ? C.tealSoft : "transparent"} border={monitor.active ? C.teal : C.border} style={{ marginBottom: 14 }}>
                {monitor.active ? "ACTIVE" : "INACTIVE"}
              </Pill>

              <div style={{ fontFamily: FM, fontSize: 12.5, color: C.sub }} className="flex flex-col gap-2 mb-4">
                <div className="flex justify-between"><span>Monitoring</span><span style={{ color: C.text }}>{symbols.length || SYMBOL_POOL.length} Markets</span></div>
                <div className="flex justify-between"><span>Last Scan</span><span style={{ color: C.text }}>{monitor.lastScan || "—"}</span></div>
                <div className="flex justify-between"><span>Check Interval</span><span style={{ color: C.text }}>~5 دقائق</span></div>
              </div>

              <button
                onClick={toggleMonitor}
                disabled={!currentStrategyId}
                style={{ background: monitor.active ? C.redSoft : C.tealSoft, border: `1px solid ${monitor.active ? C.red : C.teal}`, color: monitor.active ? C.red : C.teal, opacity: currentStrategyId ? 1 : 0.5 }}
                className="w-full rounded-lg py-2.5 text-sm flex items-center justify-center gap-2"
              >
                <Power size={14} /> {monitor.active ? "إيقاف المراقبة" : "بدء المراقبة"}
              </button>
              {!currentStrategyId && (
                <p style={{ color: C.muted, fontSize: 10.5 }} className="text-center mt-2">احفظ الاستراتيجية أولًا</p>
              )}
            </div>

            <div style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-5">
              <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 14.5 }} className="mb-3">Live Events</div>
              {monitor.events.length === 0 && (
                <div style={{ color: C.muted }} className="flex flex-col items-center justify-center py-16 text-sm gap-2">
                  <MonitorDot size={22} />
                  ابدأ المراقبة لعرض أحداث الفحص الحقيقية (يفحص الخادم كل 5 دقائق تقريبًا)
                </div>
              )}
              <div className="flex flex-col gap-2 max-h-[420px] overflow-auto scroll-thin">
                {monitor.events.map((e) => (
                  <div key={e.id} style={{ background: C.surfaceHi, border: `1px solid ${C.borderSoft}` }} className="rounded-lg px-3 py-2 flex items-center justify-between fade-in">
                    <span style={{ fontSize: 12.5 }}>{e.msg}</span>
                    <span style={{ color: C.muted, fontFamily: FM, fontSize: 10.5 }}>{e.time}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ============ TAB: SAVED ============ */}
        {activeTab === "saved" && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {savedLoading && (
              <>
                {[0, 1, 2].map((i) => <div key={i} className="skeleton h-40 rounded-2xl" />)}
              </>
            )}
            {!savedLoading && saved.length === 0 && (
              <div style={{ background: C.surface, border: `1px dashed ${C.border}`, color: C.muted }} className="col-span-full rounded-2xl py-14 flex flex-col items-center gap-2 text-sm">
                <FolderOpen size={22} /> لا توجد استراتيجيات محفوظة بعد
              </div>
            )}
            {saved.map((r) => (
              <div key={r.id} style={{ background: C.surface, border: `1px solid ${C.border}` }} className="rounded-2xl p-4 flex flex-col gap-3 fade-in">
                <div className="flex items-start justify-between">
                  <div style={{ fontFamily: FD, fontWeight: 600, fontSize: 14 }}>{r.name}</div>
                  <Pill
                    color={r.status === "ACTIVE" ? C.teal : r.status === "DRAFT" ? C.sub : C.red}
                    bg={r.status === "ACTIVE" ? C.tealSoft : "transparent"}
                    border={r.status === "ACTIVE" ? C.teal : C.border}
                  >
                    {r.status}
                  </Pill>
                </div>
                <div style={{ color: C.sub, fontFamily: FM, fontSize: 11.5 }}>{r.symbol} • {r.timeframe}</div>

                <div className="flex items-center gap-3">
                  <ScoreRing pct={r.confidence} size={46} color={C.gold} />
                  <div style={{ fontSize: 11.5, color: C.sub }} className="flex flex-col gap-0.5">
                    <span>Conditions: <span style={{ color: C.text }}>{r.conditions}</span></span>
                    <span>Schools: <span style={{ color: C.text }}>{r.schools}</span></span>
                    <span>Signals: <span style={{ color: C.text }}>{r.signals}</span></span>
                  </div>
                </div>
                <div style={{ color: C.muted, fontSize: 11 }}>آخر تفعيل: {r.lastTrigger}</div>

                <div style={{ borderTop: `1px solid ${C.borderSoft}` }} className="pt-2.5 flex items-center gap-1 flex-wrap">
                  <IconBtn icon={Edit3} onClick={() => loadStrategy(r)} title="تحرير" color={C.blue} />
                  <IconBtn icon={Copy} onClick={() => duplicateSaved(r)} title="تكرار" />
                  <IconBtn icon={Power} onClick={() => toggleSavedStatus(r)} title="تفعيل/تعطيل" color={r.status === "ACTIVE" ? C.teal : C.muted} />
                  <IconBtn icon={Eye} onClick={() => setViewTarget(r)} title="عرض" />
                  <IconBtn icon={Trash2} onClick={() => setDeleteTarget(r)} title="حذف" color={C.red} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ============ MODALS ============ */}
      {deleteTarget && (
        <Modal title="حذف الاستراتيجية؟" danger onClose={() => setDeleteTarget(null)}>
          <p style={{ color: C.sub, fontSize: 13 }} className="mb-4">
            سيتم حذف «{deleteTarget.name}» نهائيًا من القائمة المحفوظة. هذا الإجراء لا يمكن التراجع عنه.
          </p>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setDeleteTarget(null)} style={{ background: C.surfaceHi, border: `1px solid ${C.border}`, color: C.text }} className="px-3.5 py-2 rounded-lg text-sm">إلغاء</button>
            <button onClick={confirmDelete} style={{ background: C.red, color: "#1A0505" }} className="px-3.5 py-2 rounded-lg text-sm font-medium">حذف نهائي</button>
          </div>
        </Modal>
      )}

      {viewTarget && (
        <Modal title={viewTarget.name} onClose={() => setViewTarget(null)}>
          <div style={{ fontFamily: FM, fontSize: 12, color: C.sub }} className="flex flex-col gap-1.5">
            <div className="flex justify-between"><span>Symbol</span><span style={{ color: C.text }}>{viewTarget.symbol}</span></div>
            <div className="flex justify-between"><span>Timeframe</span><span style={{ color: C.text }}>{viewTarget.timeframe}</span></div>
            <div className="flex justify-between"><span>Conditions</span><span style={{ color: C.text }}>{viewTarget.conditions}</span></div>
            <div className="flex justify-between"><span>Schools</span><span style={{ color: C.text }}>{viewTarget.schools}</span></div>
            <div className="flex justify-between"><span>Confidence</span><span style={{ color: C.gold }}>{viewTarget.confidence}%</span></div>
            <div className="flex justify-between"><span>Status</span><span style={{ color: C.teal }}>{viewTarget.status}</span></div>
            <div className="flex justify-between"><span>Signals</span><span style={{ color: C.text }}>{viewTarget.signals}</span></div>
          </div>
        </Modal>
      )}

      {toast && (
        <div style={{ background: C.surfaceHi, border: `1px solid ${C.gold}`, color: C.text }} className="fixed bottom-5 left-1/2 -translate-x-1/2 px-4 py-2.5 rounded-xl text-sm shadow-2xl fade-in z-50">
          {toast}
        </div>
      )}
    </div>
  );
}
