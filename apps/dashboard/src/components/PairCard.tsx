import type { Pair } from "@/lib/types";
import Link from "next/link";

export function PairCard({ pair }: { pair: Pair }) {
  const changeColor =
    pair.price_change_24h && pair.price_change_24h >= 0
      ? "text-green-400"
      : "text-red-400";

  return (
    <Link
      href={`/pairs/${encodeURIComponent(pair.symbol)}`}
      className="block rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-3 transition-colors hover:border-[var(--text-secondary)]"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold">{pair.symbol}</span>
        <span className="text-xs text-[var(--text-secondary)]">{pair.category}</span>
      </div>
      <div className="mt-1 flex items-baseline gap-3">
        <span className="text-lg font-bold">
          ${pair.current_price?.toFixed(2) ?? "—"}
        </span>
        <span className={`text-xs font-semibold ${changeColor}`}>
          {pair.price_change_24h ? `${pair.price_change_24h >= 0 ? "+" : ""}${pair.price_change_24h.toFixed(2)}%` : "—"}
        </span>
      </div>
    </Link>
  );
}
