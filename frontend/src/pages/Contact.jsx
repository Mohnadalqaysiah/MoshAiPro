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

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">{tx.h1}</h1>
        <p className="text-gray-400 mb-12">{tx.sub}</p>

        <div className="grid md:grid-cols-2 gap-12">
          {/* Contact Info */}
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-6">{tx.infoTitle}</h2>

            <a href="mailto:support@qaffel.com"
               className="flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-blue-500 transition group">
              <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center group-hover:bg-blue-600/30 transition">
                <Mail className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">{tx.emailLabel}</p>
                <p className="font-medium">support@qaffel.com</p>
              </div>
            </a>

            <div className="p-4 bg-blue-950/30 border border-blue-800/30 rounded-xl">
              <p className="text-blue-300 text-sm font-medium mb-2 flex items-center gap-2">
                <Clock size={14}/> {tx.hoursTitle}
              </p>
              <p className="text-gray-400 text-sm">{tx.hours1}</p>
              <p className="text-gray-400 text-sm mt-1">{tx.hours2}</p>
            </div>

            <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
              <p className="text-gray-300 text-sm font-medium mb-2">{tx.responseTitle}</p>
              <p className="text-gray-400 text-sm">{tx.responseBody()}</p>
            </div>
          </div>

          {/* Contact Form */}
          <div>
            {sent ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center py-8">
                <CheckCircle className="w-16 h-16 text-green-400" />
                <h3 className="text-xl font-bold">{tx.sentTitle}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  {tx.sentBody(form.email)}
                </p>
                <button onClick={() => { setSent(false); setForm({ name: '', email: '', subject: '', message: '' }) }}
                        className="mt-2 text-blue-400 hover:underline text-sm">
                  {tx.sendAnother}
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">{tx.name}</label>
                    <input type="text" required value={form.name}
                           onChange={e => setForm(p => ({...p, name: e.target.value}))}
                           className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition"
                           placeholder={tx.namePh} />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">{tx.emailLabel}</label>
                    <input type="email" required value={form.email}
                           onChange={e => setForm(p => ({...p, email: e.target.value}))}
                           className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition"
                           placeholder="email@example.com" dir="ltr" />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">{tx.subject}</label>
                  <select value={form.subject}
                          onChange={e => setForm(p => ({...p, subject: e.target.value}))}
                          className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition">
                    <option value="">{tx.subjectChoose}</option>
                    {tx.subjects.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">{tx.message}</label>
                  <textarea required rows={5} value={form.message}
                             onChange={e => setForm(p => ({...p, message: e.target.value}))}
                             className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition resize-none"
                             placeholder={tx.messagePh} />
                </div>

                {error && (
                  <p className="text-red-400 text-sm flex items-center gap-1">
                    <AlertCircle size={13}/> {error}
                  </p>
                )}

                <button type="submit" disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 py-3 rounded-xl font-medium flex items-center justify-center gap-2 transition">
                  {loading
                    ? <span className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                    : <><Send className="w-4 h-4" /> {tx.send}</>
                  }
                </button>
              </form>
            )}
          </div>
        </div>
      </main>

    </PublicLayout>
  )
}
