import type { Pair } from "@/lib/types";
import Link from "next/link";

export function PairCard({ pair }: { pair: Pair }) {
  const change = pair.price_change_24h;
  const isPositive = change !== null && change >= 0;

  return (
    <Link
      href={`/pairs/${encodeURIComponent(pair.symbol)}`}
      className="block rounded border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2.5 transition-colors hover:border-[var(--border-focus)] hover:bg-[var(--bg-card)]"
    >
      <div className="flex items-center justify-between text-xs">
        <span className="font-bold text-[var(--text-primary)]">{pair.symbol}</span>
        <span className="text-[var(--text-muted)]">{pair.category}</span>
      </div>
      <div className="mt-1 flex items-baseline justify-between">
        <span className="text-sm font-bold">
          ${pair.current_price?.toFixed(2) ?? "—"}
        </span>
        <span
          className={`text-xs font-semibold ${isPositive ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}`}
        >
          {change !== null
            ? `${isPositive ? "+" : ""}${change.toFixed(2)}%`
            : "—"}
        </span>
      </div>
    </Link>
  );
}
