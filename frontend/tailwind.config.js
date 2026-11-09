/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Adicionando as cores do seu design para o Tailwind v3
        gray: {
          950: '#0d1117',
          900: '#161b22',
          800: '#21262d',
          700: '#30363d',
          600: '#484f58',
          500: '#6e7681',
          400: '#909dab',
          300: '#c9d1d9',
        },
        purple: {
          400: '#c084fc',
          600: '#9333ea',
          700: '#7e22ce',
          800: '#6b21a8',
          900: '#581c87',
        },
        pink: {
          400: '#f472b6',
        },
      }
    },
  },
  plugins: [],
}
