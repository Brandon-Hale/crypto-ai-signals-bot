"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { EquitySnapshot } from "@/lib/types";

interface PnlChartProps {
  data?: EquitySnapshot[];
}

export function PnlChart({ data = [] }: PnlChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
        <h2 className="mb-2 text-lg font-bold">P&L Chart</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          No equity data yet. Start the bot to begin tracking.
        </p>
      </div>
    );
  }

  const chartData = data.map((d) => ({
    time: new Date(d.snapshotted_at).toLocaleDateString(),
    equity: d.equity_usd,
    openPnl: d.open_pnl,
  }));

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <h2 className="mb-4 text-lg font-bold">Cumulative P&L</h2>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
          <XAxis dataKey="time" stroke="#8888a0" fontSize={10} />
          <YAxis stroke="#8888a0" fontSize={10} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1a1a2e",
              border: "1px solid #2a2a3e",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke="#00c853"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
