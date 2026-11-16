# Goldfish Meeting Compass

Build a React + Vite + TypeScript + Tailwind + shadcn/ui app called "Goldfish".

Constraints: no Supabase or backend integration, no external fonts/CDNs/analytics.

All data comes from a typed client in src/api.ts (base URL http://127.0.0.1:8000)

with a USE_MOCKS flag that reads /mocks/*.json. Types come from the schema below.

Screen 1 only: three columns.

LEFT: "Can read" folder toggles (1-1s, Meetings, Inbox, HR-private), "Remembers: nothing",

and a monospace receipt ("Left this device: 0 bytes. Kept: nothing").

CENTRE: card "Before you see Priya · 14:00" listing items, each with a state pill

(Clear / Check this / Not found), source chips (date + file; hover shows the exact

quote), and a red "7 weeks old" badge on stale items. Ask bar at the bottom with

a mic button ("Ask about your notes").

RIGHT: day calendar with a 14:00 "Priya 1:1 · brief ready" block.

Colours: yellow #FFD84D, ink navy, accent #1a07cc. Keyboard accessible.

Include loading, empty and error states.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/3418dc4b-fff3-419a-b33c-3a0dd4dc308c).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
