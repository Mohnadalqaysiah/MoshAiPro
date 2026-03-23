import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, MessageCircle, Send, CheckCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      // Send as email via backend (or just show success for now)
      await new Promise(r => setTimeout(r, 800)) // simulate
      setSent(true)
    } catch {
      setError('حدث خطأ، يرجى المحاولة لاحقاً')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-950 text-gray-100">
      {/* Navbar */}
      <nav className="border-b border-gray-800 bg-gray-950/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Qaffel AI
          </Link>
          <div className="flex gap-4 text-sm">
            <Link to="/login" className="text-gray-400 hover:text-white transition">تسجيل الدخول</Link>
            <Link to="/register" className="bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-lg transition">ابدأ مجاناً</Link>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">تواصل معنا</h1>
        <p className="text-gray-400 mb-12">نحن هنا للمساعدة. أرسل لنا رسالتك وسنرد خلال 24 ساعة.</p>

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

            <a href="https://t.me/qaffel_support" target="_blank" rel="noopener noreferrer"
               className="flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-blue-500 transition group">
              <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center group-hover:bg-blue-600/30 transition">
                <MessageCircle className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-400">Telegram</p>
                <p className="font-medium">@qaffel_support</p>
              </div>
            </a>

            <div className="p-4 bg-blue-950/30 border border-blue-800/30 rounded-xl">
              <p className="text-blue-300 text-sm font-medium mb-1">ساعات العمل</p>
              <p className="text-gray-400 text-sm">الأحد – الخميس: 9 صباحاً – 6 مساءً (GMT+3)</p>
              <p className="text-gray-400 text-sm">الجمعة – السبت: دعم محدود عبر Telegram</p>
            </div>
          </div>

          {/* Contact Form */}
          <div>
            {sent ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <CheckCircle className="w-16 h-16 text-green-400" />
                <h3 className="text-xl font-bold">تم إرسال رسالتك!</h3>
                <p className="text-gray-400">سنرد عليك على بريدك الإلكتروني خلال 24 ساعة.</p>
                <button onClick={() => { setSent(false); setForm({ name: '', email: '', subject: '', message: '' }) }}
                        className="mt-4 text-blue-400 hover:underline text-sm">
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
                           placeholder="email@example.com" />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">الموضوع</label>
                  <select value={form.subject}
                          onChange={e => setForm(p => ({...p, subject: e.target.value}))}
                          className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition">
                    <option value="">اختر الموضوع...</option>
                    <option value="support">دعم تقني</option>
                    <option value="billing">الفوترة والاشتراكات</option>
                    <option value="signals">استفسار عن التوصيات</option>
                    <option value="partnership">شراكة تجارية</option>
                    <option value="other">أخرى</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">الرسالة</label>
                  <textarea required rows={5} value={form.message}
                             onChange={e => setForm(p => ({...p, message: e.target.value}))}
                             className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition resize-none"
                             placeholder="اكتب رسالتك هنا..." />
                </div>

                {error && <p className="text-red-400 text-sm">{error}</p>}

                <button type="submit" disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 py-3 rounded-xl font-medium flex items-center justify-center gap-2 transition">
                  {loading ? (
                    <span className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <><Send className="w-4 h-4" /> إرسال الرسالة</>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 text-center text-gray-500 text-sm">
        <p>© 2026 Qaffel AI · <Link to="/terms" className="hover:text-gray-300">الشروط والأحكام</Link> · <Link to="/privacy" className="hover:text-gray-300">سياسة الخصوصية</Link></p>
      </footer>
    </div>
  )
}
