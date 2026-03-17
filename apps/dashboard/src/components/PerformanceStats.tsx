import type { PerformanceSummary } from "@/lib/types";

interface PerformanceStatsProps {
  performance: PerformanceSummary[];
}

export function PerformanceStats({ performance }: PerformanceStatsProps) {
  if (performance.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
        <h2 className="mb-2 text-lg font-bold">Strategy Performance</h2>
        <p className="text-sm text-[var(--text-secondary)]">No performance data yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <h2 className="mb-4 text-lg font-bold">Strategy Performance</h2>
      <div className="space-y-3">
        {performance.map((p) => (
          <div
            key={p.id}
            className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-3"
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold capitalize">
                {p.strategy.replace("_", " ")}
              </span>
              <span
                className="text-sm font-bold"
                style={{
                  color:
                    p.total_pnl_usd >= 0
                      ? "var(--accent-green)"
                      : "var(--accent-red)",
                }}
              >
                ${p.total_pnl_usd.toFixed(2)}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs text-[var(--text-secondary)]">
              <div>
                Win Rate:{" "}
                <span className="text-[var(--text-primary)]">
                  {p.win_rate ? (p.win_rate * 100).toFixed(1) : "0"}%
                </span>
              </div>
              <div>
                Trades:{" "}
                <span className="text-[var(--text-primary)]">{p.total_trades}</span>
              </div>
              <div>
                Avg R:R:{" "}
                <span className="text-[var(--text-primary)]">
                  {p.avg_rr?.toFixed(2) ?? "—"}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
