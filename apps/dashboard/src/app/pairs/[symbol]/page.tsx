import { supabase } from "@/lib/supabase";
import type { Signal, Trade } from "@/lib/types";

interface PairPageProps {
  params: Promise<{ symbol: string }>;
}

export default async function PairPage({ params }: PairPageProps) {
  const { symbol } = await params;
  const decodedSymbol = decodeURIComponent(symbol);

  const { data: pairs } = await supabase
    .from("pairs")
    .select("*")
    .eq("symbol", decodedSymbol)
    .limit(1);

  const pair = pairs?.[0];
  if (!pair) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6">
        <p className="text-xs text-[var(--text-muted)]">pair not found: {decodedSymbol}</p>
      </main>
    );
  }

  const [{ data: signals }, { data: trades }] = await Promise.all([
    supabase
      .from("signals")
      .select("*")
      .eq("pair_id", pair.id)
      .order("created_at", { ascending: false })
      .limit(50),
    supabase
      .from("trades")
      .select("*")
      .eq("pair_id", pair.id)
      .order("opened_at", { ascending: false })
      .limit(50),
  ]);

  const pairSignals = (signals as Signal[]) ?? [];
  const pairTrades = (trades as Trade[]) ?? [];

  const totalPnl = pairTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
  const closedTrades = pairTrades.filter((t) => t.status === "closed");
  const wins = closedTrades.filter((t) => (t.pnl_usd ?? 0) > 0).length;
  const winRate = closedTrades.length > 0 ? wins / closedTrades.length : 0;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 border-b border-[var(--border)] pb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-bold">{decodedSymbol}</h1>
          <span className="text-xs text-[var(--text-muted)]">{pair.category}</span>
        </div>
        <div className="mt-1 flex gap-4 text-xs text-[var(--text-muted)]">
          <span>
            price <span className="text-[var(--text-secondary)]">${pair.current_price ?? "—"}</span>
          </span>
          <span>
            24h vol{" "}
            <span className="text-[var(--text-secondary)]">
              ${pair.volume_24h ? Number(pair.volume_24h).toLocaleString() : "—"}
            </span>
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-4 gap-px overflow-hidden rounded border border-[var(--border)] bg-[var(--border)]">
        <StatCell label="signals" value={pairSignals.length.toString()} />
        <StatCell label="trades" value={pairTrades.length.toString()} />
        <StatCell
          label="win rate"
          value={`${(winRate * 100).toFixed(1)}%`}
          valueColor={winRate >= 0.5 ? "var(--accent-green)" : "var(--accent-red)"}
        />
        <StatCell
          label="p&l"
          value={`${totalPnl >= 0 ? "+" : ""}$${totalPnl.toFixed(2)}`}
          valueColor={totalPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)"}
        />
      </div>

      {/* Signal history */}
      <div>
        <div className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          Signal History
        </div>

        {pairSignals.length === 0 && (
          <p className="text-xs text-[var(--text-muted)]">no signals for this pair</p>
        )}

        <div className="space-y-px">
          {pairSignals.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between rounded border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-xs"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-12 font-bold ${
                    s.direction === "LONG" ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"
                  }`}
                >
                  {s.direction}
                </span>
                <span className="text-[var(--text-secondary)]">{s.strategy.replace(/_/g, " ")}</span>
                <span className="text-[var(--text-muted)]">{s.timeframe}</span>
              </div>
              <div className="flex gap-3 text-[11px] text-[var(--text-muted)]">
                <span>
                  conf <span className="text-[var(--text-secondary)]">{(s.confidence * 100).toFixed(0)}%</span>
                </span>
                <span className={
                  s.status === "won" ? "font-bold text-[var(--accent-green)]"
                    : s.status === "lost" || s.status === "stopped" ? "font-bold text-[var(--accent-red)]"
                      : "text-[var(--text-muted)]"
                }>
                  {s.status}
                </span>
                <span>{new Date(s.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
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
