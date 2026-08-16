import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { lazy, Suspense, useEffect } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { LangProvider, useLang } from './contexts/LangContext'
import { ThemeProvider } from './contexts/ThemeContext'
import OnboardingTour from './components/OnboardingTour'
import './App.css'

// Eagerly load only the most critical shared components
import Navbar             from './components/Navbar'
import TrialBanner        from './components/TrialBanner'
import TelegramLinkBanner from './components/TelegramLinkBanner'
import EmailVerifyBanner  from './components/EmailVerifyBanner'

// Lazy-load all pages — each becomes its own JS chunk
const Landing        = lazy(() => import('./pages/Landing'))
const Login          = lazy(() => import('./pages/Login'))
const Register       = lazy(() => import('./pages/Register'))
const Pricing        = lazy(() => import('./pages/Pricing'))
const Terms          = lazy(() => import('./pages/Terms'))
const Privacy        = lazy(() => import('./pages/Privacy'))
const Contact        = lazy(() => import('./pages/Contact'))
const About          = lazy(() => import('./pages/About'))
const Vision         = lazy(() => import('./pages/Vision'))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'))
const ReferralProgram = lazy(() => import('./pages/ReferralProgram'))
const BlogList        = lazy(() => import('./pages/BlogList'))
const BlogPost        = lazy(() => import('./pages/BlogPost'))
const Admin          = lazy(() => import('./pages/Admin'))
const StrategyBuilder = lazy(() => import('./pages/StrategyBuilder'))
const Dashboard      = lazy(() => import('./pages/Dashboard'))
const Signals        = lazy(() => import('./pages/Signals'))
const Markets        = lazy(() => import('./pages/Markets'))
const Analytics      = lazy(() => import('./pages/Analytics'))
const Analyses       = lazy(() => import('./pages/Analyses'))
const Profile        = lazy(() => import('./pages/Profile'))
const AffiliatePage  = lazy(() => import('./pages/AffiliatePage'))
const MarketOverview = lazy(() => import('./pages/MarketOverview'))
const Backtesting    = lazy(() => import('./pages/Backtesting'))
const TradeJournal   = lazy(() => import('./pages/TradeJournal'))
const ChatBot        = lazy(() => import('./components/ChatBot'))
const SupportChatWidget = lazy(() => import('./components/SupportChatWidget'))

const PageLoader = () => (
  <div className="min-h-screen bg-gray-950 flex items-center justify-center">
    <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
  </div>
)

// صفحات تحتاج تسجيل دخول
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen bg-gray-950 flex items-center justify-center"><div className="text-gray-400">جاري التحميل...</div></div>
  if (!user)   return <Navigate to="/login" replace />
  return children
}

// صفحات المسؤول فقط
function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user || user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return children
}

// يزامن لغة العرض مع بادئة /en/* بالرابط — مسارات SEO حقيقية، مش
// مجرد تفضيل محفوظ محلياً. لا يلمس اختيار المستخدم المحفوظ إلا وقت
// الخروج من /en/* (يرجّعه للتفضيل الأصلي).
function LangRouteSync() {
  const location = useLocation()
  const { setLangDirect } = useLang()
  useEffect(() => {
    const isEn = location.pathname === '/en' || location.pathname.startsWith('/en/')
    setLangDirect(isEn ? 'en' : (localStorage.getItem('qaffel_lang') || 'ar'))
  }, [location.pathname, setLangDirect])
  return null
}

function AppRoutes() {
  const { user } = useAuth()
  const { lang } = useLang()

  return (
    <Suspense fallback={<PageLoader />}>
      <LangRouteSync />
      <Routes>
        {/* Landing & Public Pages — accessible to all */}
        <Route path="/"                  element={<Landing />} />
        <Route path="/terms"             element={<Terms />} />
        <Route path="/privacy"           element={<Privacy />} />
        <Route path="/contact"           element={<Contact />} />
        <Route path="/about"             element={<About />} />
        <Route path="/vision"            element={<Vision />} />
        <Route path="/forgot-password"   element={<ForgotPassword />} />
        <Route path="/login"             element={user ? <Navigate to="/dashboard" /> : <Login />} />
        <Route path="/register"          element={user ? <Navigate to="/dashboard" /> : <Register />} />
        <Route path="/pricing"           element={<Pricing />} />
        <Route path="/referral"          element={<ReferralProgram />} />
        <Route path="/blog"              element={<BlogList />} />
        <Route path="/blog/:slug"        element={<BlogPost />} />

        {/* English mirrors — نفس الصفحات المذكورة فوق، وهي فعلياً bilingual،
            بادئة /en تفرض عرض المحتوى الإنجليزي (LangRouteSync) بدل الاعتماد
            على تفضيل محفوظ بالمتصفح، عشان قوقل يقدر يفهرس نسخة إنجليزية حقيقية.
            باقي الصفحات العامة (about/contact/vision/terms/privacy) عربي فقط
            بالمحتوى حالياً فما إلها مرآة /en بعد. */}
        <Route path="/en"                element={<Landing />} />
        <Route path="/en/pricing"        element={<Pricing />} />
        <Route path="/en/referral"       element={<ReferralProgram />} />
        <Route path="/en/blog"           element={<BlogList />} />
        <Route path="/en/blog/:slug"     element={<BlogPost />} />

        {/* Admin */}
        <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />

        {/* Strategy Builder — full-bleed terminal UI, any logged-in user (paid actions gated inside) */}
        <Route path="/strategies" element={<ProtectedRoute><StrategyBuilder /></ProtectedRoute>} />

        {/* Protected */}
        <Route path="/*" element={
          <ProtectedRoute>
            <div className="min-h-screen bg-gray-900 text-gray-100" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
              <Navbar />
              <EmailVerifyBanner />
              <TrialBanner />
              <TelegramLinkBanner />
              <OnboardingTour />
              <main className="container mx-auto px-3 sm:px-4 py-5 sm:py-6 max-w-7xl">
                <Routes>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/signals"   element={<Signals />} />
                  <Route path="/markets"   element={<Markets />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/analyses"  element={<Analyses />} />
                  <Route path="/profile"   element={<Profile />} />
                  <Route path="/affiliate"       element={<AffiliatePage />} />
                  <Route path="/market-overview" element={<MarketOverview />} />
                  <Route path="/backtesting"     element={<Backtesting />} />
                  <Route path="/journal"         element={<TradeJournal />} />
                </Routes>
              </main>
              <ChatBot />
              <SupportChatWidget />
            </div>
          </ProtectedRoute>
        } />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <LangProvider>
        <AuthProvider>
          <Router>
            <AppRoutes />
          </Router>
        </AuthProvider>
      </LangProvider>
    </ThemeProvider>
  )
}
