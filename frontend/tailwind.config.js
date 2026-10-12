/** @type {import('tailwindcss').Config} */
module.exports = {
  // The UI markup is split across the JavaScript view modules. Include them
  // so Tailwind keeps the matching component classes in the generated CSS.
  content: ['./index.html', './app.js', './js/**/*.js'],
  theme: {
    extend: {
      colors: {
        forest: { DEFAULT: '#0c4a3e', dark: '#07362d' },
        emerald: '#10715d',
      },
      boxShadow: {
        panel: '0 14px 38px rgba(15, 49, 40, 0.08)',
      },
    },
  },
  plugins: [],
};
