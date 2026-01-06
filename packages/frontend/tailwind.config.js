/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Preke Design System v3 Colors
        preke: {
          // Brand colors
          gold: {
            DEFAULT: 'var(--preke-gold)',
            light: 'var(--preke-gold-light)',
            dark: 'var(--preke-gold-dark)',
          },
          // Backgrounds
          bg: {
            base: 'var(--preke-bg-base)',
            elevated: 'var(--preke-bg-elevated)',
            surface: 'var(--preke-bg-surface)',
            card: 'var(--preke-bg-card)',
            hover: 'var(--preke-bg-hover)',
            active: 'var(--preke-bg-active)',
            video: 'var(--preke-bg-video)',
          },
          // Text
          text: {
            DEFAULT: 'var(--preke-text)',
            dim: 'var(--preke-text-dim)',
            muted: 'var(--preke-text-muted)',
            subtle: 'var(--preke-text-subtle)',
            inverse: 'var(--preke-text-inverse)',
          },
          // Status colors
          blue: {
            DEFAULT: 'var(--preke-blue)',
            light: 'var(--preke-blue-light)',
            bg: 'var(--preke-blue-bg)',
          },
          green: {
            DEFAULT: 'var(--preke-green)',
            light: 'var(--preke-green-light)',
            bg: 'var(--preke-green-bg)',
          },
          red: {
            DEFAULT: 'var(--preke-red)',
            light: 'var(--preke-red-light)',
            bg: 'var(--preke-red-bg)',
          },
          amber: {
            DEFAULT: 'var(--preke-amber)',
            light: 'var(--preke-amber-light)',
            bg: 'var(--preke-amber-bg)',
          },
          purple: {
            DEFAULT: 'var(--preke-purple)',
            light: 'var(--preke-purple-light)',
            bg: 'var(--preke-purple-bg)',
          },
          // Borders
          border: {
            DEFAULT: 'var(--preke-border)',
            light: 'var(--preke-border-light)',
            strong: 'var(--preke-border-strong)',
          },
          // Surface (semantic shortcuts for elevated elements)
          surface: {
            DEFAULT: 'var(--preke-surface)',
            border: 'var(--preke-surface-border)',
            elevated: 'var(--preke-surface-elevated)',
          },
        },
        // Legacy r58 colors (for backwards compatibility during migration)
        r58: {
          bg: {
            primary: 'var(--preke-bg-base)',
            secondary: 'var(--preke-bg-elevated)',
            tertiary: 'var(--preke-bg-surface)',
          },
          text: {
            primary: 'var(--preke-text)',
            secondary: 'var(--preke-text-dim)',
            muted: 'var(--preke-text-muted)',
          },
          accent: {
            primary: 'var(--preke-gold)',
            success: 'var(--preke-green)',
            danger: 'var(--preke-red)',
            warning: 'var(--preke-amber)',
          },
          recorder: 'var(--preke-red)',
          mixer: 'var(--preke-purple)',
        }
      },
      fontFamily: {
        sans: ['var(--preke-font-sans)', 'sans-serif'],
        mono: ['var(--preke-font-mono)', 'monospace'],
      },
      fontSize: {
        'xs': 'var(--preke-font-xs)',
        'sm': 'var(--preke-font-sm)',
        'base': 'var(--preke-font-base)',
        'md': 'var(--preke-font-md)',
        'lg': 'var(--preke-font-lg)',
        'xl': 'var(--preke-font-xl)',
        '2xl': 'var(--preke-font-2xl)',
        '3xl': 'var(--preke-font-3xl)',
        '4xl': 'var(--preke-font-4xl)',
      },
      borderRadius: {
        'xs': 'var(--preke-radius-xs)',
        'sm': 'var(--preke-radius-sm)',
        'md': 'var(--preke-radius-md)',
        'lg': 'var(--preke-radius-lg)',
        'xl': 'var(--preke-radius-xl)',
        '2xl': 'var(--preke-radius-2xl)',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        // Sidebar
        'sidebar': 'var(--preke-sidebar-width)',
        'sidebar-expanded': 'var(--preke-sidebar-width-expanded)',
        // Toolbar
        'toolbar': 'var(--preke-toolbar-height)',
        'header': 'var(--preke-header-height)',
        // Electron titlebar
        'titlebar': 'var(--preke-titlebar-height)',
      },
      boxShadow: {
        'xs': 'var(--preke-shadow-xs)',
        'sm': 'var(--preke-shadow-sm)',
        'md': 'var(--preke-shadow-md)',
        'lg': 'var(--preke-shadow-lg)',
        'xl': 'var(--preke-shadow-xl)',
        'glow': 'var(--preke-shadow-glow)',
        'gold': 'var(--preke-shadow-gold)',
        'green': 'var(--preke-shadow-green)',
        'red': 'var(--preke-shadow-red)',
      },
      backdropBlur: {
        'preke-sm': 'var(--preke-blur-sm)',
        'preke-md': 'var(--preke-blur-md)',
        'preke-lg': 'var(--preke-blur-lg)',
        'preke-xl': 'var(--preke-blur-xl)',
      },
      zIndex: {
        'dropdown': 'var(--preke-z-dropdown)',
        'sticky': 'var(--preke-z-sticky)',
        'modal-backdrop': 'var(--preke-z-modal-backdrop)',
        'modal': 'var(--preke-z-modal)',
        'toast': 'var(--preke-z-toast)',
        'tooltip': 'var(--preke-z-tooltip)',
        'splash': 'var(--preke-z-splash)',
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'recording': 'recording 1.5s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
        'fade-in-up': 'fade-in-up 0.4s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
      },
      keyframes: {
        'recording': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-in-up': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
