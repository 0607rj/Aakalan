# Aakalan frontend

Next.js (App Router) + TypeScript strict + Tailwind CSS. Run from the repo root with `make dev`, or here with `npm run dev` (port 3000).
Checks: `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run build`.
API types: `npm run gen:api` regenerates `src/lib/api/schema.d.ts` from `../backend/openapi.json`.
Set `NEXT_PUBLIC_API_URL` (see `.env.example`); defaults to `http://localhost:8000`.
