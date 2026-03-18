import type { PerformanceSummary } from "@/lib/types";

interface PerformanceStatsProps {
  performance: PerformanceSummary[];
}

const strategyLabel: Record<string, string> = {
  news_sentiment: "news",
  technical_confluence: "technical",
  volume_spike: "volume",
};

export function PerformanceStats({ performance }: PerformanceStatsProps) {
  if (performance.length === 0) {
    return (
      <div className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
        <div className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          Strategy Performance
        </div>
        <div className="text-xs text-[var(--text-muted)]">no data yet</div>
      </div>
    );
  }

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
      <div className="mb-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
        Strategy Performance
      </div>

      {/* Header */}
      <div className="mb-1 grid grid-cols-5 gap-2 text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
        <div>strategy</div>
        <div className="text-right">p&l</div>
        <div className="text-right">win%</div>
        <div className="text-right">trades</div>
        <div className="text-right">w/l</div>
      </div>

      <div className="space-y-0.5">
        {performance.map((p) => {
          const wr = p.win_rate ? p.win_rate * 100 : 0;
          return (
            <div
              key={p.id}
              className="grid grid-cols-5 gap-2 rounded px-1 py-1.5 text-xs transition-colors hover:bg-[var(--bg-card)]"
            >
              <div className="font-semibold text-[var(--text-primary)]">
                {strategyLabel[p.strategy] ?? p.strategy}
              </div>
              <div
                className="text-right font-bold"
                style={{
                  color: p.total_pnl_usd >= 0 ? "var(--accent-green)" : "var(--accent-red)",
                }}
              >
                {p.total_pnl_usd >= 0 ? "+" : ""}${p.total_pnl_usd.toFixed(2)}
              </div>
              <div
                className="text-right"
                style={{
                  color: wr >= 50 ? "var(--accent-green)" : "var(--accent-red)",
                }}
              >
                {wr.toFixed(1)}%
              </div>
              <div className="text-right text-[var(--text-secondary)]">{p.total_trades}</div>
              <div className="text-right text-[var(--text-muted)]">
                <span className="text-[var(--accent-green)]">{p.winning_trades}</span>
                /
                <span className="text-[var(--accent-red)]">{p.losing_trades}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
