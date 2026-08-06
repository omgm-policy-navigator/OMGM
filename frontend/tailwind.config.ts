import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#6FA77E",
          surface: "#EAF5EC",
          "surface-container": "#D6EAD8",
          background: "#FFFFFF",
          border: "#B8D8C1",
          warm: "#FCEFE6",
          dim: "rgb(0 0 0 / 0.4)",
        },
        text: {
          primary: "#1A2B1C",
          secondary: "#5D6E5F",
        },
      },
      fontFamily: {
        sans: ["Manrope", "system-ui", "sans-serif"],
      },
      fontSize: {
        h1: ["48px", { lineHeight: "64px", fontWeight: "800", letterSpacing: "-0.02em" }],
        h2: ["32px", { lineHeight: "44px", fontWeight: "700", letterSpacing: "-0.01em" }],
        h3: ["24px", { lineHeight: "32px", fontWeight: "700", letterSpacing: "0" }],
        h4: ["20px", { lineHeight: "28px", fontWeight: "600", letterSpacing: "0" }],
        "body-lg": ["18px", { lineHeight: "28px", fontWeight: "600", letterSpacing: "0" }],
        "body-md": ["16px", { lineHeight: "24px", fontWeight: "500", letterSpacing: "0" }],
        "body-sm": ["14px", { lineHeight: "20px", fontWeight: "400", letterSpacing: "0" }],
        caption: ["12px", { lineHeight: "16px", fontWeight: "500", letterSpacing: "0.01em" }],
      },
      borderRadius: {
        xl: "12px",
        "3xl": "24px",
        arch: "45px 45px 0 0",
      },
      boxShadow: {
        card: "0 12px 32px rgba(111, 167, 126, 0.12)",
        cta: "0 8px 24px rgba(0, 0, 0, 0.08)",
      },
      transitionTimingFunction: {
        sidebar: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
} satisfies Config;
