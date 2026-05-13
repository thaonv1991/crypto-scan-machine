/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        main: '#05070d',
        panel: 'rgba(15, 18, 28, 0.76)',
        card: 'rgba(18, 22, 34, 0.72)',
        border: 'rgba(255,255,255,0.07)',
        primary: {
          DEFAULT: '#7c5cff',
          soft: 'rgba(124,92,255,0.18)'
        },
        cyan: '#22d3ee',
        green: '#10f2a0',
        yellow: '#facc15',
        red: '#ff4d6d',
        text: {
          primary: '#ffffff',
          secondary: '#a1a8b8',
          muted: '#6c7486'
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
