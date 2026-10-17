/**
 * AuthShell (2026-10-17) — إطار صفحات الدخول والتسجيل واستعادة كلمة المرور بالهوية الجديدة.
 * شريط علوي (الشعار + اللغة + الرئيسية) وعمودان على الشاشات الكبيرة: لوحة تعريف + بطاقة النموذج.
 * داخل .qpub فتتحوّل ألوان النموذج الموجود (رمادي/أزرق) تلقائياً — منطق الصفحات لم يُلمس.
 */
import { Link } from 'react-router-dom'
import '../styles/landing-v2.css'
import '../styles/public-v2.css'

const BrandMark = () => (
  <span className="qauth-mark"><svg width="22" height="22" viewBox="0 0 36 36" fill="none" aria-hidden="true"><circle cx="17" cy="17" r="11.5" stroke="#DDE5F2" strokeWidth="3.2" /><path d="M22 22 L31 31" stroke="#3CF2C0" strokeWidth="3.2" strokeLinecap="round" /></svg></span>
)

export default function AuthShell({ isAr, onToggleLang, eyebrow, title, titleGrad, lead, points = [], children }) {
  return (
    <div className="qpub qauth" dir={isAr ? 'rtl' : 'ltr'}>
      <header className="qauth-top">
        <Link to={isAr ? '/' : '/en'} className="qauth-brand" aria-label="Qaffel AI"><BrandMark /><span dir="ltr">Qaffel <span className="qp-grad">AI</span></span></Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Link to={isAr ? '/' : '/en'} className="qauth-home">{isAr ? 'الرئيسية' : 'Home'}</Link>
          {onToggleLang && (
            <button type="button" onClick={onToggleLang} className="qauth-lang" aria-label={isAr ? 'English' : 'العربية'}>{isAr ? 'EN' : 'ع'}</button>
          )}
        </div>
      </header>

      <div className="qauth-grid">
        <aside className="qauth-side">
          {eyebrow && <span className="qp-eyebrow">{eyebrow}</span>}
          <h1 className="qp-h1" style={{ fontSize: 'clamp(30px,3.6vw,46px)' }}>{title}{titleGrad && <><br /><span className="qp-grad">{titleGrad}</span></>}</h1>
          {lead && <p className="qp-lead" style={{ marginInline: 0 }}>{lead}</p>}
          {points.length > 0 && (
            <ul className="qp-check" style={{ marginTop: 26 }}>
              {points.map((pt) => <li key={pt} style={{ fontSize: 15, color: '#C9D5EA' }}>{pt}</li>)}
            </ul>
          )}
        </aside>
        <main className="qauth-main">{children}</main>
      </div>
    </div>
  )
}
