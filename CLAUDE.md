# CLAUDE.md

## Project Overview

Crypto AI signal bot monorepo — Python bot + Next.js dashboard.

## Repository Layout

- `apps/bot/` — Python 3.12+ signal bot (ccxt, anthropic, pandas, ta, pydantic, APScheduler)
- `apps/dashboard/` — Next.js 15 dashboard (TypeScript strict, Tailwind v4, Recharts)
- `supabase/` — Database migrations (Supabase CLI)
- `docker-compose.yml` — Bot containerisation

## Key Commands

### Bot
```bash
cd apps/bot
pip install -r requirements.txt
python main.py
```

### Dashboard
```bash
cd apps/dashboard
npm install
npm run dev
```

### Database
```bash
npx supabase db push          # Apply migrations to remote
npx supabase migration new X  # Create new migration
```

## Conventions

- **Python:** Pydantic models for all data, strict types, no `Any`. Loguru for logging.
- **TypeScript:** Strict mode, zero `any` types. Shared types in `src/lib/types.ts`.
- **Exchange calls:** Always check Redis cache first, write back with TTL. Never hammer the API.
- **Claude calls:** Deduped via Redis key per pair+direction+strategy (2h TTL).
- **Stops/targets:** Always ATR-based, never fixed pip distances.
- **Trade mode:** Read once at startup from `TRADE_MODE` env var, immutable at runtime.
- **DB writes:** Wrapped in try/except, logged via loguru, never crash the loop.

## Architecture Notes

- `BaseTrader` ABC with `PaperTrader` and `LiveTrader` implementations
- `BaseStrategy` ABC with 3 strategy implementations
- `trader_factory.py` returns correct trader based on env var
- All 8 live safety guards must pass before any real order
- Scheduler runs strategy loop every 5 min, maintenance every 1 hour
