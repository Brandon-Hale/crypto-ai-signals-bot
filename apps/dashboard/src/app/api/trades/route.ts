import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
const VALID_STATUSES = ["open", "closed", "cancelled"];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status");
  const limit = Math.max(1, Math.min(100, parseInt(searchParams.get("limit") ?? "50", 10) || 50));

  // Validate status parameter
  if (status && !VALID_STATUSES.includes(status)) {
    return NextResponse.json(
      { error: `Invalid status. Must be one of: ${VALID_STATUSES.join(", ")}` },
      { status: 400 },
    );
  }

  let query = supabase
    .from("trades")
    .select("*")
    .order("opened_at", { ascending: false })
    .limit(limit);

  if (status) {
    query = query.eq("status", status);
  }

  const { data, error } = await query;

  if (error) {
    return NextResponse.json({ error: "Failed to fetch trades" }, { status: 500 });
  }

  return NextResponse.json(data ?? []);
}
