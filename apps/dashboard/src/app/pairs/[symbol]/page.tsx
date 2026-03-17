import { supabase } from "@/lib/supabase";
import type { Signal, Trade } from "@/lib/types";

interface PairPageProps {
  params: Promise<{ symbol: string }>;
}

export default async function PairPage({ params }: PairPageProps) {
  const { symbol } = await params;
  const decodedSymbol = decodeURIComponent(symbol);

  // Fetch pair info
  const { data: pairs } = await supabase
    .from("pairs")
    .select("*")
    .eq("symbol", decodedSymbol)
    .limit(1);

  const pair = pairs?.[0];
  if (!pair) {
    return (
      <main className="p-6">
        <h1 className="text-xl font-bold">Pair not found: {decodedSymbol}</h1>
      </main>
    );
  }

  // Fetch signals and trades for this pair
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
    <main className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{decodedSymbol}</h1>
        <div className="mt-2 flex gap-6 text-sm text-[var(--text-secondary)]">
          <span>Category: {pair.category}</span>
          <span>Price: ${pair.current_price ?? "—"}</span>
          <span>24h Vol: ${pair.volume_24h ? Number(pair.volume_24h).toLocaleString() : "—"}</span>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-4 gap-4">
        <StatCard label="Total Signals" value={pairSignals.length.toString()} />
        <StatCard label="Total Trades" value={pairTrades.length.toString()} />
        <StatCard
          label="Win Rate"
          value={`${(winRate * 100).toFixed(1)}%`}
        />
        <StatCard
          label="P&L"
          value={`$${totalPnl.toFixed(2)}`}
          color={totalPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)"}
        />
      </div>

      <div className="space-y-6">
        <section>
          <h2 className="mb-3 text-lg font-bold">Signal History</h2>
          {pairSignals.length === 0 && (
            <p className="text-sm text-[var(--text-secondary)]">No signals for this pair.</p>
          )}
          <div className="space-y-2">
            {pairSignals.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded border border-[var(--border)] bg-[var(--bg-card)] p-3 text-sm"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-bold ${
                      s.direction === "LONG"
                        ? "bg-green-500/20 text-green-400"
                        : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {s.direction}
                  </span>
                  <span>{s.strategy}</span>
                  <span className="text-[var(--text-secondary)]">{s.timeframe}</span>
                </div>
                <div className="flex gap-4 text-xs text-[var(--text-secondary)]">
                  <span>Conf: {(s.confidence * 100).toFixed(0)}%</span>
                  <span>Status: {s.status}</span>
                  <span>{new Date(s.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center">
      <div className="text-xs uppercase text-[var(--text-secondary)]">{label}</div>
      <div className="mt-1 text-xl font-bold" style={color ? { color } : undefined}>
        {value}
      </div>
    </div>
  );
}
