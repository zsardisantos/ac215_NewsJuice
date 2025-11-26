/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          pink: '#FF3B9A',
          purple: '#8B3A8F',
          dark: '#1A1625',
          darker: '#0F0B14',
        }
      }
    },
  },
  plugins: [],
}
