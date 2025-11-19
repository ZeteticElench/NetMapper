/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        'network-up': '#10b981',
        'network-down': '#ef4444',
        'network-warning': '#f59e0b',
        'network-unknown': '#6b7280',
      },
    },
  },
  plugins: [],
}
