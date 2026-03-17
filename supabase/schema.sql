-- Crypto Signal Bot — Supabase Schema
-- Run this in the Supabase SQL editor to set up all tables.

-- Trading pairs we are actively watching
CREATE TABLE pairs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol          TEXT UNIQUE NOT NULL,
  base_asset      TEXT NOT NULL,
  quote_asset     TEXT NOT NULL,
  category        TEXT NOT NULL,
  current_price   NUMERIC(20,8),
  price_change_24h NUMERIC(8,4),
  volume_24h      NUMERIC(24,2),
  atr_14          NUMERIC(20,8),
  is_active       BOOLEAN DEFAULT true,
  last_updated    TIMESTAMPTZ DEFAULT now(),
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- AI-generated trading signals
CREATE TABLE signals (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pair_id           UUID REFERENCES pairs(id),
  strategy          TEXT NOT NULL,
  direction         TEXT NOT NULL,
  confidence        NUMERIC(4,3) NOT NULL,
  entry_price       NUMERIC(20,8) NOT NULL,
  target_price      NUMERIC(20,8) NOT NULL,
  stop_price        NUMERIC(20,8) NOT NULL,
  risk_reward       NUMERIC(6,3) NOT NULL,
  edge_pct          NUMERIC(6,4),
  timeframe         TEXT NOT NULL,
  reasoning         TEXT NOT NULL,
  news_headlines    JSONB,
  indicators        JSONB,
  signal_metadata   JSONB,
  status            TEXT DEFAULT 'open',
  created_at        TIMESTAMPTZ DEFAULT now(),
  resolved_at       TIMESTAMPTZ,
  resolved_price    NUMERIC(20,8)
);

-- Trades executed from signals
CREATE TABLE trades (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id       UUID REFERENCES signals(id),
  pair_id         UUID REFERENCES pairs(id),
  mode            TEXT NOT NULL,
  direction       TEXT NOT NULL,
  order_id        TEXT,
  exchange        TEXT NOT NULL DEFAULT 'binance',
  entry_price     NUMERIC(20,8) NOT NULL,
  exit_price      NUMERIC(20,8),
  stop_price      NUMERIC(20,8) NOT NULL,
  target_price    NUMERIC(20,8) NOT NULL,
  size_usd        NUMERIC(14,2) NOT NULL,
  size_base       NUMERIC(20,8),
  pnl_usd         NUMERIC(14,2),
  pnl_pct         NUMERIC(8,4),
  fees_usd        NUMERIC(14,6) DEFAULT 0,
  exit_reason     TEXT,
  status          TEXT DEFAULT 'open',
  opened_at       TIMESTAMPTZ DEFAULT now(),
  closed_at       TIMESTAMPTZ
);

-- OHLCV snapshots per pair per timeframe
CREATE TABLE ohlcv_snapshots (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pair_id     UUID REFERENCES pairs(id),
  timeframe   TEXT NOT NULL,
  open        NUMERIC(20,8) NOT NULL,
  high        NUMERIC(20,8) NOT NULL,
  low         NUMERIC(20,8) NOT NULL,
  close       NUMERIC(20,8) NOT NULL,
  volume      NUMERIC(24,2) NOT NULL,
  candle_ts   TIMESTAMPTZ NOT NULL,
  snapshotted_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(pair_id, timeframe, candle_ts)
);

-- Performance summary per strategy
CREATE TABLE performance_summary (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy        TEXT NOT NULL,
  timeframe       TEXT,
  total_signals   INTEGER DEFAULT 0,
  total_trades    INTEGER DEFAULT 0,
  winning_trades  INTEGER DEFAULT 0,
  losing_trades   INTEGER DEFAULT 0,
  stopped_trades  INTEGER DEFAULT 0,
  total_pnl_usd   NUMERIC(14,2) DEFAULT 0,
  win_rate        NUMERIC(5,4),
  avg_rr          NUMERIC(6,3),
  avg_edge_pct    NUMERIC(6,4),
  max_drawdown    NUMERIC(8,4),
  updated_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE(strategy, timeframe)
);

-- Equity curve snapshots
CREATE TABLE equity_snapshots (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mode        TEXT NOT NULL DEFAULT 'paper',
  equity_usd  NUMERIC(14,2) NOT NULL,
  open_pnl    NUMERIC(14,2) DEFAULT 0,
  snapshotted_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_signals_pair_id ON signals(pair_id);
CREATE INDEX idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_strategy ON signals(strategy);
CREATE INDEX idx_trades_signal_id ON trades(signal_id);
CREATE INDEX idx_trades_mode ON trades(mode);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_ohlcv_pair_timeframe ON ohlcv_snapshots(pair_id, timeframe);
CREATE INDEX idx_ohlcv_candle_ts ON ohlcv_snapshots(candle_ts DESC);
CREATE INDEX idx_equity_snapshots_time ON equity_snapshots(snapshotted_at DESC);
