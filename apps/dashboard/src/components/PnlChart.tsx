"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { EquitySnapshot } from "@/lib/types";

interface PnlChartProps {
  data?: EquitySnapshot[];
}

export function PnlChart({ data = [] }: PnlChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
        <div className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          P&L
        </div>
        <div className="flex h-40 items-center justify-center text-xs text-[var(--text-muted)]">
          waiting for data...
        </div>
      </div>
    );
  }

  const baseline = data[0]?.equity_usd ?? 10000;

  const chartData = data.map((d) => {
    const pnl = d.equity_usd - baseline;
    return {
      time: new Date(d.snapshotted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      pnl,
    };
  });

  const latestPnl = chartData[chartData.length - 1]?.pnl ?? 0;
  const pnlPct = baseline > 0 ? (latestPnl / baseline) * 100 : 0;

  const allPnls = chartData.map((d) => d.pnl);
  const minPnl = Math.min(...allPnls);
  const maxPnl = Math.max(...allPnls);
  const padding = Math.max(Math.abs(maxPnl), Math.abs(minPnl)) * 0.1 || 10;

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          P&L
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`font-bold ${latestPnl >= 0 ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}`}
          >
            {latestPnl >= 0 ? "+" : ""}${latestPnl.toFixed(2)}
          </span>
          <span className="text-[var(--text-muted)]">
            ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%)
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="pnlGradPos" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4ade80" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="pnlGradNeg" x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor="#f87171" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#f87171" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1a1a1a"
            vertical={false}
          />
          <XAxis
            dataKey="time"
            stroke="#444"
            fontSize={9}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#444"
            fontSize={9}
            tickLine={false}
            axisLine={false}
            domain={[minPnl - padding, maxPnl + padding]}
            tickFormatter={(v: number) => `${v >= 0 ? "+" : ""}$${v.toFixed(0)}`}
          />
          <ReferenceLine y={0} stroke="#333" strokeDasharray="3 3" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#161616",
              border: "1px solid #262626",
              borderRadius: 4,
              fontSize: 11,
              fontFamily: "JetBrains Mono, monospace",
              color: "#c8c8c8",
            }}
            formatter={(value: number) => [
              `${value >= 0 ? "+" : ""}$${value.toFixed(2)}`,
              "P&L",
            ]}
          />
          <Area
            type="monotone"
            dataKey="pnl"
            stroke={latestPnl >= 0 ? "#4ade80" : "#f87171"}
            strokeWidth={1.5}
            fill={latestPnl >= 0 ? "url(#pnlGradPos)" : "url(#pnlGradNeg)"}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
