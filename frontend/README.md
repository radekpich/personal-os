# Personal OS Frontend

Next.js 15 App Router frontend pro každodenní úkolovník.

## Stack

- Next.js 15.5.7 + React 19
- TypeScript strict
- Tailwind CSS v4
- shadcn/ui styl: Radix primitives, `class-variance-authority`, `cn()`
- `next-themes` pro světlý/tmavý režim
- TanStack Query pro server state
- `react-hook-form` + `zod` pro formuláře
- Playwright smoke skript pro E2E ověření

## Design tokens

Veškeré základní barvy, typografie, radiusy, spacing a stíny jsou v jednom souboru:

```text
src/app/globals.css
```

Změnou CSS proměnných v `:root` a `.dark` jde přebarvit celý vzhled.

## Lokální spuštění

Backend musí běžet s CORS pro frontend origin, typicky:

```bash
cd ../backend
export CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
export COOKIE_SECURE=false
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cp .env.example .env.local
npm install
npm run dev
```

Aplikace poběží na `http://localhost:3000`.

## Produkční build

`NEXT_PUBLIC_API_BASE_URL` je klientská proměnná, takže se propisuje při buildu:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.example.com npm run build
npm run start
```

## Ověření

```bash
npm run lint
npm run typecheck
npm run build
```

E2E smoke proti běžícímu backendu a frontendu:

```bash
FRONTEND_BASE_URL=http://127.0.0.1:3000 \
PHASE3_E2E_EMAIL=user@example.com \
PHASE3_E2E_PASSWORD='...' \
npm run phase3:smoke
```

Smoke ověřuje login, quick capture, Inbox, detail drawer, optimistic done, calendar token regeneraci, command palette a mobilní 375px layout.

## PWA

- `public/manifest.webmanifest`
- `public/icons/icon-192.png`
- `public/icons/icon-512.png`
- `public/sw.js`

Service worker cachuje pouze statické assety. Offline synchronizace není implementovaná záměrně.
