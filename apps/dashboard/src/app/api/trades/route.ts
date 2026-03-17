import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import type { Trade } from "@/lib/types";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status");
  const limit = parseInt(searchParams.get("limit") ?? "50", 10);

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
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json((data as Trade[]) ?? []);
}
