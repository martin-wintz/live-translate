/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{html,js}',
  ],
  theme: {
    extend: {
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '.4' },
          '50%': { opacity: '.1' },
        },
      },
      // Define the animation with a faster duration
      animation: {
        // Adjust the duration as needed (e.g., 500ms)
        'pulse-fast': 'pulse 1000ms cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}

