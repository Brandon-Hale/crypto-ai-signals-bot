/** Shared TypeScript types — mirrors Supabase schema. Zero `any` types. */

export interface Pair {
  id: string;
  symbol: string;
  base_asset: string;
  quote_asset: string;
  category: "large_cap" | "mid_cap" | "defi" | "layer1" | "layer2";
  current_price: number | null;
  price_change_24h: number | null;
  volume_24h: number | null;
  atr_14: number | null;
  is_active: boolean;
  last_updated: string;
}

export interface Signal {
  id: string;
  pair_id: string;
  strategy: "news_sentiment" | "technical_confluence" | "volume_spike";
  direction: "LONG" | "SHORT";
  confidence: number;
  entry_price: number;
  target_price: number;
  stop_price: number;
  risk_reward: number;
  edge_pct: number | null;
  timeframe: "1h" | "4h" | "1d";
  reasoning: string;
  news_headlines: Array<{ title: string; source: string }> | null;
  indicators: Record<string, number> | null;
  signal_metadata: Record<string, number | string | string[]> | null;
  status: "open" | "won" | "lost" | "stopped" | "expired" | "cancelled";
  created_at: string;
  resolved_at: string | null;
  resolved_price: number | null;
}

export interface Trade {
  id: string;
  signal_id: string;
  pair_id: string;
  mode: "paper" | "live";
  direction: "LONG" | "SHORT";
  order_id: string | null;
  exchange: string;
  entry_price: number;
  exit_price: number | null;
  stop_price: number;
  target_price: number;
  size_usd: number;
  size_base: number | null;
  pnl_usd: number | null;
  pnl_pct: number | null;
  fees_usd: number;
  exit_reason: "target_hit" | "stop_hit" | "expired" | "manual" | null;
  status: "open" | "closed" | "cancelled";
  opened_at: string;
  closed_at: string | null;
}

export interface PerformanceSummary {
  id: string;
  strategy: string;
  timeframe: string | null;
  total_signals: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  stopped_trades: number;
  total_pnl_usd: number;
  win_rate: number | null;
  avg_rr: number | null;
  avg_edge_pct: number | null;
  max_drawdown: number | null;
  updated_at: string;
}

export interface EquitySnapshot {
  id: string;
  mode: "paper" | "live";
  equity_usd: number;
  open_pnl: number;
  snapshotted_at: string;
}

export interface BotStatus {
  status: "running" | "idle" | "error" | "stopped" | "paused";
  trade_mode: "paper" | "live";
  last_run: string | null;
  paper_equity: number | null;
}
