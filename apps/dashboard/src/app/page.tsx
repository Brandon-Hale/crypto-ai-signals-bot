import { supabase } from "@/lib/supabase";
import { redis } from "@/lib/redis";
import type { Signal, PerformanceSummary, BotStatus } from "@/lib/types";
import { SignalFeed } from "@/components/SignalFeed";
import { PnlChart } from "@/components/PnlChart";
import { PerformanceStats } from "@/components/PerformanceStats";

async function getBotStatus(): Promise<BotStatus> {
  const [status, tradeMode, lastRun, equity] = await Promise.all([
    redis.get<string>("bot:status"),
    redis.get<string>("bot:trade_mode"),
    redis.get<string>("bot:last_run"),
    redis.get<string>("bot:paper:equity"),
  ]);

  return {
    status: (status as BotStatus["status"]) ?? "idle",
    trade_mode: (tradeMode as BotStatus["trade_mode"]) ?? "paper",
    last_run: lastRun,
    paper_equity: equity ? parseFloat(equity) : null,
  };
}

async function getRecentSignals(): Promise<Signal[]> {
  const { data } = await supabase
    .from("signals")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(20);

  return (data as Signal[]) ?? [];
}

async function getPerformance(): Promise<PerformanceSummary[]> {
  const { data } = await supabase.from("performance_summary").select("*");
  return (data as PerformanceSummary[]) ?? [];
}

export const revalidate = 30;

export default async function DashboardPage() {
  const [botStatus, signals, performance] = await Promise.all([
    getBotStatus(),
    getRecentSignals(),
    getPerformance(),
  ]);

  const totalPnl = performance.reduce((sum, p) => sum + p.total_pnl_usd, 0);
  const totalTrades = performance.reduce((sum, p) => sum + p.total_trades, 0);
  const totalWins = performance.reduce((sum, p) => sum + p.winning_trades, 0);
  const winRate = totalTrades > 0 ? totalWins / totalTrades : 0;
  const openSignals = signals.filter((s) => s.status === "open").length;

  return (
    <main className="min-h-screen p-6">
      {/* Top Stats Strip */}
      <div className="mb-8 flex flex-wrap items-center gap-4 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
        <StatusBadge status={botStatus.status} />
        <ModeBadge mode={botStatus.trade_mode} />
        {botStatus.last_run && (
          <Stat label="Last Run" value={new Date(botStatus.last_run).toLocaleTimeString()} />
        )}
        <Stat label="Signals Today" value={signals.length.toString()} />
        <Stat label="Open Trades" value={openSignals.toString()} />
        <Stat
          label="Cumulative P&L"
          value={`$${totalPnl.toFixed(2)}`}
          color={totalPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)"}
        />
        <Stat label="Win Rate" value={`${(winRate * 100).toFixed(1)}%`} />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <SignalFeed signals={signals} />
        </div>
        <div className="space-y-6 lg:col-span-2">
          <PnlChart />
          <PerformanceStats performance={performance} />
        </div>
      </div>
    </main>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: "bg-green-500/20 text-green-400",
    idle: "bg-gray-500/20 text-gray-400",
    error: "bg-red-500/20 text-red-400",
    stopped: "bg-gray-500/20 text-gray-500",
  };

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${colors[status] ?? colors.idle}`}>
      {status}
    </span>
  );
}

function ModeBadge({ mode }: { mode: string }) {
  const isLive = mode === "live";
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${
        isLive ? "animate-pulse bg-amber-500/20 text-amber-400" : "bg-gray-500/20 text-gray-400"
      }`}
    >
      {mode}
    </span>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="text-center">
      <div className="text-xs uppercase text-[var(--text-secondary)]">{label}</div>
      <div className="text-sm font-bold" style={color ? { color } : undefined}>
        {value}
      </div>
    </div>
  );
}
