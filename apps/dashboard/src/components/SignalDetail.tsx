import type { Signal } from "@/lib/types";

export function SignalDetail({ signal }: { signal: Signal }) {
  return (
    <div className="mt-1 rounded-b-lg border border-t-0 border-[var(--border)] bg-[var(--bg-secondary)] p-4 text-sm">
      <h3 className="mb-2 font-bold text-[var(--text-primary)]">AI Reasoning</h3>
      <p className="mb-4 whitespace-pre-wrap text-[var(--text-secondary)]">
        {signal.reasoning}
      </p>

      {signal.news_headlines && signal.news_headlines.length > 0 && (
        <div className="mb-4">
          <h4 className="mb-1 font-semibold text-[var(--text-primary)]">News Headlines</h4>
          <ul className="space-y-1 text-xs text-[var(--text-secondary)]">
            {signal.news_headlines.map((h, i) => (
              <li key={i}>
                [{h.source}] {h.title}
              </li>
            ))}
          </ul>
        </div>
      )}

      {signal.indicators && (
        <div>
          <h4 className="mb-1 font-semibold text-[var(--text-primary)]">Indicators at Signal Time</h4>
          <div className="grid grid-cols-3 gap-2 text-xs text-[var(--text-secondary)]">
            {Object.entries(signal.indicators).map(([key, val]) => (
              <div key={key}>
                <span className="text-[var(--text-primary)]">{key}:</span>{" "}
                {typeof val === "number" ? val.toFixed(4) : val}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
