import { supabase } from "@/lib/supabase";
import { redis } from "@/lib/redis";
import type { Signal, PerformanceSummary, EquitySnapshot, BotStatus, SignalWithTrade } from "@/lib/types";
import { LiveDashboard } from "@/components/LiveDashboard";

async function getBotStatus(): Promise<BotStatus> {
  const [status, tradeMode, lastRun, equity, heartbeat] = await Promise.all([
    redis.get<string>("bot:status"),
    redis.get<string>("bot:trade_mode"),
    redis.get<string>("bot:last_run"),
    redis.get<string>("bot:paper:equity"),
    redis.get<string>("bot:heartbeat"),
  ]);

  let resolvedStatus: BotStatus["status"];
  if (!heartbeat) {
    resolvedStatus = "stopped";
  } else if (status === "paused") {
    resolvedStatus = "paused";
  } else {
    resolvedStatus = (status as BotStatus["status"]) ?? "idle";
  }

  return {
    status: resolvedStatus,
    trade_mode: (tradeMode as BotStatus["trade_mode"]) ?? "paper",
    last_run: lastRun,
    paper_equity: equity ? parseFloat(equity) : null,
  };
}

async function getRecentSignals(): Promise<SignalWithTrade[]> {
  const { data } = await supabase
    .from("signals")
    .select("*, pairs(symbol), trades(size_usd, pnl_usd, pnl_pct, exit_reason, status)")
    .order("created_at", { ascending: false })
    .limit(20);

  if (!data) return [];

  return data.map((row) => {
    const trade = Array.isArray(row.trades) ? row.trades[0] : row.trades;
    return {
      ...row,
      pair_symbol: (row.pairs as { symbol: string } | null)?.symbol ?? "Unknown",
      trade_size_usd: trade?.size_usd ?? null,
      trade_pnl_usd: trade?.pnl_usd ?? null,
      trade_pnl_pct: trade?.pnl_pct ?? null,
      trade_exit_reason: trade?.exit_reason ?? null,
      trade_status: trade?.status ?? null,
    };
  }) as SignalWithTrade[];
}

async function getPerformance(): Promise<PerformanceSummary[]> {
  const { data } = await supabase.from("performance_summary").select("*");
  return (data as PerformanceSummary[]) ?? [];
}

async function getEquitySnapshots(): Promise<EquitySnapshot[]> {
  const { data } = await supabase
    .from("equity_snapshots")
    .select("*")
    .order("snapshotted_at", { ascending: true })
    .limit(200);

  return (data as EquitySnapshot[]) ?? [];
}

async function getOpenTradeCount(): Promise<number> {
  const { count } = await supabase
    .from("trades")
    .select("*", { count: "exact", head: true })
    .eq("status", "open");

  return count ?? 0;
}

async function getSignalsTodayCount(signals: Signal[]): Promise<number> {
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  return signals.filter((s) => new Date(s.created_at) >= todayStart).length;
}

export const revalidate = 30;

export default async function DashboardPage() {
  const [botStatus, signals, performance, equitySnapshots, openTradeCount] = await Promise.all([
    getBotStatus(),
    getRecentSignals(),
    getPerformance(),
    getEquitySnapshots(),
    getOpenTradeCount(),
  ]);

  const signalsToday = await getSignalsTodayCount(signals);

  return (
    <LiveDashboard
      initialSignals={signals}
      initialPerformance={performance}
      initialEquity={equitySnapshots}
      initialBotStatus={botStatus}
      initialOpenTrades={openTradeCount}
      initialSignalsToday={signalsToday}
    />
  );
}
