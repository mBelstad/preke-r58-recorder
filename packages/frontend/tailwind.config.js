/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // R58 Design System Colors
        r58: {
          bg: {
            primary: '#0f172a',    // Slate 900
            secondary: '#1e293b',  // Slate 800
            tertiary: '#334155',   // Slate 700
          },
          text: {
            primary: '#f8fafc',    // Slate 50
            secondary: '#94a3b8',  // Slate 400
          },
          accent: {
            primary: '#3b82f6',    // Blue 500
            success: '#22c55e',    // Green 500
            danger: '#ef4444',     // Red 500
            warning: '#f59e0b',    // Amber 500
          },
          // Mode-specific colors
          recorder: '#1e40af',     // Deep Blue
          mixer: '#7c3aed',        // Rich Purple
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'r58': '8px',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'recording': 'recording 1.5s ease-in-out infinite',
      },
      keyframes: {
        recording: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        }
      }
    },
  },
  plugins: [],
}

