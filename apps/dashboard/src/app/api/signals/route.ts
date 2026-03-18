import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get("limit") ?? "20", 10);
  const status = searchParams.get("status"); // e.g. "open", "won", "lost", "stopped", "expired"

  let query = supabase
    .from("signals")
    .select("*, pairs(symbol)")
    .order("created_at", { ascending: false })
    .limit(limit);

  if (status && status !== "all") {
    query = query.eq("status", status);
  }

  const { data, error } = await query;

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Flatten the joined pair symbol onto each signal
  const signals = (data ?? []).map((row) => ({
    ...row,
    pair_symbol: (row.pairs as { symbol: string } | null)?.symbol ?? "Unknown",
  }));

  return NextResponse.json(signals);
}
