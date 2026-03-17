# Crypto AI Signal Bot

AI-powered cryptocurrency trading signal bot with a Next.js dashboard. Monitors live crypto markets via Binance, uses Claude AI to analyse price action and news, generates actionable LONG/SHORT signals, paper trades them, and tracks performance.

```
                                    ┌─────────────┐
                                    │   Binance    │
                                    │  REST + WS   │
                                    └──────┬───────┘
                                           │
┌──────────────┐    ┌──────────────────────▼───────────────────────┐
│  CryptoPanic │───▶│              Python Bot                      │
│  / NewsAPI   │    │                                              │
└──────────────┘    │  ┌─────────┐ ┌────────────┐ ┌────────────┐  │
                    │  │  News   │ │ Technical  │ │  Volume    │  │
┌──────────────┐    │  │Sentiment│ │Confluence  │ │  Spike     │  │
│  Claude AI   │◀──▶│  └────┬────┘ └─────┬──────┘ └─────┬──────┘  │
│  (Sonnet)    │    │       └────────────┼──────────────┘          │
└──────────────┘    │                    ▼                         │
                    │           Paper / Live Trader                │
                    └──────────┬──────────────────┬────────────────┘
                               │                  │
                    ┌──────────▼──────┐ ┌─────────▼─────────┐
                    │    Supabase     │ │   Upstash Redis   │
                    │   (Postgres)    │ │   (Live State)    │
                    └──────────┬──────┘ └─────────┬─────────┘
                               │                  │
                    ┌──────────▼──────────────────▼─────────┐
                    │         Next.js Dashboard              │
                    │   Signals · P&L · Drawdown · Charts   │
                    └───────────────────────────────────────┘
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Bot | Python 3.12+, ccxt, anthropic SDK, pandas, ta, APScheduler, pydantic |
| Dashboard | Next.js 15, TypeScript (strict), Tailwind CSS v4, Recharts |
| Database | Supabase (PostgreSQL) — signals, trades, OHLCV, performance |
| Cache | Upstash Redis — live prices, indicators, bot state, dedup |
| Exchange | Binance via ccxt (swappable to Kraken, Bybit, 100+ others) |
| AI | Claude Sonnet — structured JSON signal generation |

## Monorepo Structure

```
├── apps/
│   ├── bot/                  # Python signal bot
│   │   ├── main.py           # Entry point + graceful shutdown
│   │   ├── config.py         # Settings via pydantic-settings
│   │   ├── scheduler.py      # APScheduler loop definitions
│   │   ├── strategies/       # 3 signal strategies
│   │   ├── clients/          # Exchange, Claude, News, Redis, Supabase
│   │   ├── models/           # Pydantic data models
│   │   ├── trading/          # Paper + Live trader implementations
│   │   ├── indicators/       # RSI, MACD, BB, ATR calculations
│   │   └── trader_factory.py # Returns trader based on TRADE_MODE
│   └── dashboard/            # Next.js frontend
│       └── src/
│           ├── app/          # Pages + API routes
│           ├── components/   # SignalFeed, PnlChart, etc.
│           ├── hooks/        # useSignals, usePerformance
│           └── lib/          # Supabase, Redis clients + types
├── supabase/
│   ├── config.toml           # Supabase CLI config
│   └── migrations/           # Versioned SQL migrations
└── docker-compose.yml
```

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker (for bot deployment)
- Accounts: [Supabase](https://supabase.com), [Upstash](https://upstash.com), [Binance](https://binance.com), [CryptoPanic](https://cryptopanic.com) (free tier)
- [Anthropic API key](https://console.anthropic.com)

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd crypto-ai-signals-bot

# Bot environment
cp apps/bot/.env.example apps/bot/.env
# Edit apps/bot/.env with your API keys

# Dashboard environment
cp apps/dashboard/.env.example apps/dashboard/.env.local
# Edit apps/dashboard/.env.local with Supabase + Upstash keys
```

### 2. Set up Supabase

Link your Supabase project and push the schema:

```bash
npx supabase link --project-ref <your-project-ref>
npx supabase db push
```

Or paste `supabase/migrations/20260317092525_init_schema.sql` into the Supabase SQL Editor.

### 3. Create a Binance API key

1. Go to Binance → API Management
2. Create a new API key with **read-only** permissions (sufficient for paper mode)
3. Add the key and secret to `apps/bot/.env`

### 4. Run locally

**Bot:**
```bash
cd apps/bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Dashboard:**
```bash
cd apps/dashboard
npm install
npm run dev
```

**Or via Docker (bot only):**
```bash
docker compose up --build
```

## Trading Strategies

### 1. News Sentiment
Detects mispricing between breaking crypto news and current market price. Fetches headlines from CryptoPanic, combines with technical context, and asks Claude to assess whether the market has fully priced in the information.

**Edge:** 15–60 minute lag between news publication and full price adjustment.

### 2. Technical Confluence
Scores 6 independent technical conditions (RSI, MACD crossover, Bollinger Band position, EMA alignment, volume confirmation) and generates signals when 4+ align on the same direction.

**Edge:** Multi-indicator alignment has higher probability of sustained moves than any single indicator.

### 3. Volume Spike Detection
Monitors for unusual volume (>2.5x average), then analyses trade pressure (buy vs sell volume) and order book imbalance to detect potential informed accumulation or distribution.

**Edge:** Large players often accumulate before public catalysts, leaving volume footprints.

## Paper Trading

Paper mode is the default. Every trade is simulated with realistic mechanics:

- Entry at live market price (not signal price — avoids look-ahead bias)
- ATR-based dynamic stop-loss and take-profit levels
- Position size: `BOT_PAPER_TRADE_SIZE` (default $200 USD)
- Exits: target hit, stop hit, or expired (signal timeframe exceeded)
- P&L: `(exit - entry) / entry * size` for LONG, inverse for SHORT
- Full audit trail in Supabase — every signal records indicators, Claude reasoning, and outcome

## Live Trading

Set `TRADE_MODE=live` in `apps/bot/.env`. All 8 safety guards must pass before any real order:

1. `TRADE_MODE == "live"` — explicit mode check
2. `daily_spend < MAX_DAILY_SPEND` — hard $50 daily ceiling
3. `confidence >= 0.75` — higher bar for real money
4. `risk_reward >= 1.8` — minimum R:R ratio
5. `volume_24h >= $5M` — reject thin markets
6. `ATR% >= 0.5%` — reject dead/flat markets
7. `open_positions < 3` — cap concurrent exposure
8. `balance >= trade_size` — sufficient funds check

Live exits use OCO (One-Cancels-Other) orders placed on the exchange — the bot doesn't rely solely on polling.

## Deployment

| Component | Platform | Notes |
|-----------|----------|-------|
| Bot | Fly.io / Railway / VPS | Long-running Docker process |
| Dashboard | Vercel | Zero config, auto-deploy on push |
| Database | supabase.com | Managed Postgres, free tier available |
| Cache | upstash.com | Serverless Redis, free tier available |

**Fly.io (recommended for bot):**
```bash
cd apps/bot
fly launch
fly secrets set ANTHROPIC_API_KEY=... SUPABASE_URL=... # etc
fly deploy
```

**Vercel (dashboard):**
```bash
cd apps/dashboard
vercel --prod
```

## Environment Variables

See [`apps/bot/.env.example`](apps/bot/.env.example) and [`apps/dashboard/.env.example`](apps/dashboard/.env.example) for the full list.

## Disclaimer

Cryptocurrency trading carries significant risk of loss. This software is for **educational and research purposes**. Paper mode is the safe default. Live trading is only appropriate for users in jurisdictions where it is legal, who understand the risks, and who can afford to lose the capital deployed.

In Australia, verify the AUSTRAC registration status of your chosen exchange. This is not financial advice.

## License

See [LICENSE](LICENSE) for details.
