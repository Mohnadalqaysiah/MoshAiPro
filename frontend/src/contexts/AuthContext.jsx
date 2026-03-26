import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]   = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('mosh_token'))
  const [loading, setLoading] = useState(true)

  // Set axios default header
  useEffect(() => {
    if (token) axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    else delete axios.defaults.headers.common['Authorization']
  }, [token])

  // Load profile on mount
  useEffect(() => {
    if (token) {
      axios.get(`${API}/api/v1/auth/me`)
        .then(r => setUser(r.data))
        .catch(() => { localStorage.removeItem('mosh_token'); setToken(null) })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  const login = async (email, password) => {
    const r = await axios.post(`${API}/api/v1/auth/login`, { email, password })
    localStorage.setItem('mosh_token', r.data.token)
    setToken(r.data.token)
    setUser(r.data.user)
    return r.data.user
  }

  const register = async (email, password, full_name, ref = '') => {
    const url = ref
      ? `${API}/api/v1/auth/register?ref=${encodeURIComponent(ref)}`
      : `${API}/api/v1/auth/register`
    const r = await axios.post(url, { email, password, full_name })
    localStorage.setItem('mosh_token', r.data.token)
    setToken(r.data.token)
    setUser(r.data.user)
    return r.data.user
  }

  const logout = () => {
    localStorage.removeItem('mosh_token')
    setToken(null)
    setUser(null)
    delete axios.defaults.headers.common['Authorization']
  }

  const refreshUser = async () => {
    if (!token) return
    const r = await axios.get(`${API}/api/v1/auth/me`)
    setUser(r.data)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
