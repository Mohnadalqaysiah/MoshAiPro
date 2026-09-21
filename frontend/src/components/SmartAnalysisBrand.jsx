import { useId } from 'react'

// اسم ودجت الشات الموحّد — تغييره هنا يكفي (الواجهة فقط؛ الخلفية لها نسختها بـchat_agent.py/public_chat.py)
export const BRAND = {
  ar: { name: 'تحليل ذكي', short: 'تحليل ذكي', tagline: 'محلّل الأسواق بالذكاء الاصطناعي' },
  en: { name: 'Smart Analysis', short: 'Smart Analysis', tagline: 'AI-powered market analyst' },
}

// شبكة عصبية مصغّرة: عقد متصلة ونبض يمرّ عبرها — تعبّر عن "التفكير" لا عن "الدردشة".
// active=true يسرّع النبض (أثناء انتظار الرد).
export function NeuralOrb({ size = 28, active = false, className = '' }) {
  const uid = useId().replace(/:/g, '')
  const nodes = [
    [16, 6], [7, 12], [25, 12], [11, 22], [21, 22], [16, 16],
  ]
  const links = [[0, 1], [0, 2], [1, 3], [2, 4], [3, 4], [5, 0], [5, 1], [5, 2], [5, 3], [5, 4]]
  return (
    <svg
      width={size} height={size} viewBox="0 0 32 32" fill="none"
      className={className} aria-hidden="true"
    >
      <defs>
        <radialGradient id={`o${uid}`} cx="50%" cy="40%" r="65%">
          <stop offset="0%" stopColor="#67E8F9" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#6366F1" stopOpacity="0.05" />
        </radialGradient>
        <linearGradient id={`l${uid}`} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#22D3EE" />
          <stop offset="1" stopColor="#A78BFA" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="15" fill={`url(#o${uid})`} stroke={`url(#l${uid})`} strokeOpacity="0.55" />
      {links.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]}
          stroke={`url(#l${uid})`} strokeWidth="0.9" strokeOpacity="0.7"
          className="sa-link"
          style={{ animationDelay: `${(i % 5) * 0.25}s`, animationDuration: active ? '0.7s' : '2.4s' }}
        />
      ))}
      {nodes.map(([x, y], i) => (
        <circle
          key={i} cx={x} cy={y} r={i === 5 ? 2.4 : 1.7}
          fill={i === 5 ? '#FDE68A' : '#E0F2FE'}
          className="sa-node"
          style={{ animationDelay: `${i * 0.3}s`, animationDuration: active ? '0.9s' : '2.8s' }}
        />
      ))}
    </svg>
  )
}

// أنماط الحركة تُحقن مرة واحدة من الودجتين
export const BRAND_CSS = `
  @keyframes saPulse { 0%,100% { opacity:.35 } 50% { opacity:1 } }
  @keyframes saNode  { 0%,100% { transform:scale(1) } 50% { transform:scale(1.35) } }
  @keyframes saScan  { 0% { transform:translateX(-100%) } 100% { transform:translateX(100%) } }
  @keyframes saRise  { from { opacity:0; transform:translateY(8px) scale(.98) } to { opacity:1; transform:none } }
  .sa-link { animation: saPulse 2.4s ease-in-out infinite }
  .sa-node { animation: saNode 2.8s ease-in-out infinite; transform-box: fill-box; transform-origin: center }
  .sa-panel { animation: saRise .22s ease both }
  .sa-scan::after { content:''; position:absolute; inset:0; background:linear-gradient(90deg,transparent,rgba(103,232,249,.18),transparent); animation: saScan 2.2s linear infinite }
  @media (prefers-reduced-motion: reduce) {
    .sa-link,.sa-node,.sa-scan::after,.sa-panel { animation: none !important }
  }
`
