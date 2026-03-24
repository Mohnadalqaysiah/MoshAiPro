import { useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { Mail, Send, CheckCircle, AlertCircle, Clock } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Contact() {
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
      setError('حدث خطأ، يرجى المحاولة لاحقاً أو راسلنا مباشرة على support@qaffel.com')
    } finally { setLoading(false) }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-950 text-gray-100">
      {/* Navbar */}
      <nav className="border-b border-gray-800 bg-gray-950/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-sm">Q</div>
            <span className="font-bold text-lg">Qaffel <span className="text-blue-400">AI</span></span>
          </Link>
          <div className="flex gap-4 text-sm">
            <Link to="/login"    className="text-gray-400 hover:text-white transition">تسجيل الدخول</Link>
            <Link to="/register" className="bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-lg transition">ابدأ مجاناً</Link>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">تواصل معنا</h1>
        <p className="text-gray-400 mb-12">نحن هنا للمساعدة. راسلنا وسنرد خلال 24 ساعة.</p>

        <div className="grid md:grid-cols-2 gap-12">
          {/* Contact Info */}
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-6">وسائل التواصل</h2>

            <a href="mailto:support@qaffel.com"
               className="flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-blue-500 transition group">
              <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center group-hover:bg-blue-600/30 transition">
                <Mail className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">البريد الإلكتروني</p>
                <p className="font-medium">support@qaffel.com</p>
              </div>
            </a>

            <div className="p-4 bg-blue-950/30 border border-blue-800/30 rounded-xl">
              <p className="text-blue-300 text-sm font-medium mb-2 flex items-center gap-2">
                <Clock size={14}/> ساعات الدعم
              </p>
              <p className="text-gray-400 text-sm">الأحد – الخميس: 9 صباحاً – 8 مساءً (GMT+3)</p>
              <p className="text-gray-400 text-sm mt-1">الجمعة – السبت: دعم محدود عبر الإيميل</p>
            </div>

            <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl">
              <p className="text-gray-300 text-sm font-medium mb-2">وقت الاستجابة</p>
              <p className="text-gray-400 text-sm">نرد على جميع الرسائل خلال <strong className="text-white">24 ساعة</strong> في أيام العمل.</p>
            </div>
          </div>

          {/* Contact Form */}
          <div>
            {sent ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center py-8">
                <CheckCircle className="w-16 h-16 text-green-400" />
                <h3 className="text-xl font-bold">تم إرسال رسالتك!</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  وصلتنا رسالتك بنجاح. سنرد عليك على <span className="text-blue-400">{form.email}</span> خلال 24 ساعة.
                </p>
                <button onClick={() => { setSent(false); setForm({ name: '', email: '', subject: '', message: '' }) }}
                        className="mt-2 text-blue-400 hover:underline text-sm">
                  إرسال رسالة أخرى
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">الاسم</label>
                    <input type="text" required value={form.name}
                           onChange={e => setForm(p => ({...p, name: e.target.value}))}
                           className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition"
                           placeholder="اسمك الكريم" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">البريد الإلكتروني</label>
                    <input type="email" required value={form.email}
                           onChange={e => setForm(p => ({...p, email: e.target.value}))}
                           className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition"
                           placeholder="email@example.com" dir="ltr" />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">الموضوع</label>
                  <select value={form.subject}
                          onChange={e => setForm(p => ({...p, subject: e.target.value}))}
                          className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition">
                    <option value="">اختر الموضوع...</option>
                    <option value="دعم تقني">دعم تقني</option>
                    <option value="الفوترة والاشتراكات">الفوترة والاشتراكات</option>
                    <option value="استفسار عن التوصيات">استفسار عن التوصيات</option>
                    <option value="شراكة تجارية">شراكة تجارية</option>
                    <option value="أخرى">أخرى</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">الرسالة</label>
                  <textarea required rows={5} value={form.message}
                             onChange={e => setForm(p => ({...p, message: e.target.value}))}
                             className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition resize-none"
                             placeholder="اكتب رسالتك هنا..." />
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
                    : <><Send className="w-4 h-4" /> إرسال الرسالة</>
                  }
                </button>
              </form>
            )}
          </div>
        </div>
      </main>

      <footer className="border-t border-gray-800 py-8 text-center text-gray-500 text-sm">
        <p>© 2026 Qaffel AI · <Link to="/terms" className="hover:text-gray-300">الشروط والأحكام</Link> · <Link to="/privacy" className="hover:text-gray-300">سياسة الخصوصية</Link></p>
      </footer>
    </div>
  )
}
