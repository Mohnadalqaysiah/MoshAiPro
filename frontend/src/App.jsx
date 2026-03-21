import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Dashboard  from './pages/Dashboard'
import Signals    from './pages/Signals'
import Markets    from './pages/Markets'
import Analytics  from './pages/Analytics'
import Login      from './pages/Login'
import Register   from './pages/Register'
import Pricing    from './pages/Pricing'
import Admin      from './pages/Admin'
import Navbar     from './components/Navbar'
import ChatBot    from './components/ChatBot'
import TrialBanner from './components/TrialBanner'
import './App.css'

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

  return (
    <Routes>
      {/* Public */}
      <Route path="/login"    element={user ? <Navigate to="/dashboard" /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/dashboard" /> : <Register />} />
      <Route path="/pricing"  element={<Pricing />} />

      {/* Admin */}
      <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />

      {/* Protected */}
      <Route path="/*" element={
        <ProtectedRoute>
          <div className="min-h-screen bg-gray-900 text-gray-100">
            <Navbar />
            <TrialBanner />
            <main className="container mx-auto px-4 py-6">
              <Routes>
                <Route path="/"          element={<Dashboard />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/signals"   element={<Signals />} />
                <Route path="/markets"   element={<Markets />} />
                <Route path="/analytics" element={<Analytics />} />
              </Routes>
            </main>
            <ChatBot />
          </div>
        </ProtectedRoute>
      } />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  )
}
