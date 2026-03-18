"use client";

import { useState, useEffect, useCallback } from "react";
import type { Signal } from "@/lib/types";
import { SignalDetail } from "./SignalDetail";

type SignalWithSymbol = Signal & { pair_symbol?: string };

type FilterStatus = "all" | "open" | "won" | "lost" | "stopped" | "expired";

const filters: { value: FilterStatus; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
  { value: "stopped", label: "Stopped" },
  { value: "expired", label: "Expired" },
];

const strategyTag: Record<string, { label: string; color: string }> = {
  news_sentiment: { label: "NEWS", color: "text-[var(--accent-blue)]" },
  technical_confluence: { label: "TECH", color: "text-[var(--accent-purple)]" },
  volume_spike: { label: "VOL", color: "text-[var(--accent-orange)]" },
};

export function SignalFeed({ signals: initialSignals }: { signals: SignalWithSymbol[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterStatus>("all");
  const [signals, setSignals] = useState<SignalWithSymbol[]>(initialSignals);
  const [loading, setLoading] = useState(false);

  // Keep "all" in sync with realtime updates from parent
  const [realtimeSignals, setRealtimeSignals] = useState<SignalWithSymbol[]>(initialSignals);
  useEffect(() => {
    setRealtimeSignals(initialSignals);
    if (activeFilter === "all") {
      setSignals(initialSignals);
    }
  }, [initialSignals, activeFilter]);

  const fetchSignals = useCallback(async (status: FilterStatus) => {
    if (status === "all") {
      setSignals(realtimeSignals);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/signals?status=${status}&limit=50`);
      if (res.ok) {
        const data = await res.json();
        setSignals(data);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [realtimeSignals]);

  const handleFilterChange = (filter: FilterStatus) => {
    setActiveFilter(filter);
    setExpandedId(null);
    fetchSignals(filter);
  };

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          Signal Feed
        </h2>
        <span className="text-[10px] text-[var(--text-muted)]">
          {signals.length} signal{signals.length !== 1 ? "s" : ""}
          {activeFilter !== "all" && ` (${activeFilter})`}
        </span>
      </div>

      {/* Filter tabs */}
      <div className="mb-3 flex gap-1 overflow-x-auto">
        {filters.map((f) => {
          const isActive = activeFilter === f.value;
          return (
            <button
              key={f.value}
              onClick={() => handleFilterChange(f.value)}
              className={`rounded px-2 py-1 text-[11px] font-medium transition-colors ${
                isActive
                  ? "bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-focus)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent"
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {loading && (
        <div className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-4 text-center text-xs text-[var(--text-muted)]">
          loading...
        </div>
      )}

      {!loading && signals.length === 0 && (
        <div className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-8 text-center text-xs text-[var(--text-muted)]">
          {activeFilter === "all" ? "waiting for signals..." : `no ${activeFilter} signals`}
        </div>
      )}

      {!loading && (
        <div className="space-y-1.5">
          {signals.map((signal) => {
            const tag = strategyTag[signal.strategy] ?? { label: "???", color: "text-[var(--text-secondary)]" };
            const isLong = signal.direction === "LONG";
            const isExpanded = expandedId === signal.id;
            const age = getRelativeTime(signal.created_at);

            return (
              <div key={signal.id}>
                <button
                  onClick={() => setExpandedId(isExpanded ? null : signal.id)}
                  className={`w-full border bg-[var(--bg-secondary)] px-3 py-3 text-left transition-colors hover:bg-[var(--bg-card)] ${
                    isExpanded
                      ? "rounded-t border-[var(--border-focus)]"
                      : "rounded border-[var(--border)]"
                  }`}
                >
                  {/* Row 1: pair + direction + age */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-sm font-bold ${
                          isLong ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"
                        }`}
                      >
                        {signal.direction}
                      </span>
                      <span className="text-sm font-semibold text-[var(--text-primary)]">
                        {signal.pair_symbol ?? signal.pair_id.slice(0, 8)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusTag status={signal.status} />
                      <span className="text-[11px] text-[var(--text-muted)]">{age}</span>
                    </div>
                  </div>

                  {/* Row 2: strategy + timeframe + metrics */}
                  <div className="mt-1.5 flex items-center gap-3 text-[11px]">
                    <span className={`font-bold ${tag.color}`}>{tag.label}</span>
                    <span className="text-[var(--text-muted)]">{signal.timeframe}</span>
                    <span className="text-[var(--text-muted)]">&middot;</span>
                    <span className="text-[var(--text-secondary)]">
                      conf <span className="text-[var(--text-primary)]">{(signal.confidence * 100).toFixed(0)}%</span>
                    </span>
                    <span className="text-[var(--text-secondary)]">
                      r:r <span className="text-[var(--text-primary)]">{signal.risk_reward.toFixed(1)}</span>
                    </span>
                  </div>

                  {/* Row 3: prices */}
                  <div className="mt-1.5 flex gap-4 text-[11px] text-[var(--text-muted)]">
                    <span>
                      entry <span className="text-[var(--text-secondary)]">${formatPrice(signal.entry_price)}</span>
                    </span>
                    <span>
                      tp <span className="text-[var(--accent-green)]">${formatPrice(signal.target_price)}</span>
                    </span>
                    <span>
                      sl <span className="text-[var(--accent-red)]">${formatPrice(signal.stop_price)}</span>
                    </span>
                  </div>
                </button>
                {isExpanded && <SignalDetail signal={signal} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatusTag({ status }: { status: Signal["status"] }) {
  const styles: Record<string, string> = {
    open: "bg-[var(--accent-blue)]/10 text-[var(--accent-blue)]",
    won: "bg-[var(--accent-green)]/10 text-[var(--accent-green)]",
    lost: "bg-[var(--accent-red)]/10 text-[var(--accent-red)]",
    stopped: "bg-[var(--accent-red)]/10 text-[var(--accent-red)]",
    expired: "bg-[var(--text-muted)]/10 text-[var(--text-muted)]",
    cancelled: "bg-[var(--text-muted)]/10 text-[var(--text-muted)]",
  };

  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${styles[status] ?? "text-[var(--text-muted)]"}`}>
      {status}
    </span>
  );
}

function formatPrice(price: number): string {
  if (price >= 1000) return price.toFixed(2);
  if (price >= 1) return price.toFixed(4);
  return price.toFixed(6);
}

function getRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}
