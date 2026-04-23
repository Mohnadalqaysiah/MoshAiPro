/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ── Gray scale driven by CSS variables ─────────────────────────────
      // Dark/light theme is controlled purely by changing these vars.
      // Every bg-gray-*, text-gray-*, border-gray-*, and opacity variants
      // (bg-gray-800/60 etc.) will automatically adapt.
      colors: {
        gray: {
          50:  'rgb(var(--tw-gray-50)  / <alpha-value>)',
          100: 'rgb(var(--tw-gray-100) / <alpha-value>)',
          200: 'rgb(var(--tw-gray-200) / <alpha-value>)',
          300: 'rgb(var(--tw-gray-300) / <alpha-value>)',
          400: 'rgb(var(--tw-gray-400) / <alpha-value>)',
          500: 'rgb(var(--tw-gray-500) / <alpha-value>)',
          600: 'rgb(var(--tw-gray-600) / <alpha-value>)',
          700: 'rgb(var(--tw-gray-700) / <alpha-value>)',
          800: 'rgb(var(--tw-gray-800) / <alpha-value>)',
          900: 'rgb(var(--tw-gray-900) / <alpha-value>)',
          950: 'rgb(var(--tw-gray-950) / <alpha-value>)',
        },
        primary: {
          50:  '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        },
        success: '#10b981',
        danger:  '#ef4444',
        warning: '#f59e0b',
      },
      fontFamily: {
        sans:   ['Inter', 'system-ui', 'sans-serif'],
        arabic: ['Tajawal', 'sans-serif'],
      },
    },
  },
  plugins: [],
  darkMode: 'class',
}
