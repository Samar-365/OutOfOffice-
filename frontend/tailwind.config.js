/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        forest: {
          950: '#040d06',
          900: '#081c0f',
          850: '#0c2b17',
          800: '#113b20',
          700: '#18532d',
          600: '#21733e',
          500: '#2d9953',
          400: '#3fc06e',
          300: '#64dd8f',
          200: '#9df0ba',
          100: '#d1fae1',
          50: '#f0fdf4',
        },
        grass: {
          neon: '#16db65',
          lime: '#5aff15',
          glow: '#10b981',
          deep: '#059669',
        },
        dark: {
          bg: '#080d0a',
          surface: '#0f1712',
          card: 'rgba(17, 27, 21, 0.75)',
          border: 'rgba(34, 197, 94, 0.15)',
          input: 'rgba(10, 18, 13, 0.85)',
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-grass': '0 0 35px -5px rgba(22, 219, 101, 0.35)',
        'glow-lime': '0 0 45px -5px rgba(90, 255, 21, 0.45)',
        'glow-subtle': '0 0 20px -2px rgba(16, 185, 129, 0.2)',
        'glass-card': '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
      },
      animation: {
        'grass-pulse': 'grassPulse 2.5s infinite ease-in-out',
        'nature-breeze': 'natureBreeze 6s infinite ease-in-out',
        'glow-shimmer': 'glowShimmer 3s infinite linear',
      },
      keyframes: {
        grassPulse: {
          '0%, 100%': { transform: 'scale(1)', boxShadow: '0 0 20px 0px rgba(22, 219, 101, 0.4)' },
          '50%': { transform: 'scale(1.025)', boxShadow: '0 0 40px 8px rgba(90, 255, 21, 0.65)' },
        },
        natureBreeze: {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '50%': { transform: 'translateY(-6px) rotate(1.5deg)' },
        },
        glowShimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        }
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
