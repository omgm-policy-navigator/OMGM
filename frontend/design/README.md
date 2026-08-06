# Frontend Design Source

This directory keeps design references that the frontend team needs while implementing React screens.

## Structure

- `reference/`: Source design documents copied from `docs/design` for frontend-local review.
- `../src/design/`: Runtime-safe React/Tailwind design contracts such as tokens and reusable constants.

## Rules

- Do not import HTML reference files from application code.
- Put values used by React components in `src/design/tokens.ts`.
- Keep visual source references and runnable application code separate.
- When `docs/design` changes, update this directory in the same frontend task.
