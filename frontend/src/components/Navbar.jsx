import { Link, useLocation } from 'react-router-dom'
import { TrendingUp, BarChart2, Activity, Moon, Sun, Zap } from 'lucide-react'

export default function Navbar({ darkMode, setDarkMode }) {
  const location = useLocation()

  const links = [
    { path: '/', label: 'لوحة التحكم', icon: <Activity size={16} /> },
    { path: '/signals', label: 'الإشارات', icon: <Zap size={16} /> },
    { path: '/markets', label: 'الأسواق', icon: <TrendingUp size={16} /> },
    { path: '/analytics', label: 'التحليلات', icon: <BarChart2 size={16} /> },
  ]

  return (
    <nav className="bg-gray-800 dark:bg-gray-900 border-b border-gray-700 px-6 py-3">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-white text-sm">M</div>
          <span className="text-white font-bold text-lg">Mosh AI Pro <span className="text-blue-400">v5</span></span>
        </div>

        <div className="flex items-center gap-1">
          {links.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-colors ${
                location.pathname === link.path
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              }`}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
        </div>

        <button
          onClick={() => setDarkMode(!darkMode)}
          className="p-2 rounded-lg text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
        >
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </nav>
  )
}
