import { useState } from 'react'
import axios from 'axios'
import { Mail, Send, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const T = {
  ar: {
    h1: 'تواصل معنا',
    sub: 'نحن هنا للمساعدة. راسلنا وسنرد خلال 24 ساعة.',
    infoTitle: 'وسائل التواصل',
    emailLabel: 'البريد الإلكتروني',
    hoursTitle: 'ساعات الدعم',
    hours1: 'الأحد – الخميس: 9 صباحاً – 8 مساءً (GMT+3)',
    hours2: 'الجمعة – السبت: دعم محدود عبر الإيميل',
    responseTitle: 'وقت الاستجابة',
    responseBody: (email) => <>نرد على جميع الرسائل خلال <strong className="text-white">24 ساعة</strong> في أيام العمل.</>,
    sentTitle: 'تم إرسال رسالتك!',
    sentBody: (email) => <>وصلتنا رسالتك بنجاح. سنرد عليك على <span className="text-blue-400">{email}</span> خلال 24 ساعة.</>,
    sendAnother: 'إرسال رسالة أخرى',
    name: 'الاسم',
    namePh: 'اسمك الكريم',
    subject: 'الموضوع',
    subjectChoose: 'اختر الموضوع...',
    subjects: ['دعم تقني', 'الفوترة والاشتراكات', 'استفسار عن التوصيات', 'شراكة تجارية', 'أخرى'],
    message: 'الرسالة',
    messagePh: 'اكتب رسالتك هنا...',
    send: 'إرسال الرسالة',
    genericError: 'حدث خطأ، يرجى المحاولة لاحقاً أو راسلنا مباشرة على support@qaffel.com',
  },
  en: {
    h1: 'Contact Us',
    sub: "We're here to help. Reach out and we'll reply within 24 hours.",
    infoTitle: 'Ways to Reach Us',
    emailLabel: 'Email',
    hoursTitle: 'Support Hours',
    hours1: 'Sunday – Thursday: 9 AM – 8 PM (GMT+3)',
    hours2: 'Friday – Saturday: Limited email support',
    responseTitle: 'Response Time',
    responseBody: () => <>We reply to all messages within <strong className="text-white">24 hours</strong> on business days.</>,
    sentTitle: 'Your message was sent!',
    sentBody: (email) => <>We received your message. We'll reply to <span className="text-blue-400">{email}</span> within 24 hours.</>,
    sendAnother: 'Send another message',
    name: 'Name',
    namePh: 'Your name',
    subject: 'Subject',
    subjectChoose: 'Choose a subject...',
    subjects: ['Technical Support', 'Billing & Subscriptions', 'Signal Inquiry', 'Business Partnership', 'Other'],
    message: 'Message',
    messagePh: 'Type your message here...',
    send: 'Send Message',
    genericError: 'Something went wrong, please try again later or email us directly at support@qaffel.com',
  },
}

export default function Contact() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']

  useSEO({
    title: isAr ? 'تواصل معنا | Qaffel AI' : 'Contact Us | Qaffel AI',
    description: isAr
      ? 'تواصل مع فريق Qaffel AI للدعم الفني أو الاستفسارات عن منصة إشارات التداول.'
      : 'Get in touch with the Qaffel AI team for technical support or questions about the trading signals platform.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'تواصل معنا' : 'Contact Us', path: isAr ? '/contact' : '/en/contact' },
  ])
  const [form, setForm]     = useState({ name: '', email: '', subject: '', message: '' })
  const [sent, setSent]     = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await axios.post(`${API}/api/v1/auth/contact`, form)
      setSent(true)
    } catch {
      setError(tx.genericError)
    } finally { setLoading(false) }
  }

  return (
    <PublicLayout>

      <section className="qp-hero">
        <div className="qp-wrap qp-narrow">
          <span className="qp-eyebrow">{isAr ? 'نحن هنا لمساعدتك' : "We're here to help"}</span>
          <h1 className="qp-h1">{tx.h1}</h1>
          <p className="qp-lead">{tx.sub}</p>
        </div>
      </section>

      <div className="qp-wrap" style={{ paddingBottom: 'clamp(56px,8vw,96px)' }}>
        <div className="qp-grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,340px),1fr))', alignItems: 'start' }}>
          {/* Contact Info */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <h2 className="qp-h3" style={{ fontSize: 20, marginBottom: 4 }}>{tx.infoTitle}</h2>

            <a href="mailto:support@qaffel.com" className="qp-card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span className="qp-ico lg"><Mail size={22} /></span>
              <span>
                <span className="qp-faint" style={{ display: 'block', fontSize: 13 }}>{tx.emailLabel}</span>
                <span className="qp-mono" style={{ color: '#fff', fontWeight: 700 }}>support@qaffel.com</span>
              </span>
            </a>

            <a href="https://t.me/Qaffelbot" target="_blank" rel="noreferrer" className="qp-card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span className="qp-ico lg sky"><Send size={20} /></span>
              <span>
                <span className="qp-faint" style={{ display: 'block', fontSize: 13 }}>Telegram</span>
                <span className="qp-mono" style={{ color: '#fff', fontWeight: 700 }}>@Qaffelbot</span>
              </span>
            </a>

            <div className="qp-card qp-goldline">
              <p style={{ color: 'var(--gold)', fontWeight: 700, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Clock size={15} /> {tx.hoursTitle}
              </p>
              <p className="qp-sub" style={{ fontSize: 14 }}>{tx.hours1}</p>
              <p className="qp-sub" style={{ fontSize: 14, marginTop: 4 }}>{tx.hours2}</p>
            </div>

            <div className="qp-card">
              <p style={{ color: '#fff', fontWeight: 700, fontSize: 14, marginBottom: 6 }}>{tx.responseTitle}</p>
              <p className="qp-sub" style={{ fontSize: 14 }}>{tx.responseBody()}</p>
            </div>
          </div>

          {/* Contact Form */}
          <div className="qp-card" style={{ padding: 'clamp(20px,3vw,32px)' }}>
            {sent ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, textAlign: 'center', paddingBlock: 32 }}>
                <span className="qp-ico lg" style={{ width: 64, height: 64, borderRadius: 20 }}><CheckCircle size={32} /></span>
                <h3 className="qp-h3" style={{ fontSize: 22 }}>{tx.sentTitle}</h3>
                <p className="qp-sub" style={{ fontSize: 14 }}>{tx.sentBody(form.email)}</p>
                <button type="button" onClick={() => { setSent(false); setForm({ name: '', email: '', subject: '', message: '' }) }}
                        className="qp-link" style={{ fontSize: 14, background: 'none', border: 0, cursor: 'pointer' }}>
                  {tx.sendAnother}
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="qp-grid qp-g2" style={{ gap: 14 }}>
                  <div className="qp-field">
                    <label htmlFor="c-name">{tx.name}</label>
                    <input id="c-name" type="text" required value={form.name}
                           onChange={e => setForm(p => ({...p, name: e.target.value}))}
                           className="qp-input" placeholder={tx.namePh} />
                  </div>
                  <div className="qp-field">
                    <label htmlFor="c-email">{tx.emailLabel}</label>
                    <input id="c-email" type="email" required value={form.email}
                           onChange={e => setForm(p => ({...p, email: e.target.value}))}
                           className="qp-input" placeholder="email@example.com" dir="ltr" />
                  </div>
                </div>

                <div className="qp-field">
                  <label htmlFor="c-subject">{tx.subject}</label>
                  <select id="c-subject" value={form.subject}
                          onChange={e => setForm(p => ({...p, subject: e.target.value}))}
                          className="qp-input">
                    <option value="">{tx.subjectChoose}</option>
                    {tx.subjects.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>

                <div className="qp-field">
                  <label htmlFor="c-msg">{tx.message}</label>
                  <textarea id="c-msg" required rows={5} value={form.message}
                             onChange={e => setForm(p => ({...p, message: e.target.value}))}
                             className="qp-input" placeholder={tx.messagePh} />
                </div>

                {error && (
                  <p style={{ color: 'var(--coral)', fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <AlertCircle size={14}/> {error}
                  </p>
                )}

                <button type="submit" disabled={loading} className="qp-btn qp-mint" style={{ width: '100%' }}>
                  {loading
                    ? <span className="animate-spin" style={{ width: 20, height: 20, border: '2px solid var(--mint-ink)', borderTopColor: 'transparent', borderRadius: 999 }} />
                    : <><Send size={16} /> {tx.send}</>
                  }
                </button>
              </form>
            )}
          </div>
        </div>
      </div>

    </PublicLayout>
  )
}
