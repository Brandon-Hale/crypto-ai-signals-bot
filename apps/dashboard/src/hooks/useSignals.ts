"use client";

import { useEffect, useState } from "react";
import type { Signal } from "@/lib/types";

export function useSignals(limit: number = 20) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSignals() {
      try {
        const res = await fetch(`/api/signals?limit=${limit}`);
        if (res.ok) {
          const data: Signal[] = await res.json();
          setSignals(data);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchSignals();
    const interval = setInterval(fetchSignals, 30000);
    return () => clearInterval(interval);
  }, [limit]);

  return { signals, loading };
}
