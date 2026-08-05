import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

const publicApiOnlyPatterns = [
  {
    group: ["@/pages/*/*", "@/features/*/*", "@/entities/*/*"],
    message: "Import FSD slices through their public index.ts entry point.",
  },
];

const restrictedImportPatterns = (patterns) => [
  "error",
  {
    patterns: [...publicApiOnlyPatterns, ...patterns],
  },
];

export default tseslint.config(
  {
    ignores: ["dist/**", "node_modules/**", "*.tsbuildinfo", "eslint.config.js"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
      globals: {
        ...globals.browser,
        ...globals.es2022,
      },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-floating-promises": "error",
      "no-restricted-imports": restrictedImportPatterns([]),
    },
  },
  {
    files: ["src/shared/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": restrictedImportPatterns([
        {
          group: ["@/app/**", "@/pages/**", "@/features/**", "@/entities/**"],
          message: "shared must not depend on higher FSD layers.",
        },
      ]),
    },
  },
  {
    files: ["src/entities/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": restrictedImportPatterns([
        {
          group: ["@/app/**", "@/pages/**", "@/features/**"],
          message: "entities may depend on shared only, not app/pages/features.",
        },
      ]),
    },
  },
  {
    files: ["src/features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": restrictedImportPatterns([
        {
          group: ["@/app/**", "@/pages/**"],
          message: "features may depend on entities/shared only, not app/pages.",
        },
      ]),
    },
  },
  {
    files: ["src/pages/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": restrictedImportPatterns([
        {
          group: ["@/app/**"],
          message: "pages must not depend on app.",
        },
      ]),
    },
  },
  {
    files: ["src/**/*.test.ts", "src/**/*.test.tsx", "src/test-setup.ts"],
    languageOptions: {
      globals: {
        ...globals.vitest,
      },
    },
  },
);
