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
            primary: 'var(--r58-bg-primary)',
            secondary: 'var(--r58-bg-secondary)',
            tertiary: 'var(--r58-bg-tertiary)',
          },
          text: {
            primary: 'var(--r58-text-primary)',
            secondary: 'var(--r58-text-secondary)',
            muted: 'var(--r58-text-muted)',
          },
          accent: {
            primary: 'var(--r58-accent-primary)',
            success: 'var(--r58-accent-success)',
            danger: 'var(--r58-accent-danger)',
            warning: 'var(--r58-accent-warning)',
          },
          // Mode-specific colors
          recorder: 'var(--r58-mode-recorder)',
          mixer: 'var(--r58-mode-mixer)',
        }
      },
      fontFamily: {
        sans: ['var(--r58-font-sans)', 'sans-serif'],
        mono: ['var(--r58-font-mono)', 'monospace'],
      },
      borderRadius: {
        'r58': 'var(--r58-border-radius)',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        // Electron chrome spacing
        'titlebar': 'var(--r58-titlebar-height)',
        'window-controls': 'var(--r58-window-controls-width)',
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
