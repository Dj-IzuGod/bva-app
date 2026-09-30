/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // UI/UX ADDENDUM tokens. Every later phase MUST use these semantic
      // colors instead of ad-hoc hex values (consistency rule).
      colors: {
        // Vulnerability grades: HIGH red, MEDIUM amber, LOW blue, NONE gray.
        vuln: {
          high: "#dc2626",
          medium: "#d97706",
          low: "#2563eb",
          none: "#64748b",
        },
        // Pair types: genuine teal, impostor rose -- used in all charts.
        pairtype: {
          genuine: "#0d9488",
          impostor: "#e11d48",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        // Single soft card shadow, used (only) by the Card component.
        card: "0 1px 2px rgba(15, 23, 42, 0.06), 0 4px 12px rgba(15, 23, 42, 0.06)",
      },
    },
  },
  plugins: [],
};
