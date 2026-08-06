import type { Config } from "tailwindcss";
import { designTokens } from "./src/design";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: designTokens.color.brand.primary,
          "primary-hover": designTokens.color.brand.primaryHover,
          "primary-strong": designTokens.color.brand.primaryStrong,
          surface: designTokens.color.brand.surface,
          "surface-container": designTokens.color.brand.surfaceContainer,
          background: designTokens.color.brand.background,
          border: designTokens.color.brand.border,
          warm: designTokens.color.brand.warm,
          dim: designTokens.color.brand.dim,
        },
        text: {
          primary: designTokens.color.text.primary,
          secondary: designTokens.color.text.secondary,
        },
      },
      fontFamily: {
        sans: [...designTokens.typography.fontFamily],
      },
      fontSize: {
        h1: designTokens.typography.fontSize.h1,
        h2: designTokens.typography.fontSize.h2,
        h3: designTokens.typography.fontSize.h3,
        h4: designTokens.typography.fontSize.h4,
        "body-lg": designTokens.typography.fontSize.bodyLg,
        "body-md": designTokens.typography.fontSize.bodyMd,
        "body-sm": designTokens.typography.fontSize.bodySm,
        caption: designTokens.typography.fontSize.caption,
      },
      borderRadius: {
        xl: designTokens.radius.button,
        "3xl": designTokens.radius.largeContainer,
        arch: designTokens.radius.arch,
      },
      boxShadow: {
        card: designTokens.shadow.card,
        cta: designTokens.shadow.cta,
      },
      transitionTimingFunction: {
        sidebar: designTokens.motion.sidebarEase,
      },
    },
  },
} satisfies Config;
