/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{html,js,jsx,tsx}'],
  theme: {
    extend: {
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '.4' },
          '50%': { opacity: '.1' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        fadeOut: {
          from: { opacity: '1' },
          to: { opacity: '0' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(244, 63, 94, 0.4)' },
          '50%': { boxShadow: '0 0 4px 2px rgba(251, 113, 133, 0.4)' },
        },
      },
      // Define the animation with a faster duration
      animation: {
        // Adjust the duration as needed (e.g., 500ms)
        'pulse-fast': 'pulse 1000ms cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 1s ease-in-out forwards',
        'fade-in-fast': 'fadeIn 0.4s ease-in-out forwards',
        'fade-out': 'fadeOut 0.4s ease-in-out forwards',
        glow: 'glowPulse 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
