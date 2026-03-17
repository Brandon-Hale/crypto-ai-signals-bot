"use client";

import { useState } from "react";
import type { Signal } from "@/lib/types";
import { SignalDetail } from "./SignalDetail";

const strategyColors: Record<string, string> = {
  news_sentiment: "bg-blue-500/20 text-blue-400",
  technical_confluence: "bg-purple-500/20 text-purple-400",
  volume_spike: "bg-orange-500/20 text-orange-400",
};

const strategyLabels: Record<string, string> = {
  news_sentiment: "News",
  technical_confluence: "Technical",
  volume_spike: "Volume",
};

export function SignalFeed({ signals }: { signals: Signal[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold text-[var(--text-primary)]">Recent Signals</h2>
      {signals.length === 0 && (
        <p className="text-sm text-[var(--text-secondary)]">No signals yet.</p>
      )}
      {signals.map((signal) => (
        <div key={signal.id}>
          <button
            onClick={() => setExpandedId(expandedId === signal.id ? null : signal.id)}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4 text-left transition-colors hover:border-[var(--text-secondary)]"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`rounded px-2 py-0.5 text-xs font-bold ${strategyColors[signal.strategy]}`}>
                  {strategyLabels[signal.strategy]}
                </span>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-bold ${
                    signal.direction === "LONG"
                      ? "bg-green-500/20 text-green-400"
                      : "bg-red-500/20 text-red-400"
                  }`}
                >
                  {signal.direction}
                </span>
                <span className="text-sm font-semibold">{signal.pair_id}</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
                <span>Conf: {(signal.confidence * 100).toFixed(0)}%</span>
                <span>R:R {signal.risk_reward.toFixed(1)}</span>
                <span>{signal.timeframe}</span>
                <StatusPill status={signal.status} />
              </div>
            </div>
            <div className="mt-2 flex gap-6 text-xs text-[var(--text-secondary)]">
              <span>Entry: ${signal.entry_price.toFixed(2)}</span>
              <span>Target: ${signal.target_price.toFixed(2)}</span>
              <span>Stop: ${signal.stop_price.toFixed(2)}</span>
            </div>
          </button>
          {expandedId === signal.id && <SignalDetail signal={signal} />}
        </div>
      ))}
    </div>
  );
}

function StatusPill({ status }: { status: Signal["status"] }) {
  const colors: Record<string, string> = {
    open: "bg-blue-500/20 text-blue-400",
    won: "bg-green-500/20 text-green-400",
    lost: "bg-red-500/20 text-red-400",
    stopped: "bg-red-500/20 text-red-300",
    expired: "bg-gray-500/20 text-gray-400",
    cancelled: "bg-gray-500/20 text-gray-500",
  };

  return (
    <span className={`rounded px-2 py-0.5 text-xs font-bold ${colors[status]}`}>
      {status}
    </span>
  );
}
