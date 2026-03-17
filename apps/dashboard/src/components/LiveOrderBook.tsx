"use client";

interface OrderBookProps {
  bids: Array<{ price: number; amount: number }>;
  asks: Array<{ price: number; amount: number }>;
}

export function LiveOrderBook({ bids, asks }: OrderBookProps) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <h3 className="mb-3 text-sm font-bold">Order Book</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="mb-1 text-xs font-semibold text-green-400">Bids</div>
          {bids.slice(0, 10).map((level, i) => (
            <div key={i} className="flex justify-between text-xs">
              <span className="text-green-400">${level.price.toFixed(2)}</span>
              <span className="text-[var(--text-secondary)]">{level.amount.toFixed(4)}</span>
            </div>
          ))}
        </div>
        <div>
          <div className="mb-1 text-xs font-semibold text-red-400">Asks</div>
          {asks.slice(0, 10).map((level, i) => (
            <div key={i} className="flex justify-between text-xs">
              <span className="text-red-400">${level.price.toFixed(2)}</span>
              <span className="text-[var(--text-secondary)]">{level.amount.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
