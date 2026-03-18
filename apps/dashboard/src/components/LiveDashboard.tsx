"use client";

import { useEffect, useState } from "react";
import { supabaseBrowser } from "@/lib/supabase-browser";
import type { Signal, PerformanceSummary, EquitySnapshot, BotStatus } from "@/lib/types";
import { SignalFeed } from "./SignalFeed";
import { PnlChart } from "./PnlChart";
import { PerformanceStats } from "./PerformanceStats";
import { BotControls } from "./BotControls";

type SignalWithSymbol = Signal & { pair_symbol: string };

interface LiveDashboardProps {
  initialSignals: SignalWithSymbol[];
  initialPerformance: PerformanceSummary[];
  initialEquity: EquitySnapshot[];
  initialBotStatus: BotStatus;
  initialOpenTrades: number;
  initialSignalsToday: number;
}

export function LiveDashboard({
  initialSignals,
  initialPerformance,
  initialEquity,
  initialBotStatus,
  initialOpenTrades,
  initialSignalsToday,
}: LiveDashboardProps) {
  const [signals, setSignals] = useState<SignalWithSymbol[]>(initialSignals);
  const [performance, setPerformance] = useState<PerformanceSummary[]>(initialPerformance);
  const [equity, setEquity] = useState<EquitySnapshot[]>(initialEquity);
  const [openTrades, setOpenTrades] = useState(initialOpenTrades);
  const [signalsToday, setSignalsToday] = useState(initialSignalsToday);
  const [botStatus, setBotStatus] = useState<BotStatus>(initialBotStatus);

  // Poll bot status from Redis (can't use Realtime for Redis)
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("/api/live");
        if (res.ok) {
          const data = await res.json();
          setBotStatus(data.bot);
        }
      } catch { /* ignore */ }
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // Supabase Realtime subscriptions
  useEffect(() => {
    const channel = supabaseBrowser
      .channel("dashboard-realtime")
      // New signals
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "signals" },
        async (payload) => {
          const newSignal = payload.new as Signal;
          // Fetch the pair symbol
          const { data } = await supabaseBrowser
            .from("pairs")
            .select("symbol")
            .eq("id", newSignal.pair_id)
            .limit(1);
          const symbol = data?.[0]?.symbol ?? "Unknown";

          const withSymbol: SignalWithSymbol = { ...newSignal, pair_symbol: symbol };
          setSignals((prev) => [withSymbol, ...prev].slice(0, 20));

          // Update signals today count
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          if (new Date(newSignal.created_at) >= today) {
            setSignalsToday((prev) => prev + 1);
          }
        },
      )
      // Signal status updates (won/lost/stopped)
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "signals" },
        (payload) => {
          const updated = payload.new as Signal;
          setSignals((prev) =>
            prev.map((s) => (s.id === updated.id ? { ...s, ...updated } : s)),
          );
        },
      )
      // New trades
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "trades" },
        () => {
          setOpenTrades((prev) => prev + 1);
        },
      )
      // Trade updates (closed)
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "trades" },
        (payload) => {
          const updated = payload.new as { status: string };
          if (updated.status === "closed") {
            setOpenTrades((prev) => Math.max(0, prev - 1));
          }
        },
      )
      // Equity snapshots
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "equity_snapshots" },
        (payload) => {
          const snapshot = payload.new as EquitySnapshot;
          setEquity((prev) => [...prev, snapshot].slice(-200));
        },
      )
      // Performance summary updates
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "performance_summary" },
        async () => {
          // Refetch all performance data on any change
          const { data } = await supabaseBrowser
            .from("performance_summary")
            .select("*");
          if (data) {
            setPerformance(data as PerformanceSummary[]);
          }
        },
      )
      .subscribe();

    return () => {
      supabaseBrowser.removeChannel(channel);
    };
  }, []);

  // Derived stats
  const totalPnl = performance.reduce((sum, p) => sum + p.total_pnl_usd, 0);
  const totalTrades = performance.reduce((sum, p) => sum + p.total_trades, 0);
  const totalWins = performance.reduce((sum, p) => sum + p.winning_trades, 0);
  const winRate = totalTrades > 0 ? totalWins / totalTrades : 0;

  const statusIndicator =
    botStatus.status === "running" ? "\u25CF"
    : botStatus.status === "error" ? "\u25CF"
    : botStatus.status === "paused" ? "\u25CF"
    : "\u25CB";

  const statusColor =
    botStatus.status === "running" ? "text-[var(--accent-green)]"
    : botStatus.status === "idle" ? "text-[var(--accent-green)]"
    : botStatus.status === "error" ? "text-[var(--accent-red)]"
    : botStatus.status === "paused" ? "text-[var(--accent-amber)]"
    : "text-[var(--text-muted)]";

  return (
    <main className="px-6 py-6">
      {/* Header */}
      <div className="mb-6 border-b border-[var(--border)] pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-bold tracking-tight text-[var(--text-primary)]">
              sigbot
            </h1>
            <span className="text-[var(--text-muted)]">/</span>
            <span className="text-[var(--text-secondary)]">dashboard</span>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className={statusColor}>
              {statusIndicator} {botStatus.status}
            </span>
            <span className="text-[var(--text-muted)]">|</span>
            <span className={botStatus.trade_mode === "live" ? "text-[var(--accent-amber)]" : "text-[var(--text-secondary)]"}>
              {botStatus.trade_mode}
            </span>
            {botStatus.last_run && (
              <>
                <span className="text-[var(--text-muted)]">|</span>
                <span className="text-[var(--text-secondary)]">
                  last: {new Date(botStatus.last_run).toLocaleTimeString()}
                </span>
              </>
            )}
            <span className="text-[var(--text-muted)]">|</span>
            <BotControls initialStatus={botStatus.status} />
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-5 gap-px overflow-hidden rounded border border-[var(--border)] bg-[var(--border)]">
        <StatCell label="signals today" value={signalsToday.toString()} />
        <StatCell label="open trades" value={openTrades.toString()} />
        <StatCell label="total trades" value={totalTrades.toString()} />
        <StatCell
          label="cumulative p&l"
          value={`${totalPnl >= 0 ? "+" : ""}$${totalPnl.toFixed(2)}`}
          valueColor={totalPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)"}
        />
        <StatCell
          label="win rate"
          value={`${(winRate * 100).toFixed(1)}%`}
          valueColor={winRate >= 0.5 ? "var(--accent-green)" : "var(--accent-red)"}
        />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <SignalFeed signals={signals} />
        </div>
        <div className="space-y-4 lg:col-span-3">
          <PnlChart data={equity} />
          <PerformanceStats performance={performance} />
        </div>
      </div>
    </main>
  );
}

function StatCell({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="bg-[var(--bg-secondary)] px-4 py-3">
      <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">{label}</div>
      <div
        className="mt-0.5 text-sm font-bold"
        style={valueColor ? { color: valueColor } : undefined}
      >
        {value}
      </div>
    </div>
  );
}
