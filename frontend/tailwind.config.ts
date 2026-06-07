import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        neon: {
          cyan: '#22d3ee',
          purple: '#a78bfa',
          green: '#34d399',
          pink: '#f472b6',
          orange: '#fb923c',
          yellow: '#fbbf24',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 12px rgba(34, 211, 238, 0.4)',
        'glow-green': '0 0 12px rgba(52, 211, 153, 0.4)',
        'glow-purple': '0 0 12px rgba(167, 139, 250, 0.4)',
        'glow-pink': '0 0 12px rgba(244, 114, 182, 0.4)',
        'glow-red': '0 0 12px rgba(248, 113, 113, 0.4)',
        'glow-orange': '0 0 12px rgba(251, 146, 60, 0.4)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config
