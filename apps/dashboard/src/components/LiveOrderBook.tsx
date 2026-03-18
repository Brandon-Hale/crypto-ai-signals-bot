"use client";

interface OrderBookProps {
  bids: Array<{ price: number; amount: number }>;
  asks: Array<{ price: number; amount: number }>;
}

export function LiveOrderBook({ bids, asks }: OrderBookProps) {
  const maxBid = Math.max(...bids.slice(0, 10).map((l) => l.amount), 1);
  const maxAsk = Math.max(...asks.slice(0, 10).map((l) => l.amount), 1);

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
      <div className="mb-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
        Order Book
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[var(--accent-green)]">
            bids
          </div>
          {bids.slice(0, 10).map((level, i) => (
            <div key={i} className="relative flex justify-between py-px text-[11px]">
              <div
                className="absolute inset-y-0 left-0 bg-[var(--accent-green)] opacity-[0.06]"
                style={{ width: `${(level.amount / maxBid) * 100}%` }}
              />
              <span className="relative text-[var(--accent-green)]">${level.price.toFixed(2)}</span>
              <span className="relative text-[var(--text-muted)]">{level.amount.toFixed(4)}</span>
            </div>
          ))}
        </div>
        <div>
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[var(--accent-red)]">
            asks
          </div>
          {asks.slice(0, 10).map((level, i) => (
            <div key={i} className="relative flex justify-between py-px text-[11px]">
              <div
                className="absolute inset-y-0 right-0 bg-[var(--accent-red)] opacity-[0.06]"
                style={{ width: `${(level.amount / maxAsk) * 100}%` }}
              />
              <span className="relative text-[var(--accent-red)]">${level.price.toFixed(2)}</span>
              <span className="relative text-[var(--text-muted)]">{level.amount.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
