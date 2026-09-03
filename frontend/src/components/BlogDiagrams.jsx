/**
 * BlogDiagrams — رسوم توضيحية SVG مضمّنة لمفاهيم ICT/SMC (Order Block،
 * FVG، BOS/CHoCH). SVG مباشر بدل ملفات صور — صفر وزن شبكي إضافي (يضل
 * جزء من الـJS chunk الموجود أصلاً)، وحاد الدقة على أي كثافة شاشة.
 * المصطلحات (OB, FVG, BOS, CHoCH) تُستخدم بالإنجليزية بالنسختين
 * العربية والإنجليزية أصلاً بالمقالات — الرسم محايد اللغة، والتسمية
 * التوضيحية (caption) تحت كل رسم هي يلي تُترجم.
 */
function Candle({ x, open, close, high, low, bullish, highlight }) {
  const bodyTop = Math.min(open, close)
  const bodyBottom = Math.max(open, close)
  const color = bullish ? '#22c55e' : '#ef4444'
  return (
    <g>
      <line x1={x} x2={x} y1={high} y2={low} stroke={color} strokeWidth="1.5" />
      <rect
        x={x - 7} y={bodyTop} width="14" height={Math.max(bodyBottom - bodyTop, 2)}
        fill={color} rx="1.5"
        opacity={highlight ? 1 : 0.85}
      />
      {highlight && (
        <rect x={x - 10} y={bodyTop - 3} width="20" height={bodyBottom - bodyTop + 6}
          fill="none" stroke="#fbbf24" strokeWidth="1.5" strokeDasharray="3 2" rx="3" />
      )}
    </g>
  )
}

function DiagramFrame({ children, caption }) {
  return (
    <figure className="my-6 bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <svg viewBox="0 0 320 160" className="w-full h-auto" role="img" aria-label={caption}>
        {children}
      </svg>
      <figcaption className="text-center text-xs text-gray-500 mt-2">{caption}</figcaption>
    </figure>
  )
}

// ── Order Block: شمعة هبوطية (OB) قبل اندفاع صعودي، ثم رجوع واختبار ──
export function OrderBlockDiagram({ caption }) {
  return (
    <DiagramFrame caption={caption}>
      <line x1="10" y1="140" x2="310" y2="140" stroke="#374151" strokeWidth="1" />
      <Candle x={40}  open={90}  close={100} high={85}  low={105} bullish={false} />
      <Candle x={65}  open={95}  close={105} high={90}  low={110} bullish={false} highlight />
      <Candle x={95}  open={95}  close={70}  high={65}  low={100} bullish={true} />
      <Candle x={120} open={70}  close={45}  high={40}  low={75}  bullish={true} />
      <Candle x={145} open={45}  close={25}  high={20}  low={50}  bullish={true} />
      {/* السعر يرجع لاختبار الـOB */}
      <path d="M 165 25 C 220 30, 260 70, 260 100" fill="none" stroke="#60a5fa" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arrow)" />
      <Candle x={280} open={100} close={90}  high={85}  low={105} bullish={true} />
      <text x="65" y="130" textAnchor="middle" fontSize="10" fill="#fbbf24">Order Block</text>
      <text x="260" y="118" textAnchor="middle" fontSize="9" fill="#60a5fa">Retest</text>
      <defs>
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#60a5fa" />
        </marker>
      </defs>
    </DiagramFrame>
  )
}

// ── FVG: 3 شموع، فجوة بين High الأولى وLow الثالثة ──
export function FVGDiagram({ caption }) {
  return (
    <DiagramFrame caption={caption}>
      <line x1="10" y1="140" x2="310" y2="140" stroke="#374151" strokeWidth="1" />
      <Candle x={90}  open={110} close={90}  high={85}  low={115} bullish={true} />
      <Candle x={130} open={90}  close={55}  high={50}  low={95}  bullish={true} />
      <Candle x={170} open={55}  close={35}  high={30}  low={60}  bullish={true} />
      {/* الفجوة: بين high الشمعة الأولى (85) وlow الشمعة الثالثة (60) */}
      <rect x={70} y={60} width={120} height={25} fill="#fbbf24" opacity="0.18" />
      <rect x={70} y={60} width={120} height={25} fill="none" stroke="#fbbf24" strokeWidth="1" strokeDasharray="3 2" />
      <text x="130" y="55" textAnchor="middle" fontSize="10" fill="#fbbf24">FVG</text>
      {/* رجوع لملء الفجوة */}
      <path d="M 200 35 C 240 45, 250 65, 240 75" fill="none" stroke="#60a5fa" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arrow2)" />
      <Candle x={250} open={75} close={65} high={60} low={80} bullish={true} />
      <defs>
        <marker id="arrow2" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#60a5fa" />
        </marker>
      </defs>
    </DiagramFrame>
  )
}

// ── BOS/CHoCH: هيكل صاعد (HH/HL) ثم كسر هابط = CHoCH ──
export function BosChochDiagram({ caption }) {
  const pts = [
    [20, 110], [55, 60], [90, 80], [125, 35], [160, 65], [195, 25],
  ]
  return (
    <DiagramFrame caption={caption}>
      <line x1="10" y1="140" x2="310" y2="140" stroke="#374151" strokeWidth="1" />
      <polyline points={pts.map(p => p.join(',')).join(' ')} fill="none" stroke="#22c55e" strokeWidth="2" />
      {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="2.5" fill="#22c55e" />)}
      <text x="55" y="52" fontSize="8" fill="#9ca3af">HH</text>
      <text x="90" y="95" fontSize="8" fill="#9ca3af">HL</text>
      <text x="125" y="27" fontSize="8" fill="#9ca3af">HH</text>
      {/* BOS label على أول كسر بنفس الاتجاه */}
      <text x="125" y="15" textAnchor="middle" fontSize="9" fill="#22c55e" fontWeight="bold">BOS</text>
      {/* كسر الاتجاه — CHoCH */}
      <polyline points="195,25 230,100 265,80 300,130" fill="none" stroke="#ef4444" strokeWidth="2" strokeDasharray="5 3" />
      <circle cx="230" cy="100" r="3" fill="#ef4444" />
      <text x="230" y="118" textAnchor="middle" fontSize="9" fill="#ef4444" fontWeight="bold">CHoCH</text>
    </DiagramFrame>
  )
}
