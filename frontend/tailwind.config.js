/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#F0FDF4',
          100: '#DCFCE7',
          500: '#10B981', // Primary Emerald Accent
          600: '#059669',
          700: '#047857',
          teal: '#0D9488',
        },
        sidebar: {
          bg: '#1E293B',    // Dark Sidebar Background
          active: '#0F172A',
          text: '#94A3B8',
          hover: '#334155'
        },
        surface: {
          bg: '#F8FAFC',    // Main Body Background
          card: '#FFFFFF',
          border: '#E2E8F0'
        }
      },
    },
  },
  plugins: [],
}
