import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'
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

function AppRoutes() {
  const { user } = useAuth()
  const { lang } = useLang()

  return (
    <Suspense fallback={<PageLoader />}>
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

        {/* Admin */}
        <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
        <Route path="/admin/strategy-builder" element={<AdminRoute><StrategyBuilder /></AdminRoute>} />

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
