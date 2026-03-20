import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Signals from './pages/Signals'
import Markets from './pages/Markets'
import Analytics from './pages/Analytics'
import Navbar from './components/Navbar'
import ChatBot from './components/ChatBot'
import './App.css'

function App() {
  const [darkMode, setDarkMode] = useState(true)

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        <Router>
          <Navbar darkMode={darkMode} setDarkMode={setDarkMode} />
          <main className="container mx-auto px-4 py-8 relative">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/signals" element={<Signals />} />
              <Route path="/markets" element={<Markets />} />
              <Route path="/analytics" element={<Analytics />} />
            </Routes>
          </main>
          <ChatBot />
        </Router>
      </div>
    </div>
  )
}

export default App
