/**
 * LegalDoc (2026-10-17) — قالب الشروط والخصوصية بالهوية الجديدة: عنوان + فهرس جانبي ثابت + أقسام مرقّمة.
 * العناوين بصيغة "1. العنوان" — الرقم يُفصل ويُعرض كشارة.
 */
import { Link } from 'react-router-dom'

const split = (h) => {
  const m = /^(\d+)\.\s*(.*)$/.exec(h)
  return m ? [m[1], m[2]] : [null, h]
}

export default function LegalDoc({ isAr, eyebrow, h1, updated, sections, contactLabel, contactLink }) {
  const all = [...sections, { h: isAr ? `${sections.length + 1}. التواصل` : `${sections.length + 1}. Contact`, contact: true }]
  return (
    <>
      <section className="qp-hero">
        <div className="qp-wrap qp-narrow">
          <span className="qp-eyebrow">{eyebrow}</span>
          <h1 className="qp-h1">{h1}</h1>
          <p className="qp-lead" style={{ fontSize: 14, color: 'var(--faint)' }}>{updated}</p>
        </div>
      </section>

      <div className="qp-wrap" style={{ paddingBottom: 'clamp(56px,8vw,96px)' }}>
        <div className="qp-doc">
          <nav className="qp-toc" aria-label={isAr ? 'المحتويات' : 'Contents'}>
            <b>{isAr ? 'المحتويات' : 'Contents'}</b>
            {all.map((s, i) => {
              const [n, title] = split(s.h)
              return <a key={i} href={`#s${i + 1}`}><span>{n || i + 1}</span>{title}</a>
            })}
          </nav>

          <article className="qp-art">
            {all.map((s, i) => {
              const [n, title] = split(s.h)
              return (
                <section key={i} id={`s${i + 1}`} className="qp-card">
                  <h2><span className="n">{n || i + 1}</span>{title}</h2>
                  {s.contact ? (
                    <p>{contactLabel}{' '}<Link to={isAr ? '/contact' : '/en/contact'} className="qp-link">{contactLink}</Link>
                      {' · '}<a href="mailto:support@qaffel.com" className="qp-link" dir="ltr">support@qaffel.com</a></p>
                  ) : (<>
                    {s.p && <p>{s.p}</p>}
                    {s.ul && <ul>{s.ul.map((li, j) => <li key={j}>{li}</li>)}</ul>}
                  </>)}
                </section>
              )
            })}
          </article>
        </div>
      </div>
    </>
  )
}
