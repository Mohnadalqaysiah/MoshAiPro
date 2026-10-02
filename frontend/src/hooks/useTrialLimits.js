import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// (2026-10-03) مصدر حقيقة واحد لحدود التجربة المجانية المعروضة بصفحات
// التسويق (الرئيسية، التسجيل، من نحن، الرؤية، صفحات الدول، المدونة) —
// بدل أرقام ثابتة بالكود يمكن تنحرف عن trial_analysis_limit/trial_chat_limit
// الفعليين بـSiteSettings (نفس الحدّين اللذين auth.py._provision_trial_user
// يطبّقهما فعلياً عند التسجيل). القيم الافتراضية (10/20) تظهر فقط للحظة
// تحميل الصفحة الأولى قبل وصول الرد، وتطابق القيم الافتراضية بالباكند.
let _cache = null

export default function useTrialLimits() {
  const [limits, setLimits] = useState(_cache || { analyses: 10, chat: 20 })

  useEffect(() => {
    if (_cache) return
    axios.get(`${API}/api/v1/subscription/plans`)
      .then(r => {
        if (r.data?.trial) { _cache = r.data.trial; setLimits(r.data.trial) }
      })
      .catch(() => {})
  }, [])

  return limits
}
