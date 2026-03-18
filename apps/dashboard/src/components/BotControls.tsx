"use client";

import { useState } from "react";
import type { BotStatus } from "@/lib/types";

interface BotControlsProps {
  initialStatus: BotStatus["status"];
}

export function BotControls({ initialStatus }: BotControlsProps) {
  const [status, setStatus] = useState(initialStatus);
  const [loading, setLoading] = useState(false);

  const isOnline = status !== "stopped";
  const isPaused = status === "paused";
  const isRunning = status === "running" || status === "idle";

  async function sendCommand(action: "pause" | "resume") {
    setLoading(true);
    try {
      const res = await fetch("/api/bot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        setStatus(action === "pause" ? "paused" : "idle");
      }
    } finally {
      setLoading(false);
    }
  }

  if (!isOnline) {
    return (
      <span className="text-[11px] text-[var(--text-muted)]">
        offline
      </span>
    );
  }

  return (
    <button
      onClick={() => sendCommand(isPaused ? "resume" : "pause")}
      disabled={loading}
      className={`rounded border px-2.5 py-1 text-[11px] font-bold transition-colors ${
        isRunning
          ? "border-[var(--accent-red)]/30 text-[var(--accent-red)] hover:bg-[var(--accent-red)]/10"
          : "border-[var(--accent-green)]/30 text-[var(--accent-green)] hover:bg-[var(--accent-green)]/10"
      } disabled:opacity-40`}
    >
      {loading ? "..." : isPaused ? "resume" : "pause"}
    </button>
  );
}
