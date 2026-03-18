import type { Signal } from "@/lib/types";

export function SignalDetail({ signal }: { signal: Signal }) {
  return (
    <div className="rounded-b border border-t-0 border-[var(--border-focus)] bg-[var(--bg-card)] px-3 py-3 text-xs">
      {/* Reasoning */}
      <div className="mb-3">
        <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
          reasoning
        </div>
        <p className="whitespace-pre-wrap leading-relaxed text-[var(--text-secondary)]">
          {signal.reasoning}
        </p>
      </div>

      {/* News headlines */}
      {signal.news_headlines && signal.news_headlines.length > 0 && (
        <div className="mb-3">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
            headlines
          </div>
          <div className="space-y-0.5">
            {signal.news_headlines.map((h, i) => (
              <div key={i} className="text-[var(--text-secondary)]">
                <span className="text-[var(--text-muted)]">[{h.source}]</span> {h.title}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Indicators */}
      {signal.indicators && (
        <div>
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
            indicators
          </div>
          <div className="grid grid-cols-4 gap-x-4 gap-y-0.5">
            {Object.entries(signal.indicators).map(([key, val]) => (
              <div key={key} className="text-[var(--text-muted)]">
                {key.replace(/_/g, " ")}{" "}
                <span className="text-[var(--text-secondary)]">
                  {typeof val === "number" ? val.toFixed(4) : val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
