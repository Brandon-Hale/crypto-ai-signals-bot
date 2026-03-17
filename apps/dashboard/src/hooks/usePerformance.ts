"use client";

import { useEffect, useState } from "react";
import type { PerformanceSummary } from "@/lib/types";

export function usePerformance() {
  const [performance, setPerformance] = useState<PerformanceSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPerformance() {
      try {
        const res = await fetch("/api/performance");
        if (res.ok) {
          const data: PerformanceSummary[] = await res.json();
          setPerformance(data);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchPerformance();
    const interval = setInterval(fetchPerformance, 60000);
    return () => clearInterval(interval);
  }, []);

  return { performance, loading };
}
