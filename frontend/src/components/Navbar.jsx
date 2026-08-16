import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { TrendingUp, BarChart2, Activity, Zap, LogOut, Shield, User, Menu, X, Settings, History, Globe, Sun, Moon, BookOpen, Sparkles } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { useTheme } from '../contexts/ThemeContext'
import useSiteSettings from '../hooks/useSiteSettings'

export default function Navbar() {
  const location  = useLocation()
  const navigate  = useNavigate()
  const { user, logout } = useAuth()
  const { lang, toggle: toggleLang } = useLang()
  const { isDark, toggle: toggleTheme } = useTheme()
  const siteSettings = useSiteSettings()
  const [open, setOpen] = useState(false)

  const isAr = lang === 'ar'

  const links = [
    { path: '/dashboard',      label: isAr ? 'لوحة التحكم'   : 'Dashboard',      icon: <Activity size={16} /> },
    { path: '/signals',        label: isAr ? 'الإشارات'       : 'Signals',        icon: <Zap size={16} /> },
    { path: '/analyses',       label: isAr ? 'سجل التحليل'   : 'Analyses',       icon: <History size={16} /> },
    { path: '/market-overview',label: isAr ? 'نظرة الأسواق'  : 'Overview',       icon: <Globe size={16} /> },
    { path: '/backtesting',    label: isAr ? 'الأداء التاريخي': 'Backtesting',    icon: <BarChart2 size={16} /> },
    { path: '/analytics',      label: isAr ? 'التحليلات'      : 'Analytics',      icon: <TrendingUp size={16} /> },
    { path: '/journal',        label: isAr ? 'يومية التداول'  : 'Journal',         icon: <BookOpen size={16} /> },
    { path: '/strategies',     label: isAr ? 'بناء الاستراتيجيات' : 'Strategies', icon: <Sparkles size={16} /> },
  ]

  const handleLogout = () => { logout(); navigate('/login') }

  const planBadge = {
    trial:   { label: 'تجريبي', cls: 'bg-blue-900/50 text-blue-300 border border-blue-700/50' },
    weekly:  { label: 'أسبوعي', cls: 'bg-green-900/50 text-green-300 border border-green-700/50' },
    monthly: { label: 'شهري',   cls: 'bg-purple-900/50 text-purple-300 border border-purple-700/50' },
    banned:  { label: 'محظور',  cls: 'bg-red-900/50 text-red-300 border border-red-700/50' },
  }
  const badge = user ? planBadge[user.plan] : null

  const isActive = (path) =>
    location.pathname === path || (path === '/dashboard' && location.pathname === '/')

  return (
    <nav className="bg-gray-800 border-b border-gray-700 px-4 py-3" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container mx-auto flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          {siteSettings.site_logo_url ? (
            <img src={siteSettings.site_logo_url} alt="logo" className="h-8 w-auto object-contain" />
          ) : (
            <img src="/brand/logo-icon-only.png" alt="Qaffel AI" className="w-8 h-8 rounded-lg object-contain" />
          )}
          <span className="text-white font-bold text-base">{siteSettings.site_name || 'Qaffel AI'}</span>
        </Link>

        {/* Desktop Nav Links */}
        <div className="hidden md:flex items-center gap-1">
          {links.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive(link.path) ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              }`}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
        </div>

        {/* Desktop User Menu */}
        <div className="hidden md:flex items-center gap-2">
          {user && badge && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>{badge.label}</span>
          )}
          {user?.role === 'admin' && (
            <Link to="/admin" className="flex items-center gap-1 text-xs text-yellow-400 hover:text-yellow-300 px-2 py-1.5 rounded-lg hover:bg-gray-700">
              <Shield size={14} /> الإدارة
            </Link>
          )}
          {user && (
            <Link to="/affiliate" className="flex items-center gap-1 text-xs text-yellow-400/80 hover:text-yellow-400 px-2 py-1.5 rounded-lg hover:bg-gray-700 transition">
              💰 {isAr ? 'إحالاتي' : 'Referrals'}
            </Link>
          )}
          {user && (
            <Link to="/profile" className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white px-2 py-1.5 rounded-lg bg-gray-700/50 hover:bg-gray-700 transition">
              <User size={13} />
              <span className="max-w-[100px] truncate">{user.full_name || user.email}</span>
            </Link>
          )}
          <button
            onClick={toggleTheme}
            title={isDark ? (isAr ? 'الوضع النهاري' : 'Light mode') : (isAr ? 'الوضع الليلي' : 'Dark mode')}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-yellow-400 px-2 py-1.5 rounded-lg hover:bg-gray-700"
          >
            {isDark ? <Sun size={14} /> : <Moon size={14} />}
          </button>
          <button
            onClick={toggleLang}
            title={isAr ? 'Switch to English' : 'التبديل للعربية'}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-blue-400 px-2 py-1.5 rounded-lg hover:bg-gray-700"
          >
            <Globe size={14} /> {isAr ? 'EN' : 'AR'}
          </button>
          <button onClick={handleLogout} className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-400 px-2 py-1.5 rounded-lg hover:bg-gray-700">
            <LogOut size={14} /> {isAr ? 'خروج' : 'Logout'}
          </button>
        </div>

        {/* Mobile: lang + badge + hamburger */}
        <div className="flex md:hidden items-center gap-1.5 shrink-0">
          {user && badge && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>{badge.label}</span>
          )}
          <button
            onClick={toggleLang}
            title={isAr ? 'Switch to English' : 'التبديل للعربية'}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-blue-400 px-2 py-1.5 rounded-lg hover:bg-gray-700"
          >
            <Globe size={14} /> {isAr ? 'EN' : 'AR'}
          </button>
          <button onClick={() => setOpen(!open)} className="text-gray-300 hover:text-white p-1">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Dropdown Menu */}
      {open && (
        <div className={`md:hidden mt-2 border-t border-gray-700 pt-3 space-y-1`} dir={isAr ? 'rtl' : 'ltr'}>
          {links.map(link => (
            <Link
              key={link.path}
              to={link.path}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm transition-colors ${
                isActive(link.path) ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
          <div className="border-t border-gray-700 my-2" />
          {user?.role === 'admin' && (
            <Link to="/admin" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm text-yellow-400 hover:bg-gray-700">
              <Shield size={16} /> الإدارة
            </Link>
          )}
          {user && (
            <Link to="/affiliate" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm text-yellow-400 hover:bg-gray-700">
              💰 {isAr ? 'إحالاتي' : 'Referrals'}
            </Link>
          )}
          {user && (
            <Link to="/profile" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm text-gray-400 hover:bg-gray-700">
              <Settings size={14} />
              <span className="truncate">حسابي — {user.full_name || user.email}</span>
            </Link>
          )}
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 w-full px-4 py-2.5 rounded-lg text-sm text-gray-400 hover:bg-gray-700"
          >
            {isDark ? <Sun size={16} className="text-yellow-400" /> : <Moon size={16} className="text-blue-400" />}
            {isDark ? (isAr ? 'الوضع النهاري' : 'Light Mode') : (isAr ? 'الوضع الليلي' : 'Dark Mode')}
          </button>
          <button onClick={handleLogout} className="flex items-center gap-2 w-full px-4 py-2.5 rounded-lg text-sm text-red-400 hover:bg-gray-700">
            <LogOut size={16} /> تسجيل الخروج
          </button>
        </div>
      )}
    </nav>
  )
}
