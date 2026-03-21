import { Link, useLocation, useNavigate } from 'react-router-dom'
import { TrendingUp, BarChart2, Activity, Zap, LogOut, Shield, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const links = [
    { path: '/dashboard', label: 'لوحة التحكم', icon: <Activity size={16} /> },
    { path: '/signals',   label: 'الإشارات',    icon: <Zap size={16} /> },
    { path: '/markets',   label: 'الأسواق',     icon: <TrendingUp size={16} /> },
    { path: '/analytics', label: 'التحليلات',   icon: <BarChart2 size={16} /> },
  ]

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const planBadge = {
    trial:   { label: 'تجريبي', cls: 'bg-blue-900/50 text-blue-300 border border-blue-700/50' },
    weekly:  { label: 'أسبوعي', cls: 'bg-green-900/50 text-green-300 border border-green-700/50' },
    monthly: { label: 'شهري',   cls: 'bg-purple-900/50 text-purple-300 border border-purple-700/50' },
    banned:  { label: 'محظور',  cls: 'bg-red-900/50 text-red-300 border border-red-700/50' },
  }

  const badge = user ? planBadge[user.plan] : null

  return (
    <nav className="bg-gray-800 border-b border-gray-700 px-4 py-3" dir="rtl">
      <div className="container mx-auto flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-white text-sm">M</div>
          <span className="text-white font-bold text-lg">Mosh AI Pro <span className="text-blue-400">v5</span></span>
        </div>

        {/* Nav Links */}
        <div className="flex items-center gap-1">
          {links.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                location.pathname === link.path || (link.path === '/dashboard' && location.pathname === '/')
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              }`}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
        </div>

        {/* User Menu */}
        <div className="flex items-center gap-2">
          {user && badge && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
              {badge.label}
            </span>
          )}

          {user?.role === 'admin' && (
            <Link
              to="/admin"
              className="flex items-center gap-1 text-xs text-yellow-400 hover:text-yellow-300 px-2 py-1.5 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <Shield size={14} />
              الإدارة
            </Link>
          )}

          {user && (
            <div className="flex items-center gap-1.5 text-xs text-gray-400 px-2 py-1.5 rounded-lg bg-gray-700/50">
              <User size={13} />
              <span className="max-w-[120px] truncate">{user.full_name || user.email}</span>
            </div>
          )}

          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-400 px-2 py-1.5 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <LogOut size={14} />
            خروج
          </button>
        </div>
      </div>
    </nav>
  )
}
