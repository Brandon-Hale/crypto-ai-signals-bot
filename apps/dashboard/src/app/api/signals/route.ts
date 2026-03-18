import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
const VALID_STATUSES = ["open", "won", "lost", "stopped", "expired", "cancelled"];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = Math.max(1, Math.min(100, parseInt(searchParams.get("limit") ?? "20", 10) || 20));
  const status = searchParams.get("status");

  // Validate status parameter
  if (status && status !== "all" && !VALID_STATUSES.includes(status)) {
    return NextResponse.json(
      { error: `Invalid status. Must be one of: all, ${VALID_STATUSES.join(", ")}` },
      { status: 400 },
    );
  }

  let query = supabase
    .from("signals")
    .select("*, pairs(symbol), trades(size_usd, pnl_usd, pnl_pct, exit_reason, status)")
    .order("created_at", { ascending: false })
    .limit(limit);

  if (status && status !== "all") {
    query = query.eq("status", status);
  }

  const { data, error } = await query;

  if (error) {
    return NextResponse.json({ error: "Failed to fetch signals" }, { status: 500 });
  }

  // Flatten the joined pair symbol onto each signal
  const signals = (data ?? []).map((row) => ({
    ...row,
    pair_symbol: (row.pairs as { symbol: string } | null)?.symbol ?? "Unknown",
  }));

  return NextResponse.json(signals);
}
