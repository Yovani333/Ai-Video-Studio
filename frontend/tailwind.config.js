/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#121316",
        mist: "#f4f5f7",
        electric: "#6d5dfc",
      },
      boxShadow: {
        soft: "0 24px 70px -32px rgba(21, 22, 28, 0.35)",
      },
    },
  },
  plugins: [],
};
